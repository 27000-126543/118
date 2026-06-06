from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr

from backend.models import (
    SimulationStatus, AlertLevel, ApprovalStatus, UserRole
)


class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.RESEARCHER


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    password: Optional[str] = Field(None, min_length=6)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class SimulationBase(BaseModel):
    name: str
    description: Optional[str] = None
    core_radius: float
    viscosity: float
    thermal_expansion: float
    icb_heat_flux: float
    cmb_heat_flux: Optional[float] = None
    inner_core_radius: Optional[float] = None
    max_iterations: int = 10000
    magnetic_reynolds_critical: float = 50.0
    dipole_tilt_threshold: float = 10.0


class SimulationCreate(SimulationBase):
    pass


class SimulationResponse(SimulationBase):
    id: int
    owner_id: int
    status: SimulationStatus
    progress: float
    current_iteration: int
    rayleigh_number: Optional[float] = None
    prandtl_number: Optional[float] = None
    magnetic_reynolds_number: Optional[float] = None
    relaxation_time: Optional[float] = None
    dipole_moment: Optional[float] = None
    dipole_tilt: Optional[float] = None
    inner_core_symmetry: Optional[float] = None
    total_magnetic_energy: Optional[float] = None
    total_kinetic_energy: Optional[float] = None
    magnetic_energy_generation_efficiency: Optional[float] = None
    warning_count: int = 0
    has_polarity_reversal: bool = False
    polarity_reversal_count: int = 0
    approval_status: ApprovalStatus
    submitted_for_approval: bool
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SimulationUpdate(BaseModel):
    status: Optional[SimulationStatus] = None
    progress: Optional[float] = None
    current_iteration: Optional[int] = None
    error_message: Optional[str] = None


class TimeSeriesDataResponse(BaseModel):
    id: int
    simulation_id: int
    time_step: int
    simulation_time: float
    magnetic_energy: Optional[float] = None
    kinetic_energy: Optional[float] = None
    dipole_moment: Optional[float] = None
    dipole_tilt: Optional[float] = None
    magnetic_reynolds: Optional[float] = None
    inner_core_symmetry: Optional[float] = None
    temperature_anomaly: Optional[float] = None
    velocity_magnitude: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PolarityReversalResponse(BaseModel):
    id: int
    simulation_id: int
    start_time: float
    end_time: Optional[float] = None
    start_iteration: int
    end_iteration: Optional[int] = None
    reversal_type: str
    duration: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: int
    simulation_id: int
    recipient_id: int
    level: AlertLevel
    title: str
    message: str
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    is_read: bool
    needs_review: bool
    reviewed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    simulation_id: int
    alert_id: Optional[int] = None
    comments: str
    approved: bool
    suggest_cmb_adjustment: Optional[float] = None
    suggest_inner_core_adjustment: Optional[float] = None
    suggest_viscosity_adjustment: Optional[float] = None


class ReviewResponse(BaseModel):
    id: int
    simulation_id: int
    reviewer_id: int
    alert_id: Optional[int] = None
    comments: str
    approved: bool
    suggest_cmb_adjustment: Optional[float] = None
    suggest_inner_core_adjustment: Optional[float] = None
    suggest_viscosity_adjustment: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalCreate(BaseModel):
    simulation_id: int
    level: str
    comments: Optional[str] = None
    approved: bool


class ApprovalResponse(BaseModel):
    id: int
    simulation_id: int
    approver_id: int
    level: str
    comments: Optional[str] = None
    approved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ParameterAdjustmentResponse(BaseModel):
    id: int
    simulation_id: int
    reviewer_id: int
    old_cmb_heat_flux: Optional[float] = None
    new_cmb_heat_flux: Optional[float] = None
    old_inner_core_radius: Optional[float] = None
    new_inner_core_radius: Optional[float] = None
    old_viscosity: Optional[float] = None
    new_viscosity: Optional[float] = None
    reason: str
    approved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DailyStatisticsResponse(BaseModel):
    id: int
    date: datetime
    total_simulations: int
    completed_simulations: int
    completion_rate: float
    avg_magnetic_energy_efficiency: float
    polarity_reversal_frequency: float
    avg_iterations_per_simulation: float
    avg_simulation_duration_hours: float
    error_count: int

    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):
    id: int
    target_paleomagnetic_record: str
    recommended_viscosity: float
    recommended_inner_core_growth_rate: float
    confidence_score: float
    matching_simulations: List[Dict[str, Any]]
    used_features: List[str]
    model_version: str
    created_at: datetime

    class Config:
        from_attributes = True


class GroupFailureStatusResponse(BaseModel):
    id: int
    group_name: str
    consecutive_failures: int
    is_paused: bool
    last_failure_time: Optional[datetime] = None
    last_notification_time: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class SimulationMetrics(BaseModel):
    magnetic_reynolds: float
    dipole_tilt: float
    inner_core_symmetry: float
    magnetic_energy: float
    kinetic_energy: float
    dipole_moment: float


class RealTimeUpdate(BaseModel):
    simulation_id: int
    iteration: int
    progress: float
    metrics: SimulationMetrics
    status: SimulationStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
