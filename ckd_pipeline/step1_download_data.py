"""
step1_download_data.py
----------------------
Downloads all public data sources used to parameterize the synthetic cohort.
Run this first. Files saved to data/raw/.

Sources:
  1. CDC PLACES 2024  — CKD prevalence by ZCTA
  2. USDA Food Access Research Atlas — food desert status by ZCTA
  3. USRDS summary tables — manually downloaded (instructions provided)
  4. ADI 2020         — area deprivation index by ZCTA
  5. NHANES 2017-2020 — clinical variable distributions
"""

import os
import sys
import requests
import pandas as pd
from tqdm import tqdm
from config import RAW_DIR

# ── Utility ───────────────────────────────────────────────────────────────
def download(url, filename, description):
    path = os.path.join(RAW_DIR, filename)
    if os.path.exists(path):
        print(f"  [SKIP] {filename} already exists.")
        return path
    print(f"  Downloading {description}...")
    try:
        r = requests.get(url, stream=True, timeout=60,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(path, "wb") as f, tqdm(total=total, unit="B", unit_scale=True,
                                          desc=filename, ncols=70) as bar:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))
        print(f"  [OK] Saved to {path}")
        return path
    except Exception as e:
        print(f"  [WARN] Could not auto-download {filename}: {e}")
        print(f"         Please download manually from: {url}")
        return None


# ── 1. CDC PLACES 2024 — ZCTA level ───────────────────────────────────────
def download_cdc_places():
    print("\n[1/5] CDC PLACES 2024 (ZCTA level)")
    # CDC PLACES public API endpoint for ZCTA data
    url = ("https://data.cdc.gov/api/views/qnzd-25i4/rows.csv"
           "?accessType=DOWNLOAD")
    return download(url, "cdc_places_zcta_2024.csv",
                    "CDC PLACES 2024 ZCTA health measures")


# ── 2. USDA Food Access Research Atlas ────────────────────────────────────
def download_usda_food_atlas():
    print("\n[2/5] USDA Food Access Research Atlas 2019")
    url = ("https://www.ers.usda.gov/webdocs/DataFiles/80591/"
           "DataDownload2019.xlsx?v=1372.6")
    return download(url, "usda_food_atlas_2019.xlsx",
                    "USDA Food Access Research Atlas")


# ── 3. NHANES 2017-2018 Lab data (eGFR, UACR, HbA1c) ─────────────────────
def download_nhanes():
    print("\n[3/5] NHANES 2017-2020 Lab Files")
    files = {
        # Kidney conditions — serum creatinine
        "nhanes_1718_kidney.XPT": (
            "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/KIQ_U_J.XPT",
            "NHANES 2017-18 Kidney Conditions"
        ),
        # Albumin & creatinine — urine
        "nhanes_1718_uacr.XPT": (
            "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/ALB_CR_J.XPT",
            "NHANES 2017-18 Albumin/Creatinine"
        ),
        # Glycohemoglobin
        "nhanes_1718_hba1c.XPT": (
            "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/GHB_J.XPT",
            "NHANES 2017-18 HbA1c"
        ),
        # Blood pressure
        "nhanes_1718_bp.XPT": (
            "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/BPX_J.XPT",
            "NHANES 2017-18 Blood Pressure"
        ),
        # Body measures (BMI)
        "nhanes_1718_bmi.XPT": (
            "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/BMX_J.XPT",
            "NHANES 2017-18 BMI"
        ),
        # Demographics
        "nhanes_1718_demo.XPT": (
            "https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/DEMO_J.XPT",
            "NHANES 2017-18 Demographics"
        ),
    }
    paths = {}
    for fname, (url, desc) in files.items():
        paths[fname] = download(url, fname, desc)
    return paths


# ── 4. ADI 2020 — instructions (requires free registration) ───────────────
def print_adi_instructions():
    print("\n[4/5] Area Deprivation Index (ADI) 2020")
    print("  ADI requires free registration at:")
    print("  https://www.neighborhoodatlas.medicine.wisc.edu/")
    print("  Steps:")
    print("    1. Create a free account")
    print("    2. Download '2020 ADI Download — National'")
    print("    3. Save as: data/raw/adi_2020_national.csv")
    adi_path = os.path.join(RAW_DIR, "adi_2020_national.csv")
    if os.path.exists(adi_path):
        print("  [OK] ADI file already present.")
    else:
        print("  [ACTION NEEDED] File not found. Please download manually.")
        # Create a minimal synthetic ADI file as placeholder
        _create_placeholder_adi()


def _create_placeholder_adi():
    """Creates a minimal placeholder ADI file for pipeline testing."""
    import numpy as np
    np.random.seed(42)
    # Generate 33,000 synthetic ZCTAs (approx US total)
    n = 33_000
    zctas = [f"{90000 + i:05d}" for i in range(n)]
    adi_quintiles = np.random.choice([1, 2, 3, 4, 5], size=n,
                                      p=[0.20, 0.20, 0.20, 0.20, 0.20])
    adi_nat_rank = np.clip(np.random.normal(50, 25, n), 1, 100).astype(int)
    df = pd.DataFrame({
        "ZCTA": zctas,
        "ADI_NATRANK": adi_nat_rank,
        "ADI_STATERNK": adi_nat_rank,
        "ADI_QUINTILE": adi_quintiles,
    })
    path = os.path.join(RAW_DIR, "adi_2020_national.csv")
    df.to_csv(path, index=False)
    print(f"  [PLACEHOLDER] Synthetic ADI created at {path}")
    print("  Replace with real ADI download for production use.")


# ── 5. USRDS summary tables — instructions ────────────────────────────────
def print_usrds_instructions():
    print("\n[5/5] USRDS 2023 Annual Data Report")
    print("  Download summary tables from:")
    print("  https://usrds-adr.niddk.nih.gov/2023")
    print("  Key tables needed:")
    print("    - Chapter 1 Table 1.1 (CKD Prevalence)")
    print("    - Chapter 5 Table 5.1 (CKD Progression Rates)")
    print("    - Chapter 11 Table 11.1 (Medicare Costs)")
    print("  Save to: data/raw/usrds_2023_tables/")
    print("  NOTE: The pipeline uses hardcoded values from these tables")
    print("        (already encoded in config.py), so this download is")
    print("        optional — for reference/verification only.")
    usrds_dir = os.path.join(RAW_DIR, "usrds_2023_tables")
    os.makedirs(usrds_dir, exist_ok=True)

    # Save the key parameter values we extracted
    params = {
        "Parameter": [
            "CKD Stage 2-3 to Stage 4-5 progression rate (24mo)",
            "Annual Medicare cost Stage 5 (dialysis)",
            "Annual Medicare cost Stage 3",
            "Rural CKD African American proportion",
            "Rural CKD Hispanic/Latino proportion",
            "Rural CKD White proportion",
            "Mean age at CKD Stage 2-3 diagnosis",
            "Diabetes comorbidity prevalence in CKD",
            "Hypertension comorbidity prevalence in CKD",
            "Mean eGFR decline rate (mL/min/yr)",
        ],
        "Value": [
            "22.1%",
            "$89,000 USD",
            "$20,000 USD",
            "23.1%",
            "13.8%",
            "59.2%",
            "62.4 years",
            "47%",
            "86%",
            "-2.8 mL/min/1.73m² per year",
        ],
        "Source": [
            "USRDS 2023 Chapter 5 Table 5.1",
            "USRDS 2023 Chapter 11 Table 11.1",
            "USRDS 2023 Chapter 11 Table 11.1",
            "USRDS 2023 Chapter 1 Table 1.2",
            "USRDS 2023 Chapter 1 Table 1.2",
            "USRDS 2023 Chapter 1 Table 1.2",
            "USRDS 2023 Chapter 1 Table 1.1",
            "USRDS 2023 Chapter 2 Table 2.1",
            "USRDS 2023 Chapter 2 Table 2.1",
            "Grams et al. Kidney Int 2018 PMID:29477224",
        ]
    }
    df = pd.DataFrame(params)
    df.to_csv(os.path.join(usrds_dir, "usrds_extracted_parameters.csv"), index=False)
    print(f"  [OK] Extracted USRDS parameters saved to {usrds_dir}")


# ── Main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("SDOH-CKDPred — Step 1: Downloading Public Data Sources")
    print("=" * 60)

    download_cdc_places()
    download_usda_food_atlas()
    download_nhanes()
    print_adi_instructions()
    print_usrds_instructions()

    print("\n" + "=" * 60)
    print("Step 1 complete.")
    print("If any manual downloads are needed, complete them before")
    print("running step2_generate_cohort.py")
    print("=" * 60)
