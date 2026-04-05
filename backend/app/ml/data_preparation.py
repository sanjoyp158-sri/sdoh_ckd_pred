"""
Data preparation and splitting logic for model training.
Implements temporal data splits with proper chronological ordering.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DataPreparation:
    """
    Data preparation for CKD progression model training.
    
    Features:
    - Load historical patient data with 24-month outcomes
    - Filter to Stage 2-3 CKD patients at baseline
    - Temporal data split (70% train, 15% validation, 15% test)
    - Chronological ordering (train < validation < test)
    """
    
    def __init__(self):
        """Initialize Data Preparation."""
        self.train_ratio = 0.70
        self.val_ratio = 0.15
        self.test_ratio = 0.15
    
    def load_historical_data(self, data_path: str) -> pd.DataFrame:
        """
        Load historical patient data with 24-month outcomes.
        
        Args:
            data_path: Path to historical data file
        
        Returns:
            DataFrame with patient records and outcomes
        """
        logger.info(f"Loading historical data from {data_path}")
        
        # In production, this would load from database or file
        # For now, return empty DataFrame with expected schema
        df = pd.DataFrame(columns=[
            'patient_id',
            'baseline_date',
            'outcome_date',
            'progressed_to_stage_4_5',
            'egfr',
            'uacr',
            'hba1c',
            'systolic_bp',
            'diastolic_bp',
            'bmi',
            'ckd_stage',
            'age',
            'sex',
            'visit_frequency_12mo',
            'insurance_type',
            'adi_percentile',
            'food_desert',
            'housing_stability_score',
            'transportation_access_score',
        ])
        
        logger.info(f"Loaded {len(df)} patient records")
        return df
    
    def filter_stage_2_3_patients(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter to Stage 2-3 CKD patients at baseline.
        
        Args:
            df: DataFrame with patient records
        
        Returns:
            Filtered DataFrame with only Stage 2-3 patients
        """
        logger.info("Filtering to Stage 2-3 CKD patients")
        
        if df.empty:
            return df
        
        # Filter to Stage 2, 3a, 3b
        valid_stages = ['2', '3a', '3b']
        filtered_df = df[df['ckd_stage'].isin(valid_stages)].copy()
        
        logger.info(f"Filtered to {len(filtered_df)} Stage 2-3 patients")
        return filtered_df
    
    def temporal_split(
        self,
        df: pd.DataFrame,
        date_column: str = 'baseline_date'
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Implement temporal data split with chronological ordering.
        
        Args:
            df: DataFrame with patient records
            date_column: Column name containing dates for temporal ordering
        
        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        logger.info("Performing temporal data split")
        
        if df.empty:
            return df, df, df
        
        # Sort by date
        df_sorted = df.sort_values(date_column).reset_index(drop=True)
        
        # Calculate split indices
        n = len(df_sorted)
        train_end = int(n * self.train_ratio)
        val_end = int(n * (self.train_ratio + self.val_ratio))
        
        # Split data
        train_df = df_sorted.iloc[:train_end].copy()
        val_df = df_sorted.iloc[train_end:val_end].copy()
        test_df = df_sorted.iloc[val_end:].copy()
        
        logger.info(
            f"Split data: train={len(train_df)} ({len(train_df)/n*100:.1f}%), "
            f"val={len(val_df)} ({len(val_df)/n*100:.1f}%), "
            f"test={len(test_df)} ({len(test_df)/n*100:.1f}%)"
        )
        
        # Verify chronological ordering
        if not train_df.empty and not val_df.empty:
            train_max_date = train_df[date_column].max()
            val_min_date = val_df[date_column].min()
            assert train_max_date <= val_min_date, \
                "Train data must precede validation data chronologically"
        
        if not val_df.empty and not test_df.empty:
            val_max_date = val_df[date_column].max()
            test_min_date = test_df[date_column].min()
            assert val_max_date <= test_min_date, \
                "Validation data must precede test data chronologically"
        
        logger.info("Temporal ordering verified")
        
        return train_df, val_df, test_df
    
    def prepare_training_data(
        self,
        data_path: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Complete data preparation pipeline.
        
        Args:
            data_path: Path to historical data file
        
        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        # Load data
        df = self.load_historical_data(data_path)
        
        # Filter to Stage 2-3 patients
        df_filtered = self.filter_stage_2_3_patients(df)
        
        # Temporal split
        train_df, val_df, test_df = self.temporal_split(df_filtered)
        
        return train_df, val_df, test_df
    
    def get_split_statistics(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Get statistics about the data split.
        
        Args:
            train_df: Training DataFrame
            val_df: Validation DataFrame
            test_df: Test DataFrame
        
        Returns:
            Dictionary with split statistics
        """
        total = len(train_df) + len(val_df) + len(test_df)
        
        if total == 0:
            return {
                'total': 0,
                'train_count': 0,
                'val_count': 0,
                'test_count': 0,
                'train_ratio': 0.0,
                'val_ratio': 0.0,
                'test_ratio': 0.0,
            }
        
        return {
            'total': total,
            'train_count': len(train_df),
            'val_count': len(val_df),
            'test_count': len(test_df),
            'train_ratio': len(train_df) / total,
            'val_ratio': len(val_df) / total,
            'test_ratio': len(test_df) / total,
        }
