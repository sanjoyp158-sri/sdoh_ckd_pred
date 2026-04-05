# Implementation Plan: CKD Early Detection System

## Overview

This implementation plan breaks down the SDOH-CKDPred system into discrete coding tasks. The system integrates clinical, administrative, and SDOH data to predict CKD progression using XGBoost with SHAP explainability, then triggers automated interventions for high-risk patients. The implementation follows a layered architecture: data integration → ML analytics → risk stratification → intervention orchestration → user interfaces.

Technology stack: Python/FastAPI backend, React frontend, PostgreSQL database, Redis cache, XGBoost ML model, Hypothesis for property-based testing.

## Tasks

- [x] 1. Set up project structure and core infrastructure
  - Initialize Git repository and connect to remote: https://github.com/sanjoyp158-sri/sdoh_ckd_pred.git
  - Create .gitignore for Python, Node.js, and environment files
  - Create Python project with FastAPI backend structure
  - Set up PostgreSQL database with initial schema
  - Configure Redis for caching
  - Set up Docker configuration for local development
  - Create core data models and type definitions
  - Configure logging and monitoring infrastructure
  - Push initial project structure to GitHub
  - _Requirements: 13.1, 13.2, 14.1_

- [x] 2. Implement Data Integration Layer
  - [x] 2.1 Create data ingestion interfaces and models
    - Implement `ClinicalRecord`, `AdministrativeRecord`, `SDOHRecord`, and `UnifiedPatientRecord` data classes
    - Create `DataIntegrationLayer` class with ingestion methods
    - Implement data validation for required fields
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 2.2 Write property tests for data ingestion completeness
    - **Property 1: Clinical Data Ingestion Completeness**
    - **Property 2: Administrative Data Ingestion Completeness**
    - **Property 3: SDOH Data Retrieval Completeness**
    - **Validates: Requirements 1.1, 1.2, 1.3**

  - [x] 2.3 Implement data harmonization logic
    - Create `harmonize_patient_record()` method to combine all data sources
    - Implement missing data handling with regional averages for SDOH
    - Add error logging with source identification
    - _Requirements: 1.4, 1.5_

  - [x] 2.4 Write property tests for data harmonization
    - **Property 4: Data Harmonization Combines All Sources**
    - **Property 5: Data Ingestion Error Handling**
    - **Validates: Requirements 1.4, 1.5**

  - [x] 2.5 Create database persistence layer
    - Implement PostgreSQL schema for patient records
    - Create data access objects (DAOs) for CRUD operations
    - Add encryption at rest using AES-256
    - _Requirements: 13.1_

- [x] 3. Implement ML Analytics Engine core
  - [x] 3.1 Create ML Analytics Engine class and interfaces
    - Implement `MLAnalyticsEngine` class with prediction methods
    - Create `PredictionResult` and `ModelMetrics` data classes
    - Set up model registry for versioning
    - _Requirements: 2.1, 15.4_

  - [x] 3.2 Implement feature engineering pipeline
    - Extract clinical features (eGFR, UACR, HbA1c, BP, BMI, medications)
    - Extract administrative features (visit frequency, referrals, insurance)
    - Extract SDOH features (ADI, food desert, housing, transportation)
    - Create temporal features (eGFR slope, time since diagnosis)
    - Create interaction features (eGFR × ADI, UACR × food desert)
    - _Requirements: 2.3_

  - [x] 3.3 Write property tests for feature engineering
    - **Property 7: Prediction Uses All Feature Types**
    - **Validates: Requirements 2.3**

  - [x] 3.4 Implement XGBoost classifier integration
    - Create `XGBoostClassifier` wrapper class
    - Configure XGBoost parameters (max_depth=6, learning_rate=0.05, etc.)
    - Implement model loading from registry
    - Add prediction method with 500ms timeout
    - _Requirements: 2.1, 2.4_

  - [x] 3.5 Write property tests for prediction
    - **Property 6: Risk Score Bounds**
    - **Property 8: Prediction Latency**
    - **Validates: Requirements 2.1, 2.4**

- [x] 4. Checkpoint - Ensure core data and ML infrastructure works
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement SHAP Explainer
  - [x] 5.1 Create SHAP Explainer class
    - Implement `SHAPExplainer` class using TreeSHAP
    - Create `SHAPExplanation`, `Factor`, and `CategorizedFactors` data classes
    - Pre-compute background dataset (1000 samples) for efficiency
    - Cache SHAP explainer object
    - _Requirements: 3.1, 3.2_

  - [x] 5.2 Implement SHAP value computation and explanation generation
    - Compute SHAP values for all features
    - Identify top 5 contributing factors
    - Categorize factors as clinical, administrative, or SDOH
    - Normalize SHAP values to sum to (prediction - baseline)
    - Meet 200ms latency requirement
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 5.3 Write property tests for SHAP explanations
    - **Property 9: SHAP Completeness**
    - **Property 10: SHAP Top Factors**
    - **Property 11: SHAP Factor Categorization**
    - **Property 12: SHAP Value Normalization**
    - **Property 13: SHAP Explanation Latency**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

- [x] 6. Implement Risk Stratification Module
  - [x] 6.1 Create Risk Stratification Module
    - Implement `RiskStratificationModule` class
    - Create `RiskTier` enum (HIGH, MODERATE, LOW)
    - Implement `stratify_patient()` method with thresholds (>0.65, 0.35-0.65, <0.35)
    - Add tier change logging with timestamps
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 6.2 Write property tests for risk stratification
    - **Property 14: Risk Tier Assignment Correctness**
    - **Property 15: Risk Tier Change Logging**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

- [ ] 7. Implement Intervention Workflow Engine
  - [ ] 7.1 Create Intervention Workflow Engine core
    - Implement `InterventionWorkflowEngine` class
    - Create `WorkflowStatus` and `WorkflowStep` data classes
    - Implement workflow initiation with 1-hour SLA
    - Create audit trail with timestamps for each step
    - _Requirements: 5.1, 5.3_

  - [ ] 7.2 Implement workflow orchestration and retry logic
    - Trigger all four intervention components in parallel
    - Implement retry logic with exponential backoff (5min, 15min, 45min)
    - Mark workflow as complete when all steps succeed
    - Send notification to care coordination team on completion
    - _Requirements: 5.2, 5.4, 5.5_

  - [ ] 7.3 Write property tests for intervention workflows
    - **Property 16: High-Risk Workflow Initiation Timing**
    - **Property 17: Intervention Workflow Completeness**
    - **Property 18: Intervention Step Retry Logic**
    - **Property 19: Workflow Completion Notification**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

- [ ] 8. Implement Telehealth Scheduler
  - [ ] 8.1 Create Telehealth Scheduler service
    - Implement `TelehealthScheduler` class
    - Create `Appointment` and `AppointmentSlot` data classes
    - Implement availability checking (14-day window)
    - Select earliest available appointment slot
    - _Requirements: 7.1, 7.2_

  - [ ] 8.2 Implement appointment confirmation and escalation
    - Send confirmation with video link, time, and instructions
    - Support multiple contact methods (email, SMS)
    - Implement escalation logic for no availability within 14 days
    - Attempt scheduling within 21 days on escalation
    - _Requirements: 7.3, 7.4, 7.5_

  - [ ] 8.3 Write property tests for telehealth scheduling
    - **Property 24: Telehealth Availability Check**
    - **Property 25: Earliest Appointment Selection**
    - **Property 26: Appointment Confirmation Completeness**
    - **Property 27: Telehealth Scheduling Escalation**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

- [ ] 9. Implement Home Blood Draw Dispatcher
  - [ ] 9.1 Create Home Blood Draw Dispatcher service
    - Implement `HomeBloodDrawDispatcher` class
    - Create `ShipmentTracking` data class
    - Implement address verification
    - Dispatch kits within 2 business days
    - _Requirements: 8.1, 8.2_

  - [ ] 9.2 Implement kit contents and tracking
    - Include collection instructions, prepaid label, and requisition forms
    - Send tracking information to patient
    - Schedule 7-day follow-up reminder if no sample received
    - _Requirements: 8.3, 8.4, 8.5_

  - [ ] 9.3 Write property tests for blood draw dispatch
    - **Property 28: Blood Draw Address Verification**
    - **Property 29: Blood Draw Kit Dispatch Timing**
    - **Property 30: Blood Draw Kit Contents**
    - **Property 31: Blood Draw Tracking Notification**
    - **Property 32: Blood Draw Follow-up Reminder**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

- [ ] 10. Implement Case Manager Enrollment
  - [ ] 10.1 Create Case Manager Enrollment service
    - Implement `CaseManagerEnrollment` class
    - Create `CaseManager` and `CaseRecord` data classes
    - Implement capacity-based assignment (max 50 patients per manager)
    - Create case records with demographics, risk factors, and SDOH barriers
    - _Requirements: 9.1, 9.2_

  - [ ] 10.2 Implement case manager notification and caseload management
    - Notify assigned case manager within 24 hours
    - Include SHAP explanation factors in case record
    - Enforce 50-patient caseload limit
    - _Requirements: 9.3, 9.4, 9.5_

  - [ ] 10.3 Write property tests for case management
    - **Property 33: Case Manager Assignment by Capacity**
    - **Property 34: Case Record Completeness**
    - **Property 35: Case Manager Notification Timing**
    - **Property 36: Case Record SHAP Inclusion**
    - **Property 37: Case Manager Caseload Limit**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

- [ ] 11. Checkpoint - Ensure intervention services work end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Implement FastAPI backend endpoints
  - [ ] 12.1 Create prediction API endpoints
    - Implement POST `/api/v1/predict` endpoint for risk prediction
    - Implement GET `/api/v1/predictions/{patient_id}` for retrieving predictions
    - Add request validation and error handling
    - Implement TLS 1.3 encryption for data in transit
    - _Requirements: 2.1, 13.2_

  - [ ] 12.2 Create dashboard API endpoints
    - Implement GET `/api/v1/patients` with filtering (risk tier, CKD stage, date range)
    - Implement GET `/api/v1/patients/{patient_id}` for patient details
    - Implement POST `/api/v1/acknowledgments` for provider acknowledgments
    - _Requirements: 6.1, 6.2, 6.3, 6.5_

  - [ ] 12.3 Implement authentication and authorization
    - Add JWT-based authentication
    - Implement role-based access control (RBAC)
    - Create middleware for authentication and authorization checks
    - _Requirements: 13.3_

  - [ ] 12.4 Add audit logging middleware
    - Log all data access events with user ID, timestamp, and data elements
    - Store audit logs in separate database table
    - Implement audit log query endpoints for compliance
    - _Requirements: 13.4_

  - [ ] 12.5 Write property tests for security
    - **Property 48: Data at Rest Encryption**
    - **Property 49: Data in Transit Encryption**
    - **Property 50: Data Access Authentication and Authorization**
    - **Property 51: Data Access Audit Logging**
    - **Validates: Requirements 13.1, 13.2, 13.3, 13.4**

- [ ] 13. Implement Provider Dashboard frontend
  - [ ] 13.1 Create React dashboard application structure
    - Set up React project with TypeScript
    - Configure routing and state management
    - Create layout components (header, sidebar, main content)
    - _Requirements: 6.1_

  - [ ] 13.2 Implement patient list view
    - Create patient list table component with sorting
    - Implement filtering by risk tier, CKD stage, and date range
    - Display risk scores, risk tiers, and prediction dates
    - Add color-coded risk tier indicators
    - _Requirements: 6.1, 6.2_

  - [ ] 13.3 Implement patient detail view
    - Create patient detail page with SHAP waterfall chart
    - Display top 5 SHAP explanation factors with visual indicators
    - Show clinical values, administrative metrics, and SDOH indicators
    - Display eGFR trend timeline
    - Add provider acknowledgment button
    - _Requirements: 6.3, 6.4, 6.5_

  - [ ] 13.4 Write property tests for dashboard functionality
    - **Property 20: Dashboard Patient List Completeness**
    - **Property 21: Dashboard Filtering Correctness**
    - **Property 22: Dashboard Patient Detail Display**
    - **Property 23: Provider Acknowledgment Recording**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

- [ ] 14. Implement model training pipeline
  - [ ] 14.1 Create data preparation and splitting logic
    - Load historical patient data with 24-month outcomes
    - Filter to Stage 2-3 CKD patients at baseline
    - Implement temporal data split (70% train, 15% validation, 15% test)
    - Ensure chronological ordering (train < validation < test)
    - _Requirements: 11.1, 11.2_

  - [ ] 14.2 Write property tests for data splitting
    - **Property 41: Training Data Split Proportions**
    - **Property 42: Temporal Validation Ordering**
    - **Validates: Requirements 11.1, 11.2**

  - [ ] 14.3 Implement model training and hyperparameter tuning
    - Implement XGBoost training with hyperparameter tuning on validation set
    - Tune learning rate, max depth, subsample ratio
    - Train final model on train + validation sets
    - Exclude race and ethnicity as direct features
    - _Requirements: 11.3, 10.5_

  - [ ] 14.4 Implement model evaluation and fairness monitoring
    - Evaluate model on held-out test set
    - Calculate AUROC, sensitivity, specificity, PPV, NPV
    - Compute metrics separately for racial/ethnic subgroups
    - Check AUROC disparity across subgroups (max 0.05)
    - Generate performance report
    - _Requirements: 11.4, 11.5, 10.1, 10.2, 10.3, 10.4_

  - [ ] 14.5 Write property tests for model training and fairness
    - **Property 38: Fairness Monitoring by Subgroup**
    - **Property 39: Fairness Disparity Flagging**
    - **Property 40: Quarterly Fairness Report Completeness**
    - **Property 43: Model Performance Report Completeness**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 11.5**

  - [ ] 14.6 Implement model deployment and A/B testing
    - Compare new model performance against production model
    - Promote model if AUROC improvement >= 0.02
    - Version models and maintain rollback capability
    - Implement A/B testing with 10% traffic to new model
    - _Requirements: 15.2, 15.3, 15.4, 15.5_

  - [ ] 14.7 Write property tests for model deployment
    - **Property 58: Model Performance Comparison**
    - **Property 59: Model Promotion Threshold**
    - **Property 60: Model Versioning and Rollback**
    - **Property 61: A/B Testing Traffic Split**
    - **Validates: Requirements 15.2, 15.3, 15.4, 15.5**

- [ ] 15. Implement cost-effectiveness tracking
  - [ ] 15.1 Create cost tracking infrastructure
    - Implement `CostEffectivenessReport`, `InterventionCosts`, and `AvoidedCosts` data classes
    - Track intervention costs (telehealth, blood draws, case management)
    - Track avoided costs (prevented progression, hospitalizations)
    - _Requirements: 12.1, 12.2_

  - [ ] 15.2 Implement cost reporting and BCR calculation
    - Calculate benefit-cost ratio (avoided costs / intervention costs)
    - Generate quarterly cost-effectiveness reports
    - Stratify reports by risk tier and geographic region
    - Target BCR >= 3.75:1
    - _Requirements: 12.3, 12.4, 12.5_

  - [ ] 15.3 Write property tests for cost tracking
    - **Property 44: Intervention Cost Tracking Completeness**
    - **Property 45: Avoided Cost Tracking Completeness**
    - **Property 46: Benefit-Cost Ratio Calculation**
    - **Property 47: Cost-Effectiveness Report Stratification**
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.5**

- [ ] 16. Implement monitoring and alerting system
  - [ ] 16.1 Create monitoring infrastructure
    - Implement metrics collection for prediction latency, data ingestion success rates, and intervention workflow completion rates
    - Create system health dashboard with real-time metrics
    - Set up Prometheus/Grafana or similar monitoring stack
    - _Requirements: 14.1, 14.4_

  - [ ] 16.2 Implement alerting rules
    - Alert operations team when prediction latency exceeds 1 second
    - Alert data engineering team when ingestion failure rate exceeds 5% over 1 hour
    - Generate daily summary reports of system performance and intervention outcomes
    - _Requirements: 14.2, 14.3, 14.5_

  - [ ] 16.3 Write property tests for monitoring
    - **Property 53: System Monitoring Metric Coverage**
    - **Property 54: Prediction Latency Alerting**
    - **Property 55: Data Ingestion Failure Alerting**
    - **Property 56: Real-time Metrics Dashboard**
    - **Property 57: Daily Performance Report Generation**
    - **Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5**

- [ ] 17. Implement data de-identification for research
  - [ ] 17.1 Create de-identification service
    - Implement automatic PII removal for training data
    - Remove patient IDs, names, addresses, dates of birth
    - Generalize geographic data to ZIP code prefix
    - Add de-identification audit logging
    - _Requirements: 13.5_

  - [ ] 17.2 Write property tests for de-identification
    - **Property 52: Training Data De-identification**
    - **Validates: Requirements 13.5**

- [ ] 18. Checkpoint - Ensure complete system integration
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 19. Create Docker deployment configuration
  - [ ] 19.1 Create Dockerfiles and docker-compose
    - Create Dockerfile for FastAPI backend
    - Create Dockerfile for React frontend
    - Create docker-compose.yml with all services (backend, frontend, PostgreSQL, Redis)
    - Configure environment variables and secrets management
    - _Requirements: 13.1, 13.2_

  - [ ] 19.2 Create deployment documentation and push to GitHub
    - Document deployment process
    - Create environment setup guide
    - Document API endpoints and authentication
    - Create troubleshooting guide
    - Ensure all code, documentation, and configuration files are committed
    - Push final codebase to GitHub: https://github.com/sanjoyp158-sri/sdoh_ckd_pred.git
    - Create GitHub releases/tags for version tracking
    - _Requirements: All_

- [ ] 20. Final integration testing and validation
  - [ ] 20.1 Run complete end-to-end workflow tests
    - Test data ingestion → prediction → intervention workflow
    - Verify all intervention services trigger correctly
    - Test dashboard displays predictions and explanations
    - Validate security and audit logging
    - _Requirements: All_

  - [ ] 20.2 Run performance validation
    - Verify prediction latency < 500ms
    - Verify SHAP explanation latency < 200ms
    - Verify intervention workflow initiation < 1 hour
    - Load test API endpoints
    - _Requirements: 2.4, 3.5, 5.1_

  - [ ] 20.3 Run model validation tests
    - Verify model AUROC >= 0.87 on test set
    - Verify fairness metrics across subgroups (disparity <= 0.05)
    - Verify race/ethnicity not used as features
    - _Requirements: 2.2, 10.1, 10.2, 10.3, 10.5_

- [ ] 21. Final checkpoint - System ready for deployment
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- **GitHub Repository**: All code and data components will be version controlled and pushed to https://github.com/sanjoyp158-sri/sdoh_ckd_pred.git
- Tasks marked with `*` are optional property-based tests that can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases
- The implementation follows a bottom-up approach: data layer → ML layer → intervention layer → UI layer
- Security, monitoring, and compliance are integrated throughout rather than added at the end
- Model training pipeline is separate from the prediction service to allow independent scaling
- Commit and push code regularly to GitHub after completing each major task or checkpoint
