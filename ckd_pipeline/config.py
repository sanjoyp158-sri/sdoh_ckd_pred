"""
config.py
---------
Central configuration for SDOH-CKDPred pipeline.
All parameters in one place — change here, affects all steps.
"""

import os

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
RAW_DIR     = os.path.join(BASE_DIR, "data", "raw")
PROC_DIR    = os.path.join(BASE_DIR, "data", "processed")
MODEL_DIR   = os.path.join(BASE_DIR, "models")
OUTPUT_DIR  = os.path.join(BASE_DIR, "outputs")
FIGURE_DIR  = os.path.join(BASE_DIR, "figures")

for d in [RAW_DIR, PROC_DIR, MODEL_DIR, OUTPUT_DIR, FIGURE_DIR]:
    os.makedirs(d, exist_ok=True)

# ── Random seed (reproducibility) ─────────────────────────────────────────
SEED = 42

# ── Cohort sizes (from manuscript) ────────────────────────────────────────
N_TRAIN          = 47_832   # Training cohort
N_EXTERNAL       = 12_441   # External validation cohort
N_PILOT          = 18_347   # Pilot simulation cohort

# ── Outcome definition ────────────────────────────────────────────────────
PREDICTION_HORIZON_MONTHS = 24
EVENT_RATE = 0.221          # 22.1% — from USRDS 2023

# ── Demographic distributions (USRDS 2023 rural CKD population) ───────────
RACE_DIST = {
    "African_American": 0.231,
    "Hispanic_Latino":  0.138,
    "White":            0.592,
    "Other":            0.039,
}

AGE_MEAN = 62.4
AGE_STD  = 13.1
AGE_MIN  = 18
AGE_MAX  = 95

SEX_FEMALE_PROB = 0.52      # USRDS 2023

# ── CKD Stage distribution at baseline (Stage 2-3 patients) ───────────────
STAGE_DIST = {"Stage_2": 0.38, "Stage_3a": 0.35, "Stage_3b": 0.27}

# ── Clinical variable distributions (NHANES 2017-2020) ───────────────────
# eGFR by stage (mL/min/1.73m²)
EGFR_PARAMS = {
    "Stage_2":  {"mean": 72.0, "std": 8.0,  "lo": 60,  "hi": 89},
    "Stage_3a": {"mean": 49.0, "std": 7.0,  "lo": 45,  "hi": 59},
    "Stage_3b": {"mean": 36.0, "std": 5.0,  "lo": 30,  "hi": 44},
}
EGFR_SLOPE_MEAN = -2.8      # mL/min/1.73m² per year (USRDS)
EGFR_SLOPE_STD  =  2.1

UACR_MEAN_LOG   = 3.8       # log-normal (mg/g)
UACR_STD_LOG    = 1.2

HBA1C_MEAN      = 7.2       # %
HBA1C_STD       = 1.4

SBP_MEAN        = 138.0     # mmHg
SBP_STD         = 18.0
DBP_MEAN        = 82.0
DBP_STD         = 11.0

BMI_MEAN        = 31.2
BMI_STD         = 6.8

# ── SDOH distributions (ADI 2020, CDC PLACES, USDA) ──────────────────────
ADI_QUINTILE_DIST = [0.20, 0.20, 0.20, 0.20, 0.20]  # uniform nationally
FOOD_DESERT_PROB_BY_ADI = {1: 0.08, 2: 0.14, 3: 0.22, 4: 0.31, 5: 0.42}
HEALTHCARE_SHORTAGE_PROB_BY_ADI = {1: 0.12, 2: 0.19, 3: 0.28, 4: 0.38, 5: 0.51}

# ── Comorbidity prevalence (USRDS 2023) ───────────────────────────────────
DIABETES_PREV   = 0.47
HYPERTENSION_PREV = 0.86
CHF_PREV        = 0.18

# ── Utilization distributions ─────────────────────────────────────────────
PCP_VISIT_GAP_PROB = 0.31   # prob of >12 months since last PCP visit
MED_ADHERENCE_MEAN = 0.72
MED_ADHERENCE_STD  = 0.18

# ── Progression probability modifiers (Tangri 2011, Grams 2018) ───────────
# Base rate by stage
BASE_PROG_RATE = {
    "Stage_2":  0.08,
    "Stage_3a": 0.18,
    "Stage_3b": 0.38,
}
# Multipliers
DIABETES_PROG_MULT     = 1.62
HYPERTENSION_PROG_MULT = 1.41
ADI5_PROG_MULT         = 1.38   # High deprivation
FOOD_DESERT_PROG_MULT  = 1.22
EGFR_SLOPE_PROG_MULT   = 1.15   # per 1 mL/min/yr faster decline

# ── Model parameters ──────────────────────────────────────────────────────
XGB_PARAMS = {
    "max_depth":        8,
    "learning_rate":    0.05,
    "n_estimators":     500,
    "subsample":        0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "gamma":            0.1,
    "reg_alpha":        0.1,
    "reg_lambda":       1.0,
    "eval_metric":      "auc",
    "use_label_encoder": False,
    "random_state":     SEED,
    "n_jobs":           -1,
}

CV_FOLDS = 5
RISK_THRESHOLD = 0.65       # Youden's J optimized

# ── Cost-effectiveness parameters (USRDS 2023 Medicare) ──────────────────
COST_STAGE5_PER_YEAR  = 89_000   # USD
COST_STAGE3_PER_YEAR  = 20_000   # USD
ANNUAL_OPERATING_COST = 3_036_000
COST_STAGE5_RANGE     = (75_000, 105_000)  # sensitivity analysis

# ── Subgroups for equity analysis ─────────────────────────────────────────
SUBGROUPS = {
    "race_ethnicity": ["African_American", "Hispanic_Latino", "White"],
    "geography":      ["Rural", "Urban"],
    "adi":            ["High_ADI_Q5"],
}

# ── Figure settings ───────────────────────────────────────────────────────
FIGURE_DPI    = 300
FIGURE_FORMAT = "png"
FONT_FAMILY   = "DejaVu Sans"
