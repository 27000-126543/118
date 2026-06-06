import os
import json
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Tuple
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import (
    Simulation, SimulationStatus, User, Alert, AlertLevel,
    Review, ParameterAdjustmentLog
)
from backend.physics.mesh_and_fields import SphericalShellMesh
from backend.physics.dynamo_simulation import DynamoSimulation
from backend.services.simulation_service import SimulationTaskManager


class AlertService:
    def __init__(self, db: Session):
        self.db = db

    def create_alert(
        self,
        simulation_id: int,
        alert_data: Dict[str, Any],
        notify_roles: Optional[List[str]] = None
    ) -> List[Alert]:
        if notify_roles is None:
            notify_roles = ['geophysicist', 'postdoc', 'professor', 'chief_scientist']

        recipients = self.db.query(User).filter(User.role.in_(notify_roles)).all()

        alerts = []
        for recipient in recipients:
            alert = Alert(
                simulation_id=simulation_id,
                recipient_id=recipient.id,
                level=alert_data.get('level', AlertLevel.WARNING),
                title=alert_data.get('title', 'Simulation Alert'),
                message=alert_data.get('message', ''),
                metric_name=alert_data.get('metric_name'),
                metric_value=alert_data.get('metric_value'),
                threshold=alert_data.get('threshold'),
                needs_review=alert_data.get('needs_review', False)
            )
            self.db.add(alert)
            alerts.append(alert)

        self.db.commit()
        for alert in alerts:
            self.db.refresh(alert)

        return alerts

    def mark_read(self, alert_id: int, user_id: int) -> Optional[Alert]:
        alert = self.db.query(Alert).filter(
            Alert.id == alert_id,
            Alert.recipient_id == user_id
        ).first()
        if alert:
            alert.is_read = True
            self.db.commit()
            self.db.refresh(alert)
        return alert

    def mark_reviewed(self, alert_id: int, user_id: int) -> Optional[Alert]:
        alert = self.db.query(Alert).filter(
            Alert.id == alert_id,
            Alert.recipient_id == user_id
        ).first()
        if alert:
            alert.reviewed = True
            self.db.commit()
            self.db.refresh(alert)
        return alert

    def delete_alert(self, alert_id: int, user_id: int) -> bool:
        alert = self.db.query(Alert).filter(
            Alert.id == alert_id,
            Alert.recipient_id == user_id
        ).first()
        if alert:
            self.db.delete(alert)
            self.db.commit()
            return True
        return False

    def get_unread_count(self, user_id: int) -> int:
        return self.db.query(Alert).filter(
            Alert.recipient_id == user_id,
            Alert.is_read == False
        ).count()

    def get_user_alerts(
        self,
        user_id: int,
        level: Optional[str] = None,
        is_read: Optional[bool] = None,
        needs_review: Optional[bool] = None,
        simulation_id: Optional[int] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[Alert], int]:
        query = self.db.query(Alert).filter(Alert.recipient_id == user_id)

        if level:
            query = query.filter(Alert.level == level)
        if is_read is not None:
            query = query.filter(Alert.is_read == is_read)
        if needs_review is not None:
            query = query.filter(Alert.needs_review == needs_review)
        if simulation_id:
            query = query.filter(Alert.simulation_id == simulation_id)
        if keyword:
            query = query.filter(Alert.title.ilike(f"%{keyword}%"))

        total = query.count()
        alerts = query.order_by(Alert.created_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return alerts, total


class ReviewService:
    def __init__(self, db: Session):
        self.db = db

    def create_review(
        self,
        simulation_id: int,
        reviewer_id: int,
        comments: str,
        approved: bool,
        alert_id: Optional[int] = None,
        suggest_cmb_adjustment: Optional[float] = None,
        suggest_inner_core_adjustment: Optional[float] = None,
        suggest_viscosity_adjustment: Optional[float] = None
    ) -> Review:
        review = Review(
            simulation_id=simulation_id,
            reviewer_id=reviewer_id,
            alert_id=alert_id,
            comments=comments,
            approved=approved,
            suggest_cmb_adjustment=suggest_cmb_adjustment,
            suggest_inner_core_adjustment=suggest_inner_core_adjustment,
            suggest_viscosity_adjustment=suggest_viscosity_adjustment
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)

        if approved:
            self._apply_adjustments(simulation_id, review)

        return review

    def _apply_adjustments(self, simulation_id: int, review: Review):
        sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not sim:
            return

        adjustment_log = ParameterAdjustmentLog(
            simulation_id=simulation_id,
            reviewer_id=review.reviewer_id,
            reason=review.comments,
            approved=True
        )

        if review.suggest_cmb_adjustment is not None:
            adjustment_log.old_cmb_heat_flux = sim.cmb_heat_flux
            sim.cmb_heat_flux = review.suggest_cmb_adjustment
            adjustment_log.new_cmb_heat_flux = review.suggest_cmb_adjustment

        if review.suggest_inner_core_adjustment is not None:
            adjustment_log.old_inner_core_radius = sim.inner_core_radius
            sim.inner_core_radius = review.suggest_inner_core_adjustment
            adjustment_log.new_inner_core_radius = review.suggest_inner_core_adjustment

        if review.suggest_viscosity_adjustment is not None:
            adjustment_log.old_viscosity = sim.viscosity
            sim.viscosity = review.suggest_viscosity_adjustment
            adjustment_log.new_viscosity = review.suggest_viscosity_adjustment

        self.db.add(adjustment_log)

        sim.status = SimulationStatus.ADJUSTING
        sim.warning_count += 1
        sim.updated_at = datetime.utcnow()
        self.db.commit()

    def get_simulation_reviews(self, simulation_id: int) -> List[Review]:
        return self.db.query(Review).filter(
            Review.simulation_id == simulation_id
        ).order_by(Review.created_at.desc()).all()

    def get_adjustment_logs(self, simulation_id: int) -> List[ParameterAdjustmentLog]:
        return self.db.query(ParameterAdjustmentLog).filter(
            ParameterAdjustmentLog.simulation_id == simulation_id
        ).order_by(ParameterAdjustmentLog.created_at.desc()).all()


class SimulationRunner:
    def __init__(self, db: Session, simulation_id: int):
        self.db = db
        self.simulation_id = simulation_id
        self.task_manager = SimulationTaskManager(db)
        self.alert_service = AlertService(db)

        self.sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        self.dynamo = None

    def create_alert_callback(self) -> Callable[[Dict[str, Any]], None]:
        def callback(alert_data: Dict[str, Any]):
            self.alert_service.create_alert(self.simulation_id, alert_data)
            self.sim.warning_count += 1
            self.db.commit()
        return callback

    def create_progress_callback(self) -> Callable[[Dict[str, Any]], None]:
        def callback(progress_data: Dict[str, Any]):
            metrics = progress_data.get('metrics', {})
            self.task_manager.update_status(
                self.simulation_id,
                SimulationStatus.ITERATING,
                progress=progress_data.get('progress', 0),
                current_iteration=progress_data.get('iteration', 0),
                magnetic_reynolds_number=metrics.get('magnetic_reynolds'),
                dipole_moment=metrics.get('dipole_moment'),
                dipole_tilt=metrics.get('dipole_tilt'),
                inner_core_symmetry=metrics.get('inner_core_symmetry'),
                total_magnetic_energy=metrics.get('magnetic_energy'),
                total_kinetic_energy=metrics.get('kinetic_energy')
            )

            if progress_data.get('iteration', 0) % 50 == 0:
                self.task_manager.save_time_series(self.simulation_id, metrics)

        return callback

    def initialize(self) -> Tuple[bool, str]:
        if not self.sim:
            return False, "Simulation not found"

        try:
            self.task_manager.update_status(
                self.simulation_id,
                SimulationStatus.INITIALIZATION,
                progress=30.0
            )

            with open(self.sim.mesh_file, 'r') as f:
                mesh_config = json.load(f)

            mesh = SphericalShellMesh(
                outer_radius=mesh_config['outer_radius'],
                inner_radius=mesh_config['inner_radius'],
                n_radial=mesh_config.get('n_radial', 32),
                n_theta=mesh_config.get('n_theta', 64),
                n_phi=mesh_config.get('n_phi', 128)
            )
            mesh.generate()

            params = {
                'density': 13000.0,
                'gravity': 10.0,
                'thermal_expansion': self.sim.thermal_expansion,
                'viscosity': self.sim.viscosity,
                'thermal_diffusivity': 1e-5,
                'magnetic_diffusivity': 2.0,
                'rotation_rate': 7.29e-5,
                'icb_heat_flux': self.sim.icb_heat_flux,
                'cmb_heat_flux': self.sim.cmb_heat_flux,
                'typical_velocity': np.sqrt(self.sim.rayleigh_number) * 1e-5 if self.sim.rayleigh_number else 0.001,
                'magnetic_reynolds_critical': self.sim.magnetic_reynolds_critical,
                'dipole_tilt_threshold': self.sim.dipole_tilt_threshold,
                'max_iterations': self.sim.max_iterations
            }

            self.dynamo = DynamoSimulation(
                mesh=mesh,
                params=params,
                output_dir=self.sim.output_dir,
                progress_callback=self.create_progress_callback(),
                alert_callback=self.create_alert_callback()
            )

            self.task_manager.update_status(
                self.simulation_id,
                SimulationStatus.INITIALIZATION,
                progress=40.0
            )

            return True, "Initialization completed successfully"
        except Exception as e:
            self.task_manager.update_status(
                self.simulation_id,
                SimulationStatus.ERROR,
                error_message=f"Initialization failed: {str(e)}"
            )
            return False, f"Initialization failed: {str(e)}"

    def run(self, max_iterations: Optional[int] = None) -> Dict[str, Any]:
        if not self.dynamo:
            success, msg = self.initialize()
            if not success:
                return {'success': False, 'message': msg}

        self.task_manager.update_status(
            self.simulation_id,
            SimulationStatus.ITERATING,
            progress=50.0
        )

        result = self.dynamo.run(max_iterations=max_iterations)

        if result['success']:
            final_state = result['final_state']
            self.task_manager.update_status(
                self.simulation_id,
                SimulationStatus.COMPLETED,
                progress=100.0,
                current_iteration=final_state['iteration'],
                dipole_moment=final_state['dipole_moment'],
                dipole_tilt=final_state['dipole_tilt'],
                magnetic_reynolds_number=final_state['magnetic_reynolds'],
                inner_core_symmetry=final_state['inner_core_symmetry'],
                total_magnetic_energy=final_state['magnetic_energy'],
                total_kinetic_energy=final_state['kinetic_energy'],
                has_polarity_reversal=final_state['has_polarity_reversal'],
                polarity_reversal_count=final_state['polarity_reversal_count'],
                magnetic_energy_generation_efficiency=final_state['magnetic_energy'] / max(final_state['kinetic_energy'], 1e-10)
            )

            if result.get('polarity_reversals'):
                self.task_manager.save_polarity_reversals(
                    self.simulation_id, result['polarity_reversals']
                )

            self.task_manager.record_success()

        else:
            self.task_manager.update_status(
                self.simulation_id,
                SimulationStatus.ERROR,
                error_message=result.get('message', 'Simulation failed')
            )
            self.task_manager.record_failure()

        result['simulation_id'] = self.simulation_id
        return result

    def step(self, n_steps: int = 1) -> Dict[str, Any]:
        if not self.dynamo:
            success, msg = self.initialize()
            if not success:
                return {'success': False, 'message': msg}

        for _ in range(n_steps):
            if not self.dynamo.step():
                return {
                    'success': False,
                    'message': 'Simulation became unstable',
                    'state': self.dynamo.state.to_dict()
                }

        return {
            'success': True,
            'state': self.dynamo.state.to_dict()
        }

    def restart_with_adjustments(self) -> Dict[str, Any]:
        self.db.refresh(self.sim)

        if self.sim.status != SimulationStatus.ADJUSTING:
            return {'success': False, 'message': 'Simulation is not in adjustment state'}

        self.sim.status = SimulationStatus.INITIALIZATION
        self.sim.progress = 0.0
        self.sim.current_iteration = 0
        self.sim.error_message = None
        self.sim.started_at = None
        self.sim.completed_at = None
        self.db.commit()

        old_output_dir = self.sim.output_dir
        new_output_dir = old_output_dir + f"_adjusted_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(new_output_dir, exist_ok=True)
        self.sim.output_dir = new_output_dir

        self.dynamo = None
        return self.run()
