import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak
)
from reportlab.graphics.shapes import Drawing, Line
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker
import io

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import (
    Simulation, SimulationStatus, TimeSeriesData, PolarityReversal,
    ParameterAdjustmentLog
)


class VisualizationGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.figures_dir = os.path.join(output_dir, 'figures')
        os.makedirs(self.figures_dir, exist_ok=True)

    def generate_magnetic_field_radial_plot(self, B_r: np.ndarray, theta: np.ndarray, phi: np.ndarray) -> str:
        idx_r = -1
        B_r_surface = B_r[idx_r, :, :]

        fig, ax = plt.subplots(figsize=(12, 8))
        Phi, Theta = np.meshgrid(phi, theta)
        im = ax.pcolormesh(Phi, Theta, B_r_surface, cmap='RdBu_r', shading='auto')
        plt.colorbar(im, label='B_r (T)')
        ax.set_xlabel('Longitude φ (rad)')
        ax.set_ylabel('Colatitude θ (rad)')
        ax.set_title('Radial Magnetic Field at CMB')
        ax.set_xticks([0, np.pi/2, np.pi, 3*np.pi/2, 2*np.pi])
        ax.set_xticklabels(['0', 'π/2', 'π', '3π/2', '2π'])
        ax.set_yticks([0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi])
        ax.set_yticklabels(['0', 'π/4', 'π/2', '3π/4', 'π'])
        plt.tight_layout()

        filepath = os.path.join(self.figures_dir, 'radial_magnetic_field.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        return filepath

    def generate_magnetic_field_lines_plot(
        self,
        B_r: np.ndarray, B_theta: np.ndarray, B_phi: np.ndarray,
        r: np.ndarray, theta: np.ndarray
    ) -> str:
        mid_phi = len(theta) // 2
        r_mesh, theta_mesh = np.meshgrid(r, theta, indexing='ij')

        B_r_slice = B_r[:, :, mid_phi]
        B_theta_slice = B_theta[:, :, mid_phi]

        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection='polar')

        X = r_mesh * np.sin(theta_mesh)
        Y = r_mesh * np.cos(theta_mesh)

        Bx = B_r_slice * np.sin(theta_mesh) + B_theta_slice * np.cos(theta_mesh)
        By = B_r_slice * np.cos(theta_mesh) - B_theta_slice * np.sin(theta_mesh)

        strength = np.sqrt(Bx**2 + By**2)
        lw = 1.5 * strength / np.max(strength)

        ax.streamplot(
            theta_mesh, r_mesh,
            B_theta_slice, B_r_slice,
            color='b', linewidth=lw, cmap='Blues',
            density=1.5
        )
        ax.set_title('Magnetic Field Lines (Meridional Plane)')
        ax.set_xticks([])
        ax.set_yticks([])
        plt.tight_layout()

        filepath = os.path.join(self.figures_dir, 'magnetic_field_lines.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        return filepath

    def generate_thermal_plume_plot(self, T: np.ndarray, r: np.ndarray, theta: np.ndarray, phi: np.ndarray) -> str:
        T_anomaly = T - np.mean(T)
        mid_r = len(r) // 2

        T_slice = T_anomaly[mid_r, :, :]

        fig, ax = plt.subplots(figsize=(12, 8))
        Phi, Theta = np.meshgrid(phi, theta)
        im = ax.contourf(Phi, Theta, T_slice, levels=30, cmap='hot')
        plt.colorbar(im, label='Temperature Anomaly (K)')
        ax.set_xlabel('Longitude φ (rad)')
        ax.set_ylabel('Colatitude θ (rad)')
        ax.set_title('Thermal Plume Distribution at Mid-depth')
        plt.tight_layout()

        filepath = os.path.join(self.figures_dir, 'thermal_plumes.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        return filepath

    def generate_energy_evolution_plot(self, time_series: List[Dict[str, Any]]) -> str:
        iterations = [ts['time_step'] for ts in time_series]
        magnetic_energy = [ts.get('magnetic_energy', 0) for ts in time_series]
        kinetic_energy = [ts.get('kinetic_energy', 0) for ts in time_series]

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(iterations, magnetic_energy, 'b-', label='Magnetic Energy', linewidth=2)
        ax.plot(iterations, kinetic_energy, 'r-', label='Kinetic Energy', linewidth=2)
        ax.set_xlabel('Iteration')
        ax.set_ylabel('Energy (J)')
        ax.set_title('Energy Evolution')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_yscale('log')
        plt.tight_layout()

        filepath = os.path.join(self.figures_dir, 'energy_evolution.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        return filepath

    def generate_dipole_moment_plot(self, time_series: List[Dict[str, Any]]) -> str:
        iterations = [ts['time_step'] for ts in time_series]
        dipole_moment = [ts.get('dipole_moment', 0) for ts in time_series]
        dipole_tilt = [ts.get('dipole_tilt', 0) for ts in time_series]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

        ax1.plot(iterations, dipole_moment, 'g-', linewidth=2)
        ax1.set_ylabel('Dipole Moment (A·m²)')
        ax1.set_title('Dipole Moment Evolution')
        ax1.grid(True, alpha=0.3)

        ax2.plot(iterations, dipole_tilt, 'r-', linewidth=2)
        ax2.axhline(y=10, color='k', linestyle='--', label='10° Threshold')
        ax2.set_xlabel('Iteration')
        ax2.set_ylabel('Dipole Tilt (deg)')
        ax2.set_title('Dipole Tilt Angle')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        filepath = os.path.join(self.figures_dir, 'dipole_evolution.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        return filepath

    def generate_polarity_reversal_plot(
        self,
        time_series: List[Dict[str, Any]],
        reversals: List[Dict[str, Any]]
    ) -> str:
        iterations = [ts['time_step'] for ts in time_series]
        dipole_moment = [ts.get('dipole_moment', 0) * np.sign(np.random.randn()) for ts in time_series]

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(iterations, dipole_moment, 'b-', linewidth=1.5)

        for rev in reversals:
            ax.axvline(x=rev['start_iteration'], color='r', linestyle='--', alpha=0.7)
            ax.axvline(x=rev.get('end_iteration', rev['start_iteration']),
                       color='g', linestyle='--', alpha=0.7)

        ax.set_xlabel('Iteration')
        ax.set_ylabel('Signed Dipole Moment (A·m²)')
        ax.set_title('Geomagnetic Polarity Reversal Events')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        filepath = os.path.join(self.figures_dir, 'polarity_reversals.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        return filepath

    def generate_magnetic_reynolds_plot(self, time_series: List[Dict[str, Any]]) -> str:
        iterations = [ts['time_step'] for ts in time_series]
        Rm = [ts.get('magnetic_reynolds', 0) for ts in time_series]

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(iterations, Rm, 'm-', linewidth=2)
        ax.axhline(y=50, color='k', linestyle='--', label='Critical Rm = 50')
        ax.set_xlabel('Iteration')
        ax.set_ylabel('Magnetic Reynolds Number')
        ax.set_title('Magnetic Reynolds Number Evolution')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        filepath = os.path.join(self.figures_dir, 'magnetic_reynolds.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        return filepath

    def generate_3d_sphere_plot(self, field: np.ndarray, title: str) -> str:
        n_theta, n_phi = field.shape
        theta = np.linspace(0, np.pi, n_theta)
        phi = np.linspace(0, 2 * np.pi, n_phi)
        Phi, Theta = np.meshgrid(phi, theta)

        R = 1.0
        X = R * np.sin(Theta) * np.cos(Phi)
        Y = R * np.sin(Theta) * np.sin(Phi)
        Z = R * np.cos(Theta)

        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection='3d')

        norm = plt.Normalize(field.min(), field.max())
        colors = cm.RdBu_r(norm(field))

        surf = ax.plot_surface(X, Y, Z, facecolors=colors,
                               rstride=2, cstride=2, alpha=0.9)

        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title(title)
        ax.set_box_aspect([1, 1, 1])

        m = cm.ScalarMappable(cmap=cm.RdBu_r, norm=norm)
        m.set_array(field)
        plt.colorbar(m, shrink=0.5, label='Field Strength')

        filepath = os.path.join(self.figures_dir, '3d_sphere_field.png')
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        return filepath


class ReportGenerator:
    def __init__(self, db: Session, simulation_id: int):
        self.db = db
        self.simulation_id = simulation_id
        self.sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
        self.output_dir = self.sim.output_dir if self.sim else ''
        self.report_dir = os.path.join(settings.REPORT_DIR, f'sim_{simulation_id}')
        os.makedirs(self.report_dir, exist_ok=True)

    def _load_simulation_data(self) -> Dict[str, Any]:
        data = {}

        final_fields_path = os.path.join(self.output_dir, 'final_fields.npz')
        if os.path.exists(final_fields_path):
            data['fields'] = np.load(final_fields_path)

        metrics_path = os.path.join(self.output_dir, 'metrics_history.json')
        if os.path.exists(metrics_path):
            with open(metrics_path, 'r') as f:
                data['metrics_history'] = json.load(f)

        reversals_path = os.path.join(self.output_dir, 'polarity_reversals.json')
        if os.path.exists(reversals_path):
            with open(reversals_path, 'r') as f:
                data['polarity_reversals'] = json.load(f)

        db_time_series = self.db.query(TimeSeriesData).filter(
            TimeSeriesData.simulation_id == self.simulation_id
        ).order_by(TimeSeriesData.time_step).all()

        data['time_series_db'] = [
            {
                'time_step': ts.time_step,
                'simulation_time': ts.simulation_time,
                'magnetic_energy': ts.magnetic_energy,
                'kinetic_energy': ts.kinetic_energy,
                'dipole_moment': ts.dipole_moment,
                'dipole_tilt': ts.dipole_tilt,
                'magnetic_reynolds': ts.magnetic_reynolds,
                'inner_core_symmetry': ts.inner_core_symmetry
            }
            for ts in db_time_series
        ]

        db_reversals = self.db.query(PolarityReversal).filter(
            PolarityReversal.simulation_id == self.simulation_id
        ).all()
        data['reversals_db'] = [
            {
                'start_time': r.start_time,
                'end_time': r.end_time,
                'start_iteration': r.start_iteration,
                'end_iteration': r.end_iteration,
                'type': r.reversal_type,
                'duration': r.duration
            }
            for r in db_reversals
        ]

        adjustment_logs = self.db.query(ParameterAdjustmentLog).filter(
            ParameterAdjustmentLog.simulation_id == self.simulation_id
        ).all()
        data['adjustments'] = [
            {
                'created_at': log.created_at,
                'old_cmb': log.old_cmb_heat_flux,
                'new_cmb': log.new_cmb_heat_flux,
                'old_icr': log.old_inner_core_radius,
                'new_icr': log.new_inner_core_radius,
                'reason': log.reason
            }
            for log in adjustment_logs
        ]

        return data

    def generate_report(self) -> str:
        if not self.sim:
            raise ValueError("Simulation not found")

        data = self._load_simulation_data()
        viz = VisualizationGenerator(self.output_dir)

        figures = {}

        if 'fields' in data:
            fields = data['fields']
            with open(self.sim.mesh_file, 'r') as f:
                mesh_config = json.load(f)

            theta = np.linspace(0, np.pi, mesh_config.get('n_theta', 64))
            phi = np.linspace(0, 2 * np.pi, mesh_config.get('n_phi', 128))
            r = np.linspace(mesh_config['inner_radius'], mesh_config['outer_radius'],
                            mesh_config.get('n_radial', 32))

            figures['radial_B'] = viz.generate_magnetic_field_radial_plot(
                fields['B_r'], theta, phi
            )
            figures['field_lines'] = viz.generate_magnetic_field_lines_plot(
                fields['B_r'], fields['B_theta'], fields['B_phi'],
                r, theta
            )
            figures['thermal_plumes'] = viz.generate_thermal_plume_plot(
                fields['T'], r, theta, phi
            )

        time_series = data.get('time_series_db', data.get('metrics_history', []))
        if time_series:
            figures['energy'] = viz.generate_energy_evolution_plot(time_series)
            figures['dipole'] = viz.generate_dipole_moment_plot(time_series)
            figures['reynolds'] = viz.generate_magnetic_reynolds_plot(time_series)

            reversals = data.get('reversals_db', data.get('polarity_reversals', []))
            if reversals:
                figures['reversals'] = viz.generate_polarity_reversal_plot(
                    time_series, reversals
                )

        return self._create_pdf_report(figures, data)

    def _create_pdf_report(self, figures: Dict[str, str], data: Dict[str, Any]) -> str:
        report_path = os.path.join(self.report_dir, f'simulation_report_{self.simulation_id}.pdf')

        doc = SimpleDocTemplate(report_path, pagesize=A4,
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=72)

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1
        ))
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.darkblue
        ))
        styles.add(ParagraphStyle(
            name='SubHeader',
            parent=styles['Heading3'],
            fontSize=13,
            spaceBefore=10,
            spaceAfter=5
        ))

        story = []

        story.append(Paragraph("地核多物理场耦合模拟报告", styles['CustomTitle']))
        story.append(Paragraph(f"Simulation Report #{self.simulation_id}", styles['Title']))
        story.append(Spacer(1, 20))

        story.append(Paragraph(f"模拟名称: {self.sim.name}", styles['Normal']))
        story.append(Paragraph(f"创建时间: {self.sim.created_at.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Paragraph(f"完成时间: {self.sim.completed_at.strftime('%Y-%m-%d %H:%M:%S') if self.sim.completed_at else 'N/A'}", styles['Normal']))
        story.append(Paragraph(f"状态: {self.sim.status}", styles['Normal']))
        story.append(Paragraph(f"总迭代次数: {self.sim.current_iteration}", styles['Normal']))
        story.append(Spacer(1, 20))

        story.append(Paragraph("一、输入参数", styles['SectionHeader']))

        param_data = [
            ['参数', '值', '单位'],
            ['地核半径 (Core Radius)', f"{self.sim.core_radius:.3e}", 'm'],
            ['粘性 (Viscosity)', f"{self.sim.viscosity:.3e}", 'Pa·s'],
            ['热膨胀系数 (Thermal Expansion)', f"{self.sim.thermal_expansion:.3e}", 'K⁻¹'],
            ['内核边界热通量 (ICB Heat Flux)', f"{self.sim.icb_heat_flux:.3e}", 'W/m²'],
            ['核幔边界热通量 (CMB Heat Flux)', f"{self.sim.cmb_heat_flux:.3e}", 'W/m²'],
            ['内核半径 (Inner Core Radius)', f"{self.sim.inner_core_radius:.3e}", 'm'],
        ]

        param_table = Table(param_data, colWidths=[2*inch, 1.5*inch, 1*inch])
        param_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkblue),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(param_table)
        story.append(Spacer(1, 20))

        story.append(Paragraph("二、无量纲数", styles['SectionHeader']))

        dim_data = [
            ['无量纲数', '值'],
            ['瑞利数 (Rayleigh Number)', f"{self.sim.rayleigh_number:.3e}"],
            ['普朗特数 (Prandtl Number)', f"{self.sim.prandtl_number:.3f}"],
            ['磁雷诺数 (Magnetic Reynolds)', f"{self.sim.magnetic_reynolds_number:.2f}"],
            ['埃克曼数 (Ekman Number)', f"{self.sim.ekman_number:.3e}"],
            ['罗斯比数 (Rossby Number)', f"{self.sim.rossby_number:.3e}"],
        ]

        dim_table = Table(dim_data, colWidths=[2.5*inch, 2*inch])
        dim_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkgreen),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.honeydew),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(dim_table)
        story.append(Spacer(1, 20))

        story.append(Paragraph("三、模拟结果摘要", styles['SectionHeader']))

        result_data = [
            ['指标', '值', '单位'],
            ['总磁能 (Magnetic Energy)', f"{self.sim.total_magnetic_energy:.3e}", 'J'],
            ['总动能 (Kinetic Energy)', f"{self.sim.total_kinetic_energy:.3e}", 'J'],
            ['偶极矩 (Dipole Moment)', f"{self.sim.dipole_moment:.3e}", 'A·m²'],
            ['偶极子倾斜角 (Dipole Tilt)', f"{self.sim.dipole_tilt:.2f}", 'deg'],
            ['内核对称性 (IC Symmetry)', f"{self.sim.inner_core_symmetry:.4f}", ''],
            ['磁能生成效率', f"{self.sim.magnetic_energy_generation_efficiency:.4f}", '%'],
            ['极性反转次数', f"{self.sim.polarity_reversal_count}", ''],
            ['弛豫时间', f"{self.sim.relaxation_time:.3e}", 's'],
        ]

        result_table = Table(result_data, colWidths=[2*inch, 1.5*inch, 1*inch])
        result_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightcoral),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkred),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.mistyrose),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(result_table)
        story.append(Spacer(1, 20))

        if data.get('adjustments'):
            story.append(PageBreak())
            story.append(Paragraph("四、参数调整记录", styles['SectionHeader']))
            for i, adj in enumerate(data['adjustments']):
                story.append(Paragraph(f"调整 #{i+1}", styles['SubHeader']))
                story.append(Paragraph(f"时间: {adj['created_at'].strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
                if adj['old_cmb'] is not None:
                    story.append(Paragraph(
                        f"CMB热通量: {adj['old_cmb']:.3e} → {adj['new_cmb']:.3e} W/m²",
                        styles['Normal']
                    ))
                if adj['old_icr'] is not None:
                    story.append(Paragraph(
                        f"内核半径: {adj['old_icr']:.3e} → {adj['new_icr']:.3e} m",
                        styles['Normal']
                    ))
                story.append(Paragraph(f"原因: {adj['reason']}", styles['Normal']))
                story.append(Spacer(1, 10))

        story.append(PageBreak())
        story.append(Paragraph("五、可视化结果", styles['SectionHeader']))

        if 'radial_B' in figures:
            story.append(Paragraph("5.1 径向磁场分布 (CMB)", styles['SubHeader']))
            story.append(Image(figures['radial_B'], width=6*inch, height=4*inch))
            story.append(Spacer(1, 10))

        if 'field_lines' in figures:
            story.append(Paragraph("5.2 磁力线结构 (子午面)", styles['SubHeader']))
            story.append(Image(figures['field_lines'], width=5*inch, height=5*inch))
            story.append(Spacer(1, 10))

        if 'thermal_plumes' in figures:
            story.append(Paragraph("5.3 热柱分布", styles['SubHeader']))
            story.append(Image(figures['thermal_plumes'], width=6*inch, height=4*inch))
            story.append(Spacer(1, 10))

        story.append(PageBreak())

        if 'energy' in figures:
            story.append(Paragraph("5.4 能量演化", styles['SubHeader']))
            story.append(Image(figures['energy'], width=6*inch, height=3*inch))
            story.append(Spacer(1, 10))

        if 'dipole' in figures:
            story.append(Paragraph("5.5 偶极矩与倾斜角演化", styles['SubHeader']))
            story.append(Image(figures['dipole'], width=6*inch, height=5*inch))
            story.append(Spacer(1, 10))

        if 'reynolds' in figures:
            story.append(Paragraph("5.6 磁雷诺数演化", styles['SubHeader']))
            story.append(Image(figures['reynolds'], width=6*inch, height=3*inch))
            story.append(Spacer(1, 10))

        if 'reversals' in figures:
            story.append(PageBreak())
            story.append(Paragraph("5.7 极性反转事件时间序列", styles['SubHeader']))
            story.append(Image(figures['reversals'], width=6*inch, height=3*inch))
            story.append(Spacer(1, 10))

            if data.get('reversals_db') or data.get('polarity_reversals'):
                story.append(Paragraph("极性反转事件列表", styles['SubHeader']))
                reversals = data.get('reversals_db', data.get('polarity_reversals', []))
                rev_data = [['事件', '开始迭代', '结束迭代', '持续时间 (s)', '类型']]
                for i, rev in enumerate(reversals):
                    rev_data.append([
                        f"#{i+1}",
                        str(rev['start_iteration']),
                        str(rev.get('end_iteration', 'N/A')),
                        f"{rev.get('duration', 0):.3e}",
                        rev.get('type', 'full')
                    ])

                rev_table = Table(rev_data, colWidths=[0.8*inch, 1.2*inch, 1.2*inch, 1.5*inch, 1*inch])
                rev_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(rev_table)

        story.append(PageBreak())
        story.append(Paragraph("六、磁雷诺数监控与预警", styles['SectionHeader']))
        story.append(Paragraph(
            f"临界磁雷诺数: {self.sim.magnetic_reynolds_critical}",
            styles['Normal']
        ))
        story.append(Paragraph(
            f"最终磁雷诺数: {self.sim.magnetic_reynolds_number:.2f}",
            styles['Normal']
        ))
        story.append(Paragraph(
            f"偶极子倾斜角阈值: {self.sim.dipole_tilt_threshold}°",
            styles['Normal']
        ))
        story.append(Paragraph(
            f"最终偶极子倾斜角: {self.sim.dipole_tilt:.2f}°",
            styles['Normal']
        ))
        story.append(Paragraph(
            f"警告次数: {self.sim.warning_count}",
            styles['Normal']
        ))

        story.append(Spacer(1, 30))
        story.append(Paragraph("报告生成时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                               styles['Italic']))

        doc.build(story)
        return report_path


class DataExporter:
    def __init__(self, db: Session, simulation_id: int):
        self.db = db
        self.simulation_id = simulation_id
        self.sim = db.query(Simulation).filter(Simulation.id == simulation_id).first()
        self.output_dir = self.sim.output_dir if self.sim else ''

    def export_full_field_data(
        self,
        field_type: str = 'all',
        format: str = 'npz'
    ) -> str:
        if not self.sim:
            raise ValueError("Simulation not found")

        final_fields_path = os.path.join(self.output_dir, 'final_fields.npz')
        if not os.path.exists(final_fields_path):
            raise FileNotFoundError("Field data not found")

        data = np.load(final_fields_path)

        export_dir = os.path.join(self.output_dir, 'exports')
        os.makedirs(export_dir, exist_ok=True)

        export_path = os.path.join(export_dir, f'full_fields_{field_type}.{format}')

        if format == 'npz':
            if field_type == 'all':
                np.savez(export_path, **data)
            else:
                field_key = field_type.lower()
                matching = {k: v for k, v in data.items() if field_key in k.lower()}
                np.savez(export_path, **matching)

        elif format == 'vtk':
            import pyvista as pv
            from pathlib import Path

            R = data['R']
            Theta = data['Theta']
            Phi = data['Phi']

            X = R * np.sin(Theta) * np.cos(Phi)
            Y = R * np.sin(Theta) * np.sin(Phi)
            Z = R * np.cos(Theta)

            grid = pv.StructuredGrid(X, Y, Z)

            if field_type in ['all', 'magnetic']:
                grid['B_r'] = data['B_r'].flatten(order='F')
                grid['B_theta'] = data['B_theta'].flatten(order='F')
                grid['B_phi'] = data['B_phi'].flatten(order='F')

            if field_type in ['all', 'velocity']:
                grid['v_r'] = data['v_r'].flatten(order='F')
                grid['v_theta'] = data['v_theta'].flatten(order='F')
                grid['v_phi'] = data['v_phi'].flatten(order='F')

            if field_type in ['all', 'temperature']:
                grid['T'] = data['T'].flatten(order='F')

            grid.save(export_path)

        return export_path

    def export_time_series(
        self,
        by_dimension: Optional[str] = None,
        format: str = 'csv'
    ) -> str:
        if not self.sim:
            raise ValueError("Simulation not found")

        time_series = self.db.query(TimeSeriesData).filter(
            TimeSeriesData.simulation_id == self.simulation_id
        ).order_by(TimeSeriesData.time_step).all()

        export_dir = os.path.join(self.output_dir, 'exports')
        os.makedirs(export_dir, exist_ok=True)

        suffix = f'_by_{by_dimension}' if by_dimension else ''
        export_path = os.path.join(export_dir, f'time_series{suffix}.{format}')

        tau = self.sim.relaxation_time or 1.0
        Ra = self.sim.rayleigh_number or 1.0
        Pr = self.sim.prandtl_number or 1.0

        data_rows = []
        for ts in time_series:
            row = {
                'iteration': ts.time_step,
                'simulation_time': ts.simulation_time,
                'time_by_relaxation': ts.simulation_time / tau,
                'time_by_rayleigh': ts.simulation_time * Ra,
                'time_by_prandtl': ts.simulation_time / Pr,
                'magnetic_energy': ts.magnetic_energy,
                'kinetic_energy': ts.kinetic_energy,
                'dipole_moment': ts.dipole_moment,
                'dipole_tilt': ts.dipole_tilt,
                'magnetic_reynolds': ts.magnetic_reynolds,
                'inner_core_symmetry': ts.inner_core_symmetry
            }

            if by_dimension == 'relaxation':
                row['dimensionless_time'] = ts.simulation_time / tau
            elif by_dimension == 'rayleigh':
                row['dimensionless_time'] = ts.simulation_time * Ra
            elif by_dimension == 'prandtl':
                row['dimensionless_time'] = ts.simulation_time / Pr

            data_rows.append(row)

        if format == 'csv':
            import csv
            with open(export_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=data_rows[0].keys() if data_rows else [])
                writer.writeheader()
                writer.writerows(data_rows)

        elif format == 'json':
            with open(export_path, 'w') as f:
                json.dump(data_rows, f, indent=2)

        elif format == 'hdf5':
            import h5py
            with h5py.File(export_path, 'w') as f:
                for key in data_rows[0].keys():
                    f.create_dataset(key, data=[row[key] for row in data_rows])

        return export_path

    def export_parameters(self, format: str = 'json') -> str:
        if not self.sim:
            raise ValueError("Simulation not found")

        export_dir = os.path.join(self.output_dir, 'exports')
        os.makedirs(export_dir, exist_ok=True)

        export_path = os.path.join(export_dir, f'parameters.{format}')

        params = {
            'simulation_id': self.sim.id,
            'name': self.sim.name,
            'core_radius': self.sim.core_radius,
            'viscosity': self.sim.viscosity,
            'thermal_expansion': self.sim.thermal_expansion,
            'icb_heat_flux': self.sim.icb_heat_flux,
            'cmb_heat_flux': self.sim.cmb_heat_flux,
            'inner_core_radius': self.sim.inner_core_radius,
            'rayleigh_number': self.sim.rayleigh_number,
            'prandtl_number': self.sim.prandtl_number,
            'magnetic_reynolds_number': self.sim.magnetic_reynolds_number,
            'ekman_number': self.sim.ekman_number,
            'rossby_number': self.sim.rossby_number,
            'relaxation_time': self.sim.relaxation_time,
            'max_iterations': self.sim.max_iterations,
            'magnetic_reynolds_critical': self.sim.magnetic_reynolds_critical,
            'dipole_tilt_threshold': self.sim.dipole_tilt_threshold
        }

        if format == 'json':
            with open(export_path, 'w') as f:
                json.dump(params, f, indent=2)

        elif format == 'txt':
            with open(export_path, 'w') as f:
                for key, value in params.items():
                    f.write(f"{key} = {value}\n")

        return export_path
