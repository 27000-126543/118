from datetime import datetime
import enum

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship

from backend.database import Base


class SimulationStatus(str, enum.Enum):
    PENDING_VERIFICATION = "待校验"
    MESH_GENERATION = "网格生成"
    INITIALIZATION = "初始化"
    ITERATING = "发电机迭代"
    COMPLETED = "完成"
    ERROR = "异常"
    NEEDS_REVIEW = "需复核"
    ADJUSTING = "参数调整"


class AlertLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ApprovalStatus(str, enum.Enum):
    PENDING = "待审批"
    POSTDOC_APPROVED = "博士后通过"
    PROFESSOR_APPROVED = "教授通过"
    REJECTED = "已拒绝"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    POSTDOC = "postdoc"
    PROFESSOR = "professor"
    GEOPHYSICIST = "geophysicist"
    CHIEF_SCIENTIST = "chief_scientist"
    RESEARCHER = "researcher"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.RESEARCHER)
    full_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    simulations = relationship("Simulation", back_populates="owner")
    reviews = relationship("Review", back_populates="reviewer")
    approvals = relationship("Approval", back_populates="approver")
    alerts = relationship("Alert", back_populates="recipient")


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(20), default=SimulationStatus.PENDING_VERIFICATION)
    progress = Column(Float, default=0.0)
    current_iteration = Column(Integer, default=0)
    max_iterations = Column(Integer, default=10000)

    core_radius = Column(Float, nullable=False, comment="地核半径 (m)")
    viscosity = Column(Float, nullable=False, comment="粘性 (Pa·s)")
    thermal_expansion = Column(Float, nullable=False, comment="热膨胀系数 (K^-1)")
    icb_heat_flux = Column(Float, nullable=False, comment="内核边界热通量 (W/m²)")
    cmb_heat_flux = Column(Float, comment="核幔边界热通量 (W/m²)")
    inner_core_radius = Column(Float, comment="内核半径 (m)")
    rayleigh_number = Column(Float, comment="瑞利数")
    prandtl_number = Column(Float, comment="普朗特数")
    magnetic_reynolds_number = Column(Float, comment="磁雷诺数")
    ekman_number = Column(Float, comment="埃克曼数")
    rossby_number = Column(Float, comment="罗斯比数")

    relaxation_time = Column(Float, comment="弛豫时间")
    dipole_moment = Column(Float, comment="偶极矩")
    dipole_tilt = Column(Float, comment="偶极子倾斜角 (度)")
    inner_core_symmetry = Column(Float, comment="内核对称性")
    total_magnetic_energy = Column(Float, comment="总磁能")
    total_kinetic_energy = Column(Float, comment="总动能")
    magnetic_energy_generation_efficiency = Column(Float, comment="磁能生成效率")

    parameters_file = Column(String(500))
    mesh_file = Column(String(500))
    output_dir = Column(String(500))

    magnetic_reynolds_critical = Column(Float, default=50.0)
    dipole_tilt_threshold = Column(Float, default=10.0)

    warning_count = Column(Integer, default=0)
    has_polarity_reversal = Column(Boolean, default=False)
    polarity_reversal_count = Column(Integer, default=0)

    approval_status = Column(String(20), default=ApprovalStatus.PENDING)
    submitted_for_approval = Column(Boolean, default=False)

    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="simulations")
    alerts = relationship("Alert", back_populates="simulation")
    reviews = relationship("Review", back_populates="simulation")
    adjustments = relationship("ParameterAdjustmentLog", back_populates="simulation")
    approvals = relationship("Approval", back_populates="simulation")
    time_series = relationship("TimeSeriesData", back_populates="simulation")
    polarity_reversals = relationship("PolarityReversal", back_populates="simulation")


class ParameterAdjustmentLog(Base):
    __tablename__ = "parameter_adjustment_logs"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"))
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    old_cmb_heat_flux = Column(Float)
    new_cmb_heat_flux = Column(Float)
    old_inner_core_radius = Column(Float)
    new_inner_core_radius = Column(Float)
    old_viscosity = Column(Float)
    new_viscosity = Column(Float)
    reason = Column(Text, nullable=False)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="adjustments")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"))
    recipient_id = Column(Integer, ForeignKey("users.id"))
    level = Column(String(10), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    metric_name = Column(String(50))
    metric_value = Column(Float)
    threshold = Column(Float)
    is_read = Column(Boolean, default=False)
    needs_review = Column(Boolean, default=False)
    reviewed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="alerts")
    recipient = relationship("User", back_populates="alerts")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"))
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    alert_id = Column(Integer, ForeignKey("alerts.id"))
    comments = Column(Text, nullable=False)
    approved = Column(Boolean, nullable=False)
    suggest_cmb_adjustment = Column(Float)
    suggest_inner_core_adjustment = Column(Float)
    suggest_viscosity_adjustment = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"))
    approver_id = Column(Integer, ForeignKey("users.id"))
    level = Column(String(20), nullable=False)
    comments = Column(Text)
    approved = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="approvals")
    approver = relationship("User", back_populates="approvals")


class TimeSeriesData(Base):
    __tablename__ = "time_series_data"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"))
    time_step = Column(Integer, nullable=False)
    simulation_time = Column(Float, nullable=False)
    magnetic_energy = Column(Float)
    kinetic_energy = Column(Float)
    dipole_moment = Column(Float)
    dipole_tilt = Column(Float)
    magnetic_reynolds = Column(Float)
    inner_core_symmetry = Column(Float)
    temperature_anomaly = Column(Float)
    velocity_magnitude = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="time_series")


class PolarityReversal(Base):
    __tablename__ = "polarity_reversals"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"))
    start_time = Column(Float, nullable=False)
    end_time = Column(Float)
    start_iteration = Column(Integer, nullable=False)
    end_iteration = Column(Integer)
    reversal_type = Column(String(20), default="full")
    duration = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    simulation = relationship("Simulation", back_populates="polarity_reversals")


class DailyStatistics(Base):
    __tablename__ = "daily_statistics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, unique=True, nullable=False)
    total_simulations = Column(Integer, default=0)
    completed_simulations = Column(Integer, default=0)
    completion_rate = Column(Float, default=0.0)
    avg_magnetic_energy_efficiency = Column(Float, default=0.0)
    polarity_reversal_frequency = Column(Float, default=0.0)
    avg_iterations_per_simulation = Column(Float, default=0.0)
    avg_simulation_duration_hours = Column(Float, default=0.0)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    target_paleomagnetic_record = Column(String(200))
    recommended_viscosity = Column(Float, nullable=False)
    recommended_inner_core_growth_rate = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)
    matching_simulations = Column(JSON)
    used_features = Column(JSON)
    model_version = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class GroupFailureStatus(Base):
    __tablename__ = "group_failure_status"

    id = Column(Integer, primary_key=True, index=True)
    group_name = Column(String(100), nullable=False)
    consecutive_failures = Column(Integer, default=0)
    is_paused = Column(Boolean, default=False)
    last_failure_time = Column(DateTime)
    last_notification_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
