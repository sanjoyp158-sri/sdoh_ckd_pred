# ML Model Training Summary

## Model Created Successfully ✅

The XGBoost machine learning model has been trained and is now available in the system.

## Model Performance

### SDOH-CKDPred (Full Model with SDOH Features)
- **AUROC**: 0.7151 (External Validation)
- **Sensitivity**: 5.21%
- **Specificity**: 98.90%
- **PPV (Positive Predictive Value)**: 57.20%

### Clinical-Only Baseline Model
- **AUROC**: 0.7110 (External Validation)
- **Improvement with SDOH**: +0.0041 AUROC

## SHAP Feature Importance

The model's predictions are driven by three categories of features:

1. **Clinical Features**: 71.6% contribution
   - Top factor: eGFR baseline (22.3%)
   - Diabetes (12.3%)
   - UACR baseline (3.3%)

2. **SDOH Features**: 17.5% contribution
   - ADI quintile (4.2%)
   - Food desert status
   - Healthcare shortage area

3. **Utilization Features**: 10.9% contribution
   - Missed nephrology referrals (3.3%)
   - ED visits past year (2.7%)
   - PCP visit gap (2.5%)

## Training Details

- **Training Cohort**: 47,832 patients
- **External Validation**: 12,441 patients
- **Cross-Validation**: 5-fold stratified CV
- **Oversampling**: BorderlineSMOTE (within each fold)
- **Algorithm**: XGBoost Classifier

## Model Files Location

### Backend (for API use):
- `backend/models/registry/sdoh_ckdpred_final.json` - Main SDOH-augmented model
- `backend/models/registry/clinical_only_baseline.json` - Baseline model
- `backend/models/registry/feature_list.pkl` - Feature list for main model
- `backend/models/registry/baseline_feature_list.pkl` - Feature list for baseline

### Training Pipeline:
- `ckd_pipeline/models/sdoh_ckdpred_final.json` - Original trained model
- `ckd_pipeline/outputs/` - Training results, CV metrics, SHAP analysis

## Equity Analysis

Model performance across demographic subgroups:
- **White patients**: AUROC 0.6867, PPV 56.46%
- **Rural patients**: AUROC 0.7210, PPV 60.71%
- **Urban patients**: AUROC 0.7106, PPV 54.35%
- **High ADI (Q5)**: AUROC 0.5627, PPV 56.70%

Note: Performance varies across subgroups, with lower AUROC for African American and Hispanic/Latino patients, indicating potential areas for model improvement.

## How to Retrain the Model

If you need to retrain the model with new data:

```bash
cd ckd_pipeline
python step3_train_model.py
```

Then copy the models to the backend:

```bash
cp ckd_pipeline/models/sdoh_ckdpred_final.json backend/models/registry/
cp ckd_pipeline/models/feature_list.pkl backend/models/registry/
```

## Integration with Backend

The backend API (`backend/app/ml/xgboost_classifier.py`) loads these models automatically when making predictions. The models are used by:

- Risk stratification service
- SHAP explainer for feature importance
- ML analytics engine

## Next Steps

1. ✅ Model trained and saved
2. ✅ Model files copied to backend
3. ✅ All files committed and pushed to GitHub
4. Ready for production deployment

---

**Model Version**: v1.0.0  
**Training Date**: April 5, 2026  
**Repository**: https://github.com/sanjoyp158-sri/sdoh_ckd_pred.git
