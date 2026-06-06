from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserRole, AlertLevel
from backend.schemas import (
    AlertResponse, ReviewCreate, ReviewResponse,
    ParameterAdjustmentResponse
)
from backend.auth import get_current_active_user, require_role
from backend.services.monitoring_service import AlertService, ReviewService

router = APIRouter(prefix="/monitoring", tags=["监控与预警"])


@router.get("/alerts")
def get_user_alerts(
    level: Optional[str] = None,
    is_read: Optional[bool] = None,
    needs_review: Optional[bool] = None,
    simulation_id: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    alert_service = AlertService(db)
    alerts, total = alert_service.get_user_alerts(
        user_id=current_user.id,
        level=level,
        is_read=is_read,
        needs_review=needs_review,
        simulation_id=simulation_id,
        keyword=keyword,
        page=page,
        page_size=page_size
    )
    return {"items": alerts, "total": total, "page": page, "page_size": page_size}


@router.get("/alerts/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    alert_service = AlertService(db)
    return {"unread_count": alert_service.get_unread_count(current_user.id)}


@router.put("/alerts/{alert_id}/read")
def mark_alert_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    alert_service = AlertService(db)
    alert = alert_service.mark_read(alert_id, current_user.id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"message": "Alert marked as read"}


@router.post("/alerts/{alert_id}/review")
def mark_alert_reviewed(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.GEOPHYSICIST, UserRole.ADMIN))
):
    alert_service = AlertService(db)
    alert = alert_service.mark_reviewed(alert_id, current_user.id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"message": "Alert marked as reviewed"}


@router.post("/reviews", response_model=ReviewResponse)
def create_review(
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.GEOPHYSICIST, UserRole.ADMIN, UserRole.CHIEF_SCIENTIST))
):
    review_service = ReviewService(db)
    review = review_service.create_review(
        simulation_id=review_data.simulation_id,
        reviewer_id=current_user.id,
        comments=review_data.comments,
        approved=review_data.approved,
        alert_id=review_data.alert_id,
        suggest_cmb_adjustment=review_data.suggest_cmb_adjustment,
        suggest_inner_core_adjustment=review_data.suggest_inner_core_adjustment,
        suggest_viscosity_adjustment=review_data.suggest_viscosity_adjustment
    )

    return review


@router.get("/simulations/{simulation_id}/reviews", response_model=List[ReviewResponse])
def get_simulation_reviews(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    review_service = ReviewService(db)
    return review_service.get_simulation_reviews(simulation_id)


@router.get("/simulations/{simulation_id}/adjustments", response_model=List[ParameterAdjustmentResponse])
def get_adjustment_logs(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    review_service = ReviewService(db)
    return review_service.get_adjustment_logs(simulation_id)


@router.delete("/alerts/{alert_id}")
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    alert_service = AlertService(db)
    success = alert_service.delete_alert(alert_id, current_user.id)

    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"message": "Alert deleted successfully"}


@router.post("/alerts/{alert_id}/test")
def test_alert(
    alert_id: Optional[int] = None,
    simulation_id: int = 1,
    level: AlertLevel = AlertLevel.WARNING,
    title: str = "Test Alert",
    message: str = "This is a test alert",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    alert_service = AlertService(db)
    alerts = alert_service.create_alert(
        simulation_id=simulation_id,
        alert_data={
            'level': level,
            'title': title,
            'message': message,
            'needs_review': True
        }
    )

    return {"message": "Test alert created", "alert_count": len(alerts)}
