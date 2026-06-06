from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserRole, SimulationStatus
from backend.schemas import (
    ApprovalResponse, SimulationResponse,
    DailyStatisticsResponse, GroupFailureStatusResponse
)
from backend.auth import get_current_active_user, require_role
from backend.services.approval_service import ApprovalService
from backend.services.statistics_service import StatisticsService

router = APIRouter(tags=["审批与统计"])


@router.post("/simulations/{simulation_id}/submit-approval")
def submit_for_approval(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    approval_service = ApprovalService(db)
    success, message = approval_service.submit_for_approval(simulation_id, current_user.id)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"message": message, "simulation_id": simulation_id}


@router.get("/approvals/pending-postdoc", response_model=List[SimulationResponse])
def get_pending_postdoc(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.POSTDOC, UserRole.ADMIN, UserRole.CHIEF_SCIENTIST))
):
    approval_service = ApprovalService(db)
    return approval_service.get_simulations_pending_postdoc()


@router.get("/approvals/pending-professor", response_model=List[SimulationResponse])
def get_pending_professor(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PROFESSOR, UserRole.ADMIN, UserRole.CHIEF_SCIENTIST))
):
    approval_service = ApprovalService(db)
    return approval_service.get_simulations_pending_professor()


@router.post("/approvals/{simulation_id}/postdoc")
def postdoc_approve(
    simulation_id: int,
    approved: bool,
    comments: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.POSTDOC, UserRole.ADMIN))
):
    approval_service = ApprovalService(db)
    success, message = approval_service.postdoc_approve(
        simulation_id, current_user.id, approved, comments
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"message": message, "simulation_id": simulation_id, "approved": approved}


@router.post("/approvals/{simulation_id}/professor")
def professor_approve(
    simulation_id: int,
    approved: bool,
    comments: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PROFESSOR, UserRole.ADMIN))
):
    approval_service = ApprovalService(db)
    success, message = approval_service.professor_approve(
        simulation_id, current_user.id, approved, comments
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {"message": message, "simulation_id": simulation_id, "approved": approved}


@router.get("/approvals/simulation/{simulation_id}", response_model=List[ApprovalResponse])
def get_simulation_approvals(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    approval_service = ApprovalService(db)
    return approval_service.get_approval_history(simulation_id)


@router.get("/approvals/my-approvals", response_model=List[ApprovalResponse])
def get_my_approvals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    approval_service = ApprovalService(db)
    return approval_service.get_user_approvals(current_user.id)


@router.get("/statistics/daily/generate")
def generate_daily_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.CHIEF_SCIENTIST))
):
    stats_service = StatisticsService(db)
    stats = stats_service.generate_daily_statistics()
    return {"message": "Daily statistics generated", "date": stats.date.isoformat()}


@router.get("/statistics/daily", response_model=List[DailyStatisticsResponse])
def get_daily_statistics(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stats_service = StatisticsService(db)
    return stats_service.get_daily_statistics(days=days)


@router.get("/statistics/overview")
def get_overall_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stats_service = StatisticsService(db)
    return stats_service.get_overall_statistics()


@router.get("/statistics/dashboard")
def get_dashboard(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stats_service = StatisticsService(db)
    return stats_service.get_dashboard_data(days=days)


@router.get("/statistics/heatmap")
def get_heatmap_data(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    stats_service = StatisticsService(db)
    return stats_service.get_heatmap_data(days=days)


@router.post("/statistics/{simulation_id}/animation")
def generate_animation(
    simulation_id: int,
    output_format: str = "gif",
    max_frames: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        stats_service = StatisticsService(db)
        animation_path = stats_service.generate_magnetic_field_animation(
            simulation_id, output_format=output_format, max_frames=max_frames
        )

        return {
            "message": "Animation generated successfully",
            "animation_path": animation_path,
            "simulation_id": simulation_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/group-failures", response_model=List[GroupFailureStatusResponse])
def get_group_failure_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.CHIEF_SCIENTIST))
):
    from backend.models import GroupFailureStatus
    return db.query(GroupFailureStatus).all()
