# Requirements Document

## Introduction

The SDOH-CKDPred application is an AI-enabled early detection system for Chronic Kidney Disease (CKD) in underserved communities. The system integrates clinical data with neighborhood-level Social Determinants of Health (SDOH) to predict CKD progression from Stage 2-3 to Stage 4-5 within 24 months. It provides automated telehealth intervention workflows, risk stratification, and explainable AI predictions to improve health equity and reduce healthcare costs in rural and underserved populations.

## Glossary

- **CKD_Prediction_System**: The complete AI-enabled early detection system for chronic kidney disease
- **ML_Analytics_Engine**: The machine learning component that processes clinical and SDOH data to predict CKD progression
- **XGBoost_Classifier**: The gradient boosting machine learning algorithm used for CKD progression prediction
- **SHAP_Explainer**: The SHapley Additive exPlanations component that provides interpretable explanations for ML predictions
- **Risk_Stratification_Module**: The component that categorizes patients into risk tiers based on prediction scores
- **Intervention_Workflow_Engine**: The automated system that triggers and manages telehealth interventions
- **Data_Integration_Layer**: The component that ingests and harmonizes data from clinical, administrative, and SDOH sources
- **Provider_Dashboard**: The user interface for healthcare providers to view predictions and explanations
- **Clinical_Data**: Patient health measurements including eGFR, UACR, HbA1c, blood pressure, BMI, and medications
- **Administrative_Data**: Healthcare utilization data including visit frequency, referrals, and insurance status
- **SDOH_Data**: Social determinants of health including Area Deprivation Index, food desert status, housing stability, and transportation access
- **eGFR**: Estimated Glomerular Filtration Rate, a measure of kidney function
- **UACR**: Urine Albumin-to-Creatinine Ratio, a marker of kidney damage
- **ADI**: Area Deprivation Index, a neighborhood-level measure of socioeconomic disadvantage
- **AUROC**: Area Under the Receiver Operating Characteristic curve, a performance metric for binary classifiers
- **BCR**: Benefit-Cost Ratio, a measure of cost-effectiveness
- **Stage_2_3_CKD**: Early to moderate chronic kidney disease (eGFR 30-89 mL/min/1.73m²)
- **Stage_4_5_CKD**: Advanced chronic kidney disease requiring intensive management (eGFR <30 mL/min/1.73m²)
- **Telehealth_Scheduler**: The component that automatically schedules virtual nephrology consultations
- **Home_Blood_Draw_Dispatcher**: The component that arranges home-based laboratory testing
- **Case_Manager_Enrollment**: The component that enrolls high-risk patients with case management services

## Requirements

### Requirement 1: Data Integration from Multiple Sources

**User Story:** As a healthcare system administrator, I want to integrate clinical, administrative, and SDOH data from multiple sources, so that the ML model has comprehensive patient information for accurate predictions.

#### Acceptance Criteria

1. WHEN clinical data is received from an EHR system, THE Data_Integration_Layer SHALL ingest eGFR, UACR, HbA1c, blood pressure, BMI, and medication records
2. WHEN administrative data is received, THE Data_Integration_Layer SHALL ingest visit frequency, referral records, and insurance status
3. WHEN SDOH data is requested for a patient address, THE Data_Integration_Layer SHALL retrieve ADI score, food desert status, housing stability indicators, and transportation access metrics
4. THE Data_Integration_Layer SHALL harmonize data from all three channels into a unified patient record
5. WHEN data ingestion fails for any channel, THE Data_Integration_Layer SHALL log the error with source identification and continue processing available data

### Requirement 2: CKD Progression Prediction

**User Story:** As a nephrologist, I want to predict which Stage 2-3 CKD patients will progress to Stage 4-5 within 24 months, so that I can intervene early with high-risk patients.

#### Acceptance Criteria

1. WHEN a patient record with Stage 2-3 CKD is provided, THE ML_Analytics_Engine SHALL generate a progression risk score between 0 and 1
2. THE XGBoost_Classifier SHALL achieve an AUROC of at least 0.87 on validation data
3. THE ML_Analytics_Engine SHALL process clinical features, administrative features, and SDOH features to generate predictions
4. WHEN a prediction is generated, THE ML_Analytics_Engine SHALL complete processing within 500 milliseconds
5. THE XGBoost_Classifier SHALL use only patients with Stage 2-3 CKD at baseline for prediction training

### Requirement 3: Explainable AI with SHAP

**User Story:** As a primary care physician, I want to understand why a patient was flagged as high-risk, so that I can have informed conversations with the patient about their specific risk factors.

#### Acceptance Criteria

1. WHEN a prediction is generated, THE SHAP_Explainer SHALL compute feature importance values for all input features
2. THE SHAP_Explainer SHALL identify the top 5 contributing factors for each prediction
3. THE SHAP_Explainer SHALL categorize contributing factors as clinical, administrative, or SDOH
4. WHEN SHAP values are computed, THE SHAP_Explainer SHALL normalize values to sum to the difference between the prediction and baseline risk
5. THE SHAP_Explainer SHALL generate explanations within 200 milliseconds of prediction completion

### Requirement 4: Risk Stratification

**User Story:** As a care coordinator, I want patients automatically categorized into risk tiers, so that I can prioritize outreach efforts for the highest-risk individuals.

#### Acceptance Criteria

1. WHEN a risk score is generated, THE Risk_Stratification_Module SHALL assign patients to one of three tiers: high-risk, moderate-risk, or low-risk
2. THE Risk_Stratification_Module SHALL classify patients with risk scores above 0.65 as high-risk
3. THE Risk_Stratification_Module SHALL classify patients with risk scores between 0.35 and 0.65 as moderate-risk
4. THE Risk_Stratification_Module SHALL classify patients with risk scores below 0.35 as low-risk
5. WHEN risk tier assignment changes for a patient, THE Risk_Stratification_Module SHALL log the change with timestamp and previous tier

### Requirement 5: Automated Telehealth Intervention Workflow

**User Story:** As a healthcare system, I want to automatically trigger interventions for high-risk patients, so that we can provide timely care without manual coordination delays.

#### Acceptance Criteria

1. WHEN a patient is classified as high-risk, THE Intervention_Workflow_Engine SHALL initiate the automated intervention workflow within 1 hour
2. THE Intervention_Workflow_Engine SHALL trigger all four intervention components: provider notification, telehealth scheduling, home blood draw dispatch, and case manager enrollment
3. WHEN the workflow is initiated, THE Intervention_Workflow_Engine SHALL create an audit trail with timestamps for each intervention step
4. IF any intervention step fails, THEN THE Intervention_Workflow_Engine SHALL retry the failed step up to 3 times with exponential backoff
5. WHEN all intervention steps complete, THE Intervention_Workflow_Engine SHALL mark the workflow as complete and notify the care coordination team

### Requirement 6: Provider Dashboard with Predictions

**User Story:** As a healthcare provider, I want to view patient risk predictions and explanations in a dashboard, so that I can review cases and make clinical decisions.

#### Acceptance Criteria

1. WHEN a provider accesses the dashboard, THE Provider_Dashboard SHALL display all patients with their risk scores, risk tiers, and prediction dates
2. THE Provider_Dashboard SHALL allow filtering by risk tier, CKD stage, and date range
3. WHEN a provider selects a patient, THE Provider_Dashboard SHALL display the top 5 SHAP explanation factors with visual indicators
4. THE Provider_Dashboard SHALL display clinical values, administrative metrics, and SDOH indicators for each patient
5. WHEN a provider acknowledges a high-risk alert, THE Provider_Dashboard SHALL record the acknowledgment with provider ID and timestamp

### Requirement 7: Automated Telehealth Nephrology Scheduling

**User Story:** As a high-risk CKD patient in a rural area, I want to automatically receive a telehealth nephrology appointment, so that I can access specialist care without traveling long distances.

#### Acceptance Criteria

1. WHEN a high-risk patient is identified, THE Telehealth_Scheduler SHALL check nephrology provider availability within the next 14 days
2. THE Telehealth_Scheduler SHALL schedule a virtual appointment with the earliest available nephrologist
3. WHEN an appointment is scheduled, THE Telehealth_Scheduler SHALL send appointment confirmation to the patient via their preferred contact method
4. THE Telehealth_Scheduler SHALL include video conference link, appointment time, and preparation instructions in the confirmation
5. IF no nephrology appointments are available within 14 days, THEN THE Telehealth_Scheduler SHALL escalate to the care coordination team and attempt scheduling within 21 days

### Requirement 8: Home Blood Draw Kit Dispatch

**User Story:** As a patient with transportation barriers, I want to receive a home blood draw kit, so that I can complete necessary lab work without traveling to a facility.

#### Acceptance Criteria

1. WHEN a high-risk patient is identified, THE Home_Blood_Draw_Dispatcher SHALL verify the patient's shipping address
2. THE Home_Blood_Draw_Dispatcher SHALL dispatch a blood draw kit within 2 business days
3. THE Home_Blood_Draw_Dispatcher SHALL include collection instructions, prepaid return shipping label, and required lab requisition forms
4. WHEN a kit is dispatched, THE Home_Blood_Draw_Dispatcher SHALL send tracking information to the patient
5. THE Home_Blood_Draw_Dispatcher SHALL schedule a follow-up reminder 7 days after dispatch if no sample has been received

### Requirement 9: Case Manager Enrollment

**User Story:** As a case manager, I want high-risk patients automatically enrolled in my caseload, so that I can proactively support them with care coordination and resource navigation.

#### Acceptance Criteria

1. WHEN a high-risk patient is identified, THE Case_Manager_Enrollment SHALL assign the patient to an available case manager based on current caseload capacity
2. THE Case_Manager_Enrollment SHALL create a case record with patient demographics, risk factors, and SDOH barriers
3. WHEN a patient is enrolled, THE Case_Manager_Enrollment SHALL notify the assigned case manager within 24 hours
4. THE Case_Manager_Enrollment SHALL include SHAP explanation factors in the case record to guide case manager interventions
5. THE Case_Manager_Enrollment SHALL limit each case manager to a maximum of 50 active high-risk patients

### Requirement 10: Equitable Performance Across Subgroups

**User Story:** As a health equity officer, I want the ML model to perform equally well across racial and ethnic subgroups, so that we avoid algorithmic bias and ensure fair care for all patients.

#### Acceptance Criteria

1. THE ML_Analytics_Engine SHALL achieve an AUROC within 0.05 points across all racial and ethnic subgroups
2. THE ML_Analytics_Engine SHALL monitor prediction performance separately for White, Black, Hispanic, Asian, and Other racial/ethnic groups
3. WHEN performance disparity exceeds 0.05 AUROC between any two subgroups, THE ML_Analytics_Engine SHALL flag the model for retraining
4. THE ML_Analytics_Engine SHALL generate quarterly fairness reports comparing sensitivity, specificity, and positive predictive value across subgroups
5. THE ML_Analytics_Engine SHALL exclude race and ethnicity as direct input features to the prediction model

### Requirement 11: Model Training and Validation

**User Story:** As a data scientist, I want to train and validate the XGBoost model with proper data splits, so that we have reliable performance estimates before deployment.

#### Acceptance Criteria

1. WHEN training data is prepared, THE ML_Analytics_Engine SHALL split data into 70% training, 15% validation, and 15% test sets
2. THE ML_Analytics_Engine SHALL perform temporal validation with training data preceding validation and test data chronologically
3. THE XGBoost_Classifier SHALL use hyperparameter tuning on the validation set to optimize model performance
4. THE ML_Analytics_Engine SHALL evaluate final model performance on the held-out test set
5. WHEN model training completes, THE ML_Analytics_Engine SHALL generate a performance report including AUROC, sensitivity, specificity, PPV, and NPV

### Requirement 12: Cost-Effectiveness Tracking

**User Story:** As a healthcare administrator, I want to track the cost-effectiveness of the intervention program, so that I can demonstrate value to stakeholders and payers.

#### Acceptance Criteria

1. THE CKD_Prediction_System SHALL track intervention costs including telehealth visits, home blood draws, and case management hours
2. THE CKD_Prediction_System SHALL track avoided costs from prevented Stage 4-5 CKD progression and hospitalizations
3. WHEN quarterly reports are generated, THE CKD_Prediction_System SHALL calculate the benefit-cost ratio
4. THE CKD_Prediction_System SHALL target a BCR of at least 3.75:1 for the intervention program
5. THE CKD_Prediction_System SHALL generate cost-effectiveness reports stratified by patient risk tier and geographic region

### Requirement 13: Data Privacy and Security

**User Story:** As a compliance officer, I want patient data protected according to HIPAA regulations, so that we maintain patient privacy and avoid regulatory penalties.

#### Acceptance Criteria

1. THE CKD_Prediction_System SHALL encrypt all patient data at rest using AES-256 encryption
2. THE CKD_Prediction_System SHALL encrypt all data in transit using TLS 1.3 or higher
3. WHEN a user accesses patient data, THE CKD_Prediction_System SHALL authenticate the user and verify role-based access permissions
4. THE CKD_Prediction_System SHALL log all data access events with user ID, timestamp, and data elements accessed
5. THE CKD_Prediction_System SHALL automatically de-identify data used for model training and research purposes

### Requirement 14: System Monitoring and Alerting

**User Story:** As a system administrator, I want to monitor system health and receive alerts for failures, so that I can maintain high availability and quickly resolve issues.

#### Acceptance Criteria

1. THE CKD_Prediction_System SHALL monitor prediction latency, data ingestion success rates, and intervention workflow completion rates
2. WHEN prediction latency exceeds 1 second, THE CKD_Prediction_System SHALL send an alert to the operations team
3. WHEN data ingestion failure rate exceeds 5% over a 1-hour period, THE CKD_Prediction_System SHALL send an alert to the data engineering team
4. THE CKD_Prediction_System SHALL maintain a system health dashboard with real-time metrics
5. THE CKD_Prediction_System SHALL generate daily summary reports of system performance and intervention outcomes

### Requirement 15: Model Retraining and Deployment

**User Story:** As an ML engineer, I want to retrain and deploy updated models, so that prediction accuracy remains high as patient populations and clinical practices evolve.

#### Acceptance Criteria

1. THE ML_Analytics_Engine SHALL support retraining the XGBoost_Classifier with updated data on a quarterly schedule
2. WHEN a new model is trained, THE ML_Analytics_Engine SHALL compare performance against the current production model on a held-out test set
3. IF the new model achieves at least 0.02 AUROC improvement, THEN THE ML_Analytics_Engine SHALL promote the new model to production
4. WHEN a model is deployed to production, THE ML_Analytics_Engine SHALL version the model and maintain a rollback capability
5. THE ML_Analytics_Engine SHALL perform A/B testing with 10% traffic to new models before full deployment
