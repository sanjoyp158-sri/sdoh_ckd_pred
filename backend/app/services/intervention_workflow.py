"""
Intervention Workflow Engine for high-risk CKD patients.
Orchestrates automated interventions with retry logic and audit trail.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
import logging
import asyncio

from app.models.patient import UnifiedPatientRecord, RiskTier
from app.core.config import settings


logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Status of intervention workflow."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


class StepStatus(str, Enum):
    """Status of individual workflow step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class WorkflowStep:
    """Represents a single step in the intervention workflow."""
    
    def __init__(
        self,
        step_id: str,
        step_name: str,
        status: StepStatus = StepStatus.PENDING,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        retry_count: int = 0,
        error_message: Optional[str] = None
    ):
        self.step_id = step_id
        self.step_name = step_name
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.retry_count = retry_count
        self.error_message = error_message
    
    def __repr__(self):
        return (
            f"WorkflowStep(id={self.step_id}, name={self.step_name}, "
            f"status={self.status}, retries={self.retry_count})"
        )


class InterventionWorkflow:
    """Represents a complete intervention workflow for a patient."""
    
    def __init__(
        self,
        workflow_id: str,
        patient_id: str,
        risk_score: float,
        risk_tier: RiskTier,
        initiated_at: datetime,
        status: WorkflowStatus = WorkflowStatus.PENDING
    ):
        self.workflow_id = workflow_id
        self.patient_id = patient_id
        self.risk_score = risk_score
        self.risk_tier = risk_tier
        self.initiated_at = initiated_at
        self.status = status
        self.completed_at: Optional[datetime] = None
        
        # Initialize workflow steps
        self.steps: List[WorkflowStep] = [
            WorkflowStep("telehealth", "Schedule Telehealth Appointment"),
            WorkflowStep("blood_draw", "Dispatch Home Blood Draw Kit"),
            WorkflowStep("case_manager", "Enroll with Case Manager"),
            WorkflowStep("care_coordination", "Notify Care Coordination Team")
        ]
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a workflow step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def all_steps_completed(self) -> bool:
        """Check if all steps are completed."""
        return all(step.status == StepStatus.COMPLETED for step in self.steps)
    
    def any_step_failed(self) -> bool:
        """Check if any step has failed."""
        return any(step.status == StepStatus.FAILED for step in self.steps)
    
    def __repr__(self):
        return (
            f"InterventionWorkflow(id={self.workflow_id}, patient={self.patient_id}, "
            f"status={self.status}, steps={len(self.steps)})"
        )


class InterventionWorkflowEngine:
    """
    Intervention Workflow Engine for high-risk CKD patients.
    
    Orchestrates four intervention components:
    1. Telehealth appointment scheduling
    2. Home blood draw kit dispatch
    3. Case manager enrollment
    4. Care coordination team notification
    
    Features:
    - Parallel execution of all steps
    - Retry logic with exponential backoff (5min, 15min, 45min)
    - Complete audit trail with timestamps
    - 1-hour SLA for workflow initiation
    """
    
    def __init__(self):
        """Initialize Intervention Workflow Engine."""
        self.workflows: Dict[str, InterventionWorkflow] = {}
        self.retry_delays = [5, 15, 45]  # minutes
    
    async def initiate_workflow(
        self,
        patient: UnifiedPatientRecord,
        risk_score: float,
        risk_tier: RiskTier
    ) -> InterventionWorkflow:
        """
        Initiate intervention workflow for high-risk patient.
        
        Args:
            patient: Patient record
            risk_score: Risk prediction score
            risk_tier: Assigned risk tier
        
        Returns:
            InterventionWorkflow object
        
        Raises:
            ValueError: If patient is not high-risk
        """
        # Validate high-risk tier
        if risk_tier != RiskTier.HIGH:
            raise ValueError(f"Intervention workflow only for HIGH risk patients, got {risk_tier}")
        
        # Create workflow
        workflow_id = f"wf_{patient.patient_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        initiated_at = datetime.now()
        
        workflow = InterventionWorkflow(
            workflow_id=workflow_id,
            patient_id=patient.patient_id,
            risk_score=risk_score,
            risk_tier=risk_tier,
            initiated_at=initiated_at,
            status=WorkflowStatus.IN_PROGRESS
        )
        
        self.workflows[workflow_id] = workflow
        
        logger.info(
            f"Initiated intervention workflow {workflow_id} for patient {patient.patient_id} "
            f"(risk score: {risk_score:.3f})"
        )
        
        # Check 1-hour SLA
        sla_deadline = initiated_at + timedelta(hours=settings.INTERVENTION_INITIATION_HOURS)
        logger.info(f"Workflow SLA deadline: {sla_deadline}")
        
        return workflow
    
    async def execute_workflow(
        self,
        workflow: InterventionWorkflow,
        patient: UnifiedPatientRecord
    ) -> WorkflowStatus:
        """
        Execute all workflow steps in parallel with retry logic.
        
        Args:
            workflow: Intervention workflow to execute
            patient: Patient record
        
        Returns:
            Final workflow status
        """
        logger.info(f"Executing workflow {workflow.workflow_id}")
        
        # Execute all steps in parallel
        tasks = [
            self._execute_step_with_retry(workflow, step, patient)
            for step in workflow.steps
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update workflow status based on results
        if workflow.all_steps_completed():
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            logger.info(f"Workflow {workflow.workflow_id} completed successfully")
            
            # Notify care coordination team
            await self._notify_care_coordination(workflow, patient)
        elif workflow.any_step_failed():
            completed_count = sum(1 for step in workflow.steps if step.status == StepStatus.COMPLETED)
            if completed_count > 0:
                workflow.status = WorkflowStatus.PARTIALLY_COMPLETED
            else:
                workflow.status = WorkflowStatus.FAILED
            logger.warning(
                f"Workflow {workflow.workflow_id} {workflow.status.value}: "
                f"{completed_count}/{len(workflow.steps)} steps completed"
            )
        
        return workflow.status
    
    async def _execute_step_with_retry(
        self,
        workflow: InterventionWorkflow,
        step: WorkflowStep,
        patient: UnifiedPatientRecord
    ) -> bool:
        """
        Execute a workflow step with retry logic.
        
        Args:
            workflow: Parent workflow
            step: Step to execute
            patient: Patient record
        
        Returns:
            True if step completed successfully, False otherwise
        """
        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.now()
        
        for attempt in range(len(self.retry_delays) + 1):
            try:
                # Execute step (placeholder - actual implementation would call service)
                success = await self._execute_step(step, patient)
                
                if success:
                    step.status = StepStatus.COMPLETED
                    step.completed_at = datetime.now()
                    logger.info(
                        f"Step {step.step_id} completed for workflow {workflow.workflow_id}"
                    )
                    return True
                else:
                    raise Exception(f"Step {step.step_id} execution failed")
            
            except Exception as e:
                step.retry_count = attempt
                step.error_message = str(e)
                
                if attempt < len(self.retry_delays):
                    # Retry with exponential backoff
                    delay_minutes = self.retry_delays[attempt]
                    step.status = StepStatus.RETRYING
                    logger.warning(
                        f"Step {step.step_id} failed (attempt {attempt + 1}), "
                        f"retrying in {delay_minutes} minutes: {e}"
                    )
                    await asyncio.sleep(delay_minutes * 60)  # Convert to seconds
                else:
                    # Max retries exceeded
                    step.status = StepStatus.FAILED
                    logger.error(
                        f"Step {step.step_id} failed after {attempt + 1} attempts: {e}"
                    )
                    return False
        
        return False
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        patient: UnifiedPatientRecord
    ) -> bool:
        """
        Execute a single workflow step.
        
        This is a placeholder that would call the actual service implementations.
        
        Args:
            step: Step to execute
            patient: Patient record
        
        Returns:
            True if successful, False otherwise
        """
        # Placeholder implementation
        # In production, this would call:
        # - TelehealthScheduler for telehealth step
        # - HomeBloodDrawDispatcher for blood_draw step
        # - CaseManagerEnrollment for case_manager step
        # - Care coordination notification service for care_coordination step
        
        logger.info(f"Executing step: {step.step_name} for patient {patient.patient_id}")
        
        # Simulate success (in production, would call actual services)
        return True
    
    async def _notify_care_coordination(
        self,
        workflow: InterventionWorkflow,
        patient: UnifiedPatientRecord
    ):
        """
        Notify care coordination team of workflow completion.
        
        Args:
            workflow: Completed workflow
            patient: Patient record
        """
        logger.info(
            f"Notifying care coordination team: Workflow {workflow.workflow_id} "
            f"completed for patient {patient.patient_id}"
        )
        
        # Placeholder - would send actual notification (email, SMS, etc.)
    
    def get_workflow(self, workflow_id: str) -> Optional[InterventionWorkflow]:
        """Get workflow by ID."""
        return self.workflows.get(workflow_id)
    
    def get_patient_workflows(self, patient_id: str) -> List[InterventionWorkflow]:
        """Get all workflows for a patient."""
        return [
            workflow for workflow in self.workflows.values()
            if workflow.patient_id == patient_id
        ]
    
    def get_all_workflows(self) -> List[InterventionWorkflow]:
        """Get all workflows."""
        return list(self.workflows.values())
