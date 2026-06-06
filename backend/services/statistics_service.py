import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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


class StatisticsService:
    def __init__(self, db: Session):
        self.db = db
        self.dashboard_dir = os.path.join(settings.REPORT_DIR, 'dashboard')
        os.makedirs(self.dashboard_dir, exist_ok=True)

    def generate_daily_statistics(self, date: Optional[datetime] = None) -> DailyStatistics:
        if date is None:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        next_date = date + timedelta(days=1)

        total_simulations = self.db.query(Simulation).filter(
            Simulation.created_at >= date,
            Simulation.created_at < next_date
        ).count()

        completed_simulations = self.db.query(Simulation).filter(
            Simulation.completed_at >= date,
            Simulation.completed_at < next_date,
            Simulation.status == SimulationStatus.COMPLETED
        ).count()

        completion_rate = completed_simulations / max(total_simulations, 1)

        completed_sims = self.db.query(Simulation).filter(
            Simulation.completed_at >= date,
            Simulation.completed_at < next_date,
            Simulation.status == SimulationStatus.COMPLETED
        ).all()

        avg_efficiency = 0.0
        avg_iterations = 0.0
        avg_duration = 0.0
        total_reversals = 0

        if completed_sims:
            efficiencies = [s.magnetic_energy_generation_efficiency or 0 for s in completed_sims]
            iterations = [s.current_iteration for s in completed_sims]
            durations = []
            for s in completed_sims:
                if s.started_at and s.completed_at:
                    durations.append((s.completed_at - s.started_at).total_seconds() / 3600.0)

            avg_efficiency = float(np.mean(efficiencies)) if efficiencies else 0
            avg_iterations = float(np.mean(iterations)) if iterations else 0
            avg_duration = float(np.mean(durations)) if durations else 0

            sim_ids = [s.id for s in completed_sims]
            if sim_ids:
                total_reversals = self.db.query(func.sum(Simulation.polarity_reversal_count)).filter(
                    Simulation.id.in_(sim_ids)
                ).scalar() or 0

        error_count = self.db.query(Simulation).filter(
            Simulation.updated_at >= date,
            Simulation.updated_at < next_date,
            Simulation.status == SimulationStatus.ERROR
        ).count()

        reversal_frequency = total_reversals / max(completed_simulations, 1)

        existing = self.db.query(DailyStatistics).filter(
            func.date(DailyStatistics.date) == date.date()
        ).first()

        if existing:
            existing.total_simulations = total_simulations
            existing.completed_simulations = completed_simulations
            existing.completion_rate = completion_rate
            existing.avg_magnetic_energy_efficiency = avg_efficiency
            existing.polarity_reversal_frequency = reversal_frequency
            existing.avg_iterations_per_simulation = avg_iterations
            existing.avg_simulation_duration_hours = avg_duration
            existing.error_count = error_count
            stats = existing
        else:
            stats = DailyStatistics(
                date=date,
                total_simulations=total_simulations,
                completed_simulations=completed_simulations,
                completion_rate=completion_rate,
                avg_magnetic_energy_efficiency=avg_efficiency,
                polarity_reversal_frequency=reversal_frequency,
                avg_iterations_per_simulation=avg_iterations,
                avg_simulation_duration_hours=avg_duration,
                error_count=error_count
            )
            self.db.add(stats)

        self.db.commit()
        self.db.refresh(stats)
        return stats

    def get_daily_statistics(self, days: int = 30) -> List[DailyStatistics]:
        start_date = datetime.utcnow() - timedelta(days=days)
        return self.db.query(DailyStatistics).filter(
            DailyStatistics.date >= start_date
        ).order_by(DailyStatistics.date).all()

    def generate_dashboard_charts(self, days: int = 30) -> Dict[str, str]:
        stats = self.get_daily_statistics(days)

        charts = {}

        dates = [s.date.strftime('%Y-%m-%d') for s in stats]

        fig, ax1 = plt.subplots(figsize=(14, 6))

        completion_rates = [s.completion_rate * 100 for s in stats]
        error_counts = [s.error_count for s in stats]

        ax1.bar(dates, completion_rates, alpha=0.7, label='完成率 (%)', color='steelblue')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('完成率 (%)', color='steelblue')
        ax1.tick_params(axis='y', labelcolor='steelblue')
        ax1.set_ylim(0, 100)

        ax2 = ax1.twinx()
        ax2.plot(dates, error_counts, 'r-o', label='错误数', linewidth=2, markersize=6)
        ax2.set_ylabel('错误数', color='red')
        ax2.tick_params(axis='y', labelcolor='red')

        plt.title(f'近{days}天模拟完成率与错误数趋势')
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        plt.xticks(rotation=45)
        plt.tight_layout()

        filepath = os.path.join(self.dashboard_dir, 'completion_trend.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        charts['completion_trend'] = filepath

        fig, ax = plt.subplots(figsize=(14, 6))

        avg_efficiency = [s.avg_magnetic_energy_efficiency for s in stats]
        reversal_freq = [s.polarity_reversal_frequency for s in stats]

        ax.plot(dates, avg_efficiency, 'b-o', label='平均磁能生成效率', linewidth=2, markersize=6)
        ax.plot(dates, reversal_freq, 'g-s', label='极性反转频率', linewidth=2, markersize=6)
        ax.set_xlabel('日期')
        ax.set_ylabel('效率 / 频率')
        ax.set_title(f'近{days}天磁能生成效率与极性反转频率')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()

        filepath = os.path.join(self.dashboard_dir, 'efficiency_trend.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        charts['efficiency_trend'] = filepath

        fig, ax = plt.subplots(figsize=(14, 6))

        avg_iterations = [s.avg_iterations_per_simulation for s in stats]
        avg_duration = [s.avg_simulation_duration_hours for s in stats]

        ax.bar(dates, avg_iterations, alpha=0.6, label='平均迭代次数', color='purple')
        ax.set_xlabel('日期')
        ax.set_ylabel('平均迭代次数', color='purple')
        ax.tick_params(axis='y', labelcolor='purple')

        ax3 = ax.twinx()
        ax3.plot(dates, avg_duration, 'r-o', label='平均时长 (小时)', linewidth=2, markersize=6)
        ax3.set_ylabel('平均时长 (小时)', color='red')
        ax3.tick_params(axis='y', labelcolor='red')

        plt.title(f'近{days}天模拟计算性能指标')
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax3.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        plt.xticks(rotation=45)
        plt.tight_layout()

        filepath = os.path.join(self.dashboard_dir, 'performance_trend.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        charts['performance_trend'] = filepath

        return charts

    def generate_magnetic_field_animation(
        self,
        simulation_id: int,
        output_format: str = 'mp4',
        max_frames: int = 100
    ) -> str:
        sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not sim:
            raise ValueError("Simulation not found")

        time_series = self.db.query(TimeSeriesData).filter(
            TimeSeriesData.simulation_id == simulation_id
        ).order_by(TimeSeriesData.time_step).all()

        if not time_series:
            raise ValueError("No time series data available")

        step = max(1, len(time_series) // max_frames)
        sampled_ts = time_series[::step][:max_frames]

        output_dir = os.path.join(sim.output_dir, 'animation')
        os.makedirs(output_dir, exist_ok=True)

        import matplotlib.animation as animation

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        iterations = [ts.time_step for ts in sampled_ts]
        dipole_moments = [ts.dipole_moment or 0 for ts in sampled_ts]
        dipole_tilts = [ts.dipole_tilt or 0 for ts in sampled_ts]
        magnetic_energies = [ts.magnetic_energy or 0 for ts in sampled_ts]

        ax1.set_xlim(0, max(iterations))
        ax1.set_ylim(min(dipole_moments) * 0.9, max(dipole_moments) * 1.1 if max(dipole_moments) > 0 else 1)
        line1, = ax1.plot([], [], 'b-', linewidth=2, label='偶极矩')
        ax1.set_xlabel('迭代次数')
        ax1.set_ylabel('偶极矩 (A·m²)')
        ax1.set_title('偶极矩演化')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.set_xlim(0, max(iterations))
        ax2.set_ylim(0, max(max(dipole_tilts), 90) * 1.1)
        line2, = ax2.plot([], [], 'r-', linewidth=2, label='倾斜角')
        ax2.axhline(y=10, color='k', linestyle='--', label='10° 阈值')
        ax2.set_xlabel('迭代次数')
        ax2.set_ylabel('偶极子倾斜角 (°)')
        ax2.set_title('偶极子倾斜角演化')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        title = fig.suptitle(f'模拟 #{simulation_id}: {sim.name}', fontsize=14)

        def init():
            line1.set_data([], [])
            line2.set_data([], [])
            return line1, line2

        def animate(frame):
            line1.set_data(iterations[:frame+1], dipole_moments[:frame+1])
            line2.set_data(iterations[:frame+1], dipole_tilts[:frame+1])
            title.set_text(f'模拟 #{simulation_id}: {sim.name} - 迭代 {iterations[frame]}')
            return line1, line2, title

        anim = animation.FuncAnimation(
            fig, animate, init_func=init,
            frames=len(sampled_ts), interval=100, blit=True
        )

        output_file = os.path.join(output_dir, f'magnetic_evolution.{output_format}')

        if output_format == 'mp4':
            try:
                anim.save(output_file, writer='ffmpeg', fps=10, dpi=100)
            except Exception:
                anim.save(output_file.replace('.mp4', '.gif'), writer='pillow', fps=10, dpi=100)
                output_file = output_file.replace('.mp4', '.gif')
        else:
            anim.save(output_file, writer='pillow', fps=10, dpi=100)

        plt.close()
        return output_file

    def get_overall_statistics(self) -> Dict[str, Any]:
        total_simulations = self.db.query(Simulation).count()
        completed_simulations = self.db.query(Simulation).filter(
            Simulation.status == SimulationStatus.COMPLETED
        ).count()
        running_simulations = self.db.query(Simulation).filter(
            Simulation.status == SimulationStatus.ITERATING
        ).count()
        error_simulations = self.db.query(Simulation).filter(
            Simulation.status == SimulationStatus.ERROR
        ).count()
        pending_simulations = self.db.query(Simulation).filter(
            Simulation.status == SimulationStatus.PENDING_VERIFICATION
        ).count()

        total_reversals = self.db.query(func.sum(Simulation.polarity_reversal_count)).scalar() or 0

        approved_simulations = self.db.query(Simulation).filter(
            Simulation.approval_status == '教授通过'
        ).count()

        total_users = self.db.query(func.count('*')).select_from(Simulation.owner).scalar() or 0

        group_statuses = self.db.query(GroupFailureStatus).all()
        paused_groups = [g for g in group_statuses if g.is_paused]

        return {
            'total_simulations': total_simulations,
            'completed_simulations': completed_simulations,
            'running_simulations': running_simulations,
            'error_simulations': error_simulations,
            'pending_simulations': pending_simulations,
            'overall_completion_rate': completed_simulations / max(total_simulations, 1),
            'total_polarity_reversals': total_reversals,
            'approved_simulations': approved_simulations,
            'approval_rate': approved_simulations / max(completed_simulations, 1),
            'paused_groups': [g.group_name for g in paused_groups],
            'total_consecutive_failures': sum(g.consecutive_failures for g in group_statuses)
        }

    def get_heatmap_data(self, days: int = 30) -> Dict[str, Any]:
        sims = self.db.query(Simulation).filter(
            Simulation.created_at >= datetime.utcnow() - timedelta(days=days)
        ).all()

        viscosity_range = []
        heat_flux_range = []
        dipole_moments = []
        reversal_counts = []

        for sim in sims:
            if sim.viscosity and sim.icb_heat_flux:
                viscosity_range.append(float(sim.viscosity))
                heat_flux_range.append(float(sim.icb_heat_flux))
                dipole_moments.append(float(sim.dipole_moment or 0))
                reversal_counts.append(int(sim.polarity_reversal_count or 0))

        return {
            'viscosity_range': viscosity_range,
            'heat_flux_range': heat_flux_range,
            'dipole_moments': dipole_moments,
            'reversal_counts': reversal_counts,
            'simulation_count': len(sims)
        }

    def get_dashboard_data(self, days: int = 30) -> Dict[str, Any]:
        charts = self.generate_dashboard_charts(days)
        overall = self.get_overall_statistics()
        daily_stats = self.get_daily_statistics(days)
        heatmap = self.get_heatmap_data(days)

        return {
            'overall_statistics': overall,
            'daily_statistics': [
                {
                    'date': s.date.strftime('%Y-%m-%d'),
                    'total_simulations': s.total_simulations,
                    'completed_simulations': s.completed_simulations,
                    'completion_rate': s.completion_rate,
                    'avg_magnetic_energy_efficiency': s.avg_magnetic_energy_efficiency,
                    'polarity_reversal_frequency': s.polarity_reversal_frequency,
                    'avg_iterations_per_simulation': s.avg_iterations_per_simulation,
                    'avg_simulation_duration_hours': s.avg_simulation_duration_hours,
                    'error_count': s.error_count
                }
                for s in daily_stats
            ],
            'charts': charts,
            'heatmap_data': heatmap
        }
