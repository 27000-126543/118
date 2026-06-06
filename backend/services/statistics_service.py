import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from backend.config import settings
from backend.models import (
    Simulation, SimulationStatus, DailyStatistics,
    TimeSeriesData, PolarityReversal, GroupFailureStatus,
    UserRole
)


class PhysicalConstants:
    MU0 = 4 * np.pi * 1e-7
    MAGNETIC_DIFFUSIVITY = 2.0
    THERMAL_DIFFUSIVITY = 1e-5
    DENSITY = 13000.0
    GRAVITY = 10.0
    CURRENT_DIPOLE_MOMENT = 8.0e22


class AnimationGenerator:
    def __init__(self, db: Session, simulation_id: int = None):
        self.db = db
        self.simulation_id = simulation_id
        self.mu0 = PhysicalConstants.MU0

    def _get_time_series_data(self, simulation_id: int, max_frames: int = 100) -> Tuple[List[TimeSeriesData], bool]:
        time_series = self.db.query(TimeSeriesData).filter(
            TimeSeriesData.simulation_id == simulation_id
        ).order_by(TimeSeriesData.time_step).all()

        has_sufficient_data = len(time_series) >= 10

        if has_sufficient_data:
            step = max(1, len(time_series) // max_frames)
            sampled_ts = time_series[::step][:max_frames]
            return sampled_ts, True
        else:
            return time_series, False

    def _generate_physical_evolution(self, sim: Simulation, n_frames: int = 100) -> Dict[str, np.ndarray]:
        eta = PhysicalConstants.MAGNETIC_DIFFUSIVITY
        L = sim.core_radius - (sim.inner_core_radius or sim.core_radius * 0.35)
        tau_magnetic = L**2 / eta

        rm = sim.magnetic_reynolds_number or 50.0
        r_critical = sim.magnetic_reynolds_critical or 50.0

        if rm > r_critical:
            relaxation_time = tau_magnetic / rm
            saturation_level = 1.0 + 0.3 * np.tanh((rm - r_critical) / 10.0)
        else:
            relaxation_time = tau_magnetic * 2
            saturation_level = 0.1 * np.exp(-(r_critical - rm) / 10.0)

        t = np.linspace(0, 5 * relaxation_time, n_frames)

        dipole_moment = PhysicalConstants.CURRENT_DIPOLE_MOMENT * saturation_level * (1 - np.exp(-t / relaxation_time))
        dipole_moment += 0.05 * PhysicalConstants.CURRENT_DIPOLE_MOMENT * np.sin(2 * np.pi * t / (relaxation_time * 0.5))
        dipole_moment += 0.02 * PhysicalConstants.CURRENT_DIPOLE_MOMENT * np.sin(2 * np.pi * t / (relaxation_time * 0.2))

        base_tilt = sim.dipole_tilt_threshold or 10.0
        dipole_tilt = base_tilt * (0.3 + 0.4 * (1 - np.exp(-t / (relaxation_time * 2))))
        dipole_tilt += 2.0 * np.sin(2 * np.pi * t / (relaxation_time * 0.8))

        magnetic_energy = (dipole_moment ** 2) / (2 * self.mu0 * L**3) * 1e-6
        kinetic_energy = magnetic_energy / (0.1 + 0.05 * np.sin(2 * np.pi * t / relaxation_time))

        magnetic_reynolds = rm * (1 - 0.2 * np.exp(-t / (relaxation_time * 0.5)))
        magnetic_reynolds += 5.0 * np.sin(2 * np.pi * t / (relaxation_time * 0.3))

        inner_core_symmetry = 0.95 - 0.05 * (1 - np.exp(-t / (relaxation_time * 3)))
        inner_core_symmetry += 0.01 * np.sin(2 * np.pi * t / (relaxation_time * 0.7))

        n_reversals = sim.polarity_reversal_count or 0
        if n_reversals > 0:
            reversal_times = np.linspace(relaxation_time, 4 * relaxation_time, n_reversals)
            for rt in reversal_times:
                mask = np.abs(t - rt) < relaxation_time * 0.1
                dipole_moment[mask] *= np.cos(np.pi * (t[mask] - rt) / (relaxation_time * 0.1))
                dipole_tilt[mask] += 20.0 * np.exp(-((t[mask] - rt) ** 2) / (2 * (relaxation_time * 0.05) ** 2))

        return {
            'time': t,
            'dipole_moment': dipole_moment,
            'dipole_tilt': np.clip(dipole_tilt, 0, 90),
            'magnetic_energy': magnetic_energy,
            'kinetic_energy': kinetic_energy,
            'magnetic_reynolds': magnetic_reynolds,
            'inner_core_symmetry': np.clip(inner_core_symmetry, 0, 1),
            'tau_magnetic': tau_magnetic,
            'relaxation_time': relaxation_time
        }

    def _extract_animation_data(
        self,
        sim: Simulation,
        time_series: List[TimeSeriesData],
        has_sufficient_data: bool,
        n_frames: int = 100
    ) -> Dict[str, np.ndarray]:
        if has_sufficient_data:
            iterations = np.array([ts.time_step for ts in time_series])
            dipole_moment = np.array([ts.dipole_moment or 0.0 for ts in time_series])
            dipole_tilt = np.array([ts.dipole_tilt or 0.0 for ts in time_series])
            magnetic_energy = np.array([ts.magnetic_energy or 0.0 for ts in time_series])
            kinetic_energy = np.array([ts.kinetic_energy or 0.0 for ts in time_series])
            magnetic_reynolds = np.array([ts.magnetic_reynolds or 0.0 for ts in time_series])
            inner_core_symmetry = np.array([ts.inner_core_symmetry or 0.0 for ts in time_series])

            last_valid = 0
            for i in range(len(dipole_moment)):
                if dipole_moment[i] == 0 and last_valid > 0:
                    dipole_moment[i] = dipole_moment[last_valid]
                elif dipole_moment[i] > 0:
                    last_valid = i

            last_valid = 0
            for i in range(len(dipole_tilt)):
                if dipole_tilt[i] == 0 and last_valid > 0:
                    dipole_tilt[i] = dipole_tilt[last_valid]
                elif dipole_tilt[i] > 0:
                    last_valid = i

            if len(iterations) < n_frames:
                x_old = np.arange(len(iterations))
                x_new = np.linspace(0, len(iterations) - 1, n_frames)
                iterations = np.interp(x_new, x_old, iterations)
                dipole_moment = np.interp(x_new, x_old, dipole_moment)
                dipole_tilt = np.interp(x_new, x_old, dipole_tilt)
                magnetic_energy = np.interp(x_new, x_old, magnetic_energy)
                kinetic_energy = np.interp(x_new, x_old, kinetic_energy)
                magnetic_reynolds = np.interp(x_new, x_old, magnetic_reynolds)
                inner_core_symmetry = np.interp(x_new, x_old, inner_core_symmetry)

            return {
                'time': iterations,
                'dipole_moment': dipole_moment,
                'dipole_tilt': dipole_tilt,
                'magnetic_energy': magnetic_energy,
                'kinetic_energy': kinetic_energy,
                'magnetic_reynolds': magnetic_reynolds,
                'inner_core_symmetry': inner_core_symmetry,
                'is_real_data': True
            }
        else:
            phys_data = self._generate_physical_evolution(sim, n_frames)
            phys_data['is_real_data'] = False
            return phys_data

    def generate_magnetic_field_animation(
        self,
        simulation_id: int,
        n_frames: int = 50,
        fps: int = 10
    ) -> Dict[str, Any]:
        sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not sim:
            raise ValueError("Simulation not found")

        time_series, has_sufficient = self._get_time_series_data(simulation_id, max_frames=n_frames)
        data = self._extract_animation_data(sim, time_series, has_sufficient, n_frames)

        output_dir = os.path.join(settings.OUTPUT_DIR, f'sim_{simulation_id}', 'animations')
        os.makedirs(output_dir, exist_ok=True)

        n_theta = 32
        n_phi = 64
        theta = np.linspace(0, np.pi, n_theta)
        phi = np.linspace(0, 2 * np.pi, n_phi)
        Theta, Phi = np.meshgrid(theta, phi, indexing='ij')

        fig = plt.figure(figsize=(14, 6))
        ax1 = plt.subplot(1, 2, 1, projection='mollweide')
        ax2 = plt.subplot(1, 2, 2)

        dipole_mean = np.mean(data['dipole_moment'])

        B_r_phi = np.zeros((n_theta, n_phi))
        for i, th in enumerate(theta):
            for j, ph in enumerate(phi):
                B_r_phi[i, j] = np.cos(th) * np.sin(th) ** 2

        vmax = np.max(np.abs(B_r_phi))
        im = ax1.pcolormesh(Phi - np.pi, Theta - np.pi/2, B_r_phi,
                           cmap='RdBu_r', vmin=-vmax, vmax=vmax, shading='auto')
        ax1.set_title('Radial Magnetic Field at CMB (Mollweide)')
        ax1.grid(True, alpha=0.3)
        plt.colorbar(im, ax=ax1, label='B_r (T)', shrink=0.8)

        line, = ax2.plot([], [], 'b-', linewidth=2)
        ax2.axhline(y=dipole_mean, color='r', linestyle='--', alpha=0.7, label=f'Mean = {dipole_mean:.2e}')
        ax2.set_xlim(0, n_frames)
        ax2.set_ylim(0, np.max(data['dipole_moment']) * 1.1)
        ax2.set_xlabel('Frame')
        ax2.set_ylabel('Dipole Moment (A·m²)')
        ax2.set_title('Dipole Moment Evolution')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        time_text = ax1.text(0.02, 0.95, '', transform=ax1.transAxes,
                            bbox=dict(facecolor='white', alpha=0.8))
        data_text = ax2.text(0.02, 0.95, '', transform=ax2.transAxes,
                            bbox=dict(facecolor='white', alpha=0.8))

        def update(frame):
            scale = 0.8 + 0.2 * np.sin(2 * np.pi * frame / n_frames * 3)
            B_r_phi_current = scale * B_r_phi * (data['dipole_moment'][frame] / dipole_mean)

            im.set_array(B_r_phi_current.ravel())
            im.set_clim(-np.max(np.abs(B_r_phi_current)), np.max(np.abs(B_r_phi_current)))

            line.set_data(np.arange(frame + 1), data['dipole_moment'][:frame + 1])

            time_text.set_text(f'Frame: {frame + 1}/{n_frames}')
            data_type = 'Real' if data.get('is_real_data', False) else 'Synthetic'
            data_text.set_text(f'{data_type} Data\nμ = {data["dipole_moment"][frame]:.2e}')

            return [im, line, time_text, data_text]

        anim = animation.FuncAnimation(
            fig, update, frames=n_frames, interval=1000/fps, blit=True
        )

        mp4_path = os.path.join(output_dir, 'magnetic_field_evolution.mp4')
        gif_path = os.path.join(output_dir, 'magnetic_field_evolution.gif')

        try:
            Writer = animation.writers['ffmpeg']
            writer = Writer(fps=fps, bitrate=2000)
            anim.save(mp4_path, writer=writer)
            output_file = mp4_path
            output_format = 'mp4'
        except Exception:
            anim.save(gif_path, writer='pillow', fps=fps)
            output_file = gif_path
            output_format = 'gif'

        plt.close()

        return {
            'success': True,
            'output_file': output_file,
            'format': output_format,
            'n_frames': n_frames,
            'fps': fps,
            'is_real_data': data.get('is_real_data', False),
            'note': 'Using synthetic physical evolution model' if not data.get('is_real_data', False) else 'Using real simulation data'
        }

    def generate_energy_animation(
        self,
        simulation_id: int,
        n_frames: int = 50,
        fps: int = 10
    ) -> Dict[str, Any]:
        sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not sim:
            raise ValueError("Simulation not found")

        time_series, has_sufficient = self._get_time_series_data(simulation_id, max_frames=n_frames)
        data = self._extract_animation_data(sim, time_series, has_sufficient, n_frames)

        output_dir = os.path.join(settings.OUTPUT_DIR, f'sim_{simulation_id}', 'animations')
        os.makedirs(output_dir, exist_ok=True)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        mag_mean = np.mean(data['magnetic_energy'])
        kin_mean = np.mean(data['kinetic_energy'])

        line_mag, = ax1.semilogy([], [], 'b-', linewidth=2, label='Magnetic Energy')
        line_kin, = ax1.semilogy([], [], 'r-', linewidth=2, label='Kinetic Energy')
        ax1.axhline(y=mag_mean, color='b', linestyle='--', alpha=0.5, label=f'Mag Mean = {mag_mean:.2e}')
        ax1.axhline(y=kin_mean, color='r', linestyle='--', alpha=0.5, label=f'Kin Mean = {kin_mean:.2e}')
        ax1.set_xlim(0, n_frames)
        ax1.set_ylim(min(np.min(data['magnetic_energy']), np.min(data['kinetic_energy'])) * 0.5,
                    max(np.max(data['magnetic_energy']), np.max(data['kinetic_energy'])) * 2)
        ax1.set_xlabel('Frame')
        ax1.set_ylabel('Energy (J)')
        ax1.set_title('Energy Evolution')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ratio = data['magnetic_energy'] / np.maximum(data['kinetic_energy'], 1e-10)
        line_ratio, = ax2.plot([], [], 'g-', linewidth=2)
        ax2.axhline(y=1.0, color='k', linestyle='--', alpha=0.5, label='Equal Energy')
        ax2.set_xlim(0, n_frames)
        ax2.set_ylim(0, np.max(ratio) * 1.2)
        ax2.set_xlabel('Frame')
        ax2.set_ylabel('Magnetic / Kinetic Energy')
        ax2.set_title('Energy Partition')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        time_text = ax1.text(0.02, 0.95, '', transform=ax1.transAxes,
                            bbox=dict(facecolor='white', alpha=0.8))
        data_text = ax2.text(0.02, 0.95, '', transform=ax2.transAxes,
                            bbox=dict(facecolor='white', alpha=0.8))

        def update(frame):
            line_mag.set_data(np.arange(frame + 1), data['magnetic_energy'][:frame + 1])
            line_kin.set_data(np.arange(frame + 1), data['kinetic_energy'][:frame + 1])
            line_ratio.set_data(np.arange(frame + 1), ratio[:frame + 1])

            time_text.set_text(f'Frame: {frame + 1}/{n_frames}')
            data_type = 'Real' if data.get('is_real_data', False) else 'Synthetic'
            current_ratio = ratio[frame]
            data_text.set_text(f'{data_type} Data\nRatio = {current_ratio:.3f}')

            return [line_mag, line_kin, line_ratio, time_text, data_text]

        anim = animation.FuncAnimation(
            fig, update, frames=n_frames, interval=1000/fps, blit=True
        )

        return self._save_animation(anim, output_dir, 'energy_evolution', n_frames, fps, data)

    def generate_dipole_animation(
        self,
        simulation_id: int,
        n_frames: int = 50,
        fps: int = 10
    ) -> Dict[str, Any]:
        sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not sim:
            raise ValueError("Simulation not found")

        time_series, has_sufficient = self._get_time_series_data(simulation_id, max_frames=n_frames)
        data = self._extract_animation_data(sim, time_series, has_sufficient, n_frames)

        output_dir = os.path.join(settings.OUTPUT_DIR, f'sim_{simulation_id}', 'animations')
        os.makedirs(output_dir, exist_ok=True)

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        ax1, ax2 = axes[0]
        ax3, ax4 = axes[1]

        lines = []

        line1, = ax1.plot([], [], 'g-', linewidth=2)
        ax1.axhline(y=PhysicalConstants.CURRENT_DIPOLE_MOMENT, color='k', linestyle='--', alpha=0.5, label='Current Earth')
        ax1.set_xlim(0, n_frames)
        ax1.set_ylim(0, np.max(data['dipole_moment']) * 1.1)
        ax1.set_xlabel('Frame')
        ax1.set_ylabel('Dipole Moment (A·m²)')
        ax1.set_title('Dipole Moment Evolution')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        lines.append(line1)

        tilt_threshold = sim.dipole_tilt_threshold or 10.0
        line2, = ax2.plot([], [], 'r-', linewidth=2)
        ax2.axhline(y=tilt_threshold, color='k', linestyle='--', alpha=0.7, label=f'Threshold = {tilt_threshold}°')
        ax2.set_xlim(0, n_frames)
        ax2.set_ylim(0, max(np.max(data['dipole_tilt']), tilt_threshold * 1.2))
        ax2.set_xlabel('Frame')
        ax2.set_ylabel('Dipole Tilt (deg)')
        ax2.set_title('Dipole Tilt Angle')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        lines.append(line2)

        rm_critical = sim.magnetic_reynolds_critical or 50.0
        line3, = ax3.plot([], [], 'm-', linewidth=2)
        ax3.axhline(y=rm_critical, color='k', linestyle='--', alpha=0.7, label=f'Critical = {rm_critical}')
        ax3.set_xlim(0, n_frames)
        ax3.set_ylim(0, max(np.max(data['magnetic_reynolds']), rm_critical * 1.2))
        ax3.set_xlabel('Frame')
        ax3.set_ylabel('Magnetic Reynolds Number')
        ax3.set_title('Magnetic Reynolds Number')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        lines.append(line3)

        line4, = ax4.plot([], [], 'c-', linewidth=2)
        ax4.axhline(y=0.9, color='k', linestyle='--', alpha=0.7, label='Warning Threshold = 0.9')
        ax4.set_xlim(0, n_frames)
        ax4.set_ylim(0.5, 1.0)
        ax4.set_xlabel('Frame')
        ax4.set_ylabel('Inner Core Symmetry')
        ax4.set_title('Inner Core Symmetry')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        lines.append(line4)

        plt.tight_layout()

        time_text = fig.text(0.02, 0.98, '',
                            bbox=dict(facecolor='white', alpha=0.8))

        def update(frame):
            lines[0].set_data(np.arange(frame + 1), data['dipole_moment'][:frame + 1])
            lines[1].set_data(np.arange(frame + 1), data['dipole_tilt'][:frame + 1])
            lines[2].set_data(np.arange(frame + 1), data['magnetic_reynolds'][:frame + 1])
            lines[3].set_data(np.arange(frame + 1), data['inner_core_symmetry'][:frame + 1])

            data_type = 'Real' if data.get('is_real_data', False) else 'Synthetic'
            time_text.set_text(f'Frame: {frame + 1}/{n_frames} | {data_type} Data')

            return lines + [time_text]

        anim = animation.FuncAnimation(
            fig, update, frames=n_frames, interval=1000/fps, blit=True
        )

        return self._save_animation(anim, output_dir, 'dipole_evolution', n_frames, fps, data)

    def _save_animation(
        self,
        anim: animation.FuncAnimation,
        output_dir: str,
        base_name: str,
        n_frames: int,
        fps: int,
        data: Dict[str, np.ndarray]
    ) -> Dict[str, Any]:
        mp4_path = os.path.join(output_dir, f'{base_name}.mp4')
        gif_path = os.path.join(output_dir, f'{base_name}.gif')

        output_file = ''
        output_format = ''

        try:
            Writer = animation.writers['ffmpeg']
            writer = Writer(fps=fps, bitrate=2000)
            anim.save(mp4_path, writer=writer)
            output_file = mp4_path
            output_format = 'mp4'
        except Exception:
            try:
                anim.save(gif_path, writer='pillow', fps=fps)
                output_file = gif_path
                output_format = 'gif'
            except Exception as e:
                plt.close()
                return {
                    'success': False,
                    'error': str(e),
                    'note': 'Both MP4 and GIF writers failed'
                }

        plt.close()

        return {
            'success': True,
            'output_file': output_file,
            'format': output_format,
            'n_frames': n_frames,
            'fps': fps,
            'is_real_data': data.get('is_real_data', False),
            'note': 'Using synthetic physical evolution model' if not data.get('is_real_data', False) else 'Using real simulation data'
        }


class StatisticsService:
    def __init__(self, db: Session):
        self.db = db
        self.animation_generator = AnimationGenerator(db)

    def generate_daily_statistics(self, date: Optional[datetime] = None) -> DailyStatistics:
        if date is None:
            date = datetime.now().date()

        start_date = datetime.combine(date, datetime.min.time())
        end_date = start_date + timedelta(days=1)

        total_simulations = self.db.query(Simulation).filter(
            Simulation.created_at >= start_date,
            Simulation.created_at < end_date
        ).count()

        completed_simulations = self.db.query(Simulation).filter(
            Simulation.completed_at >= start_date,
            Simulation.completed_at < end_date,
            Simulation.status == SimulationStatus.COMPLETED
        ).count()

        failed_simulations = self.db.query(Simulation).filter(
            Simulation.completed_at >= start_date,
            Simulation.completed_at < end_date,
            Simulation.status == SimulationStatus.ERROR
        ).count()

        completion_rate = completed_simulations / max(total_simulations, 1)

        completed_sims = self.db.query(Simulation).filter(
            Simulation.completed_at >= start_date,
            Simulation.completed_at < end_date,
            Simulation.status == SimulationStatus.COMPLETED
        ).all()

        avg_efficiency = 0.0
        avg_reversal_freq = 0.0
        if completed_sims:
            efficiencies = [s.magnetic_energy_generation_efficiency for s in completed_sims if s.magnetic_energy_generation_efficiency]
            if efficiencies:
                avg_efficiency = float(np.mean(efficiencies))

            total_iters = sum(s.current_iteration or 0 for s in completed_sims)
            total_reversals = sum(s.polarity_reversal_count or 0 for s in completed_sims)
            if total_iters > 0:
                avg_reversal_freq = float(total_reversals / total_iters * 1000)

        total_reversals = self.db.query(PolarityReversal).filter(
            PolarityReversal.start_time >= start_date,
            PolarityReversal.start_time < end_date
        ).count()

        stats = DailyStatistics(
            date=date,
            total_simulations=total_simulations,
            completed_simulations=completed_simulations,
            failed_simulations=failed_simulations,
            completion_rate=completion_rate,
            avg_magnetic_energy_generation_efficiency=avg_efficiency,
            avg_polarity_reversal_frequency=avg_reversal_freq,
            total_polarity_reversals=total_reversals
        )

        existing = self.db.query(DailyStatistics).filter(DailyStatistics.date == date).first()
        if existing:
            existing.total_simulations = total_simulations
            existing.completed_simulations = completed_simulations
            existing.failed_simulations = failed_simulations
            existing.completion_rate = completion_rate
            existing.avg_magnetic_energy_generation_efficiency = avg_efficiency
            existing.avg_polarity_reversal_frequency = avg_reversal_freq
            existing.total_polarity_reversals = total_reversals
            existing.updated_at = datetime.now()
            stats = existing
        else:
            self.db.add(stats)

        self.db.commit()
        return stats

    def get_dashboard_data(self, days: int = 30) -> Dict[str, Any]:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        stats = self.db.query(DailyStatistics).filter(
            DailyStatistics.date >= start_date,
            DailyStatistics.date <= end_date
        ).order_by(DailyStatistics.date).all()

        if not stats:
            self.generate_daily_statistics(end_date)
            stats = self.db.query(DailyStatistics).filter(
                DailyStatistics.date >= start_date,
                DailyStatistics.date <= end_date
            ).order_by(DailyStatistics.date).all()

        total_simulations = self.db.query(Simulation).count()
        running_simulations = self.db.query(Simulation).filter(
            Simulation.status.in_([
                SimulationStatus.MESH_GENERATION,
                SimulationStatus.INITIALIZATION,
                SimulationStatus.DYNAMO_ITERATION
            ])
        ).count()
        completed_simulations = self.db.query(Simulation).filter(
            Simulation.status == SimulationStatus.COMPLETED
        ).count()
        failed_simulations = self.db.query(Simulation).filter(
            Simulation.status == SimulationStatus.ERROR
        ).count()

        recent_simulations = self.db.query(Simulation).order_by(
            Simulation.created_at.desc()
        ).limit(10).all()

        recent_alerts = []

        performance_trend = [
            {
                'date': s.date.strftime('%Y-%m-%d'),
                'completion_rate': s.completion_rate,
                'avg_efficiency': s.avg_magnetic_energy_generation_efficiency,
                'reversal_frequency': s.avg_polarity_reversal_frequency
            }
            for s in stats
        ]

        paused_groups = self.db.query(GroupFailureStatus).filter(
            GroupFailureStatus.is_paused == True
        ).all()

        return {
            'summary': {
                'total_simulations': total_simulations,
                'running_simulations': running_simulations,
                'completed_simulations': completed_simulations,
                'failed_simulations': failed_simulations,
                'success_rate': completed_simulations / max(total_simulations, 1)
            },
            'recent_simulations': [
                {
                    'id': s.id,
                    'name': s.name,
                    'status': s.status,
                    'progress': s.progress,
                    'created_at': s.created_at.isoformat() if s.created_at else None
                }
                for s in recent_simulations
            ],
            'recent_alerts': recent_alerts,
            'performance_trend': performance_trend,
            'paused_groups': [
                {
                    'group_name': g.group_name,
                    'consecutive_failures': g.consecutive_failures,
                    'paused_at': g.paused_at.isoformat() if g.paused_at else None,
                    'paused_by': g.paused_by
                }
                for g in paused_groups
            ]
        }

    def generate_magnetic_field_animation(
        self,
        simulation_id: int,
        n_frames: int = 50,
        fps: int = 10
    ) -> Dict[str, Any]:
        return self.animation_generator.generate_magnetic_field_animation(
            simulation_id, n_frames, fps
        )

    def generate_energy_animation(
        self,
        simulation_id: int,
        n_frames: int = 50,
        fps: int = 10
    ) -> Dict[str, Any]:
        return self.animation_generator.generate_energy_animation(
            simulation_id, n_frames, fps
        )

    def generate_dipole_animation(
        self,
        simulation_id: int,
        n_frames: int = 50,
        fps: int = 10
    ) -> Dict[str, Any]:
        return self.animation_generator.generate_dipole_animation(
            simulation_id, n_frames, fps
        )

    def generate_all_animations(
        self,
        simulation_id: int,
        n_frames: int = 50,
        fps: int = 10
    ) -> Dict[str, Any]:
        results = {}
        results['magnetic_field'] = self.generate_magnetic_field_animation(simulation_id, n_frames, fps)
        results['energy'] = self.generate_energy_animation(simulation_id, n_frames, fps)
        results['dipole'] = self.generate_dipole_animation(simulation_id, n_frames, fps)

        all_success = all(r.get('success', False) for r in results.values())

        return {
            'success': all_success,
            'simulation_id': simulation_id,
            'results': results,
            'files': [
                r['output_file'] for r in results.values() if r.get('success')
            ]
        }

    def check_consecutive_failures(self, group_name: str) -> Tuple[int, bool]:
        recent_failures = self.db.query(Simulation).filter(
            Simulation.group_name == group_name,
            Simulation.status == SimulationStatus.ERROR
        ).order_by(Simulation.completed_at.desc()).limit(3).all()

        consecutive_failures = 0
        for sim in recent_failures:
            if sim.error_message and any(
                keyword in sim.error_message.lower()
                for keyword in ['divergence', 'nan', 'inf', 'energy', 'unstable']
            ):
                consecutive_failures += 1
            else:
                break

        should_pause = consecutive_failures >= 3
        return consecutive_failures, should_pause

    def pause_group(self, group_name: str, paused_by: str) -> GroupFailureStatus:
        status = self.db.query(GroupFailureStatus).filter(
            GroupFailureStatus.group_name == group_name
        ).first()

        if not status:
            status = GroupFailureStatus(group_name=group_name)

        status.consecutive_failures = 3
        status.is_paused = True
        status.paused_at = datetime.now()
        status.paused_by = paused_by

        self.db.add(status)
        self.db.commit()
        return status
