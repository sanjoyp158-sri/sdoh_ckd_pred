"""
Property-based tests for Home Blood Draw Dispatcher.
Tests universal correctness properties using Hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, settings as hyp_settings
from datetime import datetime, timedelta

from app.services.blood_draw_dispatcher import (
    HomeBloodDrawDispatcher,
    ShipmentStatus
)
from app.models.patient import (
    UnifiedPatientRecord,
    Demographics,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    Address
)


# Custom strategies
@st.composite
def patient_with_valid_address_strategy(draw):
    """Generate patient records with valid addresses."""
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


@pytest.mark.property_test
class TestProperty28_BloodDrawAddressVerification:
    """
    Property 28: Blood Draw Address Verification
    
    For any high-risk patient identified, the Home Blood Draw Dispatcher should 
    verify the patient's shipping address before dispatching a kit.
    
    **Validates: Requirements 8.1**
    """
    
    @given(patient=patient_with_valid_address_strategy())
    @hyp_settings(max_examples=50, deadline=None)
    def test_address_verification_before_dispatch(self, patient):
        """Test that address is verified before kit dispatch."""
        dispatcher = HomeBloodDrawDispatcher()
        
        # Property 1: Address verification should succeed for valid addresses
        is_valid = dispatcher.verify_address(patient)
        assert is_valid is True
        
        # Property 2: Dispatch should succeed after verification
        shipment = dispatcher.dispatch_kit(patient)
        assert shipment is not None
        
        # Property 3: Invalid addresses should fail verification
        patient.demographics.address.zip_code = "123"  # Invalid
        is_valid_invalid = dispatcher.verify_address(patient)
        assert is_valid_invalid is False
        
        # Property 4: Dispatch should fail for invalid addresses
        shipment_invalid = dispatcher.dispatch_kit(patient)
        assert shipment_invalid is None


@pytest.mark.property_test
class TestProperty29_BloodDrawKitDispatchTiming:
    """
    Property 29: Blood Draw Kit Dispatch Timing
    
    For any blood draw kit dispatch request, the kit should be dispatched 
    within 2 business days.
    
    **Validates: Requirements 8.2**
    """
    
    @given(patient=patient_with_valid_address_strategy())
    @hyp_settings(max_examples=50, deadline=None)
    def test_dispatch_timing_configuration(self, patient):
        """Test that dispatch timing is configured correctly."""
        dispatcher = HomeBloodDrawDispatcher()
        
        # Property 1: Dispatch window should be 2 business days
        assert dispatcher.dispatch_window_days == 2
        
        # Property 2: Kit should be dispatched immediately when requested
        before_dispatch = datetime.now()
        shipment = dispatcher.dispatch_kit(patient)
        after_dispatch = datetime.now()
        
        assert shipment is not None
        assert shipment.dispatch_date >= before_dispatch
        assert shipment.dispatch_date <= after_dispatch
        
        # Property 3: Dispatch should happen within seconds (immediate)
        dispatch_time = (after_dispatch - before_dispatch).total_seconds()
        assert dispatch_time < 5.0


@pytest.mark.property_test
class TestProperty30_BloodDrawKitContents:
    """
    Property 30: Blood Draw Kit Contents
    
    For any dispatched blood draw kit, it should include collection instructions, 
    a prepaid return shipping label, and required lab requisition forms.
    
    **Validates: Requirements 8.3**
    """
    
    @given(patient=patient_with_valid_address_strategy())
    @hyp_settings(max_examples=50, deadline=None)
    def test_kit_contents_completeness(self, patient):
        """Test that kit contains all required items."""
        dispatcher = HomeBloodDrawDispatcher()
        
        # Get kit contents
        contents = dispatcher.get_kit_contents()
        
        # Property 1: Kit should have contents
        assert len(contents) > 0
        
        # Property 2: Contents should include collection instructions
        contents_str = " ".join(contents).lower()
        assert "collection instructions" in contents_str or "instructions" in contents_str
        
        # Property 3: Contents should include prepaid return shipping label
        assert "prepaid" in contents_str or "shipping label" in contents_str
        
        # Property 4: Contents should include lab requisition forms
        assert "requisition" in contents_str or "lab" in contents_str
        
        # Property 5: Kit should have standard medical supplies
        assert any("tube" in item.lower() or "pad" in item.lower() or "bandage" in item.lower() 
                   for item in contents)


@pytest.mark.property_test
class TestProperty31_BloodDrawTrackingNotification:
    """
    Property 31: Blood Draw Tracking Notification
    
    For any dispatched blood draw kit, tracking information should be sent 
    to the patient.
    
    **Validates: Requirements 8.4**
    """
    
    @given(patient=patient_with_valid_address_strategy())
    @hyp_settings(max_examples=50, deadline=None)
    def test_tracking_notification(self, patient):
        """Test that tracking information is sent after dispatch."""
        dispatcher = HomeBloodDrawDispatcher()
        
        # Dispatch kit
        shipment = dispatcher.dispatch_kit(patient)
        
        assert shipment is not None
        
        # Property 1: Shipment should have tracking number
        assert shipment.tracking_number is not None
        assert len(shipment.tracking_number) > 0
        
        # Property 2: Shipment should have tracking ID
        assert shipment.tracking_id is not None
        assert patient.patient_id in shipment.tracking_id
        
        # Property 3: Tracking notification should be sent successfully
        success = dispatcher.send_tracking_notification(shipment, patient)
        assert success is True
        
        # Property 4: Complete workflow should send tracking automatically
        shipment2 = dispatcher.dispatch_for_patient(patient)
        assert shipment2 is not None
        assert shipment2.tracking_number is not None


@pytest.mark.property_test
class TestProperty32_BloodDrawFollowUpReminder:
    """
    Property 32: Blood Draw Follow-up Reminder
    
    For any dispatched kit where no sample has been received within 7 days, 
    a follow-up reminder should be scheduled and sent to the patient.
    
    **Validates: Requirements 8.5**
    """
    
    @given(patient=patient_with_valid_address_strategy())
    @hyp_settings(max_examples=50, deadline=None)
    def test_follow_up_reminder_timing(self, patient):
        """Test that follow-up reminder is sent after 7 days."""
        dispatcher = HomeBloodDrawDispatcher()
        
        # Property 1: Follow-up reminder window should be 7 days
        assert dispatcher.follow_up_reminder_days == 7
        
        # Dispatch kit
        shipment = dispatcher.dispatch_kit(patient)
        assert shipment is not None
        
        # Property 2: Reminder should not be sent before 7 days
        success_early = dispatcher.send_follow_up_reminder(shipment, patient)
        assert success_early is False
        assert shipment.follow_up_reminder_sent is False
        
        # Property 3: Reminder should be sent after 7 days
        shipment.dispatch_date = datetime.now() - timedelta(days=7)
        success_after = dispatcher.send_follow_up_reminder(shipment, patient)
        assert success_after is True
        assert shipment.follow_up_reminder_sent is True
        
        # Property 4: Reminder should not be sent if sample already received
        shipment2 = dispatcher.dispatch_kit(patient)
        shipment2.dispatch_date = datetime.now() - timedelta(days=7)
        shipment2.status = ShipmentStatus.SAMPLE_RECEIVED
        
        success_received = dispatcher.send_follow_up_reminder(shipment2, patient)
        assert success_received is False
        
        # Property 5: Reminder should not be sent twice
        success_duplicate = dispatcher.send_follow_up_reminder(shipment, patient)
        assert success_duplicate is False
