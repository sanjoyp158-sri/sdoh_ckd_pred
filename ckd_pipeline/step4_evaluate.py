"""
step4_evaluate.py
-----------------
Comprehensive evaluation: generates all performance tables from the paper.

Outputs:
  outputs/table2_performance_metrics.csv
  outputs/table3_subgroup_performance.csv
  outputs/calibration_results.csv
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
                              recall_score, f1_score, confusion_matrix)
from sklearn.preprocessing import LabelEncoder
from sklearn.calibration import calibration_curve
from scipy import stats

from config import *

# ── Helpers ────────────────────────────────────────────────────────────────
def preprocess(df):
    d = df.copy()
    le = LabelEncoder()
    d["sex_encoded"] = le.fit_transform(d["sex"])
    return d

def compute_metrics(y_true, y_prob, threshold=RISK_THRESHOLD):
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
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
    """Bootstrap 95% CI for AUROC using DeLong approximation."""
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


# ── Main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("SDOH-CKDPred — Step 4: Comprehensive Evaluation")
    print("=" * 60)

    # Load data and models
    df_train  = pd.read_csv(os.path.join(PROC_DIR, "cohort_train.csv"))
    df_ext    = pd.read_csv(os.path.join(PROC_DIR, "cohort_external_val.csv"))
    all_feats = joblib.load(os.path.join(MODEL_DIR, "feature_list.pkl"))

    final_model = xgb.XGBClassifier()
    final_model.load_model(os.path.join(MODEL_DIR, "sdoh_ckdpred_final.json"))

    # Preprocess
    df_train_p = preprocess(df_train)
    df_ext_p   = preprocess(df_ext)

    X_tr   = df_train_p[all_feats].values
    y_tr   = df_train_p["outcome_stage45_24mo"].values
    X_ext  = df_ext_p[all_feats].values
    y_ext  = df_ext_p["outcome_stage45_24mo"].values

    prob_tr  = final_model.predict_proba(X_tr)[:, 1]
    prob_ext = final_model.predict_proba(X_ext)[:, 1]

    # ── Table 2: Performance metrics ─────────────────────────────────────
    print("\n  Building Table 2: Performance Metrics...")
    rows = []
    for cohort_name, y_true, y_prob in [
        ("Training Cohort (N=47,832)",       y_tr,  prob_tr),
        ("External Validation (N=12,441)",   y_ext, prob_ext),
    ]:
        m = compute_metrics(y_true, y_prob)
        ci_lo, ci_hi = bootstrap_auroc_ci(y_true, y_prob)
        m["AUROC_CI"] = f"{m['AUROC']:.2f} ({ci_lo:.2f}–{ci_hi:.2f})"
        m["Cohort"] = cohort_name
        rows.append(m)

    table2 = pd.DataFrame(rows)
    table2.to_csv(os.path.join(OUTPUT_DIR, "table2_performance_metrics.csv"), index=False)
    print(table2[["Cohort","AUROC_CI","Sensitivity","Specificity","PPV","NPV","F1","AUPRC","Brier"]].to_string(index=False))

    # ── Table 3: Subgroup equity ──────────────────────────────────────────
    print("\n  Building Table 3: Subgroup Equity Analysis...")
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
        m = compute_metrics(sub["y"].values, sub["prob"].values)
        ci_lo, ci_hi = bootstrap_auroc_ci(sub["y"].values, sub["prob"].values, n_boot=500)
        m["Subgroup"] = name
        m["AUROC_95CI"] = f"{m['AUROC']:.2f} ({ci_lo:.2f}–{ci_hi:.2f})"
        sub_rows.append(m)
        print(f"    {name} (n={len(sub):,}): AUROC={m['AUROC']:.4f}  PPV={m['PPV']:.4f}")

    table3 = pd.DataFrame(sub_rows)
    table3.to_csv(os.path.join(OUTPUT_DIR, "table3_subgroup_performance.csv"), index=False)

    # DeLong test for subgroup differences
    print("\n  Testing subgroup AUROC differences (DeLong approximation)...")
    aa_mask  = df_ext_p2["race_ethnicity"] == "African_American"
    w_mask   = df_ext_p2["race_ethnicity"] == "White"
    hisp_mask= df_ext_p2["race_ethnicity"] == "Hispanic_Latino"

    # Simple z-test on bootstrap distributions as approximation
    def auroc_pval(m1, m2, n1, n2):
        # Hanley & McNeil approximation
        se1 = np.sqrt(m1*(1-m1) / n1)
        se2 = np.sqrt(m2*(1-m2) / n2)
        z = abs(m1 - m2) / np.sqrt(se1**2 + se2**2)
        p = 2 * (1 - stats.norm.cdf(z))
        return round(p, 4)

    aa_auroc = roc_auc_score(df_ext_p2[aa_mask]["y"], df_ext_p2[aa_mask]["prob"])
    w_auroc  = roc_auc_score(df_ext_p2[w_mask]["y"],  df_ext_p2[w_mask]["prob"])
    p_race   = auroc_pval(aa_auroc, w_auroc,
                           mask_sum := aa_mask.sum(), w_mask.sum())
    print(f"    African American vs White AUROC p-value: {p_race:.4f}")

    rural_mask = df_ext_p2["urbanicity"] == "Rural"
    urban_mask = df_ext_p2["urbanicity"] == "Urban"
    r_auroc = roc_auc_score(df_ext_p2[rural_mask]["y"], df_ext_p2[rural_mask]["prob"])
    u_auroc = roc_auc_score(df_ext_p2[urban_mask]["y"], df_ext_p2[urban_mask]["prob"])
    p_geo   = auroc_pval(r_auroc, u_auroc, rural_mask.sum(), urban_mask.sum())
    print(f"    Rural vs Urban AUROC p-value: {p_geo:.4f}")

    # ── Calibration ───────────────────────────────────────────────────────
    print("\n  Computing calibration...")
    frac_pos, mean_pred = calibration_curve(y_ext, prob_ext, n_bins=10)
    cal_df = pd.DataFrame({"mean_predicted_prob": mean_pred,
                            "fraction_positive":  frac_pos})
    cal_df.to_csv(os.path.join(OUTPUT_DIR, "calibration_curve.csv"), index=False)
    print(f"  Brier score (external): {brier_score_loss(y_ext, prob_ext):.4f}")

    print("\n" + "=" * 60)
    print("Step 4 complete. Tables saved to outputs/")
    print("Run step5_simulate_pilot.py next.")
    print("=" * 60)
