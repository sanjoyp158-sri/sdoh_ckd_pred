"""
step5_simulate_pilot.py
-----------------------
Simulates the 12-month pilot deployment on the synthetic pilot cohort.
Projects clinical outcomes and cost-effectiveness.

Outputs:
  outputs/table4_pilot_outcomes.csv
  outputs/cost_effectiveness_results.csv
"""

import os
import numpy as np
import pandas as pd
import joblib
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
from config import *

np.random.seed(SEED)


def preprocess(df):
    d = df.copy()
    le = LabelEncoder()
    d["sex_encoded"] = le.fit_transform(d["sex"])
    d["egfr_x_adi"] = d["egfr_baseline"] * d["adi_nat_rank"]
    d["uacr_x_food_desert"] = d["uacr_baseline"] * d["food_desert"]
    return d


def simulate_intervention_outcomes(df_pilot, model, features):
    """
    Apply the model to the pilot cohort and project 12-month outcomes
    by applying published intervention effect sizes to the high-risk group.

    Published effect sizes used:
    - Early detection improvement:   +32 pp (Ravizza et al 2019)
    - Nephrology referral improvement: +28 pp (Lee et al 2023)
    - Stage 5 progression reduction:  -31.9% relative (Tangri et al 2011)
    - Telehealth utilization increase: +39 pp (post-2022 rural benchmarks)
    """
    df = preprocess(df_pilot)
    X = df[features].values
    probs = model.predict_proba(X)[:, 1]
    df["risk_score"]  = probs
    df["high_risk"]   = (probs >= RISK_THRESHOLD).astype(int)

    n_total    = len(df)
    n_highrisk = df["high_risk"].sum()
    n_outreach = int(n_highrisk * 0.941)  # 94.1% outreach completion

    print(f"\n  Pilot cohort: N={n_total:,}")
    print(f"  High-risk identified (score >{RISK_THRESHOLD}): {n_highrisk:,} ({n_highrisk/n_total*100:.1f}%)")
    print(f"  Outreach triggered: {n_outreach:,} ({n_outreach/n_highrisk*100:.1f}% of high-risk)")

    # Stage 3 subgroup — used for progression outcome
    stage3_mask = df["ckd_stage"].isin(["Stage_3a", "Stage_3b"])
    n_stage3    = stage3_mask.sum()
    print(f"  Stage 3 subgroup: N={n_stage3:,}")

    # ── Baseline rates (USRDS 2023 usual care) ───────────────────────────
    baseline = {
        "early_detection_rate":   0.41,
        "nephro_referral_rate":   0.52,
        "followup_lab_rate":      0.63,
        "telehealth_rate":        0.08,
        "bp_control_rate":        0.58,
        "stage5_progression_rate":0.182,
    }

    # ── Projected post-deployment rates ───────────────────────────────────
    # Effect sizes from published comparable programs
    projected = {
        "early_detection_rate":    baseline["early_detection_rate"]   + 0.32,
        "nephro_referral_rate":    baseline["nephro_referral_rate"]   + 0.28,
        "followup_lab_rate":       baseline["followup_lab_rate"]      + 0.26,
        "telehealth_rate":         baseline["telehealth_rate"]        + 0.39,
        "bp_control_rate":         baseline["bp_control_rate"]        + 0.13,
        "stage5_progression_rate": baseline["stage5_progression_rate"] * (1 - 0.319),
    }

    # ── Absolute counts ───────────────────────────────────────────────────
    results = []
    labels = {
        "early_detection_rate":    "Early Detection Rate",
        "nephro_referral_rate":    "Nephrology Referral Rate",
        "followup_lab_rate":       "Follow-up Lab Testing Rate",
        "telehealth_rate":         "Telehealth Utilization",
        "bp_control_rate":         "BP Control (<130/80 mmHg)",
        "stage5_progression_rate": "Stage 5 Progression Rate",
    }

    for key, label in labels.items():
        b = baseline[key]
        p = projected[key]
        b_count = int(b * n_stage3)
        p_count = int(p * n_stage3)
        change  = p - b
        change_str = f"+{change*100:.0f} pp" if change > 0 else f"{change*100:.1f} pp"
        if key == "stage5_progression_rate":
            change_str = f"-{abs(change)*100:.1f} pp / -{abs(change)/b*100:.1f}% relative"

        results.append({
            "Outcome Measure":          label,
            "Simulated Baseline":       f"{b*100:.1f}% ({b_count}/{n_stage3})",
            "Projected Post-Deployment":f"{p*100:.1f}% ({p_count}/{n_stage3})",
            "Projected Change":         change_str,
        })

    table4 = pd.DataFrame(results)
    print("\n  Table 4: Projected 12-Month Pilot Outcomes")
    print(table4.to_string(index=False))

    # Patients avoiding Stage 5
    prog_baseline  = int(baseline["stage5_progression_rate"] * n_stage3)
    prog_projected = int(projected["stage5_progression_rate"] * n_stage3)
    patients_averted = prog_baseline - prog_projected
    print(f"\n  Projected patients avoiding Stage 5: {patients_averted}")

    return table4, patients_averted, n_stage3, df


def cost_effectiveness_analysis(patients_averted):
    """
    Payer-perspective cost-effectiveness from Medicare reimbursement data.
    Source: USRDS 2023 Annual Data Report Chapter 11.
    """
    print("\n  Cost-Effectiveness Analysis")
    print("  " + "-" * 40)

    cost_offset = patients_averted * (COST_STAGE5_PER_YEAR - COST_STAGE3_PER_YEAR)
    bcr = cost_offset / ANNUAL_OPERATING_COST

    print(f"  Patients averted from Stage 5:     {patients_averted}")
    print(f"  Annual cost offset (Medicare):     ${cost_offset:,.0f}")
    print(f"  Annual operating cost:             ${ANNUAL_OPERATING_COST:,.0f}")
    print(f"  Benefit-Cost Ratio (BCR):          {bcr:.2f}:1")

    # Sensitivity analysis
    print("\n  Sensitivity Analysis (USRDS cost range):")
    sensitivity_rows = []
    for stage5_cost in range(75_000, 110_000, 5_000):
        offset = patients_averted * (stage5_cost - COST_STAGE3_PER_YEAR)
        bcr_s  = offset / ANNUAL_OPERATING_COST
        print(f"    Stage 5 cost = ${stage5_cost:,}: BCR = {bcr_s:.2f}:1")
        sensitivity_rows.append({
            "stage5_annual_cost_usd": stage5_cost,
            "cost_offset_usd":        offset,
            "operating_cost_usd":     ANNUAL_OPERATING_COST,
            "bcr":                    round(bcr_s, 3),
        })

    results = {
        "patients_averted":     patients_averted,
        "cost_per_patient_differential": COST_STAGE5_PER_YEAR - COST_STAGE3_PER_YEAR,
        "annual_cost_offset_usd": cost_offset,
        "annual_operating_cost_usd": ANNUAL_OPERATING_COST,
        "bcr":                  round(bcr, 3),
    }

    return results, pd.DataFrame(sensitivity_rows)


# ── Main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("SDOH-CKDPred — Step 5: Pilot Simulation")
    print("=" * 60)

    df_pilot  = pd.read_csv(os.path.join(PROC_DIR, "cohort_pilot.csv"))
    all_feats = joblib.load(os.path.join(MODEL_DIR, "feature_list.pkl"))

    model = xgb.XGBClassifier()
    model.load_model(os.path.join(MODEL_DIR, "sdoh_ckdpred_final.json"))

    table4, patients_averted, n_stage3, df_scored = simulate_intervention_outcomes(
        df_pilot, model, all_feats
    )

    ce_results, sensitivity_df = cost_effectiveness_analysis(patients_averted)

    # Save
    table4.to_csv(os.path.join(OUTPUT_DIR, "table4_pilot_outcomes.csv"), index=False)
    sensitivity_df.to_csv(os.path.join(OUTPUT_DIR, "cost_effectiveness_sensitivity.csv"), index=False)
    pd.DataFrame([ce_results]).to_csv(
        os.path.join(OUTPUT_DIR, "cost_effectiveness_main.csv"), index=False
    )
    df_scored[["patient_id","risk_score","high_risk","ckd_stage","adi_quintile"]].to_csv(
        os.path.join(OUTPUT_DIR, "pilot_risk_scores.csv"), index=False
    )

    print("\n" + "=" * 60)
    print("Step 5 complete. Run step6_generate_figures.py next.")
    print("=" * 60)
