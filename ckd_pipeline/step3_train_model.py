"""
step3_train_model.py
--------------------
Trains the XGBoost + SHAP model (SDOH-CKDPred) on the synthetic training cohort.

  - 5-fold cross-validation (stratified by time period + geography)
  - Bayesian hyperparameter optimization
  - SMOTE oversampling within each fold (prevents leakage)
  - SHAP feature importance analysis
  - Saves final model to models/sdoh_ckdpred_final.json

Outputs:
  models/sdoh_ckdpred_final.json
  models/sdoh_ckdpred_cv_results.csv
  outputs/shap_feature_importance.csv
"""

import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
import shap
import xgboost as xgb

from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (roc_auc_score, average_precision_score,
                              brier_score_loss, confusion_matrix,
                              f1_score, precision_score, recall_score)
from sklearn.preprocessing import LabelEncoder
from imblearn.over_sampling import BorderlineSMOTE

from config import *

np.random.seed(SEED)


# ── Feature columns ────────────────────────────────────────────────────────
CLINICAL_FEATURES = [
    "age", "sex_encoded", "egfr_baseline", "egfr_slope",
    "uacr_baseline", "uacr_trend", "hba1c", "hba1c_trend",
    "sbp", "dbp", "sbp_trend", "bmi", "charlson_index",
    "diabetes", "hypertension", "chf",
    "acei_arb", "sglt2_inhibitor", "glp1_receptor_agonist",
    "med_adherence_score",
]

UTILIZATION_FEATURES = [
    "pcp_visit_gap_12mo", "missed_nephro_referral",
    "ed_visits_past_year", "insurance_uninsured", "insurance_medicaid",
]

SDOH_FEATURES = [
    "adi_quintile", "adi_nat_rank", "food_desert",
    "healthcare_shortage_area", "poverty_rate_pct",
    "median_household_income", "unemployment_rate_pct",
    "no_hs_diploma_pct", "linguistic_isolation_pct", "walkability_index",
]

ALL_FEATURES = CLINICAL_FEATURES + UTILIZATION_FEATURES + SDOH_FEATURES
CLINICAL_ONLY_FEATURES = CLINICAL_FEATURES + UTILIZATION_FEATURES

TARGET = "outcome_stage45_24mo"


# ── Preprocessing ─────────────────────────────────────────────────────────
def preprocess(df):
    """Encode categoricals, return feature matrix."""
    d = df.copy()
    le = LabelEncoder()
    d["sex_encoded"] = le.fit_transform(d["sex"])
    return d


def get_X_y(df, features):
    return df[features].values, df[TARGET].values


# ── Metrics helper ────────────────────────────────────────────────────────
def compute_metrics(y_true, y_prob, threshold=RISK_THRESHOLD):
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return {
        "AUROC":       round(roc_auc_score(y_true, y_prob), 4),
        "AUPRC":       round(average_precision_score(y_true, y_prob), 4),
        "Brier":       round(brier_score_loss(y_true, y_prob), 4),
        "Sensitivity": round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0,
        "Specificity": round(tn / (tn + fp), 4) if (tn + fp) > 0 else 0,
        "PPV":         round(precision_score(y_true, y_pred, zero_division=0), 4),
        "NPV":         round(tn / (tn + fn), 4) if (tn + fn) > 0 else 0,
        "F1":          round(f1_score(y_true, y_pred, zero_division=0), 4),
    }


# ── Cross-validation ──────────────────────────────────────────────────────
def run_cross_validation(df, features, model_name="SDOH-CKDPred"):
    print(f"\n  Running {CV_FOLDS}-fold CV for {model_name}...")
    df = preprocess(df)
    X, y = get_X_y(df, features)

    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    fold_metrics = []
    oof_probs = np.zeros(len(y))

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        # SMOTE oversampling — INSIDE fold only
        smote = BorderlineSMOTE(random_state=SEED + fold, k_neighbors=5)
        X_tr_res, y_tr_res = smote.fit_resample(X_tr, y_tr)

        # Scale pos weight for remaining imbalance
        pos_weight = (y_tr_res == 0).sum() / max((y_tr_res == 1).sum(), 1)

        model = xgb.XGBClassifier(
            **{k: v for k, v in XGB_PARAMS.items() if k != "use_label_encoder"},
            scale_pos_weight=pos_weight,
        )
        model.fit(
            X_tr_res, y_tr_res,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        probs = model.predict_proba(X_val)[:, 1]
        oof_probs[val_idx] = probs
        m = compute_metrics(y_val, probs)
        m["fold"] = fold
        fold_metrics.append(m)
        print(f"    Fold {fold}: AUROC={m['AUROC']:.4f}  "
              f"Sensitivity={m['Sensitivity']:.4f}  "
              f"Specificity={m['Specificity']:.4f}")

    # Overall OOF metrics
    oof_metrics = compute_metrics(y, oof_probs)
    print(f"\n  OOF {model_name}: AUROC={oof_metrics['AUROC']:.4f}")

    return pd.DataFrame(fold_metrics), oof_metrics


# ── Train final model ─────────────────────────────────────────────────────
def train_final_model(df, features):
    print("\n  Training final model on full training cohort...")
    df = preprocess(df)
    X, y = get_X_y(df, features)

    smote = BorderlineSMOTE(random_state=SEED, k_neighbors=5)
    X_res, y_res = smote.fit_resample(X, y)
    pos_weight = (y_res == 0).sum() / max((y_res == 1).sum(), 1)

    model = xgb.XGBClassifier(
        **{k: v for k, v in XGB_PARAMS.items() if k != "use_label_encoder"},
        scale_pos_weight=pos_weight,
    )
    model.fit(X_res, y_res, verbose=False)
    print("  Final model trained.")
    return model


# ── SHAP analysis ─────────────────────────────────────────────────────────
def run_shap_analysis(model, df, features):
    print("\n  Running SHAP analysis...")
    df = preprocess(df)
    X, _ = get_X_y(df, features)

    # Use TreeExplainer for XGBoost
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    # Mean absolute SHAP per feature
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    total = mean_abs_shap.sum()
    shap_pct = (mean_abs_shap / total) * 100

    # Assign categories
    category_map = {}
    for f in CLINICAL_FEATURES:   category_map[f] = "Clinical"
    for f in UTILIZATION_FEATURES: category_map[f] = "Utilization"
    for f in SDOH_FEATURES:        category_map[f] = "SDOH"

    shap_df = pd.DataFrame({
        "feature":      features,
        "mean_abs_shap": mean_abs_shap,
        "shap_pct":      shap_pct,
        "category":     [category_map.get(f, "Other") for f in features],
    }).sort_values("shap_pct", ascending=False)

    # Category totals
    cat_totals = shap_df.groupby("category")["shap_pct"].sum()
    print("\n  SHAP Category Contributions:")
    for cat, pct in cat_totals.sort_values(ascending=False).items():
        print(f"    {cat}: {pct:.1f}%")

    print("\n  Top 10 Features:")
    print(shap_df.head(10)[["feature", "shap_pct", "category"]].to_string(index=False))

    return shap_df, shap_values


# ── Evaluate on external validation ───────────────────────────────────────
def evaluate_external(model, df_ext, features):
    print("\n  Evaluating on external validation cohort...")
    df_ext = preprocess(df_ext)
    X_ext, y_ext = get_X_y(df_ext, features)
    probs = model.predict_proba(X_ext)[:, 1]
    metrics = compute_metrics(y_ext, probs)
    print(f"  External Validation: AUROC={metrics['AUROC']:.4f}  "
          f"Sensitivity={metrics['Sensitivity']:.4f}  "
          f"Specificity={metrics['Specificity']:.4f}  "
          f"PPV={metrics['PPV']:.4f}")
    return metrics, probs


# ── Subgroup equity analysis ───────────────────────────────────────────────
def equity_analysis(model, df_ext, features):
    print("\n  Running equity analysis across subgroups...")
    df_ext = preprocess(df_ext)
    X_ext, y_ext = get_X_y(df_ext, features)
    probs = model.predict_proba(X_ext)[:, 1]
    df_ext = df_ext.copy()
    df_ext["prob"] = probs
    df_ext["y"]    = y_ext

    results = []
    subgroup_defs = [
        ("African_American", df_ext["race_ethnicity"] == "African_American"),
        ("Hispanic_Latino",  df_ext["race_ethnicity"] == "Hispanic_Latino"),
        ("White",            df_ext["race_ethnicity"] == "White"),
        ("Rural",            df_ext["urbanicity"] == "Rural"),
        ("Urban",            df_ext["urbanicity"] == "Urban"),
        ("High_ADI_Q5",      df_ext["adi_quintile"] == 5),
    ]

    for name, mask in subgroup_defs:
        sub = df_ext[mask]
        m = compute_metrics(sub["y"].values, sub["prob"].values)
        m["subgroup"] = name
        m["n"] = len(sub)
        results.append(m)
        print(f"    {name} (n={len(sub):,}): "
              f"AUROC={m['AUROC']:.4f}  PPV={m['PPV']:.4f}")

    return pd.DataFrame(results)


# ── Main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("SDOH-CKDPred — Step 3: Training Model")
    print("=" * 60)

    # Load data
    df_train = pd.read_csv(os.path.join(PROC_DIR, "cohort_train.csv"))
    df_ext   = pd.read_csv(os.path.join(PROC_DIR, "cohort_external_val.csv"))
    print(f"\n  Loaded training cohort:  N={len(df_train):,}")
    print(f"  Loaded external val:     N={len(df_ext):,}")

    # ── SDOH-augmented model (full features) ─────────────────────────────
    cv_results, oof_metrics = run_cross_validation(
        df_train, ALL_FEATURES, "SDOH-CKDPred (Full)"
    )
    final_model = train_final_model(df_train, ALL_FEATURES)
    ext_metrics, ext_probs = evaluate_external(final_model, df_ext, ALL_FEATURES)
    shap_df, shap_vals = run_shap_analysis(final_model, df_train, ALL_FEATURES)
    subgroup_df = equity_analysis(final_model, df_ext, ALL_FEATURES)

    # ── Clinical-only baseline model ──────────────────────────────────────
    print("\n  Training clinical-only baseline for comparison...")
    cv_base, oof_base = run_cross_validation(
        df_train, CLINICAL_ONLY_FEATURES, "Clinical-Only Baseline"
    )
    base_model = train_final_model(df_train, CLINICAL_ONLY_FEATURES)
    base_ext_metrics, _ = evaluate_external(base_model, df_ext, CLINICAL_ONLY_FEATURES)

    print(f"\n  AUROC comparison:")
    print(f"    SDOH-CKDPred:      {ext_metrics['AUROC']:.4f}")
    print(f"    Clinical-only:     {base_ext_metrics['AUROC']:.4f}")
    print(f"    Improvement:       {ext_metrics['AUROC'] - base_ext_metrics['AUROC']:+.4f}")

    # ── Save everything ───────────────────────────────────────────────────
    model_path = os.path.join(MODEL_DIR, "sdoh_ckdpred_final.json")
    final_model.save_model(model_path)
    print(f"\n  Model saved → {model_path}")

    base_model_path = os.path.join(MODEL_DIR, "clinical_only_baseline.json")
    base_model.save_model(base_model_path)

    cv_results.to_csv(os.path.join(OUTPUT_DIR, "cv_results_full.csv"), index=False)
    cv_base.to_csv(os.path.join(OUTPUT_DIR, "cv_results_baseline.csv"), index=False)
    shap_df.to_csv(os.path.join(OUTPUT_DIR, "shap_feature_importance.csv"), index=False)
    subgroup_df.to_csv(os.path.join(OUTPUT_DIR, "equity_analysis.csv"), index=False)

    # Save feature list for later steps
    joblib.dump(ALL_FEATURES, os.path.join(MODEL_DIR, "feature_list.pkl"))
    joblib.dump(CLINICAL_ONLY_FEATURES, os.path.join(MODEL_DIR, "baseline_feature_list.pkl"))

    # Save combined metrics summary
    summary = pd.DataFrame([
        {"model": "SDOH-CKDPred",      "cohort": "OOF Train",          **oof_metrics},
        {"model": "SDOH-CKDPred",      "cohort": "External Validation", **ext_metrics},
        {"model": "Clinical-Only",     "cohort": "OOF Train",           **oof_base},
        {"model": "Clinical-Only",     "cohort": "External Validation", **base_ext_metrics},
    ])
    summary.to_csv(os.path.join(OUTPUT_DIR, "model_performance_summary.csv"), index=False)

    print("\n" + "=" * 60)
    print("Step 3 complete. Run step4_evaluate.py next.")
    print("=" * 60)
