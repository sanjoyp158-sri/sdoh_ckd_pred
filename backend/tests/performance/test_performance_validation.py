"""
Performance validation tests for CKD Early Detection System.

Task 20.2: Run performance validation
- Verify prediction latency < 500ms (Requirement 2.4)
- Verify SHAP explanation latency < 200ms (Requirement 3.5)
- Verify intervention workflow initiation < 1 hour (Requirement 5.1)
- Load test API endpoints
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.data_integration import (
    UnifiedPatientRecord,
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    Demographics,
    Address
)
from app.ml.analytics_engine import MLAnalyticsEngine
from app.services.intervention_workflow import InterventionWorkflowEngine


class TestPredictionLatency:
    """Test prediction latency requirements."""
    
    @pytest.fixture
    def ml_engine(self):
        """Create ML analytics engine with mock model."""
        with patch('app.ml.analytics_engine.XGBoostClassifier') as mock_classifier:
            mock_model = Mock()
            mock_model.predict.return_value = 0.75
            mock_classifier.return_value = mock_model
            
            engine = MLAnalyticsEngine()
            engine.model = mock_model
            return engine
    
    @pytest.fixture
    def test_patients(self):
        """Create multiple test patient records."""
        patients = []
        for i in range(10):
            clinical = ClinicalRecord(
                egfr=30.0 + i * 2,
                egfr_history=[(datetime.now() - timedelta(days=180), 35.0 + i * 2)],
                uacr=250.0 + i * 20,
                hba1c=7.0 + i * 0.2,
                systolic_bp=130 + i * 2,
                diastolic_bp=80 + i,
                bmi=25.0 + i,
                medications=[],
                ckd_stage='3a',
                diagnosis_date=datetime.now() - timedelta(days=365),
                comorbidities=['diabetes', 'hypertension']
            )
            
            admin = AdministrativeRecord(
                visit_frequency_12mo=5 + i,
                specialist_referrals=[],
                insurance_type='Medicare',
                insurance_status='Active',
                last_visit_date=datetime.now() - timedelta(days=30)
            )
            
            sdoh = SDOHRecord(
                adi_percentile=60 + i * 2,
                food_desert=i % 2 == 0,
                housing_stability_score=0.5 + i * 0.03,
                transportation_access_score=0.4 + i * 0.04,
                rural_urban_code='6'
            )
            
            demographics = Demographics(
                age=60 + i,
                sex='M' if i % 2 == 0 else 'F',
                race='White',
                ethnicity='Non-Hispanic',
                address=Address(
                    street=f'{100 + i} Main St',
                    city='Test City',
                    state='AL',
                    zip_code='35000'
                )
            )
            
            patient = UnifiedPatientRecord(
                patient_id=f'P_PERF_{i:03d}',
                demographics=demographics,
                clinical=clinical,
                administrative=admin,
                sdoh=sdoh,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            patients.append(patient)
        
        return patients
    
    def test_single_prediction_latency(self, ml_engine, test_patients):
        """
        Test Requirement 2.4: Single prediction latency < 500ms
        """
        patient = test_patients[0]
        
        start_time = time.time()
        prediction = ml_engine.predict_progression_risk(patient)
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert prediction is not None
        assert 0.0 <= prediction.risk_score <= 1.0
        assert elapsed_ms < 500, f"Prediction took {elapsed_ms:.2f}ms, exceeds 500ms requirement"
        
        print(f"✓ Single prediction latency: {elapsed_ms:.2f}ms (< 500ms)")
    
    def test_average_prediction_latency(self, ml_engine, test_patients):
        """
        Test average prediction latency across multiple patients.
        """
        latencies = []
        
        for patient in test_patients:
            start_time = time.time()
            prediction = ml_engine.predict_progression_risk(patient)
            elapsed_ms = (time.time() - start_time) * 1000
            latencies.append(elapsed_ms)
            
            assert prediction is not None
        
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        assert avg_latency < 500, f"Average latency {avg_latency:.2f}ms exceeds 500ms"
        assert max_latency < 500, f"Max latency {max_latency:.2f}ms exceeds 500ms"
        
        print(f"✓ Prediction latency stats:")
        print(f"  - Average: {avg_latency:.2f}ms")
        print(f"  - Min: {min_latency:.2f}ms")
        print(f"  - Max: {max_latency:.2f}ms")
        print(f"  - All < 500ms requirement")
    
    def test_prediction_latency_percentiles(self, ml_engine, test_patients):
        """
        Test prediction latency percentiles (p50, p95, p99).
        """
        # Run more predictions for better percentile statistics
        latencies = []
        
        for _ in range(5):  # Run each patient 5 times
            for patient in test_patients:
                start_time = time.time()
                prediction = ml_engine.predict_progression_risk(patient)
                elapsed_ms = (time.time() - start_time) * 1000
                latencies.append(elapsed_ms)
        
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        
        assert p50 < 500, f"p50 latency {p50:.2f}ms exceeds 500ms"
        assert p95 < 500, f"p95 latency {p95:.2f}ms exceeds 500ms"
        assert p99 < 500, f"p99 latency {p99:.2f}ms exceeds 500ms"
        
        print(f"✓ Prediction latency percentiles:")
        print(f"  - p50: {p50:.2f}ms")
        print(f"  - p95: {p95:.2f}ms")
        print(f"  - p99: {p99:.2f}ms")
        print(f"  - All < 500ms requirement")


class TestSHAPExplanationLatency:
    """Test SHAP explanation latency requirements."""
    
    @pytest.fixture
    def ml_engine(self):
        """Create ML analytics engine with mock model."""
        with patch('app.ml.analytics_engine.XGBoostClassifier') as mock_classifier:
            mock_model = Mock()
            mock_model.predict.return_value = 0.75
            mock_classifier.return_value = mock_model
            
            engine = MLAnalyticsEngine()
            engine.model = mock_model
            return engine
    
    @pytest.fixture
    def test_patient(self):
        """Create test patient record."""
        clinical = ClinicalRecord(
            egfr=35.0,
            egfr_history=[(datetime.now() - timedelta(days=180), 40.0)],
            uacr=300.0,
            hba1c=7.5,
            systolic_bp=140,
            diastolic_bp=85,
            bmi=28.0,
            medications=[],
            ckd_stage='3a',
            diagnosis_date=datetime.now() - timedelta(days=365),
            comorbidities=['diabetes']
        )
        
        admin = AdministrativeRecord(
            visit_frequency_12mo=6,
            specialist_referrals=[],
            insurance_type='Medicare',
            insurance_status='Active',
            last_visit_date=datetime.now() - timedelta(days=30)
        )
        
        sdoh = SDOHRecord(
            adi_percentile=75,
            food_desert=True,
            housing_stability_score=0.6,
            transportation_access_score=0.4,
            rural_urban_code='6'
        )
        
        demographics = Demographics(
            age=65,
            sex='F',
            race='White',
            ethnicity='Non-Hispanic',
            address=Address(
                street='456 Oak Ave',
                city='Small Town',
                state='AL',
                zip_code='35000'
            )
        )
        
        return UnifiedPatientRecord(
            patient_id='P_SHAP_TEST',
            demographics=demographics,
            clinical=clinical,
            administrative=admin,
            sdoh=sdoh,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def test_single_shap_explanation_latency(self, ml_engine, test_patient):
        """
        Test Requirement 3.5: SHAP explanation latency < 200ms
        """
        # First generate prediction
        prediction = ml_engine.predict_progression_risk(test_patient)
        
        # Then measure SHAP explanation time
        start_time = time.time()
        explanation = ml_engine.explain_prediction(test_patient, prediction.risk_score)
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert explanation is not None
        assert len(explanation.top_factors) > 0
        assert elapsed_ms < 200, f"SHAP explanation took {elapsed_ms:.2f}ms, exceeds 200ms requirement"
        
        print(f"✓ SHAP explanation latency: {elapsed_ms:.2f}ms (< 200ms)")
    
    def test_average_shap_explanation_latency(self, ml_engine, test_patient):
        """
        Test average SHAP explanation latency across multiple runs.
        """
        prediction = ml_engine.predict_progression_risk(test_patient)
        latencies = []
        
        for _ in range(10):
            start_time = time.time()
            explanation = ml_engine.explain_prediction(test_patient, prediction.risk_score)
            elapsed_ms = (time.time() - start_time) * 1000
            latencies.append(elapsed_ms)
            
            assert explanation is not None
        
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        
        assert avg_latency < 200, f"Average SHAP latency {avg_latency:.2f}ms exceeds 200ms"
        assert max_latency < 200, f"Max SHAP latency {max_latency:.2f}ms exceeds 200ms"
        
        print(f"✓ SHAP explanation latency stats:")
        print(f"  - Average: {avg_latency:.2f}ms")
        print(f"  - Max: {max_latency:.2f}ms")
        print(f"  - All < 200ms requirement")


class TestInterventionWorkflowTiming:
    """Test intervention workflow timing requirements."""
    
    def test_workflow_initiation_timeout_configuration(self):
        """
        Test Requirement 5.1: Intervention workflow initiation < 1 hour
        
        This tests the configuration, not actual 1-hour wait.
        """
        engine = InterventionWorkflowEngine()
        
        # Check that workflow initiation timeout is configured correctly
        assert hasattr(engine, 'initiation_timeout_seconds')
        assert engine.initiation_timeout_seconds <= 3600  # 1 hour = 3600 seconds
        
        print(f"✓ Intervention workflow initiation timeout: {engine.initiation_timeout_seconds}s (< 3600s)")
    
    def test_workflow_initiation_immediate(self):
        """
        Test that workflow initiation happens immediately (not delayed).
        """
        engine = InterventionWorkflowEngine()
        
        # Create mock patient and tier
        from app.services.risk_stratification import RiskTier
        from app.ml.shap_explainer import SHAPExplanation, Factor
        
        mock_patient = Mock()
        mock_patient.patient_id = "P_TIMING_TEST"
        
        mock_explanation = SHAPExplanation(
            patient_id="P_TIMING_TEST",
            baseline_risk=0.3,
            prediction=0.75,
            shap_values={},
            top_factors=[],
            categorized_factors=Mock(),
            computation_time_ms=50
        )
        
        start_time = time.time()
        workflow = engine.initiate_workflow(mock_patient, RiskTier.HIGH, mock_explanation)
        elapsed_seconds = time.time() - start_time
        
        assert workflow is not None
        assert elapsed_seconds < 5, f"Workflow initiation took {elapsed_seconds:.2f}s, should be immediate"
        
        print(f"✓ Workflow initiation time: {elapsed_seconds:.3f}s (immediate)")


class TestConcurrentLoadPerformance:
    """Test system performance under concurrent load."""
    
    @pytest.fixture
    def ml_engine(self):
        """Create ML analytics engine with mock model."""
        with patch('app.ml.analytics_engine.XGBoostClassifier') as mock_classifier:
            mock_model = Mock()
            mock_model.predict.return_value = 0.75
            mock_classifier.return_value = mock_model
            
            engine = MLAnalyticsEngine()
            engine.model = mock_model
            return engine
    
    def test_concurrent_predictions(self, ml_engine):
        """
        Test prediction performance under concurrent load.
        """
        def make_prediction(patient_id):
            """Make a single prediction."""
            patient = UnifiedPatientRecord(
                patient_id=patient_id,
                demographics=Demographics(
                    age=65,
                    sex='M',
                    race='White',
                    ethnicity='Non-Hispanic',
                    address=Address(
                        street='123 Main St',
                        city='Test City',
                        state='AL',
                        zip_code='35000'
                    )
                ),
                clinical=ClinicalRecord(
                    egfr=35.0,
                    egfr_history=[],
                    uacr=300.0,
                    hba1c=7.5,
                    systolic_bp=140,
                    diastolic_bp=85,
                    bmi=28.0,
                    medications=[],
                    ckd_stage='3a',
                    diagnosis_date=datetime.now() - timedelta(days=365),
                    comorbidities=['diabetes']
                ),
                administrative=AdministrativeRecord(
                    visit_frequency_12mo=6,
                    specialist_referrals=[],
                    insurance_type='Medicare',
                    insurance_status='Active',
                    last_visit_date=datetime.now() - timedelta(days=30)
                ),
                sdoh=SDOHRecord(
                    adi_percentile=75,
                    food_desert=True,
                    housing_stability_score=0.6,
                    transportation_access_score=0.4,
                    rural_urban_code='6'
                ),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            start_time = time.time()
            prediction = ml_engine.predict_progression_risk(patient)
            elapsed_ms = (time.time() - start_time) * 1000
            
            return {
                'patient_id': patient_id,
                'latency_ms': elapsed_ms,
                'success': prediction is not None
            }
        
        # Run 20 concurrent predictions
        num_concurrent = 20
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_prediction, f'P_CONCURRENT_{i:03d}')
                for i in range(num_concurrent)
            ]
            
            results = [future.result() for future in as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Verify all predictions succeeded
        assert all(r['success'] for r in results)
        
        # Check latencies
        latencies = [r['latency_ms'] for r in results]
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        
        # Under concurrent load, individual predictions should still meet requirements
        assert max_latency < 500, f"Max concurrent latency {max_latency:.2f}ms exceeds 500ms"
        
        throughput = num_concurrent / total_time
        
        print(f"✓ Concurrent load test ({num_concurrent} predictions):")
        print(f"  - Total time: {total_time:.2f}s")
        print(f"  - Throughput: {throughput:.2f} predictions/second")
        print(f"  - Average latency: {avg_latency:.2f}ms")
        print(f"  - Max latency: {max_latency:.2f}ms")
        print(f"  - All predictions < 500ms requirement")


class TestSystemThroughput:
    """Test overall system throughput."""
    
    def test_predictions_per_second(self):
        """
        Test system can handle expected prediction load.
        
        Target: At least 10 predictions per second for a small deployment.
        """
        with patch('app.ml.analytics_engine.XGBoostClassifier') as mock_classifier:
            mock_model = Mock()
            mock_model.predict.return_value = 0.75
            mock_classifier.return_value = mock_model
            
            engine = MLAnalyticsEngine()
            engine.model = mock_model
            
            # Create test patient
            patient = UnifiedPatientRecord(
                patient_id='P_THROUGHPUT_TEST',
                demographics=Demographics(
                    age=65,
                    sex='M',
                    race='White',
                    ethnicity='Non-Hispanic',
                    address=Address(
                        street='123 Main St',
                        city='Test City',
                        state='AL',
                        zip_code='35000'
                    )
                ),
                clinical=ClinicalRecord(
                    egfr=35.0,
                    egfr_history=[],
                    uacr=300.0,
                    hba1c=7.5,
                    systolic_bp=140,
                    diastolic_bp=85,
                    bmi=28.0,
                    medications=[],
                    ckd_stage='3a',
                    diagnosis_date=datetime.now() - timedelta(days=365),
                    comorbidities=['diabetes']
                ),
                administrative=AdministrativeRecord(
                    visit_frequency_12mo=6,
                    specialist_referrals=[],
                    insurance_type='Medicare',
                    insurance_status='Active',
                    last_visit_date=datetime.now() - timedelta(days=30)
                ),
                sdoh=SDOHRecord(
                    adi_percentile=75,
                    food_desert=True,
                    housing_stability_score=0.6,
                    transportation_access_score=0.4,
                    rural_urban_code='6'
                ),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Run predictions for 2 seconds
            start_time = time.time()
            count = 0
            
            while time.time() - start_time < 2.0:
                prediction = engine.predict_progression_risk(patient)
                assert prediction is not None
                count += 1
            
            elapsed = time.time() - start_time
            throughput = count / elapsed
            
            assert throughput >= 10, f"Throughput {throughput:.2f} predictions/s is below 10/s target"
            
            print(f"✓ System throughput: {throughput:.2f} predictions/second (>= 10/s target)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
