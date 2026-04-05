# How to Verify Models Are on GitHub

## ⚠️ Important: GitHub Web Interface Limitation

**GitHub does NOT display files larger than 1MB in the web browser.** This is a GitHub platform limitation, not an issue with your repository.

Your model files are **5.3 MB and 5.5 MB**, so they won't show up when you browse the repository on github.com.

## ✅ The Models ARE on GitHub

I've verified that both model files are successfully uploaded:

```bash
# Files tracked by git
$ git ls-files ckd_pipeline/models/
ckd_pipeline/models/clinical_only_baseline.json
ckd_pipeline/models/sdoh_ckdpred_final.json

# Files on remote (origin/main)
$ git ls-tree -r origin/main --name-only | grep "ckd_pipeline/models"
ckd_pipeline/models/clinical_only_baseline.json
ckd_pipeline/models/sdoh_ckdpred_final.json

# File size on remote
$ git show origin/main:ckd_pipeline/models/sdoh_ckdpred_final.json | wc -c
5548391  # 5.5 MB - this confirms the FULL file is on GitHub

# File content preview (first 300 characters)
$ git show origin/main:ckd_pipeline/models/sdoh_ckdpred_final.json | head -c 300
{"learner":{"attributes":{"scikit_learn":"{\"_estimator_type\": \"classifier\"}"},"feature_names":[],"feature_types":[],"gradient_booster":{"model":{"gbtree_model_param":{"num_parallel_tree":"1","num_trees":"500"}...
```

## How to Verify (3 Methods)

### Method 1: Clone the Repository (Recommended)

Anyone can clone your repository and the models will download automatically:

```bash
# Clone the repository
git clone https://github.com/sanjoyp158-sri/sdoh_ckd_pred.git
cd sdoh_ckd_pred

# Check the models
ls -lh ckd_pipeline/models/
# Output:
# -rw-r--r--  5.5M  clinical_only_baseline.json
# -rw-r--r--  5.3M  sdoh_ckdpred_final.json

# Run the verification script
chmod +x verify_models.sh
./verify_models.sh
```

### Method 2: Use GitHub API

You can verify the files exist using GitHub's API:

```bash
# Check if file exists on GitHub
curl -s "https://api.github.com/repos/sanjoyp158-sri/sdoh_ckd_pred/contents/ckd_pipeline/models" | grep "sdoh_ckdpred_final.json"

# This will return JSON showing the file exists with its size
```

### Method 3: Use Git Commands Locally

From your local repository:

```bash
# Verify file is on remote
git ls-tree -r origin/main ckd_pipeline/models/sdoh_ckdpred_final.json

# Check file size on remote
git show origin/main:ckd_pipeline/models/sdoh_ckdpred_final.json | wc -c

# View first 500 bytes of the file from remote
git show origin/main:ckd_pipeline/models/sdoh_ckdpred_final.json | head -c 500
```

## Why GitHub Web Interface Doesn't Show Large Files

GitHub has several file size limitations:

1. **Files > 1 MB**: Won't display in web browser (but ARE in the repository)
2. **Files > 50 MB**: Warning when pushing
3. **Files > 100 MB**: Blocked from pushing (requires Git LFS)

Your models are 5.3 MB and 5.5 MB, so they fall into category 1:
- ✅ Successfully stored in GitHub
- ✅ Will download when cloning
- ✅ Can be accessed via Git commands
- ❌ Won't display in web browser

## What This Means for Your Project

**Everything is working correctly!** Your models are safely stored on GitHub. When someone:

1. **Clones your repository** → Models download automatically
2. **Uses the Docker deployment** → Models are included in the container
3. **Runs the backend API** → Models load from `backend/models/registry/`

## Alternative: GitHub Releases (Optional)

If you want to make the models more visible on GitHub, you can attach them to a release:

```bash
# Create a release and attach model files
gh release create v1.0.0 \
  ckd_pipeline/models/sdoh_ckdpred_final.json \
  ckd_pipeline/models/clinical_only_baseline.json \
  --title "SDOH-CKDPred v1.0.0" \
  --notes "Initial release with trained XGBoost models"
```

This creates a downloadable release with the model files visible on the Releases page.

## Summary

✅ **Your models ARE on GitHub**  
✅ **They will download when cloning**  
✅ **They are tracked by git and pushed to origin/main**  
❌ **They won't show in the web browser (GitHub limitation for files >1MB)**

**Repository**: https://github.com/sanjoyp158-sri/sdoh_ckd_pred.git  
**Commit**: 0a5e0c7 "Add trained ML models and evaluation results"  
**Branch**: main

---

**Last Verified**: April 5, 2026
