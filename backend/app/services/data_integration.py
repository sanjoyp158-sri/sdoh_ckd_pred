"""
Data Integration Layer for ingesting and harmonizing patient data.

This module handles data ingestion from EHR systems, administrative systems,
and SDOH providers, with validation and error handling.
"""

from datetime import datetime
from typing import Dict, Optional, List, Tuple
import logging

from app.models.patient import (
    ClinicalRecord,
    AdministrativeRecord,
    SDOHRecord,
    UnifiedPatientRecord,
    Demographics,
    Address,
    Medication,
    Referral,
)


logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass


class DataIntegrationLayer:
    """
    Handles data ingestion from multiple sources and harmonization.
    
    Responsibilities:
    - Ingest clinical data from EHR systems
    - Ingest administrative data from billing systems
    - Retrieve SDOH data from external providers
    - Harmonize data into unified patient records
    - Handle ingestion failures gracefully with logging
    """
    
    def __init__(self):
        """Initialize the Data Integration Layer."""
        self.logger = logging.getLogger(__name__)
    
    def ingest_clinical_data(self, ehr_payload: Dict) -> ClinicalRecord:
        """
        Ingest clinical data from EHR system.
        
        Validates and extracts required fields: eGFR, UACR, HbA1c, 
        blood pressure, BMI, and medication records.
        
        Args:
            ehr_payload: Dictionary containing clinical data from EHR
            
        Returns:
            ClinicalRecord with validated clinical data
            
        Raises:
            DataValidationError: If required fields are missing or invalid
        """
        try:
            # Validate required fields
            required_fields = ['egfr', 'uacr', 'hba1c', 'systolic_bp', 
                             'diastolic_bp', 'bmi', 'ckd_stage', 'diagnosis_date']
            missing_fields = [f for f in required_fields if f not in ehr_payload]
            
            if missing_fields:
                error_msg = f"Missing required clinical fields: {missing_fields}"
                self.logger.error(error_msg)
                raise DataValidationError(error_msg)
            
            # Extract eGFR history if available
            egfr_history = []
            if 'egfr_history' in ehr_payload and ehr_payload['egfr_history']:
                for entry in ehr_payload['egfr_history']:
                    date = self._parse_datetime(entry.get('date'))
                    value = float(entry.get('value'))
                    egfr_history.append((date, value))
            
            # Extract medications
            medications = []
            if 'medications' in ehr_payload and ehr_payload['medications']:
                for med in ehr_payload['medications']:
                    medication = Medication(
                        name=med.get('name', ''),
                        category=med.get('category', ''),
                        start_date=self._parse_datetime(med.get('start_date')) if med.get('start_date') else None,
                        active=med.get('active', True)
                    )
                    medications.append(medication)
            
            # Extract comorbidities
            comorbidities = ehr_payload.get('comorbidities', [])
            
            # Create ClinicalRecord
            clinical_record = ClinicalRecord(
                egfr=float(ehr_payload['egfr']),
                egfr_history=egfr_history,
                uacr=float(ehr_payload['uacr']),
                hba1c=float(ehr_payload['hba1c']),
                systolic_bp=int(ehr_payload['systolic_bp']),
                diastolic_bp=int(ehr_payload['diastolic_bp']),
                bmi=float(ehr_payload['bmi']),
                medications=medications,
                ckd_stage=str(ehr_payload['ckd_stage']),
                diagnosis_date=self._parse_datetime(ehr_payload['diagnosis_date']),
                comorbidities=comorbidities
            )
            
            self.logger.info("Successfully ingested clinical data")
            return clinical_record
            
        except (KeyError, ValueError, TypeError) as e:
            error_msg = f"Error ingesting clinical data: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise DataValidationError(error_msg) from e
    
    def ingest_administrative_data(self, admin_payload: Dict) -> AdministrativeRecord:
        """
        Ingest administrative data from billing system.
        
        Validates and extracts required fields: visit frequency, 
        referral records, and insurance status.
        
        Args:
            admin_payload: Dictionary containing administrative data
            
        Returns:
            AdministrativeRecord with validated administrative data
            
        Raises:
            DataValidationError: If required fields are missing or invalid
        """
        try:
            # Validate required fields
            required_fields = ['visit_frequency_12mo', 'insurance_type', 
                             'insurance_status', 'last_visit_date']
            missing_fields = [f for f in required_fields if f not in admin_payload]
            
            if missing_fields:
                error_msg = f"Missing required administrative fields: {missing_fields}"
                self.logger.error(error_msg)
                raise DataValidationError(error_msg)
            
            # Extract specialist referrals
            referrals = []
            if 'specialist_referrals' in admin_payload and admin_payload['specialist_referrals']:
                for ref in admin_payload['specialist_referrals']:
                    referral = Referral(
                        specialty=ref.get('specialty', ''),
                        date=self._parse_datetime(ref.get('date')),
                        completed=ref.get('completed', False),
                        reason=ref.get('reason')
                    )
                    referrals.append(referral)
            
            # Create AdministrativeRecord
            admin_record = AdministrativeRecord(
                visit_frequency_12mo=int(admin_payload['visit_frequency_12mo']),
                specialist_referrals=referrals,
                insurance_type=str(admin_payload['insurance_type']),
                insurance_status=str(admin_payload['insurance_status']),
                last_visit_date=self._parse_datetime(admin_payload['last_visit_date'])
            )
            
            self.logger.info("Successfully ingested administrative data")
            return admin_record
            
        except (KeyError, ValueError, TypeError) as e:
            error_msg = f"Error ingesting administrative data: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise DataValidationError(error_msg) from e
    
    def retrieve_sdoh_data(self, patient_address: Address) -> SDOHRecord:
        """
        Retrieve SDOH data for patient address.
        
        Retrieves required SDOH fields: ADI score, food desert status,
        housing stability indicators, and transportation access metrics.
        
        Args:
            patient_address: Patient's address for SDOH lookup
            
        Returns:
            SDOHRecord with SDOH data for the address
            
        Raises:
            DataValidationError: If address is invalid or SDOH data unavailable
        """
        try:
            # Validate address has required fields
            if not patient_address or not patient_address.zip_code:
                error_msg = "Patient address or ZIP code is missing"
                self.logger.error(error_msg)
                raise DataValidationError(error_msg)
            
            # In a real implementation, this would call external SDOH APIs
            # For now, we'll simulate the data retrieval
            # TODO: Integrate with actual SDOH data providers
            
            self.logger.info(f"Retrieving SDOH data for ZIP code: {patient_address.zip_code}")
            
            # Placeholder: In production, this would query external SDOH services
            # For now, return a structure that would be populated by the API
            sdoh_data = self._fetch_sdoh_from_provider(patient_address)
            
            # Validate required SDOH fields
            required_fields = ['adi_percentile', 'food_desert', 
                             'housing_stability_score', 'transportation_access_score',
                             'rural_urban_code']
            missing_fields = [f for f in required_fields if f not in sdoh_data]
            
            if missing_fields:
                error_msg = f"Missing required SDOH fields: {missing_fields}"
                self.logger.error(error_msg)
                raise DataValidationError(error_msg)
            
            # Create SDOHRecord
            sdoh_record = SDOHRecord(
                adi_percentile=int(sdoh_data['adi_percentile']),
                food_desert=bool(sdoh_data['food_desert']),
                housing_stability_score=float(sdoh_data['housing_stability_score']),
                transportation_access_score=float(sdoh_data['transportation_access_score']),
                rural_urban_code=str(sdoh_data['rural_urban_code'])
            )
            
            self.logger.info("Successfully retrieved SDOH data")
            return sdoh_record
            
        except (KeyError, ValueError, TypeError) as e:
            error_msg = f"Error retrieving SDOH data: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise DataValidationError(error_msg) from e
    
    def harmonize_patient_record(
        self,
        patient_id: str,
        demographics: Demographics,
        clinical: ClinicalRecord,
        administrative: AdministrativeRecord,
        sdoh: Optional[SDOHRecord] = None
    ) -> UnifiedPatientRecord:
        """
        Combine data sources into unified patient record.
        
        Handles missing SDOH data by using regional averages as fallback.
        Logs errors with source identification when data is unavailable.
        
        Args:
            patient_id: Unique patient identifier
            demographics: Patient demographic information
            clinical: Clinical data record
            administrative: Administrative data record
            sdoh: SDOH data record (optional, will use regional averages if None)
            
        Returns:
            UnifiedPatientRecord combining all data sources
        """
        try:
            now = datetime.utcnow()
            
            # Handle missing SDOH data with regional averages
            if sdoh is None:
                self.logger.warning(
                    f"SDOH data unavailable for patient {patient_id}, "
                    f"using regional averages. Source: SDOH provider"
                )
                sdoh = self._get_regional_average_sdoh(demographics.address)
            
            unified_record = UnifiedPatientRecord(
                patient_id=patient_id,
                demographics=demographics,
                clinical=clinical,
                administrative=administrative,
                sdoh=sdoh,
                created_at=now,
                updated_at=now
            )
            
            self.logger.info(f"Successfully harmonized patient record for patient {patient_id}")
            return unified_record
            
        except Exception as e:
            error_msg = f"Error harmonizing patient record for patient {patient_id}: {str(e)}"
            self.logger.error(f"{error_msg}. Source: Data harmonization layer", exc_info=True)
            raise DataValidationError(error_msg) from e
    
    def ingest_patient_data(
        self,
        patient_id: str,
        demographics_payload: Dict,
        ehr_payload: Dict,
        admin_payload: Dict,
        address: Address
    ) -> UnifiedPatientRecord:
        """
        Complete data ingestion workflow for a patient.
        
        Ingests data from all sources and handles partial failures gracefully.
        Logs errors with source identification and continues processing available data.
        
        Args:
            patient_id: Unique patient identifier
            demographics_payload: Patient demographic data
            ehr_payload: Clinical data from EHR
            admin_payload: Administrative data
            address: Patient address for SDOH lookup
            
        Returns:
            UnifiedPatientRecord with all available data
            
        Raises:
            DataValidationError: If critical data (demographics, clinical, administrative) is missing
        """
        errors = []
        
        # Parse demographics
        try:
            demographics = Demographics(
                age=int(demographics_payload['age']),
                sex=str(demographics_payload['sex']),
                race=demographics_payload.get('race'),
                ethnicity=demographics_payload.get('ethnicity'),
                address=address
            )
        except Exception as e:
            error_msg = f"Failed to parse demographics for patient {patient_id}: {str(e)}"
            self.logger.error(f"{error_msg}. Source: Demographics payload")
            errors.append(('demographics', error_msg))
            raise DataValidationError(error_msg) from e
        
        # Ingest clinical data
        try:
            clinical = self.ingest_clinical_data(ehr_payload)
        except DataValidationError as e:
            error_msg = f"Failed to ingest clinical data for patient {patient_id}: {str(e)}"
            self.logger.error(f"{error_msg}. Source: EHR system")
            errors.append(('clinical', error_msg))
            raise  # Clinical data is critical, re-raise
        
        # Ingest administrative data
        try:
            administrative = self.ingest_administrative_data(admin_payload)
        except DataValidationError as e:
            error_msg = f"Failed to ingest administrative data for patient {patient_id}: {str(e)}"
            self.logger.error(f"{error_msg}. Source: Administrative system")
            errors.append(('administrative', error_msg))
            raise  # Administrative data is critical, re-raise
        
        # Retrieve SDOH data with fallback to regional averages
        sdoh = None
        try:
            sdoh = self.retrieve_sdoh_data(address)
        except DataValidationError as e:
            error_msg = f"Failed to retrieve SDOH data for patient {patient_id}: {str(e)}"
            self.logger.warning(f"{error_msg}. Source: SDOH provider. Using regional averages as fallback.")
            errors.append(('sdoh', error_msg))
            # SDOH data failure is logged but we continue with regional averages
            # The harmonize_patient_record method will handle the None value
        
        # Log any errors encountered
        if errors:
            self.logger.warning(
                f"Encountered {len(errors)} error(s) during ingestion for patient {patient_id}: "
                f"{[f'{source}: {msg}' for source, msg in errors]}"
            )
        
        # Harmonize into unified record (will use regional averages if sdoh is None)
        return self.harmonize_patient_record(
            patient_id=patient_id,
            demographics=demographics,
            clinical=clinical,
            administrative=administrative,
            sdoh=sdoh
        )
    
    
    def _get_regional_average_sdoh(self, address: Address) -> SDOHRecord:
        """
        Get regional average SDOH data as fallback when address-specific data is unavailable.
        
        Uses state-level or national averages based on available address information.
        
        Args:
            address: Patient address (may have partial information)
            
        Returns:
            SDOHRecord with regional average SDOH data
        """
        # Regional averages by state (simplified for implementation)
        # In production, this would query a database of regional statistics
        state_averages = {
            'AL': {'adi': 65, 'food_desert': True, 'housing': 0.55, 'transport': 0.45},
            'CA': {'adi': 45, 'food_desert': False, 'housing': 0.65, 'transport': 0.70},
            'FL': {'adi': 50, 'food_desert': False, 'housing': 0.60, 'transport': 0.65},
            'GA': {'adi': 55, 'food_desert': False, 'housing': 0.58, 'transport': 0.60},
            'IL': {'adi': 48, 'food_desert': False, 'housing': 0.62, 'transport': 0.68},
            'MI': {'adi': 52, 'food_desert': False, 'housing': 0.60, 'transport': 0.62},
            'MS': {'adi': 70, 'food_desert': True, 'housing': 0.50, 'transport': 0.40},
            'NC': {'adi': 53, 'food_desert': False, 'housing': 0.60, 'transport': 0.62},
            'NY': {'adi': 42, 'food_desert': False, 'housing': 0.68, 'transport': 0.75},
            'OH': {'adi': 51, 'food_desert': False, 'housing': 0.61, 'transport': 0.63},
            'PA': {'adi': 49, 'food_desert': False, 'housing': 0.63, 'transport': 0.66},
            'TX': {'adi': 54, 'food_desert': False, 'housing': 0.58, 'transport': 0.62},
        }
        
        # National averages as ultimate fallback
        national_averages = {
            'adi': 50,
            'food_desert': False,
            'housing': 0.60,
            'transport': 0.60
        }
        
        # Determine which averages to use
        if address and address.state and address.state in state_averages:
            averages = state_averages[address.state]
            self.logger.info(f"Using state-level averages for {address.state}")
        else:
            averages = national_averages
            self.logger.info("Using national averages (state not available or not in lookup)")
        
        # Determine rural/urban code based on state (simplified)
        # In production, this would use actual RUCA codes
        rural_states = ['AL', 'MS', 'WV', 'AR', 'KY']
        rural_urban_code = 'rural' if (address and address.state in rural_states) else 'urban'
        
        return SDOHRecord(
            adi_percentile=averages['adi'],
            food_desert=averages['food_desert'],
            housing_stability_score=averages['housing'],
            transportation_access_score=averages['transport'],
            rural_urban_code=rural_urban_code
        )
    
    def _parse_datetime(self, date_value) -> datetime:
        """
        Parse datetime from various formats.
        
        Args:
            date_value: Date as string, datetime, or timestamp
            
        Returns:
            datetime object
        """
        if isinstance(date_value, datetime):
            return date_value
        elif isinstance(date_value, str):
            # Try common formats
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date: {date_value}")
        elif isinstance(date_value, (int, float)):
            # Assume Unix timestamp
            return datetime.fromtimestamp(date_value)
        else:
            raise ValueError(f"Unsupported date type: {type(date_value)}")
    
    def _fetch_sdoh_from_provider(self, address: Address) -> Dict:
        """
        Fetch SDOH data from external provider.
        
        This is a placeholder for actual SDOH API integration.
        
        Args:
            address: Patient address
            
        Returns:
            Dictionary with SDOH data
        """
        # TODO: Implement actual SDOH provider integration
        # For now, return placeholder structure
        # In production, this would call external APIs like:
        # - Neighborhood Atlas for ADI
        # - USDA Food Access Research Atlas for food deserts
        # - HUD data for housing stability
        # - Census/DOT data for transportation access
        
        self.logger.warning("Using placeholder SDOH data - integrate with actual providers")
        
        return {
            'adi_percentile': 50,  # Placeholder
            'food_desert': False,  # Placeholder
            'housing_stability_score': 0.7,  # Placeholder
            'transportation_access_score': 0.6,  # Placeholder
            'rural_urban_code': 'urban'  # Placeholder
        }
