"""
Unit tests for Telehealth Scheduler.
"""

import pytest
from datetime import datetime, timedelta

from app.services.telehealth_scheduler import (
    TelehealthScheduler,
    Appointment,
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


@pytest.fixture
def sample_patient():
    """Create a sample patient record."""
    return UnifiedPatientRecord(
        patient_id="test_001",
        demographics=Demographics(
            age=65,
            sex="M",
            address=Address(zip_code="12345", state="NY")
        ),
        clinical=ClinicalRecord(
            egfr=25.0,
            egfr_history=[],
            uacr=350.0,
            hba1c=8.5,
            systolic_bp=155,
            diastolic_bp=95,
            bmi=34.0,
            medications=[],
            ckd_stage="4",
            diagnosis_date=datetime.now(),
            comorbidities=[]
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


class TestAppointmentSlot:
    """Test AppointmentSlot data class."""
    
    def test_slot_creation(self):
        """Test creating an appointment slot."""
        start_time = datetime.now()
        
        slot = AppointmentSlot(
            slot_id="slot_001",
            provider_id="dr_smith",
            provider_name="Dr. Sarah Smith",
            start_time=start_time,
            duration_minutes=30
        )
        
        assert slot.slot_id == "slot_001"
        assert slot.provider_id == "dr_smith"
        assert slot.provider_name == "Dr. Sarah Smith"
        assert slot.start_time == start_time
        assert slot.duration_minutes == 30
        assert slot.end_time == start_time + timedelta(minutes=30)


class TestAppointment:
    """Test Appointment data class."""
    
    def test_appointment_creation(self):
        """Test creating an appointment."""
        scheduled_time = datetime.now()
        
        appointment = Appointment(
            appointment_id="apt_001",
            patient_id="test_001",
            provider_id="dr_smith",
            provider_name="Dr. Sarah Smith",
            scheduled_time=scheduled_time,
            video_link="https://telehealth.example.com/join/apt_001",
            contact_method=ContactMethod.EMAIL
        )
        
        assert appointment.appointment_id == "apt_001"
        assert appointment.patient_id == "test_001"
        assert appointment.provider_id == "dr_smith"
        assert appointment.scheduled_time == scheduled_time
        assert appointment.video_link == "https://telehealth.example.com/join/apt_001"
        assert appointment.confirmation_sent is False
        assert appointment.contact_method == ContactMethod.EMAIL


class TestTelehealthScheduler:
    """Test Telehealth Scheduler."""
    
    def test_scheduler_initialization(self):
        """Test scheduler initialization."""
        scheduler = TelehealthScheduler()
        
        assert len(scheduler.appointments) == 0
        assert scheduler.availability_window_days == 14
        assert scheduler.escalation_window_days == 21
    
    def test_check_availability(self, sample_patient):
        """Test checking provider availability."""
        scheduler = TelehealthScheduler()
        
        start_date = datetime.now()
        available_slots = scheduler.check_availability(sample_patient, start_date)
        
        # Should have slots available (simulated)
        assert len(available_slots) > 0
        
        # All slots should be within 14-day window
        end_date = start_date + timedelta(days=14)
        for slot in available_slots:
            assert slot.start_time >= start_date
            assert slot.start_time <= end_date
    
    def test_schedule_appointment(self, sample_patient):
        """Test scheduling an appointment."""
        scheduler = TelehealthScheduler()
        
        # Create a slot
        slot = AppointmentSlot(
            slot_id="slot_001",
            provider_id="dr_smith",
            provider_name="Dr. Sarah Smith",
            start_time=datetime.now() + timedelta(days=1)
        )
        
        # Schedule appointment
        appointment = scheduler.schedule_appointment(
            patient=sample_patient,
            slot=slot,
            contact_method=ContactMethod.EMAIL
        )
        
        assert appointment is not None
        assert appointment.patient_id == "test_001"
        assert appointment.provider_id == "dr_smith"
        assert appointment.scheduled_time == slot.start_time
        assert "telehealth.example.com" in appointment.video_link
        assert appointment.contact_method == ContactMethod.EMAIL
    
    def test_send_confirmation(self, sample_patient):
        """Test sending appointment confirmation."""
        scheduler = TelehealthScheduler()
        
        # Create appointment
        appointment = Appointment(
            appointment_id="apt_001",
            patient_id="test_001",
            provider_id="dr_smith",
            provider_name="Dr. Sarah Smith",
            scheduled_time=datetime.now() + timedelta(days=1),
            video_link="https://telehealth.example.com/join/apt_001",
            contact_method=ContactMethod.EMAIL
        )
        
        # Send confirmation
        success = scheduler.send_confirmation(appointment, sample_patient)
        
        assert success is True
        assert appointment.confirmation_sent is True
    
    def test_escalate_scheduling(self, sample_patient):
        """Test escalating when no availability."""
        scheduler = TelehealthScheduler()
        
        success = scheduler.escalate_scheduling(
            patient=sample_patient,
            reason="No availability within 14 days"
        )
        
        assert success is True
    
    def test_schedule_for_patient_success(self, sample_patient):
        """Test complete scheduling workflow."""
        scheduler = TelehealthScheduler()
        
        appointment = scheduler.schedule_for_patient(
            patient=sample_patient,
            contact_method=ContactMethod.EMAIL
        )
        
        # Should successfully schedule
        assert appointment is not None
        assert appointment.patient_id == "test_001"
        assert appointment.confirmation_sent is True
        
        # Should be in scheduler's appointments list
        assert len(scheduler.appointments) == 1
    
    def test_get_appointment(self, sample_patient):
        """Test retrieving appointment by ID."""
        scheduler = TelehealthScheduler()
        
        appointment = scheduler.schedule_for_patient(sample_patient)
        
        retrieved = scheduler.get_appointment(appointment.appointment_id)
        
        assert retrieved == appointment
    
    def test_get_patient_appointments(self, sample_patient):
        """Test retrieving all appointments for a patient."""
        scheduler = TelehealthScheduler()
        
        # Schedule multiple appointments
        apt1 = scheduler.schedule_for_patient(sample_patient)
        apt2 = scheduler.schedule_for_patient(sample_patient)
        
        patient_appointments = scheduler.get_patient_appointments("test_001")
        
        assert len(patient_appointments) == 2
        assert apt1 in patient_appointments
        assert apt2 in patient_appointments
