from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os

from backend.database import get_db
from backend.models import User, UserRole
from backend.schemas import RecommendationResponse
from backend.auth import get_current_active_user, require_role
from backend.services.report_service import ReportGenerator, DataExporter
from backend.services.recommendation_engine import RecommendationEngine

router = APIRouter(prefix="/reports", tags=["报告与导出"])


@router.post("/{simulation_id}/generate")
def generate_report(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    from backend.models import Simulation
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()

    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    try:
        report_gen = ReportGenerator(db, simulation_id)
        report_path = report_gen.generate_report()

        return {
            "message": "Report generated successfully",
            "report_path": report_path,
            "simulation_id": simulation_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate report: {str(e)}"
        )


@router.get("/{simulation_id}/download")
def download_report(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    from backend.models import Simulation
    sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()

    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    from backend.config import settings
    report_path = os.path.join(settings.REPORT_DIR, f'sim_{simulation_id}', f'simulation_report_{simulation_id}.pdf')

    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=404,
            detail="Report not found. Please generate it first."
        )

    return FileResponse(
        report_path,
        media_type='application/pdf',
        filename=f'simulation_report_{simulation_id}.pdf'
    )


@router.get("/{simulation_id}/export/fields")
def export_field_data(
    simulation_id: int,
    field_type: str = Query("all", enum=["all", "magnetic", "velocity", "temperature"]),
    format: str = Query("npz", enum=["npz", "vtk"]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        exporter = DataExporter(db, simulation_id)
        export_path = exporter.export_full_field_data(field_type=field_type, format=format)

        return FileResponse(
            export_path,
            media_type='application/octet-stream',
            filename=os.path.basename(export_path)
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{simulation_id}/export/time-series")
def export_time_series(
    simulation_id: int,
    by_dimension: Optional[str] = Query(None, enum=["relaxation", "rayleigh", "prandtl"]),
    format: str = Query("csv", enum=["csv", "json", "hdf5"]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        exporter = DataExporter(db, simulation_id)
        export_path = exporter.export_time_series(by_dimension=by_dimension, format=format)

        media_types = {
            'csv': 'text/csv',
            'json': 'application/json',
            'hdf5': 'application/x-hdf5'
        }

        return FileResponse(
            export_path,
            media_type=media_types.get(format, 'application/octet-stream'),
            filename=os.path.basename(export_path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{simulation_id}/export/parameters")
def export_parameters(
    simulation_id: int,
    format: str = Query("json", enum=["json", "txt"]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    try:
        exporter = DataExporter(db, simulation_id)
        export_path = exporter.export_parameters(format=format)

        media_type = 'application/json' if format == 'json' else 'text/plain'

        return FileResponse(
            export_path,
            media_type=media_type,
            filename=os.path.basename(export_path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommendations")
def get_recommendation(
    paleomagnetic_record: dict,
    top_k: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.RESEARCHER, UserRole.POSTDOC, UserRole.PROFESSOR, UserRole.ADMIN))
):
    engine = RecommendationEngine(db)
    result = engine.recommend(paleomagnetic_record, top_k=top_k)

    if not result.get('success', False):
        return JSONResponse(
            status_code=202,
            content=result
        )

    return result


@router.get("/recommendations", response_model=list[RecommendationResponse])
def list_recommendations(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    engine = RecommendationEngine(db)
    return engine.get_recommendations(limit=limit)


@router.get("/recommendations/model-info")
def get_model_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    engine = RecommendationEngine(db)
    return engine.get_model_info()


@router.post("/recommendations/train")
def train_model(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.CHIEF_SCIENTIST))
):
    engine = RecommendationEngine(db)
    result = engine.train()

    if not result.get('success', False):
        return JSONResponse(
            status_code=400,
            content=result
        )

    return result
