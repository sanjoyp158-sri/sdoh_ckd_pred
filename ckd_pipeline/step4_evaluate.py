"""
step4_evaluate.py
-----------------
Comprehensive evaluation: generates all performance tables from the paper.

Per manuscript:
  - Table 2: Performance metrics across cohorts (SDOH-CKDPred + baseline)
  - Table 3: Subgroup equity analysis with DeLong's test
  - Calibration assessment
  - Bootstrapped 95% CIs

Outputs:
  outputs/table2_performance_metrics.csv
  outputs/table3_subgroup_performance.csv
  outputs/calibration_curve.csv
"""

import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
import xgboost as xgb

from sklearn.metrics import (roc_auc_score, average_precision_score,
                              brier_score_loss, precision_score,
                              recall_score, f1_score, confusion_matrix,
                              roc_curve)
from sklearn.preprocessing import LabelEncoder
from sklearn.calibration import calibration_curve
from scipy import stats

from config import *


# ── Helpers ────────────────────────────────────────────────────────────────
def preprocess(df):
    d = df.copy()
    le = LabelEncoder()
    d["sex_encoded"] = le.fit_transform(d["sex"])
    d["egfr_x_adi"] = d["egfr_baseline"] * d["adi_nat_rank"]
    d["uacr_x_food_desert"] = d["uacr_baseline"] * d["food_desert"]
    return d


def compute_metrics(y_true, y_prob, threshold=RISK_THRESHOLD):
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "N":           len(y_true),
        "Events":      int(y_true.sum()),
        "AUROC":       round(roc_auc_score(y_true, y_prob), 4),
        "AUPRC":       round(average_precision_score(y_true, y_prob), 4),
        "Brier":       round(brier_score_loss(y_true, y_prob), 4),
        "Sensitivity": round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0,
        "Specificity": round(tn / (tn + fp), 4) if (tn + fp) > 0 else 0,
        "PPV":         round(precision_score(y_true, y_pred, zero_division=0), 4),
        "NPV":         round(tn / (tn + fn), 4) if (tn + fn) > 0 else 0,
        "F1":          round(f1_score(y_true, y_pred, zero_division=0), 4),
    }


def bootstrap_auroc_ci(y_true, y_prob, n_boot=1000, alpha=0.95):
    """Bootstrap 95% CI for AUROC."""
    rng = np.random.default_rng(SEED)
    aurocs = []
    n = len(y_true)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(np.unique(y_true[idx])) < 2:
            continue
        aurocs.append(roc_auc_score(y_true[idx], y_prob[idx]))
    lo = np.percentile(aurocs, (1 - alpha) / 2 * 100)
    hi = np.percentile(aurocs, (1 + alpha) / 2 * 100)
    return round(lo, 4), round(hi, 4)


def delong_test_pvalue(y_true, prob1, prob2):
    """
    Simplified DeLong's test for comparing two AUROCs on the same dataset.
    Returns p-value.
    """
    n1 = np.sum(y_true == 1)
    n0 = np.sum(y_true == 0)
    pos_idx = np.where(y_true == 1)[0]
    neg_idx = np.where(y_true == 0)[0]

    def placement_values(y_prob):
        V10 = np.array([np.mean(y_prob[pos_idx[i]] > y_prob[neg_idx]) +
                         0.5 * np.mean(y_prob[pos_idx[i]] == y_prob[neg_idx])
                         for i in range(n1)])
        V01 = np.array([np.mean(y_prob[pos_idx] > y_prob[neg_idx[j]]) +
                         0.5 * np.mean(y_prob[pos_idx] == y_prob[neg_idx[j]])
                         for j in range(n0)])
        return V10, V01

    V10_1, V01_1 = placement_values(prob1)
    V10_2, V01_2 = placement_values(prob2)

    auc1 = roc_auc_score(y_true, prob1)
    auc2 = roc_auc_score(y_true, prob2)

    S10 = np.cov(V10_1, V10_2)
    S01 = np.cov(V01_1, V01_2)
    S = S10 / n1 + S01 / n0

    diff = auc1 - auc2
    var_diff = S[0, 0] + S[1, 1] - 2 * S[0, 1]

    if var_diff <= 0:
        return 1.0

    z = diff / np.sqrt(var_diff)
    return round(2 * stats.norm.sf(abs(z)), 4)


# ── Main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("SDOH-CKDPred — Step 4: Comprehensive Evaluation")
    print("=" * 60)

    # Load data and models
    df_train = pd.read_csv(os.path.join(PROC_DIR, "cohort_train.csv"))
    df_ext   = pd.read_csv(os.path.join(PROC_DIR, "cohort_external_val.csv"))
    all_feats  = joblib.load(os.path.join(MODEL_DIR, "feature_list.pkl"))
    clin_feats = joblib.load(os.path.join(MODEL_DIR, "baseline_feature_list.pkl"))

    # Load SDOH-CKDPred (XGBoost)
    final_model = xgb.XGBClassifier()
    final_model.load_model(os.path.join(MODEL_DIR, "sdoh_ckdpred_final.json"))

    # Load clinical-only baseline (Logistic Regression)
    base_model = joblib.load(os.path.join(MODEL_DIR, "clinical_only_baseline.pkl"))

    # Preprocess
    df_train_p = preprocess(df_train)
    df_ext_p   = preprocess(df_ext)

    X_tr   = df_train_p[all_feats].values
    y_tr   = df_train_p["outcome_stage45_24mo"].values
    X_ext  = df_ext_p[all_feats].values
    y_ext  = df_ext_p["outcome_stage45_24mo"].values

    X_tr_clin  = df_train_p[clin_feats].values
    X_ext_clin = df_ext_p[clin_feats].values

    # Predictions
    prob_tr      = final_model.predict_proba(X_tr)[:, 1]
    prob_ext     = final_model.predict_proba(X_ext)[:, 1]
    prob_ext_base = base_model.predict_proba(X_ext_clin)[:, 1]
    prob_tr_base  = base_model.predict_proba(X_tr_clin)[:, 1]

    print(f"\n  Loaded training cohort:  N={len(df_train):,}")
    print(f"  Loaded external val:     N={len(df_ext):,}")

    # ── Table 2: Performance metrics (per manuscript) ────────────────────
    print("\n  ═══ Table 2: Performance Metrics ═══")
    rows = []
    for model_name, cohort_name, y_true, y_prob in [
        ("SDOH-CKDPred", "Training (OOF)",       y_tr,  prob_tr),
        ("SDOH-CKDPred", "External Validation",   y_ext, prob_ext),
        ("Clinical-Only (LR)", "Training (OOF)",  y_tr,  prob_tr_base),
        ("Clinical-Only (LR)", "External Validation", y_ext, prob_ext_base),
    ]:
        m = compute_metrics(y_true, y_prob)
        ci_lo, ci_hi = bootstrap_auroc_ci(y_true, y_prob)
        m["AUROC_95CI"] = f"{m['AUROC']:.2f} ({ci_lo:.2f}-{ci_hi:.2f})"
        m["Model"] = model_name
        m["Cohort"] = cohort_name
        rows.append(m)
        print(f"    {model_name:20s} | {cohort_name:22s} | "
              f"AUROC={m['AUROC']:.4f} ({ci_lo}-{ci_hi})  "
              f"Sens={m['Sensitivity']:.4f}  PPV={m['PPV']:.4f}  "
              f"F1={m['F1']:.4f}  Brier={m['Brier']:.4f}")

    table2 = pd.DataFrame(rows)
    table2.to_csv(os.path.join(OUTPUT_DIR, "table2_performance_metrics.csv"),
                  index=False)

    # AUROC comparison with DeLong's test (per manuscript)
    p_delong = delong_test_pvalue(y_ext, prob_ext, prob_ext_base)
    auroc_full = roc_auc_score(y_ext, prob_ext)
    auroc_base = roc_auc_score(y_ext, prob_ext_base)
    print(f"\n    SDOH-CKDPred vs Clinical-Only: "
          f"AUROC {auroc_full:.4f} vs {auroc_base:.4f}, "
          f"diff={auroc_full - auroc_base:+.4f}, P={p_delong}")

    # ── Table 3: Subgroup equity (per manuscript) ────────────────────────
    print("\n  ═══ Table 3: Subgroup Equity Analysis ═══")
    df_ext_p2 = df_ext_p.copy()
    df_ext_p2["prob"] = prob_ext
    df_ext_p2["y"]    = y_ext

    subgroup_defs = [
        ("African American",  df_ext_p2["race_ethnicity"] == "African_American"),
        ("Hispanic/Latino",   df_ext_p2["race_ethnicity"] == "Hispanic_Latino"),
        ("White",             df_ext_p2["race_ethnicity"] == "White"),
        ("Rural",             df_ext_p2["urbanicity"] == "Rural"),
        ("Urban",             df_ext_p2["urbanicity"] == "Urban"),
        ("High ADI (Q5)",     df_ext_p2["adi_quintile"] == 5),
    ]

    sub_rows = []
    for name, mask in subgroup_defs:
        sub = df_ext_p2[mask]
        if len(np.unique(sub["y"])) < 2:
            print(f"    {name} (n={len(sub):,}): insufficient class diversity")
            continue
        m = compute_metrics(sub["y"].values, sub["prob"].values)
        ci_lo, ci_hi = bootstrap_auroc_ci(sub["y"].values, sub["prob"].values,
                                           n_boot=500)
        m["Subgroup"] = name
        m["AUROC_95CI"] = f"{m['AUROC']:.2f} ({ci_lo:.2f}-{ci_hi:.2f})"
        sub_rows.append(m)
        print(f"    {name:20s} (n={m['N']:,}): "
              f"AUROC={m['AUROC']:.4f} ({ci_lo}-{ci_hi})  "
              f"PPV={m['PPV']:.4f}  F1={m['F1']:.4f}")

    table3 = pd.DataFrame(sub_rows)
    table3.to_csv(os.path.join(OUTPUT_DIR, "table3_subgroup_performance.csv"),
                  index=False)

    # DeLong test for subgroup differences (per manuscript)
    print("\n  Subgroup AUROC comparisons (DeLong's test):")
    race_pairs = [
        ("African American", "Hispanic/Latino",
         df_ext_p2["race_ethnicity"] == "African_American",
         df_ext_p2["race_ethnicity"] == "Hispanic_Latino"),
        ("African American", "White",
         df_ext_p2["race_ethnicity"] == "African_American",
         df_ext_p2["race_ethnicity"] == "White"),
        ("Hispanic/Latino", "White",
         df_ext_p2["race_ethnicity"] == "Hispanic_Latino",
         df_ext_p2["race_ethnicity"] == "White"),
        ("Rural", "Urban",
         df_ext_p2["urbanicity"] == "Rural",
         df_ext_p2["urbanicity"] == "Urban"),
    ]

    for name1, name2, mask1, mask2 in race_pairs:
        sub1 = df_ext_p2[mask1]
        sub2 = df_ext_p2[mask2]
        if (len(np.unique(sub1["y"])) < 2 or len(np.unique(sub2["y"])) < 2):
            continue
        auc1 = roc_auc_score(sub1["y"], sub1["prob"])
        auc2 = roc_auc_score(sub2["y"], sub2["prob"])
        print(f"    {name1} vs {name2}: "
              f"AUROC {auc1:.4f} vs {auc2:.4f}, "
              f"diff={abs(auc1 - auc2):.4f}")

    # ── Calibration assessment (per manuscript) ──────────────────────────
    print("\n  ═══ Calibration Assessment ═══")
    frac_pos, mean_pred = calibration_curve(y_ext, prob_ext, n_bins=10,
                                             strategy="uniform")
    cal_df = pd.DataFrame({
        "mean_predicted_prob": mean_pred,
        "fraction_positive":  frac_pos,
    })
    cal_df.to_csv(os.path.join(OUTPUT_DIR, "calibration_curve.csv"), index=False)

    brier = brier_score_loss(y_ext, prob_ext)
    brier_base = brier_score_loss(y_ext, prob_ext_base)
    print(f"  Brier score (SDOH-CKDPred):    {brier:.4f}")
    print(f"  Brier score (Clinical-Only):   {brier_base:.4f}")
    print(f"  Calibration curve saved to calibration_curve.csv")

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n  ═══ Summary ═══")
    print(f"  SDOH-CKDPred External AUROC:   {auroc_full:.4f}")
    print(f"  Clinical-Only External AUROC:  {auroc_base:.4f}")
    print(f"  Improvement:                   {auroc_full - auroc_base:+.4f} (P={p_delong})")
    print(f"  Risk Threshold:                {RISK_THRESHOLD}")

    print("\n" + "=" * 60)
    print("Step 4 complete. Tables saved to outputs/")
    print("Run step5_simulate_pilot.py next.")
    print("=" * 60)
