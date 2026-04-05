import { RiskTier, CKDStage } from './patient';

export interface Factor {
  feature_name: string;
  feature_value: any;
  shap_value: number;
  category: 'clinical' | 'administrative' | 'sdoh';
  direction: 'increases_risk' | 'decreases_risk';
}

export interface SHAPExplanation {
  baseline_risk: number;
  prediction: number;
  top_factors: Factor[];
  computation_time_ms: number;
}

export interface PatientDetail {
  patient_id: string;
  demographics: {
    age: number;
    sex: string;
  };
  clinical: {
    egfr: number;
    egfr_history: Array<{ date: string; value: number }>;
    uacr: number;
    hba1c: number;
    systolic_bp: number;
    diastolic_bp: number;
    bmi: number;
    ckd_stage: CKDStage;
    comorbidities: string[];
  };
  administrative: {
    visit_frequency_12mo: number;
    insurance_type: string;
    last_visit_date: string;
  };
  sdoh: {
    adi_percentile: number;
    food_desert: boolean;
    housing_stability_score: number;
    transportation_access_score: number;
    rural_urban_code: string;
  };
  prediction: {
    risk_score: number;
    risk_tier: RiskTier;
    prediction_date: string;
    shap_explanation: SHAPExplanation;
  };
  acknowledged: boolean;
}
