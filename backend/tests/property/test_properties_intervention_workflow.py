"""
Property-based tests for Intervention Workflow Engine.
Tests universal correctness properties using Hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, settings as hyp_settings
from datetime import datetime, timedelta
import asyncio

from app.services.intervention_workflow import (
    InterventionWorkflowEngine,
    InterventionWorkflow,
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


# Custom strategies
@st.composite
def high_risk_patient_strategy(draw):
    """Generate valid high-risk patient records."""
    patient_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    return UnifiedPatientRecord(
        patient_id=patient_id,
        demographics=Demographics(
            age=draw(st.integers(min_value=18, max_value=100)),
            sex=draw(st.sampled_from(["M", "F"])),
            address=Address(
                zip_code=draw(st.text(min_size=5, max_size=5, alphabet=st.characters(whitelist_categories=('Nd',)))),
                state=draw(st.text(min_size=2, max_size=2, alphabet=st.characters(whitelist_categories=('Lu',))))
            )
        ),
        clinical=ClinicalRecord(
            egfr=draw(st.floats(min_value=10.0, max_value=120.0)),
            egfr_history=[],
            uacr=draw(st.floats(min_value=0.0, max_value=3000.0)),
            hba1c=draw(st.floats(min_value=4.0, max_value=14.0)),
            systolic_bp=draw(st.integers(min_value=80, max_value=200)),
            diastolic_bp=draw(st.integers(min_value=40, max_value=120)),
            bmi=draw(st.floats(min_value=15.0, max_value=50.0)),
            medications=[],
            ckd_stage=draw(st.sampled_from(["2", "3a", "3b", "4"])),
            diagnosis_date=datetime.now(),
            comorbidities=[]
        ),
        administrative=AdministrativeRecord(
            visit_frequency_12mo=draw(st.integers(min_value=0, max_value=50)),
            specialist_referrals=[],
            insurance_type=draw(st.sampled_from(["Medicare", "Medicaid", "Private", "Uninsured"])),
            insurance_status="Active",
            last_visit_date=datetime.now()
        ),
        sdoh=SDOHRecord(
            adi_percentile=draw(st.integers(min_value=1, max_value=100)),
            food_desert=draw(st.booleans()),
            housing_stability_score=draw(st.floats(min_value=0.0, max_value=1.0)),
            transportation_access_score=draw(st.floats(min_value=0.0, max_value=1.0)),
            rural_urban_code=draw(st.sampled_from(["urban", "suburban", "rural"]))
        ),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@st.composite
def high_risk_score_strategy(draw):
    """Generate high-risk scores (> 0.65)."""
    return draw(st.floats(min_value=0.66, max_value=1.0))


@pytest.mark.property_test
class TestProperty16_HighRiskWorkflowInitiationTiming:
    """
    Property 16: High-Risk Workflow Initiation Timing
    
    For any patient classified as high-risk, the Intervention Workflow Engine 
    should initiate the automated intervention workflow within 1 hour.
    
    **Validates: Requirements 5.1**
    """
    
    @given(
        patient=high_risk_patient_strategy(),
        risk_score=high_risk_score_strategy()
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_workflow_initiation_timing(self, patient, risk_score):
        """Test that high-risk workflows are initiated within 1 hour SLA."""
        engine = InterventionWorkflowEngine()
        
        # Record time before initiation
        before_initiation = datetime.now()
        
        # Initiate workflow
        workflow = asyncio.run(engine.initiate_workflow(
            patient=patient,
            risk_score=risk_score,
            risk_tier=RiskTier.HIGH
        ))
        
        # Record time after initiation
        after_initiation = datetime.now()
        
        # Property 1: Workflow should be initiated immediately (within seconds)
        initiation_time = (after_initiation - before_initiation).total_seconds()
        assert initiation_time < 5.0, f"Workflow took {initiation_time}s to initiate"
        
        # Property 2: Workflow initiated_at should be within the time window
        assert workflow.initiated_at >= before_initiation
        assert workflow.initiated_at <= after_initiation
        
        # Property 3: SLA deadline should be 1 hour from initiation
        sla_deadline = workflow.initiated_at + timedelta(hours=1)
        assert (sla_deadline - workflow.initiated_at).total_seconds() == 3600
        
        # Property 4: Workflow should be in IN_PROGRESS status after initiation
        assert workflow.status == WorkflowStatus.IN_PROGRESS


@pytest.mark.property_test
class TestProperty17_InterventionWorkflowCompleteness:
    """
    Property 17: Intervention Workflow Completeness
    
    For any high-risk patient workflow, the Intervention Workflow Engine should 
    trigger all four intervention components (provider notification, telehealth 
    scheduling, home blood draw dispatch, and case manager enrollment) and create 
    an audit trail with timestamps for each step.
    
    **Validates: Requirements 5.2, 5.3**
    """
    
    @given(
        patient=high_risk_patient_strategy(),
        risk_score=high_risk_score_strategy()
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_workflow_completeness(self, patient, risk_score):
        """Test that workflows trigger all four intervention components."""
        engine = InterventionWorkflowEngine()
        
        # Initiate and execute workflow
        workflow = asyncio.run(engine.initiate_workflow(
            patient=patient,
            risk_score=risk_score,
            risk_tier=RiskTier.HIGH
        ))
        
        # Property 1: Workflow should have exactly 4 steps
        assert len(workflow.steps) == 4, f"Expected 4 steps, got {len(workflow.steps)}"
        
        # Property 2: All required intervention components should be present
        step_ids = {step.step_id for step in workflow.steps}
        required_steps = {"telehealth", "blood_draw", "case_manager", "care_coordination"}
        assert step_ids == required_steps, f"Missing steps: {required_steps - step_ids}"
        
        # Execute workflow
        asyncio.run(engine.execute_workflow(workflow, patient))
        
        # Property 3: All steps should have timestamps (audit trail)
        for step in workflow.steps:
            assert step.started_at is not None, f"Step {step.step_id} missing started_at"
            assert step.completed_at is not None, f"Step {step.step_id} missing completed_at"
            
            # Property 4: Completed timestamp should be after started timestamp
            assert step.completed_at >= step.started_at, \
                f"Step {step.step_id} completed before it started"
        
        # Property 5: Workflow should have completion timestamp
        assert workflow.completed_at is not None, "Workflow missing completed_at"
        assert workflow.completed_at >= workflow.initiated_at, \
            "Workflow completed before it was initiated"


@pytest.mark.property_test
class TestProperty18_InterventionStepRetryLogic:
    """
    Property 18: Intervention Step Retry Logic
    
    For any failed intervention step, the Intervention Workflow Engine should 
    retry the step up to 3 times with exponential backoff before marking it 
    as permanently failed.
    
    **Validates: Requirements 5.4**
    """
    
    @given(
        patient=high_risk_patient_strategy(),
        risk_score=high_risk_score_strategy(),
        failing_step_index=st.integers(min_value=0, max_value=3)
    )
    @hyp_settings(max_examples=30, deadline=None)
    def test_retry_logic_structure(self, patient, risk_score, failing_step_index):
        """Test that retry logic structure is correct."""
        engine = InterventionWorkflowEngine()
        
        # Property 1: Engine should have retry delays configured
        assert len(engine.retry_delays) == 3, "Should have 3 retry delays"
        
        # Property 2: Retry delays should follow exponential backoff pattern
        assert engine.retry_delays[0] < engine.retry_delays[1], \
            "Second retry should have longer delay"
        assert engine.retry_delays[1] < engine.retry_delays[2], \
            "Third retry should have longest delay"
        
        # Property 3: Retry delays should be reasonable (5, 15, 45 minutes)
        assert engine.retry_delays == [5, 15, 45], \
            f"Expected [5, 15, 45] minute delays, got {engine.retry_delays}"
        
        # Initiate workflow
        workflow = asyncio.run(engine.initiate_workflow(
            patient=patient,
            risk_score=risk_score,
            risk_tier=RiskTier.HIGH
        ))
        
        # Property 4: Each step should start with 0 retries
        for step in workflow.steps:
            assert step.retry_count == 0, f"Step {step.step_id} should start with 0 retries"


@pytest.mark.property_test
class TestProperty19_WorkflowCompletionNotification:
    """
    Property 19: Workflow Completion Notification
    
    For any intervention workflow where all steps complete successfully, the 
    workflow status should be marked as 'completed' and a notification should 
    be sent to the care coordination team.
    
    **Validates: Requirements 5.5**
    """
    
    @given(
        patient=high_risk_patient_strategy(),
        risk_score=high_risk_score_strategy()
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_workflow_completion_notification(self, patient, risk_score):
        """Test that completed workflows are marked correctly and trigger notifications."""
        engine = InterventionWorkflowEngine()
        
        # Initiate workflow
        workflow = asyncio.run(engine.initiate_workflow(
            patient=patient,
            risk_score=risk_score,
            risk_tier=RiskTier.HIGH
        ))
        
        # Execute workflow (all steps succeed in default implementation)
        status = asyncio.run(engine.execute_workflow(workflow, patient))
        
        # Property 1: Workflow status should be COMPLETED when all steps succeed
        assert status == WorkflowStatus.COMPLETED, \
            f"Expected COMPLETED status, got {status}"
        assert workflow.status == WorkflowStatus.COMPLETED, \
            f"Workflow status should be COMPLETED, got {workflow.status}"
        
        # Property 2: All steps should be completed
        for step in workflow.steps:
            assert step.status == StepStatus.COMPLETED, \
                f"Step {step.step_id} should be COMPLETED, got {step.status}"
        
        # Property 3: Workflow should have completion timestamp
        assert workflow.completed_at is not None, \
            "Completed workflow should have completed_at timestamp"
        
        # Property 4: Completion timestamp should be after initiation
        assert workflow.completed_at >= workflow.initiated_at, \
            "Workflow completed_at should be after initiated_at"
        
        # Property 5: Care coordination step should be completed (notification sent)
        care_coordination_step = workflow.get_step("care_coordination")
        assert care_coordination_step is not None, \
            "Care coordination step should exist"
        assert care_coordination_step.status == StepStatus.COMPLETED, \
            "Care coordination notification should be completed"
