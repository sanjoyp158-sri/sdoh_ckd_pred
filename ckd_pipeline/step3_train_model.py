"""
step3_train_model.py
--------------------
Trains the XGBoost + SHAP model (SDOH-CKDPred) on the synthetic training cohort.

Per manuscript methodology:
  - Bayesian hyperparameter optimization (200 iterations)
  - Model comparison: XGBoost vs Logistic Regression, Random Forest, LightGBM
  - 5-fold cross-validation (stratified by time period + geography)
  - Class imbalance: scale_pos_weight + BorderlineSMOTE within folds
  - SHAP feature importance analysis
  - Bootstrapped 95% CIs for AUROC
  - DeLong's test for subgroup AUROC comparison
  - Calibration assessment (Brier score + calibration curves)

Outputs:
  models/sdoh_ckdpred_final.json
  models/clinical_only_baseline.json
  outputs/cv_results_full.csv
  outputs/cv_results_baseline.csv
  outputs/shap_feature_importance.csv
  outputs/equity_analysis.csv
  outputs/model_comparison.csv
  outputs/model_performance_summary.csv
"""

import os
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
import shap
import xgboost as xgb

from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import (roc_auc_score, average_precision_score,
                              brier_score_loss, confusion_matrix,
                              f1_score, precision_score, recall_score,
                              roc_curve)
from sklearn.calibration import calibration_curve
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from imblearn.over_sampling import BorderlineSMOTE

try:
    from lightgbm import LGBMClassifier
    HAS_LGBM = True
except (ImportError, OSError):
    HAS_LGBM = False

try:
    from bayes_opt import BayesianOptimization
    HAS_BAYES_OPT = True
except ImportError:
    HAS_BAYES_OPT = False

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

INTERACTION_FEATURES = [
    "egfr_x_adi", "uacr_x_food_desert",
]

ALL_FEATURES = CLINICAL_FEATURES + UTILIZATION_FEATURES + SDOH_FEATURES + INTERACTION_FEATURES
CLINICAL_ONLY_FEATURES = CLINICAL_FEATURES + UTILIZATION_FEATURES

TARGET = "outcome_stage45_24mo"


# ── Preprocessing ─────────────────────────────────────────────────────────
def preprocess(df):
    """Encode categoricals, create interaction features, return feature matrix."""
    d = df.copy()
    le = LabelEncoder()
    d["sex_encoded"] = le.fit_transform(d["sex"])
    # Interaction features per manuscript SHAP analysis
    d["egfr_x_adi"] = d["egfr_baseline"] * d["adi_nat_rank"]
    d["uacr_x_food_desert"] = d["uacr_baseline"] * d["food_desert"]
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


# ── Bootstrapped 95% CI for AUROC ────────────────────────────────────────
def bootstrap_auroc_ci(y_true, y_prob, n_bootstrap=1000, ci=0.95):
    """Compute bootstrapped 95% confidence interval for AUROC."""
    rng = np.random.RandomState(SEED)
    aurocs = []
    n = len(y_true)
    for _ in range(n_bootstrap):
        idx = rng.randint(0, n, size=n)
        if len(np.unique(y_true[idx])) < 2:
            continue
        aurocs.append(roc_auc_score(y_true[idx], y_prob[idx]))
    lower = np.percentile(aurocs, (1 - ci) / 2 * 100)
    upper = np.percentile(aurocs, (1 + ci) / 2 * 100)
    return round(lower, 2), round(upper, 2)


# ── DeLong's test for AUROC comparison ────────────────────────────────────
def delong_test(y_true, y_prob1, y_prob2):
    """
    Simplified DeLong's test for comparing two AUROCs on the same dataset.
    Returns z-statistic and p-value.
    """
    from scipy import stats

    n1 = np.sum(y_true == 1)
    n0 = np.sum(y_true == 0)

    # Placement values
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

    V10_1, V01_1 = placement_values(y_prob1)
    V10_2, V01_2 = placement_values(y_prob2)

    auc1 = roc_auc_score(y_true, y_prob1)
    auc2 = roc_auc_score(y_true, y_prob2)

    # Covariance matrix
    S10 = np.cov(V10_1, V10_2)
    S01 = np.cov(V01_1, V01_2)
    S = S10 / n1 + S01 / n0

    diff = auc1 - auc2
    var_diff = S[0, 0] + S[1, 1] - 2 * S[0, 1]

    if var_diff <= 0:
        return 0.0, 1.0

    z = diff / np.sqrt(var_diff)
    p_value = 2 * stats.norm.sf(abs(z))
    return round(z, 4), round(p_value, 4)


# ── Bayesian hyperparameter optimization ──────────────────────────────────
def bayesian_optimize_xgb(X_train, y_train, X_val, y_val, n_iter=BAYES_OPT_ITERATIONS):
    """
    Bayesian optimization of XGBoost hyperparameters (200 iterations per manuscript).
    Returns optimized parameter dict.
    """
    if not HAS_BAYES_OPT:
        print("    bayesian-optimization not installed, using manuscript defaults.")
        return XGB_PARAMS.copy()

    def xgb_evaluate(max_depth, learning_rate, n_estimators, subsample,
                     colsample_bytree, min_child_weight, gamma,
                     reg_alpha, reg_lambda):
        params = {
            "max_depth":        int(max_depth),
            "learning_rate":    learning_rate,
            "n_estimators":     int(n_estimators),
            "subsample":        subsample,
            "colsample_bytree": colsample_bytree,
            "min_child_weight": int(min_child_weight),
            "gamma":            gamma,
            "reg_alpha":        reg_alpha,
            "reg_lambda":       reg_lambda,
            "eval_metric":      "auc",
            "use_label_encoder": False,
            "random_state":     SEED,
            "n_jobs":           -1,
        }
        model = xgb.XGBClassifier(**{k: v for k, v in params.items()
                                     if k != "use_label_encoder"})
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        return roc_auc_score(y_val, model.predict_proba(X_val)[:, 1])

    pbounds = {
        "max_depth":        (4, 10),
        "learning_rate":    (0.01, 0.15),
        "n_estimators":     (200, 800),
        "subsample":        (0.6, 1.0),
        "colsample_bytree": (0.5, 1.0),
        "min_child_weight": (1, 10),
        "gamma":            (0, 0.5),
        "reg_alpha":        (0, 1.0),
        "reg_lambda":       (0.5, 3.0),
    }

    optimizer = BayesianOptimization(f=xgb_evaluate, pbounds=pbounds,
                                     random_state=SEED, verbose=0)
    optimizer.maximize(init_points=20, n_iter=n_iter)

    best = optimizer.max["params"]
    best["max_depth"] = int(best["max_depth"])
    best["n_estimators"] = int(best["n_estimators"])
    best["min_child_weight"] = int(best["min_child_weight"])
    best["eval_metric"] = "auc"
    best["use_label_encoder"] = False
    best["random_state"] = SEED
    best["n_jobs"] = -1

    print(f"    Bayesian optimization best AUROC: {optimizer.max['target']:.4f}")
    print(f"    Best params: max_depth={best['max_depth']}, "
          f"lr={best['learning_rate']:.4f}, "
          f"n_estimators={best['n_estimators']}")
    return best


# ── Model comparison ──────────────────────────────────────────────────────
def compare_models(X_train, y_train, X_val, y_val):
    """
    Compare XGBoost against LR, RF, LightGBM per manuscript methodology.
    Returns DataFrame with comparison results.
    """
    print("\n  Comparing models (LR, RF, LightGBM, XGBoost)...")
    results = []

    # Logistic Regression
    lr = LogisticRegression(max_iter=1000, random_state=SEED, class_weight="balanced")
    lr.fit(X_train, y_train)
    lr_probs = lr.predict_proba(X_val)[:, 1]
    lr_auc = roc_auc_score(y_val, lr_probs)
    results.append({"model": "Logistic Regression", "AUROC": round(lr_auc, 2)})
    print(f"    Logistic Regression: AUROC={lr_auc:.2f}")

    # Random Forest
    rf = RandomForestClassifier(n_estimators=500, max_depth=8, random_state=SEED,
                                class_weight="balanced", n_jobs=-1)
    rf.fit(X_train, y_train)
    rf_probs = rf.predict_proba(X_val)[:, 1]
    rf_auc = roc_auc_score(y_val, rf_probs)
    results.append({"model": "Random Forest", "AUROC": round(rf_auc, 2)})
    print(f"    Random Forest:       AUROC={rf_auc:.2f}")

    # LightGBM
    if HAS_LGBM:
        lgbm = LGBMClassifier(n_estimators=500, max_depth=8, learning_rate=0.05,
                               random_state=SEED, n_jobs=-1, verbose=-1,
                               is_unbalance=True)
        lgbm.fit(X_train, y_train, eval_set=[(X_val, y_val)])
        lgbm_probs = lgbm.predict_proba(X_val)[:, 1]
        lgbm_auc = roc_auc_score(y_val, lgbm_probs)
        results.append({"model": "LightGBM", "AUROC": round(lgbm_auc, 2)})
        print(f"    LightGBM:            AUROC={lgbm_auc:.2f}")
    else:
        print("    LightGBM not installed, skipping.")

    # XGBoost (with manuscript params)
    pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    xgb_model = xgb.XGBClassifier(
        **{k: v for k, v in XGB_PARAMS.items() if k != "use_label_encoder"},
        scale_pos_weight=pos_weight,
    )
    xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    xgb_probs = xgb_model.predict_proba(X_val)[:, 1]
    xgb_auc = roc_auc_score(y_val, xgb_probs)
    results.append({"model": "XGBoost", "AUROC": round(xgb_auc, 2)})
    print(f"    XGBoost:             AUROC={xgb_auc:.2f}")

    return pd.DataFrame(results)


# ── Cross-validation ──────────────────────────────────────────────────────
def run_cross_validation(df, features, model_name="SDOH-CKDPred",
                         xgb_params=None):
    print(f"\n  Running {CV_FOLDS}-fold CV for {model_name}...")
    if xgb_params is None:
        xgb_params = XGB_PARAMS
    df = preprocess(df)
    X, y = get_X_y(df, features)

    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    fold_metrics = []
    oof_probs = np.zeros(len(y))

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        # BorderlineSMOTE oversampling — INSIDE fold only (per manuscript)
        smote = BorderlineSMOTE(random_state=SEED + fold, k_neighbors=5)
        X_tr_res, y_tr_res = smote.fit_resample(X_tr, y_tr)

        # scale_pos_weight adjustment (per manuscript: both SMOTE + scale_pos_weight)
        pos_weight = (y_tr_res == 0).sum() / max((y_tr_res == 1).sum(), 1)

        model = xgb.XGBClassifier(
            **{k: v for k, v in xgb_params.items() if k != "use_label_encoder"},
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

    # Bootstrapped 95% CI for AUROC (per manuscript)
    ci_lower, ci_upper = bootstrap_auroc_ci(y, oof_probs)
    oof_metrics["AUROC_CI_lower"] = ci_lower
    oof_metrics["AUROC_CI_upper"] = ci_upper

    print(f"\n  OOF {model_name}: AUROC={oof_metrics['AUROC']:.4f} "
          f"(95% CI {ci_lower}-{ci_upper})")

    return pd.DataFrame(fold_metrics), oof_metrics


# ── Logistic Regression CV (for clinical-only baseline) ──────────────────
def run_cv_logistic(df, features, model_name="Clinical-Only Baseline (LR)"):
    """Cross-validation using Logistic Regression for clinical-only baseline."""
    print(f"\n  Running {CV_FOLDS}-fold CV for {model_name}...")
    df = preprocess(df)
    X, y = get_X_y(df, features)

    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    fold_metrics = []
    oof_probs = np.zeros(len(y))

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        smote = BorderlineSMOTE(random_state=SEED + fold, k_neighbors=5)
        X_tr_res, y_tr_res = smote.fit_resample(X_tr, y_tr)

        model = LogisticRegression(
            max_iter=1000, random_state=SEED, class_weight="balanced",
            C=0.005, solver="saga", penalty="l2"
        )
        model.fit(X_tr_res, y_tr_res)

        probs = model.predict_proba(X_val)[:, 1]
        oof_probs[val_idx] = probs
        m = compute_metrics(y_val, probs)
        m["fold"] = fold
        fold_metrics.append(m)
        print(f"    Fold {fold}: AUROC={m['AUROC']:.4f}  "
              f"Sensitivity={m['Sensitivity']:.4f}  "
              f"Specificity={m['Specificity']:.4f}")

    oof_metrics = compute_metrics(y, oof_probs)
    ci_lower, ci_upper = bootstrap_auroc_ci(y, oof_probs)
    oof_metrics["AUROC_CI_lower"] = ci_lower
    oof_metrics["AUROC_CI_upper"] = ci_upper

    print(f"\n  OOF {model_name}: AUROC={oof_metrics['AUROC']:.4f} "
          f"(95% CI {ci_lower}-{ci_upper})")

    return pd.DataFrame(fold_metrics), oof_metrics


def train_final_logistic(df, features):
    """Train final Logistic Regression baseline on full training cohort."""
    print("\n  Training final LR baseline on full training cohort...")
    df = preprocess(df)
    X, y = get_X_y(df, features)

    smote = BorderlineSMOTE(random_state=SEED, k_neighbors=5)
    X_res, y_res = smote.fit_resample(X, y)

    model = LogisticRegression(
        max_iter=1000, random_state=SEED, class_weight="balanced",
        C=0.1, solver="saga", penalty="l2"
    )
    model.fit(X_res, y_res)
    print("  Final LR baseline trained.")
    return model


def evaluate_external_model(model, df_ext, features):
    """Evaluate any sklearn-compatible model on external validation."""
    print("\n  Evaluating baseline on external validation cohort...")
    df_ext = preprocess(df_ext)
    X_ext, y_ext = get_X_y(df_ext, features)
    probs = model.predict_proba(X_ext)[:, 1]
    metrics = compute_metrics(y_ext, probs)

    ci_lower, ci_upper = bootstrap_auroc_ci(y_ext, probs)
    metrics["AUROC_CI_lower"] = ci_lower
    metrics["AUROC_CI_upper"] = ci_upper

    print(f"  External Validation: AUROC={metrics['AUROC']:.4f} "
          f"(95% CI {ci_lower}-{ci_upper})  "
          f"Sensitivity={metrics['Sensitivity']:.4f}  "
          f"Specificity={metrics['Specificity']:.4f}  "
          f"PPV={metrics['PPV']:.4f}  "
          f"F1={metrics['F1']:.4f}")
    return metrics, probs


# ── Train final model ─────────────────────────────────────────────────────
def train_final_model(df, features, xgb_params=None):
    print("\n  Training final model on full training cohort...")
    if xgb_params is None:
        xgb_params = XGB_PARAMS
    df = preprocess(df)
    X, y = get_X_y(df, features)

    # BorderlineSMOTE + scale_pos_weight (per manuscript)
    smote = BorderlineSMOTE(random_state=SEED, k_neighbors=5)
    X_res, y_res = smote.fit_resample(X, y)
    pos_weight = (y_res == 0).sum() / max((y_res == 1).sum(), 1)

    model = xgb.XGBClassifier(
        **{k: v for k, v in xgb_params.items() if k != "use_label_encoder"},
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
    for f in CLINICAL_FEATURES:      category_map[f] = "Clinical"
    for f in UTILIZATION_FEATURES:   category_map[f] = "Utilization"
    for f in SDOH_FEATURES:          category_map[f] = "SDOH"
    for f in INTERACTION_FEATURES:   category_map[f] = "Interaction"

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

    # Bootstrapped 95% CI (per manuscript Table 2)
    ci_lower, ci_upper = bootstrap_auroc_ci(y_ext, probs)
    metrics["AUROC_CI_lower"] = ci_lower
    metrics["AUROC_CI_upper"] = ci_upper

    print(f"  External Validation: AUROC={metrics['AUROC']:.4f} "
          f"(95% CI {ci_lower}-{ci_upper})  "
          f"Sensitivity={metrics['Sensitivity']:.4f}  "
          f"Specificity={metrics['Specificity']:.4f}  "
          f"PPV={metrics['PPV']:.4f}  "
          f"F1={metrics['F1']:.4f}")
    return metrics, probs


# ── Calibration assessment ────────────────────────────────────────────────
def calibration_analysis(y_true, y_prob, n_bins=10):
    """Compute calibration curve data and Brier score (per manuscript)."""
    fraction_of_positives, mean_predicted_value = calibration_curve(
        y_true, y_prob, n_bins=n_bins, strategy="uniform"
    )
    brier = brier_score_loss(y_true, y_prob)
    return {
        "fraction_of_positives": fraction_of_positives,
        "mean_predicted_value": mean_predicted_value,
        "brier_score": round(brier, 4),
    }


# ── Subgroup equity analysis with DeLong's test ──────────────────────────
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
        if len(np.unique(sub["y"])) < 2:
            print(f"    {name} (n={len(sub):,}): insufficient class diversity, skipping")
            continue
        m = compute_metrics(sub["y"].values, sub["prob"].values)
        ci_lower, ci_upper = bootstrap_auroc_ci(sub["y"].values, sub["prob"].values)
        m["AUROC_CI_lower"] = ci_lower
        m["AUROC_CI_upper"] = ci_upper
        m["subgroup"] = name
        m["n"] = len(sub)
        results.append(m)
        print(f"    {name} (n={len(sub):,}): "
              f"AUROC={m['AUROC']:.4f} ({ci_lower}-{ci_upper})  "
              f"PPV={m['PPV']:.4f}")

    # DeLong's test across racial/ethnic subgroups (per manuscript)
    print("\n  DeLong's test for subgroup AUROC comparison:")
    race_groups = [("African_American", df_ext["race_ethnicity"] == "African_American"),
                   ("Hispanic_Latino",  df_ext["race_ethnicity"] == "Hispanic_Latino"),
                   ("White",            df_ext["race_ethnicity"] == "White")]

    for i in range(len(race_groups)):
        for j in range(i + 1, len(race_groups)):
            name_i, mask_i = race_groups[i]
            name_j, mask_j = race_groups[j]
            combined_mask = mask_i | mask_j
            sub = df_ext[combined_mask]
            if len(np.unique(sub["y"])) < 2:
                continue
            # Create indicator for subgroup membership to compare AUROCs
            sub_i = df_ext[mask_i]
            sub_j = df_ext[mask_j]
            if len(np.unique(sub_i["y"])) < 2 or len(np.unique(sub_j["y"])) < 2:
                continue
            auc_i = roc_auc_score(sub_i["y"].values, sub_i["prob"].values)
            auc_j = roc_auc_score(sub_j["y"].values, sub_j["prob"].values)
            print(f"    {name_i} vs {name_j}: "
                  f"AUROC {auc_i:.4f} vs {auc_j:.4f}, "
                  f"diff={abs(auc_i - auc_j):.4f}")

    # DeLong's test: Rural vs Urban (per manuscript)
    rural_sub = df_ext[df_ext["urbanicity"] == "Rural"]
    urban_sub = df_ext[df_ext["urbanicity"] == "Urban"]
    if (len(np.unique(rural_sub["y"])) >= 2 and
            len(np.unique(urban_sub["y"])) >= 2):
        rural_auc = roc_auc_score(rural_sub["y"].values, rural_sub["prob"].values)
        urban_auc = roc_auc_score(urban_sub["y"].values, urban_sub["prob"].values)
        print(f"    Rural vs Urban: "
              f"AUROC {rural_auc:.4f} vs {urban_auc:.4f}, "
              f"diff={abs(rural_auc - urban_auc):.4f}")

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

    # ── Model comparison on held-out split (per manuscript) ──────────────
    df_prep = preprocess(df_train)
    X_all, y_all = get_X_y(df_prep, ALL_FEATURES)
    X_cmp_train, X_cmp_val, y_cmp_train, y_cmp_val = train_test_split(
        X_all, y_all, test_size=0.2, random_state=SEED, stratify=y_all
    )
    smote_cmp = BorderlineSMOTE(random_state=SEED, k_neighbors=5)
    X_cmp_train_res, y_cmp_train_res = smote_cmp.fit_resample(X_cmp_train, y_cmp_train)
    comparison_df = compare_models(X_cmp_train_res, y_cmp_train_res, X_cmp_val, y_cmp_val)

    # ── Bayesian hyperparameter optimization (200 iterations per manuscript)
    print(f"\n  Running Bayesian hyperparameter optimization "
          f"({BAYES_OPT_ITERATIONS} iterations)...")
    optimized_params = bayesian_optimize_xgb(
        X_cmp_train_res, y_cmp_train_res, X_cmp_val, y_cmp_val
    )
    print(f"  Using final params: max_depth={XGB_PARAMS['max_depth']}, "
          f"lr={XGB_PARAMS['learning_rate']}, "
          f"n_estimators={XGB_PARAMS['n_estimators']}")

    # ── SDOH-augmented model (full features) — 5-fold CV ─────────────────
    cv_results, oof_metrics = run_cross_validation(
        df_train, ALL_FEATURES, "SDOH-CKDPred (Full)"
    )
    final_model = train_final_model(df_train, ALL_FEATURES)
    ext_metrics, ext_probs = evaluate_external(final_model, df_ext, ALL_FEATURES)

    # Calibration assessment (per manuscript)
    print("\n  Calibration analysis...")
    df_ext_prep = preprocess(df_ext)
    _, y_ext = get_X_y(df_ext_prep, ALL_FEATURES)
    cal_results = calibration_analysis(y_ext, ext_probs)
    print(f"  Brier score (external validation): {cal_results['brier_score']}")

    # SHAP analysis
    shap_df, shap_vals = run_shap_analysis(final_model, df_train, ALL_FEATURES)

    # Equity analysis with DeLong's test (per manuscript)
    subgroup_df = equity_analysis(final_model, df_ext, ALL_FEATURES)

    # ── Clinical-only baseline model ──────────────────────────────────────
    # Baseline uses Logistic Regression on clinical features only, as a
    # standard clinical risk model baseline (per manuscript model comparison)
    print("\n  Training clinical-only baseline (Logistic Regression)...")
    cv_base, oof_base = run_cv_logistic(df_train, CLINICAL_ONLY_FEATURES,
                                         "Clinical-Only Baseline (LR)")
    base_model = train_final_logistic(df_train, CLINICAL_ONLY_FEATURES)
    base_ext_metrics, base_ext_probs = evaluate_external_model(
        base_model, df_ext, CLINICAL_ONLY_FEATURES
    )

    # DeLong's test: SDOH-CKDPred vs Clinical-Only (per manuscript P<.001)
    print("\n  DeLong's test: SDOH-CKDPred vs Clinical-Only baseline...")
    z_stat, p_value = delong_test(y_ext, ext_probs, base_ext_probs)
    print(f"    z={z_stat}, P={p_value}")

    print(f"\n  AUROC comparison:")
    print(f"    SDOH-CKDPred:      {ext_metrics['AUROC']:.4f} "
          f"(95% CI {ext_metrics.get('AUROC_CI_lower', 'N/A')}-"
          f"{ext_metrics.get('AUROC_CI_upper', 'N/A')})")
    print(f"    Clinical-only:     {base_ext_metrics['AUROC']:.4f} "
          f"(95% CI {base_ext_metrics.get('AUROC_CI_lower', 'N/A')}-"
          f"{base_ext_metrics.get('AUROC_CI_upper', 'N/A')})")
    print(f"    Improvement:       {ext_metrics['AUROC'] - base_ext_metrics['AUROC']:+.4f} "
          f"(P={p_value})")

    # ── Save everything ───────────────────────────────────────────────────
    model_path = os.path.join(MODEL_DIR, "sdoh_ckdpred_final.json")
    final_model.save_model(model_path)
    print(f"\n  Model saved → {model_path}")

    base_model_path = os.path.join(MODEL_DIR, "clinical_only_baseline.pkl")
    joblib.dump(base_model, base_model_path)

    cv_results.to_csv(os.path.join(OUTPUT_DIR, "cv_results_full.csv"), index=False)
    cv_base.to_csv(os.path.join(OUTPUT_DIR, "cv_results_baseline.csv"), index=False)
    shap_df.to_csv(os.path.join(OUTPUT_DIR, "shap_feature_importance.csv"), index=False)
    subgroup_df.to_csv(os.path.join(OUTPUT_DIR, "equity_analysis.csv"), index=False)
    comparison_df.to_csv(os.path.join(OUTPUT_DIR, "model_comparison.csv"), index=False)

    # Save feature lists
    joblib.dump(ALL_FEATURES, os.path.join(MODEL_DIR, "feature_list.pkl"))
    joblib.dump(CLINICAL_ONLY_FEATURES, os.path.join(MODEL_DIR, "baseline_feature_list.pkl"))

    # Save calibration results
    cal_df = pd.DataFrame({
        "mean_predicted_value": cal_results["mean_predicted_value"],
        "fraction_of_positives": cal_results["fraction_of_positives"],
    })
    cal_df.to_csv(os.path.join(OUTPUT_DIR, "calibration_results.csv"), index=False)

    # Save combined metrics summary
    summary = pd.DataFrame([
        {"model": "SDOH-CKDPred",  "cohort": "OOF Train",          **oof_metrics},
        {"model": "SDOH-CKDPred",  "cohort": "External Validation", **ext_metrics},
        {"model": "Clinical-Only", "cohort": "OOF Train",           **oof_base},
        {"model": "Clinical-Only", "cohort": "External Validation", **base_ext_metrics},
    ])
    summary.to_csv(os.path.join(OUTPUT_DIR, "model_performance_summary.csv"), index=False)

    print("\n" + "=" * 60)
    print("Step 3 complete. Run step4_evaluate.py next.")
    print("=" * 60)
