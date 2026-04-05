#!/bin/bash
# Script to verify ML models are present in the repository

echo "========================================="
echo "ML Model Verification Script"
echo "========================================="
echo ""

echo "Checking for model files..."
echo ""

# Check ckd_pipeline models
echo "1. CKD Pipeline Models:"
if [ -f "ckd_pipeline/models/sdoh_ckdpred_final.json" ]; then
    size=$(ls -lh ckd_pipeline/models/sdoh_ckdpred_final.json | awk '{print $5}')
    echo "   ✓ sdoh_ckdpred_final.json ($size)"
else
    echo "   ✗ sdoh_ckdpred_final.json NOT FOUND"
fi

if [ -f "ckd_pipeline/models/clinical_only_baseline.json" ]; then
    size=$(ls -lh ckd_pipeline/models/clinical_only_baseline.json | awk '{print $5}')
    echo "   ✓ clinical_only_baseline.json ($size)"
else
    echo "   ✗ clinical_only_baseline.json NOT FOUND"
fi

if [ -f "ckd_pipeline/models/feature_list.pkl" ]; then
    size=$(ls -lh ckd_pipeline/models/feature_list.pkl | awk '{print $5}')
    echo "   ✓ feature_list.pkl ($size)"
else
    echo "   ✗ feature_list.pkl NOT FOUND"
fi

echo ""

# Check backend models
echo "2. Backend Models (for API):"
if [ -f "backend/models/registry/sdoh_ckdpred_final.json" ]; then
    size=$(ls -lh backend/models/registry/sdoh_ckdpred_final.json | awk '{print $5}')
    echo "   ✓ sdoh_ckdpred_final.json ($size)"
else
    echo "   ✗ sdoh_ckdpred_final.json NOT FOUND"
fi

if [ -f "backend/models/registry/clinical_only_baseline.json" ]; then
    size=$(ls -lh backend/models/registry/clinical_only_baseline.json | awk '{print $5}')
    echo "   ✓ clinical_only_baseline.json ($size)"
else
    echo "   ✗ clinical_only_baseline.json NOT FOUND"
fi

echo ""

# Check training outputs
echo "3. Training Results:"
if [ -f "ckd_pipeline/outputs/model_performance_summary.csv" ]; then
    echo "   ✓ model_performance_summary.csv"
else
    echo "   ✗ model_performance_summary.csv NOT FOUND"
fi

if [ -f "ckd_pipeline/outputs/shap_feature_importance.csv" ]; then
    echo "   ✓ shap_feature_importance.csv"
else
    echo "   ✗ shap_feature_importance.csv NOT FOUND"
fi

if [ -f "ckd_pipeline/outputs/equity_analysis.csv" ]; then
    echo "   ✓ equity_analysis.csv"
else
    echo "   ✗ equity_analysis.csv NOT FOUND"
fi

echo ""
echo "========================================="
echo "Verification Complete"
echo "========================================="
echo ""
echo "To view model performance:"
echo "  cat ckd_pipeline/outputs/model_performance_summary.csv"
echo ""
echo "To view feature importance:"
echo "  cat ckd_pipeline/outputs/shap_feature_importance.csv"
echo ""
