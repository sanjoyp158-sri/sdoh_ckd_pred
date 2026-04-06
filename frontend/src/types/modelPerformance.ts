export interface MetricRow {
  model: string;
  cohort: string;
  AUROC: number;
  AUROC_95CI: string;
  AUPRC: number;
  Brier: number;
  Sensitivity: number;
  Specificity: number;
  PPV: number;
  NPV: number;
  F1: number;
}

export interface SubgroupRow {
  subgroup: string;
  N: number;
  AUROC: number;
  AUROC_95CI: string;
  PPV: number;
  Sensitivity: number;
  F1: number;
}

export interface ShapFeature {
  feature: string;
  shap_pct: number;
  category: string;
}

export interface ModelComparison {
  model: string;
  AUROC: string;
}

export interface ModelPerformanceData {
  performance_metrics: MetricRow[];
  subgroup_equity: SubgroupRow[];
  shap_importance: ShapFeature[];
  model_comparison: ModelComparison[];
}
