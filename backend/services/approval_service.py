from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from backend.models import (
    Simulation, SimulationStatus, User, Approval,
    ApprovalStatus, UserRole, Alert, AlertLevel
)
from backend.services.monitoring_service import AlertService


class ApprovalService:
    def __init__(self, db: Session):
        self.db = db
        self.alert_service = AlertService(db)

    def submit_for_approval(self, simulation_id: int, submitter_id: int) -> Tuple[bool, str]:
        sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not sim:
            return False, "Simulation not found"

        if sim.status != SimulationStatus.COMPLETED:
            return False, f"Simulation must be completed before approval. Current status: {sim.status}"

        if sim.submitted_for_approval:
            return False, "Simulation already submitted for approval"

        sim.submitted_for_approval = True
        sim.approval_status = ApprovalStatus.PENDING
        sim.updated_at = datetime.utcnow()
        self.db.commit()

        postdocs = self.db.query(User).filter(User.role == UserRole.POSTDOC).all()
        for postdoc in postdocs:
            self.alert_service.create_alert(
                simulation_id=simulation_id,
                alert_data={
                    'level': AlertLevel.INFO,
                    'title': '新模拟等待审批',
                    'message': f'模拟 "{sim.name}" 已提交，等待您进行博士后数值稳定性验证。',
                    'needs_review': False
                },
                notify_roles=[UserRole.POSTDOC]
            )

        return True, "Simulation submitted for approval successfully"

    def postdoc_approve(
        self,
        simulation_id: int,
        postdoc_id: int,
        approved: bool,
        comments: Optional[str] = None
    ) -> Tuple[bool, str]:
        sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not sim:
            return False, "Simulation not found"

        postdoc = self.db.query(User).filter(User.id == postdoc_id).first()
        if not postdoc or postdoc.role != UserRole.POSTDOC:
            return False, "User is not authorized for postdoc approval"

        if not sim.submitted_for_approval:
            return False, "Simulation not submitted for approval"

        if sim.approval_status != ApprovalStatus.PENDING:
            return False, f"Invalid approval status: {sim.approval_status}"

        approval = Approval(
            simulation_id=simulation_id,
            approver_id=postdoc_id,
            level='postdoc',
            comments=comments or '',
            approved=approved
        )
        self.db.add(approval)

        if approved:
            sim.approval_status = ApprovalStatus.POSTDOC_APPROVED

            professors = self.db.query(User).filter(User.role == UserRole.PROFESSOR).all()
            for prof in professors:
                self.alert_service.create_alert(
                    simulation_id=simulation_id,
                    alert_data={
                        'level': AlertLevel.INFO,
                        'title': '模拟已通过博士后验证',
                        'message': f'模拟 "{sim.name}" 已通过博士后数值稳定性验证，等待您进行教授物理合理性确认。',
                        'needs_review': False
                    },
                    notify_roles=[UserRole.PROFESSOR]
                )
        else:
            sim.approval_status = ApprovalStatus.REJECTED
            sim.submitted_for_approval = False

            self.alert_service.create_alert(
                simulation_id=simulation_id,
                alert_data={
                    'level': AlertLevel.WARNING,
                    'title': '模拟被博士后拒绝',
                    'message': f'模拟 "{sim.name}" 在博士后数值验证阶段被拒绝。原因: {comments or "未提供"}',
                    'needs_review': False
                },
                notify_roles=[UserRole.ADMIN, UserRole.RESEARCHER]
            )

        sim.updated_at = datetime.utcnow()
        self.db.commit()

        return True, f"Postdoc approval {'granted' if approved else 'denied'} successfully"

    def professor_approve(
        self,
        simulation_id: int,
        professor_id: int,
        approved: bool,
        comments: Optional[str] = None
    ) -> Tuple[bool, str]:
        sim = self.db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not sim:
            return False, "Simulation not found"

        prof = self.db.query(User).filter(User.id == professor_id).first()
        if not prof or prof.role != UserRole.PROFESSOR:
            return False, "User is not authorized for professor approval"

        if sim.approval_status != ApprovalStatus.POSTDOC_APPROVED:
            return False, f"Invalid status: simulation must pass postdoc approval first. Current: {sim.approval_status}"

        approval = Approval(
            simulation_id=simulation_id,
            approver_id=professor_id,
            level='professor',
            comments=comments or '',
            approved=approved
        )
        self.db.add(approval)

        if approved:
            sim.approval_status = ApprovalStatus.PROFESSOR_APPROVED

            self.alert_service.create_alert(
                simulation_id=simulation_id,
                alert_data={
                    'level': AlertLevel.INFO,
                    'title': '模拟已通过全部审批',
                    'message': f'模拟 "{sim.name}" 已通过教授物理合理性确认。结果将自动推送至全球地磁参考模型更新团队。',
                    'needs_review': False
                },
                notify_roles=[UserRole.ADMIN, UserRole.CHIEF_SCIENTIST, UserRole.RESEARCHER]
            )

            self._push_to_reference_model_team(sim)

        else:
            sim.approval_status = ApprovalStatus.REJECTED
            sim.submitted_for_approval = False

            self.alert_service.create_alert(
                simulation_id=simulation_id,
                alert_data={
                    'level': AlertLevel.WARNING,
                    'title': '模拟被教授拒绝',
                    'message': f'模拟 "{sim.name}" 在教授物理合理性确认阶段被拒绝。原因: {comments or "未提供"}',
                    'needs_review': False
                },
                notify_roles=[UserRole.ADMIN, UserRole.RESEARCHER, UserRole.POSTDOC]
            )

        sim.updated_at = datetime.utcnow()
        self.db.commit()

        return True, f"Professor approval {'granted' if approved else 'denied'} successfully"

    def _push_to_reference_model_team(self, sim: Simulation):
        push_record = {
            'simulation_id': sim.id,
            'name': sim.name,
            'dipole_moment': sim.dipole_moment,
            'dipole_tilt': sim.dipole_tilt,
            'magnetic_reynolds': sim.magnetic_reynolds_number,
            'inner_core_symmetry': sim.inner_core_symmetry,
            'polarity_reversal_count': sim.polarity_reversal_count,
            'approved_at': datetime.utcnow().isoformat(),
            'output_dir': sim.output_dir
        }

        push_log_file = f"{sim.output_dir}/reference_model_push.json"
        import json
        with open(push_log_file, 'w') as f:
            json.dump(push_record, f, indent=2)

    def get_approval_history(self, simulation_id: int) -> List[Approval]:
        return self.db.query(Approval).filter(
            Approval.simulation_id == simulation_id
        ).order_by(Approval.created_at).all()

    def get_simulations_pending_postdoc(self) -> List[Simulation]:
        return self.db.query(Simulation).filter(
            Simulation.submitted_for_approval == True,
            Simulation.approval_status == ApprovalStatus.PENDING
        ).order_by(Simulation.updated_at.desc()).all()

    def get_simulations_pending_professor(self) -> List[Simulation]:
        return self.db.query(Simulation).filter(
            Simulation.submitted_for_approval == True,
            Simulation.approval_status == ApprovalStatus.POSTDOC_APPROVED
        ).order_by(Simulation.updated_at.desc()).all()

    def get_user_approvals(self, user_id: int) -> List[Approval]:
        return self.db.query(Approval).filter(
            Approval.approver_id == user_id
        ).order_by(Approval.created_at.desc()).all()
