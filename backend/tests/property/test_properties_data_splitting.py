"""
Property-based tests for data preparation and splitting.
Tests universal correctness properties using Hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, settings as hyp_settings, HealthCheck
import pandas as pd
from datetime import datetime, timedelta

from app.ml.data_preparation import DataPreparation


# Custom strategies
@st.composite
def patient_dataframe_strategy(draw, min_size=30, max_size=100):
    """Generate valid patient DataFrames for testing."""
    n = draw(st.integers(min_value=min_size, max_value=max_size))
    
    # Generate dates in chronological order
    base_date = datetime(2020, 1, 1)
    dates = [base_date + timedelta(days=i*30) for i in range(n)]
    
    data = {
        'patient_id': [f'P{i:05d}' for i in range(n)],
        'baseline_date': dates,
        'outcome_date': [d + timedelta(days=730) for d in dates],  # 24 months later
        'progressed_to_stage_4_5': [draw(st.booleans()) for _ in range(n)],
        'egfr': [draw(st.floats(min_value=15.0, max_value=89.0)) for _ in range(n)],
        'uacr': [draw(st.floats(min_value=0.0, max_value=3000.0)) for _ in range(n)],
        'hba1c': [draw(st.floats(min_value=4.0, max_value=14.0)) for _ in range(n)],
        'systolic_bp': [draw(st.integers(min_value=80, max_value=200)) for _ in range(n)],
        'diastolic_bp': [draw(st.integers(min_value=40, max_value=120)) for _ in range(n)],
        'bmi': [draw(st.floats(min_value=15.0, max_value=50.0)) for _ in range(n)],
        'ckd_stage': [draw(st.sampled_from(['2', '3a', '3b'])) for _ in range(n)],
        'age': [draw(st.integers(min_value=18, max_value=100)) for _ in range(n)],
        'sex': [draw(st.sampled_from(['M', 'F'])) for _ in range(n)],
        'visit_frequency_12mo': [draw(st.integers(min_value=0, max_value=50)) for _ in range(n)],
        'insurance_type': [draw(st.sampled_from(['Medicare', 'Medicaid', 'Private'])) for _ in range(n)],
        'adi_percentile': [draw(st.integers(min_value=1, max_value=100)) for _ in range(n)],
        'food_desert': [draw(st.booleans()) for _ in range(n)],
        'housing_stability_score': [draw(st.floats(min_value=0.0, max_value=1.0)) for _ in range(n)],
        'transportation_access_score': [draw(st.floats(min_value=0.0, max_value=1.0)) for _ in range(n)],
    }
    
    return pd.DataFrame(data)


@pytest.mark.property_test
class TestProperty41_TrainingDataSplitProportions:
    """
    Property 41: Training Data Split Proportions
    
    For any training dataset, the data split should allocate 70% to training, 
    15% to validation, and 15% to test sets (within rounding tolerance).
    
    **Validates: Requirements 11.1**
    """
    
    @given(df=patient_dataframe_strategy(min_size=50, max_size=100))
    @hyp_settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large]
    )
    def test_split_proportions(self, df):
        """Test that data split proportions are correct."""
        prep = DataPreparation()
        
        # Perform temporal split
        train_df, val_df, test_df = prep.temporal_split(df)
        
        # Property 1: All data should be included in one of the splits
        total_split = len(train_df) + len(val_df) + len(test_df)
        assert total_split == len(df), \
            f"Data loss in split: {len(df)} -> {total_split}"
        
        # Property 2: Train split should be approximately 70% (within 2% tolerance)
        train_ratio = len(train_df) / len(df)
        assert 0.68 <= train_ratio <= 0.72, \
            f"Train ratio {train_ratio:.3f} outside expected range [0.68, 0.72]"
        
        # Property 3: Validation split should be approximately 15% (within 2% tolerance)
        val_ratio = len(val_df) / len(df)
        assert 0.13 <= val_ratio <= 0.17, \
            f"Validation ratio {val_ratio:.3f} outside expected range [0.13, 0.17]"
        
        # Property 4: Test split should be approximately 15% (within 2% tolerance)
        test_ratio = len(test_df) / len(df)
        assert 0.13 <= test_ratio <= 0.17, \
            f"Test ratio {test_ratio:.3f} outside expected range [0.13, 0.17]"
        
        # Property 5: Ratios should sum to 1.0
        total_ratio = train_ratio + val_ratio + test_ratio
        assert abs(total_ratio - 1.0) < 0.001, \
            f"Ratios sum to {total_ratio:.3f}, expected 1.0"


@pytest.mark.property_test
class TestProperty42_TemporalValidationOrdering:
    """
    Property 42: Temporal Validation Ordering
    
    For any data split, the maximum date in the training set should be less than 
    the minimum date in the validation set, and the maximum date in the validation 
    set should be less than the minimum date in the test set.
    
    **Validates: Requirements 11.2**
    """
    
    @given(df=patient_dataframe_strategy(min_size=50, max_size=100))
    @hyp_settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large]
    )
    def test_temporal_ordering(self, df):
        """Test that temporal ordering is maintained across splits."""
        prep = DataPreparation()
        
        # Perform temporal split
        train_df, val_df, test_df = prep.temporal_split(df, date_column='baseline_date')
        
        # Property 1: Train data should precede validation data
        if not train_df.empty and not val_df.empty:
            train_max_date = train_df['baseline_date'].max()
            val_min_date = val_df['baseline_date'].min()
            assert train_max_date <= val_min_date, \
                f"Train max date {train_max_date} > Val min date {val_min_date}"
        
        # Property 2: Validation data should precede test data
        if not val_df.empty and not test_df.empty:
            val_max_date = val_df['baseline_date'].max()
            test_min_date = test_df['baseline_date'].min()
            assert val_max_date <= test_min_date, \
                f"Val max date {val_max_date} > Test min date {test_min_date}"
        
        # Property 3: Train data should precede test data (transitivity)
        if not train_df.empty and not test_df.empty:
            train_max_date = train_df['baseline_date'].max()
            test_min_date = test_df['baseline_date'].min()
            assert train_max_date <= test_min_date, \
                f"Train max date {train_max_date} > Test min date {test_min_date}"
    
    @given(df=patient_dataframe_strategy(min_size=50, max_size=100))
    @hyp_settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.large_base_example, HealthCheck.data_too_large]
    )
    def test_no_data_leakage(self, df):
        """Test that there is no temporal data leakage between splits."""
        prep = DataPreparation()
        
        # Perform temporal split
        train_df, val_df, test_df = prep.temporal_split(df, date_column='baseline_date')
        
        # Property 4: No patient should appear in multiple splits
        train_ids = set(train_df['patient_id'])
        val_ids = set(val_df['patient_id'])
        test_ids = set(test_df['patient_id'])
        
        assert len(train_ids & val_ids) == 0, \
            "Patients appear in both train and validation sets"
        assert len(train_ids & test_ids) == 0, \
            "Patients appear in both train and test sets"
        assert len(val_ids & test_ids) == 0, \
            "Patients appear in both validation and test sets"


@pytest.mark.property_test
class TestDataPreparationProperties:
    """Additional data preparation properties."""
    
    @given(df=patient_dataframe_strategy(min_size=50, max_size=200))
    @hyp_settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.large_base_example]
    )
    def test_stage_2_3_filtering(self, df):
        """Test that filtering correctly selects Stage 2-3 patients."""
        prep = DataPreparation()
        
        # Filter to Stage 2-3
        filtered_df = prep.filter_stage_2_3_patients(df)
        
        # Property: All filtered patients should have Stage 2, 3a, or 3b
        valid_stages = {'2', '3a', '3b'}
        if not filtered_df.empty:
            assert set(filtered_df['ckd_stage'].unique()).issubset(valid_stages), \
                "Filtered data contains invalid CKD stages"
    
    @given(df=patient_dataframe_strategy(min_size=50, max_size=200))
    @hyp_settings(
        max_examples=20,
        deadline=None,
        suppress_health_check=[HealthCheck.large_base_example]
    )
    def test_split_statistics(self, df):
        """Test that split statistics are calculated correctly."""
        prep = DataPreparation()
        
        # Perform split
        train_df, val_df, test_df = prep.temporal_split(df)
        
        # Get statistics
        stats = prep.get_split_statistics(train_df, val_df, test_df)
        
        # Property: Statistics should match actual data
        assert stats['total'] == len(df)
        assert stats['train_count'] == len(train_df)
        assert stats['val_count'] == len(val_df)
        assert stats['test_count'] == len(test_df)
        assert abs(stats['train_ratio'] - len(train_df) / len(df)) < 0.001
        assert abs(stats['val_ratio'] - len(val_df) / len(df)) < 0.001
        assert abs(stats['test_ratio'] - len(test_df) / len(df)) < 0.001
