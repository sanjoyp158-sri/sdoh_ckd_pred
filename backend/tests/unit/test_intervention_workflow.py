"""
Unit tests for Intervention Workflow Engine.
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from app.services.intervention_workflow import (
    InterventionWorkflowEngine,
    InterventionWorkflow,
    WorkflowStep,
    WorkflowStatus,
    StepStatus
)
from app.models.patient import (
    UnifiedPatientRecord,
    Demographics,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    Address,
    RiskTier
)


@pytest.fixture
def sample_patient():
    """Create a sample high-risk patient record."""
    return UnifiedPatientRecord(
        patient_id="test_001",
        demographics=Demographics(
            age=65,
            sex="M",
            address=Address(zip_code="12345", state="NY")
        ),
        clinical=ClinicalRecord(
            egfr=25.0,
            egfr_history=[(datetime.now(), 30.0), (datetime.now(), 25.0)],
            uacr=350.0,
            hba1c=8.5,
            systolic_bp=155,
            diastolic_bp=95,
            bmi=34.0,
            medications=[],
            ckd_stage="4",
            diagnosis_date=datetime.now(),
            comorbidities=["diabetes", "hypertension"]
        ),
        administrative=AdministrativeRecord(
            visit_frequency_12mo=2,
            specialist_referrals=[],
            insurance_type="Medicare",
            insurance_status="Active",
            last_visit_date=datetime.now()
        ),
        sdoh=SDOHRecord(
            adi_percentile=90,
            food_desert=True,
            housing_stability_score=0.3,
            transportation_access_score=0.4,
            rural_urban_code="rural"
        ),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestWorkflowStep:
    """Test WorkflowStep data class."""
    
    def test_workflow_step_creation(self):
        """Test creating a workflow step."""
        step = WorkflowStep(
            step_id="telehealth",
            step_name="Schedule Telehealth Appointment"
        )
        
        assert step.step_id == "telehealth"
        assert step.step_name == "Schedule Telehealth Appointment"
        assert step.status == StepStatus.PENDING
        assert step.retry_count == 0
        assert step.started_at is None
        assert step.completed_at is None


class TestInterventionWorkflow:
    """Test InterventionWorkflow data class."""
    
    def test_workflow_creation(self):
        """Test creating an intervention workflow."""
        initiated_at = datetime.now()
        
        workflow = InterventionWorkflow(
            workflow_id="wf_test_001_20260405",
            patient_id="test_001",
            risk_score=0.85,
            risk_tier=RiskTier.HIGH,
            initiated_at=initiated_at
        )
        
        assert workflow.workflow_id == "wf_test_001_20260405"
        assert workflow.patient_id == "test_001"
        assert workflow.risk_score == 0.85
        assert workflow.risk_tier == RiskTier.HIGH
        assert workflow.initiated_at == initiated_at
        assert workflow.status == WorkflowStatus.PENDING
        assert len(workflow.steps) == 4
    
    def test_workflow_steps_initialized(self):
        """Test that workflow steps are initialized correctly."""
        workflow = InterventionWorkflow(
            workflow_id="wf_test",
            patient_id="test_001",
            risk_score=0.85,
            risk_tier=RiskTier.HIGH,
            initiated_at=datetime.now()
        )
        
        step_ids = [step.step_id for step in workflow.steps]
        assert "telehealth" in step_ids
        assert "blood_draw" in step_ids
        assert "case_manager" in step_ids
        assert "care_coordination" in step_ids
    
    def test_get_step(self):
        """Test retrieving a step by ID."""
        workflow = InterventionWorkflow(
            workflow_id="wf_test",
            patient_id="test_001",
            risk_score=0.85,
            risk_tier=RiskTier.HIGH,
            initiated_at=datetime.now()
        )
        
        step = workflow.get_step("telehealth")
        assert step is not None
        assert step.step_id == "telehealth"
    
    def test_all_steps_completed(self):
        """Test checking if all steps are completed."""
        workflow = InterventionWorkflow(
            workflow_id="wf_test",
            patient_id="test_001",
            risk_score=0.85,
            risk_tier=RiskTier.HIGH,
            initiated_at=datetime.now()
        )
        
        # Initially not completed
        assert not workflow.all_steps_completed()
        
        # Mark all steps as completed
        for step in workflow.steps:
            step.status = StepStatus.COMPLETED
        
        assert workflow.all_steps_completed()
    
    def test_any_step_failed(self):
        """Test checking if any step has failed."""
        workflow = InterventionWorkflow(
            workflow_id="wf_test",
            patient_id="test_001",
            risk_score=0.85,
            risk_tier=RiskTier.HIGH,
            initiated_at=datetime.now()
        )
        
        # Initially no failures
        assert not workflow.any_step_failed()
        
        # Mark one step as failed
        workflow.steps[0].status = StepStatus.FAILED
        
        assert workflow.any_step_failed()


class TestInterventionWorkflowEngine:
    """Test Intervention Workflow Engine."""
    
    def test_engine_initialization(self):
        """Test engine initialization."""
        engine = InterventionWorkflowEngine()
        
        assert len(engine.workflows) == 0
        assert engine.retry_delays == [5, 15, 45]
    
    @pytest.mark.asyncio
    async def test_initiate_workflow_high_risk(self, sample_patient):
        """Test initiating workflow for high-risk patient."""
        engine = InterventionWorkflowEngine()
        
        workflow = await engine.initiate_workflow(
            patient=sample_patient,
            risk_score=0.85,
            risk_tier=RiskTier.HIGH
        )
        
        assert workflow is not None
        assert workflow.patient_id == "test_001"
        assert workflow.risk_score == 0.85
        assert workflow.risk_tier == RiskTier.HIGH
        assert workflow.status == WorkflowStatus.IN_PROGRESS
        assert len(workflow.steps) == 4
    
    @pytest.mark.asyncio
    async def test_initiate_workflow_non_high_risk_fails(self, sample_patient):
        """Test that initiating workflow for non-high-risk patient fails."""
        engine = InterventionWorkflowEngine()
        
        with pytest.raises(ValueError, match="only for HIGH risk patients"):
            await engine.initiate_workflow(
                patient=sample_patient,
                risk_score=0.50,
                risk_tier=RiskTier.MODERATE
            )
    
    @pytest.mark.asyncio
    async def test_initiate_workflow_creates_unique_id(self, sample_patient):
        """Test that each workflow gets a unique ID."""
        engine = InterventionWorkflowEngine()
        
        workflow1 = await engine.initiate_workflow(
            patient=sample_patient,
            risk_score=0.85,
            risk_tier=RiskTier.HIGH
        )
        
        await asyncio.sleep(0.1)  # Small delay to ensure different timestamp
        
        workflow2 = await engine.initiate_workflow(
            patient=sample_patient,
            risk_score=0.90,
            risk_tier=RiskTier.HIGH
        )
        
        assert workflow1.workflow_id != workflow2.workflow_id
    
    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, sample_patient):
        """Test executing workflow successfully."""
        engine = InterventionWorkflowEngine()
        
        workflow = await engine.initiate_workflow(
            patient=sample_patient,
            risk_score=0.85,
            risk_tier=RiskTier.HIGH
        )
        
        status = await engine.execute_workflow(workflow, sample_patient)
        
        assert status == WorkflowStatus.COMPLETED
        assert workflow.status == WorkflowStatus.COMPLETED
        assert workflow.completed_at is not None
        assert workflow.all_steps_completed()
    
    def test_get_workflow(self, sample_patient):
        """Test retrieving workflow by ID."""
        engine = InterventionWorkflowEngine()
        
        workflow = InterventionWorkflow(
            workflow_id="wf_test",
            patient_id="test_001",
            risk_score=0.85,
            risk_tier=RiskTier.HIGH,
            initiated_at=datetime.now()
        )
        
        engine.workflows["wf_test"] = workflow
        
        retrieved = engine.get_workflow("wf_test")
        assert retrieved == workflow
    
    def test_get_patient_workflows(self):
        """Test retrieving all workflows for a patient."""
        engine = InterventionWorkflowEngine()
        
        workflow1 = InterventionWorkflow(
            workflow_id="wf_test_1",
            patient_id="test_001",
            risk_score=0.85,
            risk_tier=RiskTier.HIGH,
            initiated_at=datetime.now()
        )
        
        workflow2 = InterventionWorkflow(
            workflow_id="wf_test_2",
            patient_id="test_001",
            risk_score=0.90,
            risk_tier=RiskTier.HIGH,
            initiated_at=datetime.now()
        )
        
        workflow3 = InterventionWorkflow(
            workflow_id="wf_test_3",
            patient_id="test_002",
            risk_score=0.88,
            risk_tier=RiskTier.HIGH,
            initiated_at=datetime.now()
        )
        
        engine.workflows["wf_test_1"] = workflow1
        engine.workflows["wf_test_2"] = workflow2
        engine.workflows["wf_test_3"] = workflow3
        
        patient_workflows = engine.get_patient_workflows("test_001")
        
        assert len(patient_workflows) == 2
        assert all(w.patient_id == "test_001" for w in patient_workflows)
    
    def test_get_all_workflows(self):
        """Test retrieving all workflows."""
        engine = InterventionWorkflowEngine()
        
        workflow1 = InterventionWorkflow(
            workflow_id="wf_test_1",
            patient_id="test_001",
            risk_score=0.85,
            risk_tier=RiskTier.HIGH,
            initiated_at=datetime.now()
        )
        
        workflow2 = InterventionWorkflow(
            workflow_id="wf_test_2",
            patient_id="test_002",
            risk_score=0.90,
            risk_tier=RiskTier.HIGH,
            initiated_at=datetime.now()
        )
        
        engine.workflows["wf_test_1"] = workflow1
        engine.workflows["wf_test_2"] = workflow2
        
        all_workflows = engine.get_all_workflows()
        
        assert len(all_workflows) == 2


class TestWorkflowSLA:
    """Test workflow SLA requirements."""
    
    @pytest.mark.asyncio
    async def test_workflow_initiation_within_sla(self, sample_patient):
        """Test that workflow is initiated within 1-hour SLA."""
        engine = InterventionWorkflowEngine()
        
        before = datetime.now()
        workflow = await engine.initiate_workflow(
            patient=sample_patient,
            risk_score=0.85,
            risk_tier=RiskTier.HIGH
        )
        after = datetime.now()
        
        # Workflow should be initiated immediately
        assert workflow.initiated_at >= before
        assert workflow.initiated_at <= after
        
        # SLA deadline should be 1 hour from initiation
        sla_deadline = workflow.initiated_at + timedelta(hours=1)
        assert sla_deadline > workflow.initiated_at
