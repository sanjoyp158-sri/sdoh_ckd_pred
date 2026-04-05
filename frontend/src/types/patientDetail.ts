import { RiskTier, CKDStage } from './patient';

export interface Factor {
  feature_name: string;
  feature_value: any;
  shap_value: number;
  category: 'clinical' | 'administrative' | 'sdoh';
  direction: 'increases_risk' | 'decreases_risk';
}

export interface PatientDetail {
  patient_id: string;
  age: number;
  sex: string;
  risk_score: number;
  risk_tier: RiskTier;
  prediction_date: string;
  model_version: string;
  clinical: {
    egfr: number;
    uacr: number;
    hba1c: number;
    systolic_bp: number;
    diastolic_bp: number;
    bmi: number;
    ckd_stage: CKDStage;
  };
  administrative: {
    visit_frequency_12mo: number;
    specialist_referrals_count: number;
    insurance_type: string;
    insurance_status: string;
  };
  sdoh: {
    adi_percentile: number;
    food_desert: boolean;
    housing_stability_score: number;
    transportation_access_score: number;
  };
  top_factors: Factor[];
  acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: string;
}
