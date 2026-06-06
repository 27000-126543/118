import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
import time
import json
import os

from backend.physics.mesh_and_fields import (
    SphericalShellMesh,
    FieldInitializer,
    DimensionlessNumbers
)


@dataclass
class SimulationState:
    iteration: int = 0
    time: float = 0.0
    dt: float = 0.0
    B_r: np.ndarray = None
    B_theta: np.ndarray = None
    B_phi: np.ndarray = None
    T: np.ndarray = None
    v_r: np.ndarray = None
    v_theta: np.ndarray = None
    v_phi: np.ndarray = None
    P: np.ndarray = None

    dipole_moment: float = 0.0
    dipole_tilt: float = 0.0
    magnetic_energy: float = 0.0
    kinetic_energy: float = 0.0
    magnetic_reynolds: float = 0.0
    inner_core_symmetry: float = 1.0

    polarity_reversals: List[Dict[str, Any]] = field(default_factory=list)
    last_polarity: float = 1.0
    in_reversal: bool = False
    reversal_start_time: float = 0.0
    reversal_start_iteration: int = 0

    metrics_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'iteration': self.iteration,
            'time': self.time,
            'dipole_moment': self.dipole_moment,
            'dipole_tilt': self.dipole_tilt,
            'magnetic_energy': self.magnetic_energy,
            'kinetic_energy': self.kinetic_energy,
            'magnetic_reynolds': self.magnetic_reynolds,
            'inner_core_symmetry': self.inner_core_symmetry,
            'polarity_reversal_count': len(self.polarity_reversals),
            'has_polarity_reversal': len(self.polarity_reversals) > 0
        }


class DynamoSimulation:
    def __init__(
        self,
        mesh: SphericalShellMesh,
        params: Dict[str, Any],
        output_dir: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        alert_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.mesh = mesh
        self.params = params
        self.output_dir = output_dir
        self.progress_callback = progress_callback
        self.alert_callback = alert_callback

        self.state = SimulationState()
        self.initializer = FieldInitializer(mesh)

        self.mu0 = 4 * np.pi * 1e-7
        self.rho = params.get('density', 13000.0)
        self.g = params.get('gravity', 10.0)
        self.alpha_T = params.get('thermal_expansion')
        self.nu = params.get('viscosity') / self.rho
        self.kappa = params.get('thermal_diffusivity', 1e-5)
        self.eta = params.get('magnetic_diffusivity', 2.0)
        self.Omega = params.get('rotation_rate', 7.29e-5)

        self.R = mesh.R
        self.Theta = mesh.Theta
        self.Phi = mesh.Phi
        self.dr = mesh.dr
        self.dtheta = mesh.dtheta
        self.dphi = mesh.dphi
        self.volume = mesh.volume

        self.critical_magnetic_reynolds = params.get('magnetic_reynolds_critical', 50.0)
        self.max_dipole_tilt = params.get('dipole_tilt_threshold', 10.0)
        self.max_iterations = params.get('max_iterations', 10000)

        self.stability_check_interval = 10
        self.save_interval = 100
        self.metrics_interval = 10

        self._initialize_fields()
        self._compute_initial_metrics()

    def _initialize_fields(self):
        self.state.B_r, self.state.B_theta, self.state.B_phi = \
            self.initializer.initialize_magnetic_field(
                dipole_moment=self.params.get('dipole_moment', 8.0e22)
            )
        self.state.T = self.initializer.initialize_temperature_field(
            cmb_heat_flux=self.params.get('cmb_heat_flux', 0.05),
            icb_heat_flux=self.params.get('icb_heat_flux')
        )
        self.state.v_r, self.state.v_theta, self.state.v_phi = \
            self.initializer.initialize_velocity_field(
                max_speed=self.params.get('typical_velocity', 0.001)
            )
        self.state.P = np.zeros_like(self.R)

    def _compute_initial_metrics(self):
        self._update_magnetic_metrics()
        self._update_kinetic_metrics()
        self._update_dipole_metrics()
        self._update_inner_core_symmetry()

    def _gradient_r(self, f: np.ndarray) -> np.ndarray:
        grad = np.zeros_like(f)
        grad[1:-1] = (f[2:] - f[:-2]) / (2 * self.dr)
        grad[0] = (f[1] - f[0]) / self.dr
        grad[-1] = (f[-1] - f[-2]) / self.dr
        return grad

    def _gradient_theta(self, f: np.ndarray) -> np.ndarray:
        grad = np.zeros_like(f)
        grad[:, 1:-1] = (f[:, 2:] - f[:, :-2]) / (2 * self.dtheta)
        grad[:, 0] = (f[:, 1] - f[:, 0]) / self.dtheta
        grad[:, -1] = (f[:, -1] - f[:, -2]) / self.dtheta
        return grad / self.R

    def _gradient_phi(self, f: np.ndarray) -> np.ndarray:
        grad = np.zeros_like(f)
        grad[:, :, 1:] = (f[:, :, 1:] - f[:, :, :-1]) / self.dphi
        grad[:, :, 0] = (f[:, :, 0] - f[:, :, -1]) / self.dphi
        return grad / (self.R * np.sin(self.Theta))

    def _divergence(self, v_r, v_theta, v_phi) -> np.ndarray:
        term1 = self._gradient_r(self.R**2 * v_r) / self.R**2
        term2 = self._gradient_theta(np.sin(self.Theta) * v_theta) / np.sin(self.Theta)
        term3 = self._gradient_phi(v_phi)
        return term1 + term2 + term3

    def _curl(self, v_r, v_theta, v_phi):
        curl_r = (
            self._gradient_theta(np.sin(self.Theta) * v_phi) -
            self._gradient_phi(v_theta)
        ) / (self.R * np.sin(self.Theta))

        curl_theta = (
            self._gradient_phi(v_r) / (self.R * np.sin(self.Theta)) -
            self._gradient_r(self.R * v_phi) / self.R
        )

        curl_phi = (
            self._gradient_r(self.R * v_theta) / self.R -
            self._gradient_theta(v_r) / self.R
        )

        return curl_r, curl_theta, curl_phi

    def _update_magnetic_metrics(self):
        B_mag = np.sqrt(self.state.B_r**2 + self.state.B_theta**2 + self.state.B_phi**2)
        self.state.magnetic_energy = float(np.sum(B_mag**2 / (2 * self.mu0) * self.volume))

    def _update_kinetic_metrics(self):
        v_mag = np.sqrt(self.state.v_r**2 + self.state.v_theta**2 + self.state.v_phi**2)
        self.state.kinetic_energy = float(np.sum(0.5 * self.rho * v_mag**2 * self.volume))

        L = self.mesh.outer_radius - self.mesh.inner_radius
        avg_v = float(np.sqrt(np.mean(v_mag**2)))
        self.state.magnetic_reynolds = avg_v * L / self.eta

    def _update_dipole_metrics(self):
        r_outer = self.mesh.outer_radius
        mask = self.R > 0.95 * r_outer

        g10 = np.mean(self.state.B_r[mask] * np.cos(self.Theta[mask])) * 3
        g11 = np.mean(self.state.B_r[mask] * np.sin(self.Theta[mask]) * np.cos(self.Phi[mask])) * 3
        h11 = np.mean(self.state.B_r[mask] * np.sin(self.Theta[mask]) * np.sin(self.Phi[mask])) * 3

        self.state.dipole_moment = float(
            4 * np.pi / self.mu0 * r_outer**3 * np.sqrt(g10**2 + g11**2 + h11**2)
        )

        if g10 != 0:
            self.state.dipole_tilt = float(
                np.degrees(np.arctan2(np.sqrt(g11**2 + h11**2), abs(g10)))
            )
        else:
            self.state.dipole_tilt = 90.0

        current_polarity = np.sign(g10)
        if current_polarity != 0 and current_polarity != self.state.last_polarity:
            if not self.state.in_reversal:
                self.state.in_reversal = True
                self.state.reversal_start_time = self.state.time
                self.state.reversal_start_iteration = self.state.iteration
            else:
                self.state.in_reversal = False
                self.state.polarity_reversals.append({
                    'start_time': self.state.reversal_start_time,
                    'end_time': self.state.time,
                    'start_iteration': self.state.reversal_start_iteration,
                    'end_iteration': self.state.iteration,
                    'duration': self.state.time - self.state.reversal_start_time,
                    'type': 'full'
                })

        if current_polarity != 0:
            self.state.last_polarity = current_polarity

    def _update_inner_core_symmetry(self):
        r_inner = self.mesh.inner_radius
        mask = self.R < 1.2 * r_inner

        if np.sum(mask) > 0:
            T_near_ic = self.state.T[mask]
            mean_T = np.mean(T_near_ic)
            variance = np.var(T_near_ic)
            self.state.inner_core_symmetry = float(
                1.0 - min(1.0, variance / (mean_T**2 + 1e-10))
            )
        else:
            self.state.inner_core_symmetry = 1.0

    def _compute_time_step(self) -> float:
        v_mag = np.sqrt(self.state.v_r**2 + self.state.v_theta**2 + self.state.v_phi**2)
        max_v = np.max(v_mag) + 1e-10

        dt_conv = min(self.dr, self.dtheta * np.min(self.R), self.dphi * np.min(self.R * np.sin(self.Theta))) / max_v
        dt_diff = min(self.dr**2, (self.dtheta * np.min(self.R))**2) / max(self.nu, self.kappa, self.eta)

        return 0.5 * min(dt_conv, dt_diff)

    def _advance_induction(self, dt: float):
        curl_B_r, curl_B_theta, curl_B_phi = self._curl(
            self.state.B_r, self.state.B_theta, self.state.B_phi
        )
        curl_v_r, curl_v_theta, curl_v_phi = self._curl(
            self.state.v_r, self.state.v_theta, self.state.v_phi
        )

        v_cross_B_r = self.state.v_theta * self.state.B_phi - self.state.v_phi * self.state.B_theta
        v_cross_B_theta = self.state.v_phi * self.state.B_r - self.state.v_r * self.state.B_phi
        v_cross_B_phi = self.state.v_r * self.state.B_theta - self.state.v_theta * self.state.B_r

        curl_cross_r, curl_cross_theta, curl_cross_phi = self._curl(
            v_cross_B_r, v_cross_B_theta, v_cross_B_phi
        )

        self.state.B_r += dt * (self.eta * curl_B_r - curl_cross_r)
        self.state.B_theta += dt * (self.eta * curl_B_theta - curl_cross_theta)
        self.state.B_phi += dt * (self.eta * curl_B_phi - curl_cross_phi)

        r_inner_mask = self.R < self.mesh.inner_radius + 0.01 * (self.mesh.outer_radius - self.mesh.inner_radius)
        r_outer_mask = self.R > self.mesh.outer_radius - 0.01 * (self.mesh.outer_radius - self.mesh.inner_radius)
        self.state.B_r[r_inner_mask] = 0
        self.state.B_r[r_outer_mask] = self.state.B_r[r_outer_mask]

    def _advance_momentum(self, dt: float):
        buoyancy = self.rho * self.g * self.alpha_T * (self.state.T - np.mean(self.state.T))

        J_r = curl_B_r = (
            self._gradient_theta(np.sin(self.Theta) * self.state.B_phi) -
            self._gradient_phi(self.state.B_theta)
        ) / (self.mu0 * self.R * np.sin(self.Theta))
        J_theta = (
            self._gradient_phi(self.state.B_r) / (self.mu0 * self.R * np.sin(self.Theta)) -
            self._gradient_r(self.R * self.state.B_phi) / (self.mu0 * self.R)
        )
        J_phi = (
            self._gradient_r(self.R * self.state.B_theta) / (self.mu0 * self.R) -
            self._gradient_theta(self.state.B_r) / (self.mu0 * self.R)
        )

        Lorentz_r = J_theta * self.state.B_phi - J_phi * self.state.B_theta
        Lorentz_theta = J_phi * self.state.B_r - J_r * self.state.B_phi
        Lorentz_phi = J_r * self.state.B_theta - J_theta * self.state.B_r

        coriolis_r = -2 * self.rho * self.Omega * (
            -self.state.v_theta * np.cos(self.Theta) + self.state.v_phi * np.sin(self.Theta)
        )
        coriolis_theta = -2 * self.rho * self.Omega * (
            self.state.v_r * np.cos(self.Theta) + self.state.v_phi * np.cos(self.Theta)
        )
        coriolis_phi = -2 * self.rho * self.Omega * (
            -self.state.v_r * np.sin(self.Theta) - self.state.v_theta * np.cos(self.Theta)
        )

        viscous_r = self.nu * self._gradient_r(self._gradient_r(self.state.v_r))
        viscous_theta = self.nu * self._gradient_r(self._gradient_r(self.state.v_theta))
        viscous_phi = self.nu * self._gradient_r(self._gradient_r(self.state.v_phi))

        grad_P_r = self._gradient_r(self.state.P)

        self.state.v_r += dt / self.rho * (
            -grad_P_r + buoyancy + Lorentz_r + coriolis_r + viscous_r
        )
        self.state.v_theta += dt / self.rho * (
            Lorentz_theta + coriolis_theta + viscous_theta
        )
        self.state.v_phi += dt / self.rho * (
            Lorentz_phi + coriolis_phi + viscous_phi
        )

        boundary_mask = (self.R < self.mesh.inner_radius + 0.03 * (self.mesh.outer_radius - self.mesh.inner_radius)) | \
                        (self.R > self.mesh.outer_radius - 0.03 * (self.mesh.outer_radius - self.mesh.inner_radius))
        self.state.v_r[boundary_mask] *= 0.9
        self.state.v_theta[boundary_mask] *= 0.9
        self.state.v_phi[boundary_mask] *= 0.9

    def _advance_energy(self, dt: float):
        v_dot_grad_T = (
            self.state.v_r * self._gradient_r(self.state.T) +
            self.state.v_theta * self._gradient_theta(self.state.T) +
            self.state.v_phi * self._gradient_phi(self.state.T)
        )

        diffusion = self.kappa * (
            self._gradient_r(self._gradient_r(self.state.T)) +
            self._gradient_theta(self._gradient_theta(self.state.T)) / self.R**2 +
            self._gradient_phi(self._gradient_phi(self.state.T)) / (self.R**2 * np.sin(self.Theta)**2)
        )

        self.state.T += dt * (-v_dot_grad_T + diffusion)

        q_icb = self.params.get('icb_heat_flux', 0.1)
        q_cmb = self.params.get('cmb_heat_flux', 0.05)

        inner_mask = self.R < self.mesh.inner_radius + 0.05 * (self.mesh.outer_radius - self.mesh.inner_radius)
        outer_mask = self.R > self.mesh.outer_radius - 0.05 * (self.mesh.outer_radius - self.mesh.inner_radius)

        self.state.T[inner_mask] += dt * q_icb / (self.rho * 800.0)
        self.state.T[outer_mask] -= dt * q_cmb / (self.rho * 800.0)

    def _check_stability(self) -> Tuple[bool, List[str]]:
        is_stable = True
        issues = []

        if np.isnan(self.state.magnetic_energy) or np.isinf(self.state.magnetic_energy):
            is_stable = False
            issues.append("Magnetic energy is NaN or infinite")

        if np.isnan(self.state.kinetic_energy) or np.isinf(self.state.kinetic_energy):
            is_stable = False
            issues.append("Kinetic energy is NaN or infinite")

        if self.state.magnetic_energy > 1e10 * np.mean(np.abs(self.state.T)):
            is_stable = False
            issues.append("Magnetic energy is unphysically large")

        if self.state.magnetic_reynolds < 0:
            is_stable = False
            issues.append("Negative magnetic Reynolds number")

        if self.state.dipole_tilt > 170 and self.state.dipole_moment < 1e15:
            is_stable = False
            issues.append("Dipole field collapsed")

        return is_stable, issues

    def _check_alerts(self):
        if self.alert_callback:
            if self.state.magnetic_reynolds < self.critical_magnetic_reynolds:
                self.alert_callback({
                    'level': 'critical',
                    'title': '磁雷诺数过低警告',
                    'message': f'磁雷诺数 {self.state.magnetic_reynolds:.2f} 低于临界值 {self.critical_magnetic_reynolds:.2f}，发电机效应可能停止。',
                    'metric_name': 'magnetic_reynolds',
                    'metric_value': self.state.magnetic_reynolds,
                    'threshold': self.critical_magnetic_reynolds,
                    'needs_review': True
                })

            if self.state.dipole_tilt > self.max_dipole_tilt:
                self.alert_callback({
                    'level': 'warning',
                    'title': '偶极子倾斜角过大警告',
                    'message': f'偶极子倾斜角 {self.state.dipole_tilt:.2f}° 超过阈值 {self.max_dipole_tilt:.2f}°，可能预示极性反转。',
                    'metric_name': 'dipole_tilt',
                    'metric_value': self.state.dipole_tilt,
                    'threshold': self.max_dipole_tilt,
                    'needs_review': True
                })

            if self.state.inner_core_symmetry < 0.8:
                self.alert_callback({
                    'level': 'warning',
                    'title': '内核对称性下降警告',
                    'message': f'内核对称性 {self.state.inner_core_symmetry:.3f} 低于0.8，可能影响发电机稳定性。',
                    'metric_name': 'inner_core_symmetry',
                    'metric_value': self.state.inner_core_symmetry,
                    'threshold': 0.8,
                    'needs_review': False
                })

    def step(self) -> bool:
        self.state.dt = self._compute_time_step()

        self._advance_induction(self.state.dt)
        self._advance_momentum(self.state.dt)
        self._advance_energy(self.state.dt)

        self.state.time += self.state.dt
        self.state.iteration += 1

        if self.state.iteration % self.metrics_interval == 0:
            self._update_magnetic_metrics()
            self._update_kinetic_metrics()
            self._update_dipole_metrics()
            self._update_inner_core_symmetry()

            self.state.metrics_history.append({
                'iteration': self.state.iteration,
                'time': self.state.time,
                'magnetic_energy': self.state.magnetic_energy,
                'kinetic_energy': self.state.kinetic_energy,
                'dipole_moment': self.state.dipole_moment,
                'dipole_tilt': self.state.dipole_tilt,
                'magnetic_reynolds': self.state.magnetic_reynolds,
                'inner_core_symmetry': self.state.inner_core_symmetry
            })

            self._check_alerts()

        if self.state.iteration % self.stability_check_interval == 0:
            is_stable, issues = self._check_stability()
            if not is_stable:
                if self.alert_callback:
                    self.alert_callback({
                        'level': 'critical',
                        'title': '数值发散检测',
                        'message': '模拟数值不稳定: ' + '; '.join(issues),
                        'needs_review': True
                    })
                return False

        if self.progress_callback and self.state.iteration % 10 == 0:
            progress = min(100.0, (self.state.iteration / self.max_iterations) * 100)
            self.progress_callback({
                'iteration': self.state.iteration,
                'time': self.state.time,
                'progress': progress,
                'metrics': self.state.to_dict()
            })

        if self.state.iteration % self.save_interval == 0:
            self.save_checkpoint()

        return True

    def run(self, max_iterations: Optional[int] = None) -> Dict[str, Any]:
        max_it = max_iterations or self.max_iterations
        start_time = time.time()

        try:
            for _ in range(self.state.iteration, max_it):
                if not self.step():
                    return {
                        'success': False,
                        'message': 'Simulation became unstable',
                        'final_state': self.state.to_dict(),
                        'duration': time.time() - start_time,
                        'polarity_reversals': self.state.polarity_reversals
                    }
        except Exception as e:
            return {
                'success': False,
                'message': f'Simulation error: {str(e)}',
                'final_state': self.state.to_dict(),
                'duration': time.time() - start_time,
                'polarity_reversals': self.state.polarity_reversals
            }

        self.save_final_results()

        return {
            'success': True,
            'message': 'Simulation completed successfully',
            'final_state': self.state.to_dict(),
            'duration': time.time() - start_time,
            'polarity_reversals': self.state.polarity_reversals,
            'metrics_history': self.state.metrics_history
        }

    def save_checkpoint(self):
        checkpoint_dir = os.path.join(self.output_dir, 'checkpoints')
        os.makedirs(checkpoint_dir, exist_ok=True)

        checkpoint_file = os.path.join(checkpoint_dir, f'checkpoint_{self.state.iteration:08d}.npz')
        np.savez(
            checkpoint_file,
            B_r=self.state.B_r,
            B_theta=self.state.B_theta,
            B_phi=self.state.B_phi,
            T=self.state.T,
            v_r=self.state.v_r,
            v_theta=self.state.v_theta,
            v_phi=self.state.v_phi,
            P=self.state.P,
            iteration=self.state.iteration,
            time=self.state.time
        )

    def save_final_results(self):
        np.savez(
            os.path.join(self.output_dir, 'final_fields.npz'),
            B_r=self.state.B_r,
            B_theta=self.state.B_theta,
            B_phi=self.state.B_phi,
            T=self.state.T,
            v_r=self.state.v_r,
            v_theta=self.state.v_theta,
            v_phi=self.state.v_phi,
            P=self.state.P,
            R=self.R,
            Theta=self.Theta,
            Phi=self.Phi
        )

        with open(os.path.join(self.output_dir, 'metrics_history.json'), 'w') as f:
            json.dump(self.state.metrics_history, f)

        with open(os.path.join(self.output_dir, 'polarity_reversals.json'), 'w') as f:
            json.dump(self.state.polarity_reversals, f)

        with open(os.path.join(self.output_dir, 'final_metrics.json'), 'w') as f:
            json.dump(self.state.to_dict(), f)

    def get_radial_magnetic_field_at_cmb(self) -> np.ndarray:
        cmb_idx = -1
        return self.state.B_r[cmb_idx, :, :]

    def get_temperature_anomaly(self) -> np.ndarray:
        return self.state.T - np.mean(self.state.T)
