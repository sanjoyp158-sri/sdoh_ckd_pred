"""
Unit tests for Home Blood Draw Dispatcher.
"""

import pytest
from datetime import datetime, timedelta

from app.services.blood_draw_dispatcher import (
    HomeBloodDrawDispatcher,
    ShipmentTracking,
    ShipmentStatus,
    BloodDrawKit
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


class TestBloodDrawKit:
    """Test BloodDrawKit class."""
    
    def test_kit_contents(self):
        """Test that kit has required contents."""
        kit = BloodDrawKit()
        contents = kit.get_contents()
        
        # Should have standard contents
        assert len(contents) > 0
        
        # Check for required items
        contents_str = " ".join(contents).lower()
        assert "collection instructions" in contents_str
        assert "prepaid" in contents_str or "shipping label" in contents_str
        assert "requisition" in contents_str


class TestShipmentTracking:
    """Test ShipmentTracking data class."""
    
    def test_shipment_creation(self):
        """Test creating a shipment tracking record."""
        dispatch_date = datetime.now()
        
        shipment = ShipmentTracking(
            tracking_id="bd_test_001",
            patient_id="test_001",
            shipping_address="12345, NY",
            dispatch_date=dispatch_date,
            tracking_number="1Z123456789"
        )
        
        assert shipment.tracking_id == "bd_test_001"
        assert shipment.patient_id == "test_001"
        assert shipment.shipping_address == "12345, NY"
        assert shipment.dispatch_date == dispatch_date
        assert shipment.tracking_number == "1Z123456789"
        assert shipment.status == ShipmentStatus.PENDING
        assert shipment.follow_up_reminder_sent is False


class TestHomeBloodDrawDispatcher:
    """Test Home Blood Draw Dispatcher."""
    
    def test_dispatcher_initialization(self):
        """Test dispatcher initialization."""
        dispatcher = HomeBloodDrawDispatcher()
        
        assert len(dispatcher.shipments) == 0
        assert dispatcher.dispatch_window_days == 2
        assert dispatcher.follow_up_reminder_days == 7
    
    def test_verify_address_valid(self, sample_patient):
        """Test address verification with valid address."""
        dispatcher = HomeBloodDrawDispatcher()
        
        is_valid = dispatcher.verify_address(sample_patient)
        
        assert is_valid is True
    
    def test_verify_address_invalid_zip(self, sample_patient):
        """Test address verification with invalid ZIP code."""
        dispatcher = HomeBloodDrawDispatcher()
        
        # Set invalid ZIP
        sample_patient.demographics.address.zip_code = "123"
        
        is_valid = dispatcher.verify_address(sample_patient)
        
        assert is_valid is False
    
    def test_verify_address_invalid_state(self, sample_patient):
        """Test address verification with invalid state."""
        dispatcher = HomeBloodDrawDispatcher()
        
        # Set invalid state
        sample_patient.demographics.address.state = "X"
        
        is_valid = dispatcher.verify_address(sample_patient)
        
        assert is_valid is False
    
    def test_dispatch_kit_success(self, sample_patient):
        """Test dispatching kit successfully."""
        dispatcher = HomeBloodDrawDispatcher()
        
        shipment = dispatcher.dispatch_kit(sample_patient)
        
        assert shipment is not None
        assert shipment.patient_id == "test_001"
        assert shipment.status == ShipmentStatus.DISPATCHED
        assert shipment.tracking_number is not None
        assert len(dispatcher.shipments) == 1
    
    def test_dispatch_kit_invalid_address(self, sample_patient):
        """Test dispatching kit with invalid address."""
        dispatcher = HomeBloodDrawDispatcher()
        
        # Set invalid address
        sample_patient.demographics.address.zip_code = "123"
        
        shipment = dispatcher.dispatch_kit(sample_patient)
        
        assert shipment is None
        assert len(dispatcher.shipments) == 0
    
    def test_get_kit_contents(self):
        """Test getting kit contents."""
        dispatcher = HomeBloodDrawDispatcher()
        
        contents = dispatcher.get_kit_contents()
        
        assert len(contents) > 0
        assert isinstance(contents, list)
    
    def test_send_tracking_notification(self, sample_patient):
        """Test sending tracking notification."""
        dispatcher = HomeBloodDrawDispatcher()
        
        shipment = dispatcher.dispatch_kit(sample_patient)
        success = dispatcher.send_tracking_notification(shipment, sample_patient)
        
        assert success is True
    
    def test_send_follow_up_reminder_too_early(self, sample_patient):
        """Test that follow-up reminder is not sent too early."""
        dispatcher = HomeBloodDrawDispatcher()
        
        shipment = dispatcher.dispatch_kit(sample_patient)
        
        # Try to send reminder immediately (should fail)
        success = dispatcher.send_follow_up_reminder(shipment, sample_patient)
        
        assert success is False
        assert shipment.follow_up_reminder_sent is False
    
    def test_send_follow_up_reminder_after_7_days(self, sample_patient):
        """Test sending follow-up reminder after 7 days."""
        dispatcher = HomeBloodDrawDispatcher()
        
        shipment = dispatcher.dispatch_kit(sample_patient)
        
        # Simulate 7 days passing
        shipment.dispatch_date = datetime.now() - timedelta(days=7)
        
        success = dispatcher.send_follow_up_reminder(shipment, sample_patient)
        
        assert success is True
        assert shipment.follow_up_reminder_sent is True
    
    def test_send_follow_up_reminder_sample_received(self, sample_patient):
        """Test that reminder is not sent if sample already received."""
        dispatcher = HomeBloodDrawDispatcher()
        
        shipment = dispatcher.dispatch_kit(sample_patient)
        shipment.dispatch_date = datetime.now() - timedelta(days=7)
        shipment.status = ShipmentStatus.SAMPLE_RECEIVED
        
        success = dispatcher.send_follow_up_reminder(shipment, sample_patient)
        
        assert success is False
    
    def test_dispatch_for_patient_complete_workflow(self, sample_patient):
        """Test complete dispatch workflow."""
        dispatcher = HomeBloodDrawDispatcher()
        
        shipment = dispatcher.dispatch_for_patient(sample_patient)
        
        assert shipment is not None
        assert shipment.patient_id == "test_001"
        assert shipment.status == ShipmentStatus.DISPATCHED
        assert len(dispatcher.shipments) == 1
    
    def test_get_shipment(self, sample_patient):
        """Test retrieving shipment by tracking ID."""
        dispatcher = HomeBloodDrawDispatcher()
        
        shipment = dispatcher.dispatch_kit(sample_patient)
        
        retrieved = dispatcher.get_shipment(shipment.tracking_id)
        
        assert retrieved == shipment
    
    def test_get_patient_shipments(self, sample_patient):
        """Test retrieving all shipments for a patient."""
        dispatcher = HomeBloodDrawDispatcher()
        
        # Dispatch multiple kits
        shipment1 = dispatcher.dispatch_kit(sample_patient)
        shipment2 = dispatcher.dispatch_kit(sample_patient)
        
        patient_shipments = dispatcher.get_patient_shipments("test_001")
        
        assert len(patient_shipments) == 2
        assert shipment1 in patient_shipments
        assert shipment2 in patient_shipments
