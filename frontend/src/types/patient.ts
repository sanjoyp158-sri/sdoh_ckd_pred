export enum RiskTier {
  HIGH = 'high',
  MODERATE = 'moderate',
  LOW = 'low',
}

export enum CKDStage {
  STAGE_2 = '2',
  STAGE_3A = '3a',
  STAGE_3B = '3b',
  STAGE_4 = '4',
  STAGE_5 = '5',
}

export interface PatientSummary {
  patient_id: string;
  age: number;
  sex: string;
  risk_score: number;
  risk_tier: RiskTier;
  ckd_stage: CKDStage;
  prediction_date: string;
  egfr: number;
  acknowledged: boolean;
}

export interface PatientFilters {
  risk_tier?: RiskTier;
  ckd_stage?: CKDStage;
  date_from?: string;
  date_to?: string;
  search?: string;
}

export interface PatientsResponse {
  patients: PatientSummary[];
  total: number;
}
