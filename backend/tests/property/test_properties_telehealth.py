"""
Property-based tests for Telehealth Scheduler.
Tests universal correctness properties using Hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, settings as hyp_settings
from datetime import datetime, timedelta

from app.services.telehealth_scheduler import (
    TelehealthScheduler,
    AppointmentSlot,
    ContactMethod
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
def patient_strategy(draw):
    """Generate valid patient records."""
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
class TestProperty24_TelehealthAvailabilityCheck:
    """
    Property 24: Telehealth Availability Check
    
    For any high-risk patient identified, the Telehealth Scheduler should check 
    nephrology provider availability within the next 14 days.
    
    **Validates: Requirements 7.1**
    """
    
    @given(patient=patient_strategy())
    @hyp_settings(max_examples=50, deadline=None)
    def test_availability_check_window(self, patient):
        """Test that availability check covers 14-day window."""
        scheduler = TelehealthScheduler()
        
        start_date = datetime.now()
        available_slots = scheduler.check_availability(patient, start_date)
        
        # Property 1: Should check availability (return slots or empty list)
        assert isinstance(available_slots, list)
        
        # Property 2: All returned slots should be within 14-day window
        end_date = start_date + timedelta(days=14)
        for slot in available_slots:
            assert slot.start_time >= start_date, \
                f"Slot {slot.start_time} is before start date {start_date}"
            assert slot.start_time <= end_date, \
                f"Slot {slot.start_time} is after 14-day window {end_date}"
        
        # Property 3: Availability window should be 14 days
        assert scheduler.availability_window_days == 14


@pytest.mark.property_test
class TestProperty25_EarliestAppointmentSelection:
    """
    Property 25: Earliest Appointment Selection
    
    For any telehealth scheduling request with available appointments, the system 
    should select the earliest available appointment slot.
    
    **Validates: Requirements 7.2**
    """
    
    @given(patient=patient_strategy())
    @hyp_settings(max_examples=50, deadline=None)
    def test_earliest_appointment_selection(self, patient):
        """Test that scheduler selects earliest available slot."""
        scheduler = TelehealthScheduler()
        
        # Get available slots
        available_slots = scheduler.check_availability(patient)
        
        if len(available_slots) > 0:
            # Schedule appointment (should select earliest)
            appointment = scheduler.schedule_for_patient(patient)
            
            # Property 1: Appointment should be scheduled
            assert appointment is not None
            
            # Property 2: Scheduled time should be the earliest available
            earliest_slot_time = min(slot.start_time for slot in available_slots)
            assert appointment.scheduled_time == earliest_slot_time, \
                f"Scheduled {appointment.scheduled_time} but earliest was {earliest_slot_time}"


@pytest.mark.property_test
class TestProperty26_AppointmentConfirmationCompleteness:
    """
    Property 26: Appointment Confirmation Completeness
    
    For any scheduled telehealth appointment, the confirmation sent to the patient 
    should include the video conference link, appointment time, and preparation 
    instructions.
    
    **Validates: Requirements 7.3, 7.4**
    """
    
    @given(
        patient=patient_strategy(),
        contact_method=st.sampled_from([ContactMethod.EMAIL, ContactMethod.SMS, ContactMethod.PHONE])
    )
    @hyp_settings(max_examples=50, deadline=None)
    def test_confirmation_completeness(self, patient, contact_method):
        """Test that appointment confirmation includes all required information."""
        scheduler = TelehealthScheduler()
        
        # Schedule appointment
        appointment = scheduler.schedule_for_patient(patient, contact_method)
        
        if appointment is not None:
            # Property 1: Appointment should have video link
            assert appointment.video_link is not None
            assert len(appointment.video_link) > 0
            assert "http" in appointment.video_link.lower()
            
            # Property 2: Appointment should have scheduled time
            assert appointment.scheduled_time is not None
            
            # Property 3: Confirmation should be sent
            assert appointment.confirmation_sent is True
            
            # Property 4: Contact method should be recorded
            assert appointment.contact_method == contact_method
            
            # Property 5: Generate confirmation message and verify completeness
            confirmation_msg = scheduler._generate_confirmation_message(appointment)
            assert appointment.video_link in confirmation_msg
            assert appointment.provider_name in confirmation_msg
            assert "Preparation Instructions" in confirmation_msg or "preparation" in confirmation_msg.lower()


@pytest.mark.property_test
class TestProperty27_TelehealthSchedulingEscalation:
    """
    Property 27: Telehealth Scheduling Escalation
    
    For any scheduling request where no nephrology appointments are available 
    within 14 days, the system should escalate to the care coordination team 
    and attempt scheduling within 21 days.
    
    **Validates: Requirements 7.5**
    """
    
    @given(patient=patient_strategy())
    @hyp_settings(max_examples=30, deadline=None)
    def test_escalation_configuration(self, patient):
        """Test that escalation is configured correctly."""
        scheduler = TelehealthScheduler()
        
        # Property 1: Escalation window should be 21 days
        assert scheduler.escalation_window_days == 21
        
        # Property 2: Escalation window should be longer than availability window
        assert scheduler.escalation_window_days > scheduler.availability_window_days
        
        # Property 3: Escalation should succeed when called
        success = scheduler.escalate_scheduling(patient, "Test escalation")
        assert success is True
