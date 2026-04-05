# SDOH-CKDPred: Data Pipeline & Model Training
## AI-Enabled Early Detection of CKD in Underserved Communities

This repository contains the full reproducible pipeline for the simulation study
described in the JMIR AI manuscript. No real patient data is used at any point.

## Project Structure

```
ckd_pipeline/
├── README.md
├── requirements.txt
├── config.py                  # All parameters in one place
├── step1_download_data.py     # Download all public datasets
├── step2_generate_cohort.py   # Build synthetic patient cohort
├── step3_train_model.py       # Train XGBoost + SHAP
├── step4_evaluate.py          # Performance metrics + equity analysis
├── step5_simulate_pilot.py    # Pilot deployment simulation
├── step6_generate_figures.py  # Reproduce all 5 paper figures
├── data/
│   ├── raw/                   # Downloaded source files
│   └── processed/             # Cleaned merged datasets
├── models/                    # Saved model files
├── outputs/                   # Results tables (CSV)
└── figures/                   # Publication figures (PNG)
```

## Data Sources (all free, publicly available)

| Source | URL | Used For |
|--------|-----|----------|
| USRDS 2023 | https://usrds-adr.niddk.nih.gov/2023 | Progression rates, costs, demographics |
| CDC PLACES 2024 | https://www.cdc.gov/places | CKD prevalence by ZCTA |
| Area Deprivation Index | https://neighborhoodatlas.medicine.wisc.edu | ADI quintiles |
| USDA Food Atlas | https://www.ers.usda.gov/data-products/food-access-research-atlas | Food desert status |
| US Census ACS | https://data.census.gov | Income, poverty, education |
| NHANES 2017-2020 | https://www.cdc.gov/nchs/nhanes | Clinical variable distributions |

## How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download all public data
python step1_download_data.py

# 3. Generate synthetic cohort
python step2_generate_cohort.py

# 4. Train model
python step3_train_model.py

# 5. Evaluate performance
python step4_evaluate.py

# 6. Run pilot simulation
python step5_simulate_pilot.py

# 7. Generate figures
python step6_generate_figures.py
```

## Citation
If you use this pipeline, please cite the USRDS, CDC PLACES, ADI, USDA, and
Census ACS datasets as described in the manuscript references.
