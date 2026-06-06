import os
import json
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import (
    APIRouter, Depends, HTTPException, status, UploadFile, File,
    BackgroundTasks, WebSocket, WebSocketDisconnect, Query
)
from sqlalchemy.orm import Session
import numpy as np

from backend.database import get_db
from backend.models import User, UserRole, Simulation, SimulationStatus
from backend.schemas import (
    SimulationCreate, SimulationResponse, SimulationUpdate,
    TimeSeriesDataResponse, PolarityReversalResponse, ParameterAdjustmentResponse
)
from backend.auth import get_current_active_user, require_role
from backend.services.simulation_service import (
    ParameterFileParser, SimulationTaskManager
)
from backend.services.monitoring_service import (
    AlertService, ReviewService, SimulationRunner
)
from backend.config import settings

router = APIRouter(prefix="/simulations", tags=["模拟任务"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, simulation_id: int, websocket: WebSocket):
        await websocket.accept()
        if simulation_id not in self.active_connections:
            self.active_connections[simulation_id] = []
        self.active_connections[simulation_id].append(websocket)

    def disconnect(self, simulation_id: int, websocket: WebSocket):
        if simulation_id in self.active_connections:
            self.active_connections[simulation_id].remove(websocket)
            if not self.active_connections[simulation_id]:
                del self.active_connections[simulation_id]

    async def broadcast(self, simulation_id: int, message: Dict[str, Any]):
        if simulation_id in self.active_connections:
            for connection in self.active_connections[simulation_id]:
                await connection.send_json(message)


manager = ConnectionManager()


@router.post("/upload-params")
async def upload_parameters(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    try:
        params = ParameterFileParser.parse_file(file)
        is_valid, errors = ParameterFileParser.validate(params)

        return {
            "filename": file.filename,
            "parameters": params,
            "is_valid": is_valid,
            "errors": errors
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/", response_model=SimulationResponse)
def create_simulation(
    sim_data: SimulationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    task_manager = SimulationTaskManager(db)

    params = sim_data.model_dump()

    if task_manager.check_group_pause():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该课题组任务已被暂停，请联系首席科学家"
        )

    sim = task_manager.create_simulation(
        user=current_user,
        params=params,
        name=sim_data.name,
        description=sim_data.description
    )

    background_tasks.add_task(verify_and_start_simulation, sim.id, db)

    return sim


async def verify_and_start_simulation(simulation_id: int, db: Session):
    task_manager = SimulationTaskManager(db)

    await asyncio.sleep(1)
    success, msg = task_manager.generate_mesh(simulation_id)

    if not success:
        return

    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    task_manager.update_status(simulation_id, SimulationStatus.PENDING_VERIFICATION, progress=25.0)

    await manager.broadcast(simulation_id, {
        "status": "mesh_completed",
        "progress": 25.0,
        "message": "网格生成完成，等待校验"
    })


@router.get("/", response_model=List[SimulationResponse])
def list_simulations(
    status: Optional[SimulationStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Simulation)

    if current_user.role not in [UserRole.ADMIN, UserRole.CHIEF_SCIENTIST]:
        query = query.filter(Simulation.owner_id == current_user.id)

    if status:
        query = query.filter(Simulation.status == status)

    return query.order_by(Simulation.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{simulation_id}", response_model=SimulationResponse)
def get_simulation(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if current_user.role not in [UserRole.ADMIN, UserRole.CHIEF_SCIENTIST] and sim.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return sim


@router.put("/{simulation_id}", response_model=SimulationResponse)
def update_simulation(
    simulation_id: int,
    update_data: SimulationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.CHIEF_SCIENTIST))
):
    task_manager = SimulationTaskManager(db)
    sim = task_manager.update_status(simulation_id, update_data.status, **update_data.model_dump(exclude_unset=True))
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return sim


@router.post("/{simulation_id}/start")
def start_simulation(
    simulation_id: int,
    background_tasks: BackgroundTasks,
    max_iterations: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if current_user.role not in [UserRole.ADMIN, UserRole.CHIEF_SCIENTIST] and sim.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if sim.status not in [SimulationStatus.PENDING_VERIFICATION, SimulationStatus.ERROR, SimulationStatus.ADJUSTING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start simulation from status: {sim.status}"
        )

    task_manager = SimulationTaskManager(db)
    if task_manager.check_group_pause():
        raise HTTPException(
            status_code=403,
            detail="该课题组任务已被暂停，请联系首席科学家"
        )

    background_tasks.add_task(run_simulation_task, simulation_id, max_iterations, db)

    return {
        "message": "Simulation started successfully",
        "simulation_id": simulation_id
    }


async def run_simulation_task(simulation_id: int, max_iterations: Optional[int], db: Session):
    runner = SimulationRunner(db, simulation_id)
    result = runner.run(max_iterations=max_iterations)

    await manager.broadcast(simulation_id, {
        "status": "completed" if result["success"] else "error",
        "result": result
    })


@router.post("/{simulation_id}/step")
def step_simulation(
    simulation_id: int,
    n_steps: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    runner = SimulationRunner(db, simulation_id)
    result = runner.step(n_steps)

    return result


@router.post("/{simulation_id}/verify")
def verify_simulation(
    simulation_id: int,
    approved: bool,
    comments: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.GEOPHYSICIST, UserRole.ADMIN, UserRole.CHIEF_SCIENTIST))
):
    task_manager = SimulationTaskManager(db)
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()

    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if sim.status != SimulationStatus.PENDING_VERIFICATION:
        raise HTTPException(
            status_code=400,
            detail=f"Simulation not in verification status. Current: {sim.status}"
        )

    if approved:
        task_manager.update_status(simulation_id, SimulationStatus.INITIALIZATION, progress=30.0)
    else:
        task_manager.update_status(
            simulation_id, SimulationStatus.ERROR,
            error_message=f"Verification rejected: {comments or 'No reason provided'}"
        )

    return {
        "message": f"Verification {'approved' if approved else 'rejected'}",
        "simulation_id": simulation_id
    }


@router.post("/{simulation_id}/restart-adjusted")
def restart_with_adjustments(
    simulation_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.GEOPHYSICIST, UserRole.ADMIN))
):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    if sim.status != SimulationStatus.ADJUSTING:
        raise HTTPException(
            status_code=400,
            detail=f"Simulation not in adjustment state. Current: {sim.status}"
        )

    background_tasks.add_task(restart_simulation_task, simulation_id, db)

    return {
        "message": "Simulation restarting with adjusted parameters",
        "simulation_id": simulation_id
    }


async def restart_simulation_task(simulation_id: int, db: Session):
    runner = SimulationRunner(db, simulation_id)
    result = runner.restart_with_adjustments()

    await manager.broadcast(simulation_id, {
        "status": "completed" if result["success"] else "error",
        "result": result
    })


@router.delete("/{simulation_id}")
def delete_simulation(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.CHIEF_SCIENTIST))
):
    task_manager = SimulationTaskManager(db)
    success = task_manager.delete_simulation(simulation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return {"message": "Simulation deleted successfully"}


@router.get("/{simulation_id}/time-series", response_model=List[TimeSeriesDataResponse])
def get_time_series(
    simulation_id: int,
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    from backend.models import TimeSeriesData
    return db.query(TimeSeriesData).filter(
        TimeSeriesData.simulation_id == simulation_id
    ).order_by(TimeSeriesData.time_step).offset(skip).limit(limit).all()


@router.get("/{simulation_id}/polarity-reversals", response_model=List[PolarityReversalResponse])
def get_polarity_reversals(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    from backend.models import PolarityReversal
    return db.query(PolarityReversal).filter(
        PolarityReversal.simulation_id == simulation_id
    ).order_by(PolarityReversal.start_iteration).all()


@router.get("/{simulation_id}/adjustment-logs", response_model=List[ParameterAdjustmentResponse])
def get_adjustment_logs(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    from backend.models import ParameterAdjustmentLog
    return db.query(ParameterAdjustmentLog).filter(
        ParameterAdjustmentLog.simulation_id == simulation_id
    ).order_by(ParameterAdjustmentLog.created_at.desc()).all()


@router.get("/group-status")
def get_group_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.CHIEF_SCIENTIST))
):
    from backend.models import GroupFailureStatus
    return db.query(GroupFailureStatus).all()


@router.post("/group/{group_name}/resume")
def resume_group(
    group_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CHIEF_SCIENTIST, UserRole.ADMIN))
):
    task_manager = SimulationTaskManager(db)
    success = task_manager.resume_group(group_name)

    if not success:
        raise HTTPException(status_code=404, detail="Group not found")

    return {"message": f"Group {group_name} resumed successfully"}


@router.websocket("/ws/{simulation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    simulation_id: int,
    db: Session = Depends(get_db)
):
    await manager.connect(simulation_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(simulation_id, data)
    except WebSocketDisconnect:
        manager.disconnect(simulation_id, websocket)
