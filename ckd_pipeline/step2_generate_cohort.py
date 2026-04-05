"""
step2_generate_cohort.py
------------------------
Generates the three synthetic patient cohorts used in the simulation study:
  - Training cohort      (N=47,832)
  - External validation  (N=12,441)
  - Pilot simulation     (N=18,347)

All distributions are parameterized from publicly available data sources
as described in config.py. No real patient data is used.

Outputs:
  data/processed/cohort_train.csv
  data/processed/cohort_external_val.csv
  data/processed/cohort_pilot.csv
"""

import os
import numpy as np
import pandas as pd
from scipy import stats
from config import *

np.random.seed(SEED)


# ── Helper functions ───────────────────────────────────────────────────────

def assign_stage(n, seed_offset=0):
    """Assign CKD baseline stage per STAGE_DIST."""
    rng = np.random.default_rng(SEED + seed_offset)
    stages = rng.choice(
        list(STAGE_DIST.keys()),
        size=n,
        p=list(STAGE_DIST.values())
    )
    return stages


def sample_egfr(stages, seed_offset=0):
    """Sample baseline eGFR consistent with CKD stage."""
    rng = np.random.default_rng(SEED + seed_offset)
    egfr = np.zeros(len(stages))
    for i, stage in enumerate(stages):
        p = EGFR_PARAMS[stage]
        val = rng.normal(p["mean"], p["std"])
        egfr[i] = np.clip(val, p["lo"], p["hi"])
    return egfr


def sample_egfr_slope(n, seed_offset=0):
    """Sample eGFR slope (mL/min/yr) — negative = declining."""
    rng = np.random.default_rng(SEED + seed_offset)
    slope = rng.normal(EGFR_SLOPE_MEAN, EGFR_SLOPE_STD, n)
    return np.clip(slope, -15, 0)


def sample_uacr(n, seed_offset=0):
    """Sample UACR from log-normal distribution (NHANES 2017-2020)."""
    rng = np.random.default_rng(SEED + seed_offset)
    log_uacr = rng.normal(UACR_MEAN_LOG, UACR_STD_LOG, n)
    return np.clip(np.exp(log_uacr), 3, 3000)


def assign_race(n, seed_offset=0):
    """Assign race/ethnicity per USRDS 2023 rural CKD demographics."""
    rng = np.random.default_rng(SEED + seed_offset)
    return rng.choice(
        list(RACE_DIST.keys()),
        size=n,
        p=list(RACE_DIST.values())
    )


def assign_adi_quintile(n, seed_offset=0):
    """Assign ADI quintile (1=least deprived, 5=most deprived)."""
    rng = np.random.default_rng(SEED + seed_offset)
    return rng.choice([1, 2, 3, 4, 5], size=n,
                       p=ADI_QUINTILE_DIST)


def assign_food_desert(adi_quintiles, seed_offset=0):
    """Assign food desert status — higher probability in deprived areas."""
    rng = np.random.default_rng(SEED + seed_offset)
    probs = np.array([FOOD_DESERT_PROB_BY_ADI[q] for q in adi_quintiles])
    return (rng.random(len(adi_quintiles)) < probs).astype(int)


def assign_healthcare_shortage(adi_quintiles, seed_offset=0):
    """Assign healthcare shortage area designation."""
    rng = np.random.default_rng(SEED + seed_offset)
    probs = np.array([HEALTHCARE_SHORTAGE_PROB_BY_ADI[q] for q in adi_quintiles])
    return (rng.random(len(adi_quintiles)) < probs).astype(int)


def compute_progression_probability(df):
    """
    Compute individual 24-month Stage 4-5 progression probability
    using base rates from USRDS 2023 modified by Tangri 2011 and
    Grams 2018 risk multipliers.
    """
    prob = df["ckd_stage"].map(BASE_PROG_RATE).values.copy()

    # Apply multipliers
    prob *= np.where(df["diabetes"] == 1,     DIABETES_PROG_MULT,     1.0)
    prob *= np.where(df["hypertension"] == 1, HYPERTENSION_PROG_MULT, 1.0)
    prob *= np.where(df["adi_quintile"] == 5, ADI5_PROG_MULT,         1.0)
    prob *= np.where(df["food_desert"] == 1,  FOOD_DESERT_PROG_MULT,  1.0)

    # eGFR slope effect: faster decline = higher progression risk
    slope_effect = 1.0 + (np.abs(df["egfr_slope"]) - 2.8) * 0.05
    prob *= np.clip(slope_effect, 0.8, 2.5)

    # Race/ethnicity effect (NIH health disparities data)
    race_mult = np.where(df["race_ethnicity"] == "African_American", 1.35,
                np.where(df["race_ethnicity"] == "Hispanic_Latino",  1.25, 1.0))
    prob *= race_mult

    return np.clip(prob, 0.02, 0.95)


def assign_urbanicity(n, rural_frac=0.42, seed_offset=0):
    """Assign rural/urban — 42% rural based on HRSA data."""
    rng = np.random.default_rng(SEED + seed_offset)
    return rng.choice(["Rural", "Urban"], size=n,
                       p=[rural_frac, 1 - rural_frac])


# ── Main cohort generator ──────────────────────────────────────────────────

def generate_cohort(n, cohort_name, seed_offset=0):
    """
    Generate a complete synthetic patient cohort of size n.

    Parameters
    ----------
    n           : int    — number of patients
    cohort_name : str    — label (train / external_val / pilot)
    seed_offset : int    — ensures different cohorts even with same base seed

    Returns
    -------
    pd.DataFrame with all features and outcome label
    """
    print(f"\n  Generating {cohort_name} cohort (N={n:,})...")
    rng = np.random.default_rng(SEED + seed_offset)

    # ── Demographics ──────────────────────────────────────────────────────
    age = rng.normal(AGE_MEAN, AGE_STD, n)
    age = np.clip(age, AGE_MIN, AGE_MAX).astype(int)

    sex = rng.choice(["Female", "Male"], size=n,
                      p=[SEX_FEMALE_PROB, 1 - SEX_FEMALE_PROB])

    race = assign_race(n, seed_offset)
    urbanicity = assign_urbanicity(n, seed_offset=seed_offset + 10)

    # ── CKD baseline ─────────────────────────────────────────────────────
    ckd_stage = assign_stage(n, seed_offset)
    egfr_baseline = sample_egfr(ckd_stage, seed_offset)
    egfr_slope = sample_egfr_slope(n, seed_offset)
    uacr = sample_uacr(n, seed_offset)
    uacr_trend = rng.normal(0.08, 0.12, n)  # annual % increase

    # ── Clinical features ─────────────────────────────────────────────────
    diabetes = (rng.random(n) < DIABETES_PREV).astype(int)
    hypertension = (rng.random(n) < HYPERTENSION_PREV).astype(int)
    chf = (rng.random(n) < CHF_PREV).astype(int)

    hba1c = rng.normal(HBA1C_MEAN, HBA1C_STD, n)
    hba1c = np.where(diabetes == 1,
                     np.clip(hba1c, 5.5, 14.0),
                     np.clip(hba1c * 0.85, 4.5, 6.4))
    hba1c_trend = rng.normal(0.0, 0.3, n)

    sbp = rng.normal(SBP_MEAN, SBP_STD, n)
    sbp = np.clip(sbp, 90, 210)
    dbp = rng.normal(DBP_MEAN, DBP_STD, n)
    dbp = np.clip(dbp, 55, 130)
    sbp_trend = rng.normal(-0.5, 3.0, n)  # mmHg/year change

    bmi = rng.normal(BMI_MEAN, BMI_STD, n)
    bmi = np.clip(bmi, 16, 65)

    # Charlson Comorbidity Index (0-10+)
    cci = (diabetes + hypertension * 0.5 + chf * 2 +
           rng.poisson(1.2, n)).astype(int)
    cci = np.clip(cci, 0, 10)

    # ── Medication features ───────────────────────────────────────────────
    # ACE inhibitor / ARB — more common in hypertensive patients
    acei_arb = (rng.random(n) < np.where(hypertension == 1, 0.68, 0.22)).astype(int)
    sglt2i    = (rng.random(n) < np.where(diabetes == 1, 0.28, 0.03)).astype(int)
    glp1ra    = (rng.random(n) < np.where(diabetes == 1, 0.19, 0.01)).astype(int)

    med_adherence = rng.normal(MED_ADHERENCE_MEAN, MED_ADHERENCE_STD, n)
    med_adherence = np.clip(med_adherence, 0, 1)

    # ── Utilization features ──────────────────────────────────────────────
    pcp_visit_gap = (rng.random(n) < PCP_VISIT_GAP_PROB).astype(int)
    missed_nephro_referral = (rng.random(n) < 0.44).astype(int)
    ed_visits_past_year = rng.poisson(1.1, n)

    insurance_type = rng.choice(
        ["Medicare", "Medicaid", "Commercial", "Uninsured"],
        size=n, p=[0.38, 0.27, 0.28, 0.07]
    )
    insurance_uninsured = (insurance_type == "Uninsured").astype(int)
    insurance_medicaid  = (insurance_type == "Medicaid").astype(int)

    # ── SDOH features ─────────────────────────────────────────────────────
    adi_quintile = assign_adi_quintile(n, seed_offset)
    adi_nat_rank = (adi_quintile - 1) * 20 + rng.integers(1, 21, n)

    food_desert = assign_food_desert(adi_quintile, seed_offset)
    healthcare_shortage = assign_healthcare_shortage(adi_quintile, seed_offset)

    # Poverty rate (% below poverty line) — Census ACS
    poverty_rate = (adi_quintile - 1) * 6 + rng.normal(8, 3, n)
    poverty_rate = np.clip(poverty_rate, 2, 45)

    # Median household income (USD) — Census ACS, inverse of ADI
    median_income = 85_000 - (adi_quintile - 1) * 12_000 + rng.normal(0, 5000, n)
    median_income = np.clip(median_income, 22_000, 150_000)

    # Unemployment rate (%)
    unemployment_rate = (adi_quintile - 1) * 1.8 + rng.normal(4.5, 1.5, n)
    unemployment_rate = np.clip(unemployment_rate, 1, 20)

    # Education: % without HS diploma
    no_hs_diploma_pct = (adi_quintile - 1) * 4 + rng.normal(10, 3, n)
    no_hs_diploma_pct = np.clip(no_hs_diploma_pct, 1, 40)

    # Linguistic isolation (%)
    linguistic_isolation = rng.exponential(3, n) * (1 + adi_quintile * 0.3)
    linguistic_isolation = np.clip(linguistic_isolation, 0, 25)

    # Walkability index (1-20, EPA scale)
    walkability = rng.normal(8.5, 3.5, n) - (adi_quintile - 1) * 0.8
    walkability = np.clip(walkability, 1, 20)

    # ── Compute outcome labels ─────────────────────────────────────────────
    df_temp = pd.DataFrame({
        "ckd_stage": ckd_stage,
        "diabetes": diabetes,
        "hypertension": hypertension,
        "adi_quintile": adi_quintile,
        "food_desert": food_desert,
        "egfr_slope": egfr_slope,
        "race_ethnicity": race,
    })

    prog_prob = compute_progression_probability(df_temp)

    # Normalize to target event rate
    scale_factor = EVENT_RATE / prog_prob.mean()
    prog_prob_scaled = np.clip(prog_prob * scale_factor, 0.02, 0.95)

    outcome = (rng.random(n) < prog_prob_scaled).astype(int)

    print(f"    Event rate: {outcome.mean():.3f} (target: {EVENT_RATE:.3f})")

    # ── Assemble dataframe ────────────────────────────────────────────────
    df = pd.DataFrame({
        "patient_id":            [f"{cohort_name}_{i:06d}" for i in range(n)],
        "cohort":                cohort_name,

        # Demographics
        "age":                   age,
        "sex":                   sex,
        "race_ethnicity":        race,
        "urbanicity":            urbanicity,

        # CKD baseline
        "ckd_stage":             ckd_stage,
        "egfr_baseline":         np.round(egfr_baseline, 1),
        "egfr_slope":            np.round(egfr_slope, 2),
        "uacr_baseline":         np.round(uacr, 1),
        "uacr_trend":            np.round(uacr_trend, 3),

        # Clinical
        "diabetes":              diabetes,
        "hypertension":          hypertension,
        "chf":                   chf,
        "hba1c":                 np.round(hba1c, 1),
        "hba1c_trend":           np.round(hba1c_trend, 2),
        "sbp":                   np.round(sbp, 0).astype(int),
        "dbp":                   np.round(dbp, 0).astype(int),
        "sbp_trend":             np.round(sbp_trend, 1),
        "bmi":                   np.round(bmi, 1),
        "charlson_index":        cci,

        # Medications
        "acei_arb":              acei_arb,
        "sglt2_inhibitor":       sglt2i,
        "glp1_receptor_agonist": glp1ra,
        "med_adherence_score":   np.round(med_adherence, 3),

        # Utilization
        "pcp_visit_gap_12mo":    pcp_visit_gap,
        "missed_nephro_referral":missed_nephro_referral,
        "ed_visits_past_year":   ed_visits_past_year,
        "insurance_uninsured":   insurance_uninsured,
        "insurance_medicaid":    insurance_medicaid,

        # SDOH
        "adi_quintile":          adi_quintile,
        "adi_nat_rank":          adi_nat_rank,
        "food_desert":           food_desert,
        "healthcare_shortage_area": healthcare_shortage,
        "poverty_rate_pct":      np.round(poverty_rate, 1),
        "median_household_income": np.round(median_income, 0).astype(int),
        "unemployment_rate_pct": np.round(unemployment_rate, 1),
        "no_hs_diploma_pct":     np.round(no_hs_diploma_pct, 1),
        "linguistic_isolation_pct": np.round(linguistic_isolation, 1),
        "walkability_index":     np.round(walkability, 1),

        # Outcome
        "progression_prob":      np.round(prog_prob_scaled, 4),
        "outcome_stage45_24mo":  outcome,
    })

    return df


# ── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("SDOH-CKDPred — Step 2: Generating Synthetic Cohorts")
    print("=" * 60)

    # Generate three independent cohorts
    df_train    = generate_cohort(N_TRAIN,    "train",        seed_offset=0)
    df_ext_val  = generate_cohort(N_EXTERNAL, "external_val", seed_offset=100)
    df_pilot    = generate_cohort(N_PILOT,    "pilot",        seed_offset=200)

    # Save to processed
    train_path   = os.path.join(PROC_DIR, "cohort_train.csv")
    extval_path  = os.path.join(PROC_DIR, "cohort_external_val.csv")
    pilot_path   = os.path.join(PROC_DIR, "cohort_pilot.csv")

    df_train.to_csv(train_path,  index=False)
    df_ext_val.to_csv(extval_path, index=False)
    df_pilot.to_csv(pilot_path,  index=False)

    print(f"\n  Saved training cohort    → {train_path}")
    print(f"  Saved external val       → {extval_path}")
    print(f"  Saved pilot cohort       → {pilot_path}")

    # Summary
    print("\nCohort Summary:")
    for name, df in [("Train", df_train), ("External Val", df_ext_val), ("Pilot", df_pilot)]:
        print(f"\n  {name} (N={len(df):,})")
        print(f"    Event rate:      {df['outcome_stage45_24mo'].mean():.3f}")
        print(f"    Mean age:        {df['age'].mean():.1f}")
        print(f"    Diabetes prev:   {df['diabetes'].mean():.3f}")
        print(f"    High ADI (Q5):   {(df['adi_quintile']==5).mean():.3f}")
        print(f"    Food desert:     {df['food_desert'].mean():.3f}")
        print(f"    African American:{(df['race_ethnicity']=='African_American').mean():.3f}")
        print(f"    Rural:           {(df['urbanicity']=='Rural').mean():.3f}")

    print("\n" + "=" * 60)
    print("Step 2 complete. Run step3_train_model.py next.")
    print("=" * 60)
