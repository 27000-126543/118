import os
import uuid
import json
import shutil
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from fastapi import UploadFile
import numpy as np

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import (
    Simulation, SimulationStatus, User, TimeSeriesData,
    PolarityReversal, Alert, AlertLevel, ParameterAdjustmentLog,
    GroupFailureStatus
)
from backend.physics.mesh_and_fields import (
    SphericalShellMesh, DimensionlessNumbers
)


class ParameterFileParser:
    @staticmethod
    def parse_txt(content: str) -> Dict[str, Any]:
        params = {}
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                try:
                    if '.' in value or 'e' in value.lower():
                        params[key] = float(value)
                    else:
                        params[key] = int(value)
                except ValueError:
                    params[key] = value
        return params

    @staticmethod
    def parse_json(content: str) -> Dict[str, Any]:
        return json.loads(content)

    @staticmethod
    def parse_file(file: UploadFile) -> Dict[str, Any]:
        content = file.file.read().decode('utf-8')
        filename = file.filename.lower()

        if filename.endswith('.json'):
            return ParameterFileParser.parse_json(content)
        elif filename.endswith('.txt') or filename.endswith('.dat'):
            return ParameterFileParser.parse_txt(content)
        else:
            raise ValueError(f"Unsupported file format: {filename}")

    @staticmethod
    def validate(params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        required = ['core_radius', 'viscosity', 'thermal_expansion', 'icb_heat_flux']
        errors = []

        for field in required:
            if field not in params:
                errors.append(f"Missing required parameter: {field}")
            elif not isinstance(params[field], (int, float)):
                errors.append(f"Parameter {field} must be a number")
            elif params[field] <= 0:
                errors.append(f"Parameter {field} must be positive")

        if 'core_radius' in params and params['core_radius'] < 1e6:
            errors.append("Core radius is too small, should be in meters")

        if 'viscosity' in params and (params['viscosity'] < 1e-6 or params['viscosity'] > 1e10):
            errors.append("Viscosity out of reasonable range (1e-6 to 1e10 Pa·s)")

        return len(errors) == 0, errors


class SimulationTaskManager:
    def __init__(self, db: Session):
        self.db = db

    def create_simulation(
        self,
        user: User,
        params: Dict[str, Any],
        name: str,
        description: Optional[str] = None,
        parameters_file: Optional[str] = None
    ) -> Simulation:
        dimensionless = DimensionlessNumbers.calculate(
            core_radius=params['core_radius'],
            viscosity=params['viscosity'],
            thermal_expansion=params['thermal_expansion']
        )

        output_dir = os.path.join(
            settings.OUTPUT_DIR,
            f"sim_{uuid.uuid4().hex[:12]}"
        )
        os.makedirs(output_dir, exist_ok=True)

        mesh_file = os.path.join(output_dir, 'mesh.json')
        with open(mesh_file, 'w') as f:
            json.dump({
                'outer_radius': params['core_radius'],
                'inner_radius': params.get('inner_core_radius', params['core_radius'] * 0.2),
                'n_radial': params.get('n_radial', 32),
                'n_theta': params.get('n_theta', 64),
                'n_phi': params.get('n_phi', 128)
            }, f)

        simulation = Simulation(
            name=name,
            description=description,
            owner_id=user.id,
            status=SimulationStatus.PENDING_VERIFICATION,
            core_radius=params['core_radius'],
            viscosity=params['viscosity'],
            thermal_expansion=params['thermal_expansion'],
            icb_heat_flux=params['icb_heat_flux'],
            cmb_heat_flux=params.get('cmb_heat_flux', 0.05),
            inner_core_radius=params.get('inner_core_radius', params['core_radius'] * 0.2),
            max_iterations=params.get('max_iterations', 10000),
            magnetic_reynolds_critical=params.get('magnetic_reynolds_critical', 50.0),
            dipole_tilt_threshold=params.get('dipole_tilt_threshold', 10.0),
            rayleigh_number=dimensionless['rayleigh_number'],
            prandtl_number=dimensionless['prandtl_number'],
            magnetic_reynolds_number=dimensionless['magnetic_reynolds_number'],
            ekman_number=dimensionless['ekman_number'],
            rossby_number=dimensionless['rossby_number'],
            relaxation_time=DimensionlessNumbers.calculate_relaxation_time(
                dimensionless['magnetic_reynolds_number'],
                dimensionless['magnetic_diffusion_time']
            ),
            parameters_file=parameters_file,
            mesh_file=mesh_file,
            output_dir=output_dir
        )

        self.db.add(simulation)
        self.db.commit()
        self.db.refresh(simulation)

        return simulation

    def update_status(self, simulation_id: int, status: SimulationStatus, **kwargs) -> Optional[Simulation]:
        sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not sim:
            return None

        sim.status = status
        sim.updated_at = datetime.utcnow()

        for key, value in kwargs.items():
            if hasattr(sim, key):
                setattr(sim, key, value)

        if status == SimulationStatus.ITERATING and not sim.started_at:
            sim.started_at = datetime.utcnow()

        if status in [SimulationStatus.COMPLETED, SimulationStatus.ERROR]:
            sim.completed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(sim)
        return sim

    def generate_mesh(self, simulation_id: int) -> Tuple[bool, str]:
        sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not sim:
            return False, "Simulation not found"

        try:
            with open(sim.mesh_file, 'r') as f:
                mesh_config = json.load(f)

            mesh = SphericalShellMesh(
                outer_radius=mesh_config['outer_radius'],
                inner_radius=mesh_config['inner_radius'],
                n_radial=mesh_config.get('n_radial', 32),
                n_theta=mesh_config.get('n_theta', 64),
                n_phi=mesh_config.get('n_phi', 128)
            )
            mesh.generate()
            mesh.save(sim.mesh_file)

            self.update_status(simulation_id, SimulationStatus.MESH_GENERATION, progress=20.0)
            return True, "Mesh generated successfully"
        except Exception as e:
            self.update_status(simulation_id, SimulationStatus.ERROR, error_message=str(e))
            return False, f"Mesh generation failed: {str(e)}"

    def check_group_pause(self, group_name: str = "default") -> bool:
        status = self.db.query(GroupFailureStatus).filter(
            GroupFailureStatus.group_name == group_name
        ).first()
        return status.is_paused if status else False

    def record_failure(self, group_name: str = "default"):
        status = self.db.query(GroupFailureStatus).filter(
            GroupFailureStatus.group_name == group_name
        ).first()

        if not status:
            status = GroupFailureStatus(group_name=group_name)
            self.db.add(status)

        status.consecutive_failures += 1
        status.last_failure_time = datetime.utcnow()

        if status.consecutive_failures >= settings.MAX_CONSECUTIVE_FAILURES:
            status.is_paused = True
            status.last_notification_time = datetime.utcnow()

        status.updated_at = datetime.utcnow()
        self.db.commit()

    def record_success(self, group_name: str = "default"):
        status = self.db.query(GroupFailureStatus).filter(
            GroupFailureStatus.group_name == group_name
        ).first()

        if status:
            status.consecutive_failures = 0
            status.is_paused = False
            status.updated_at = datetime.utcnow()
            self.db.commit()

    def resume_group(self, group_name: str = "default") -> bool:
        status = self.db.query(GroupFailureStatus).filter(
            GroupFailureStatus.group_name == group_name
        ).first()

        if status:
            status.is_paused = False
            status.consecutive_failures = 0
            status.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False

    def save_time_series(self, simulation_id: int, metrics: Dict[str, Any]):
        ts_data = TimeSeriesData(
            simulation_id=simulation_id,
            time_step=metrics.get('iteration', 0),
            simulation_time=metrics.get('time', 0.0),
            magnetic_energy=metrics.get('magnetic_energy'),
            kinetic_energy=metrics.get('kinetic_energy'),
            dipole_moment=metrics.get('dipole_moment'),
            dipole_tilt=metrics.get('dipole_tilt'),
            magnetic_reynolds=metrics.get('magnetic_reynolds'),
            inner_core_symmetry=metrics.get('inner_core_symmetry'),
            temperature_anomaly=metrics.get('temperature_anomaly'),
            velocity_magnitude=metrics.get('velocity_magnitude')
        )
        self.db.add(ts_data)
        self.db.commit()

    def save_polarity_reversals(self, simulation_id: int, reversals: List[Dict[str, Any]]):
        for rev in reversals:
            pr = PolarityReversal(
                simulation_id=simulation_id,
                start_time=rev['start_time'],
                end_time=rev.get('end_time'),
                start_iteration=rev['start_iteration'],
                end_iteration=rev.get('end_iteration'),
                reversal_type=rev.get('type', 'full'),
                duration=rev.get('duration')
            )
            self.db.add(pr)
        self.db.commit()

    def delete_simulation(self, simulation_id: int) -> bool:
        sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not sim:
            return False

        if sim.output_dir and os.path.exists(sim.output_dir):
            shutil.rmtree(sim.output_dir)

        self.db.query(TimeSeriesData).filter(TimeSeriesData.simulation_id == simulation_id).delete()
        self.db.query(PolarityReversal).filter(PolarityReversal.simulation_id == simulation_id).delete()
        self.db.query(Alert).filter(Alert.simulation_id == simulation_id).delete()
        self.db.query(ParameterAdjustmentLog).filter(
            ParameterAdjustmentLog.simulation_id == simulation_id
        ).delete()

        self.db.delete(sim)
        self.db.commit()
        return True
