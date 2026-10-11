# Comparative Evaluation of Machine Learning Models for Phishing URL Detection

**Authors:** Gabdylshukir Dariyana and Zhanna  
**Research type:** Quantitative experimental research  
**Repository:** https://github.com/dariyanagabdylshukir-crypto/phishing-url-ml-comparison

## Overview
This research compares Logistic Regression, Random Forest, Support Vector Machine (SVM),
and XGBoost for binary phishing URL detection. It investigates the effects of model choice
and feature selection on F1-score, other classification metrics, and computational efficiency.

**Research question:** How do ML algorithm choice and URL feature selection influence
phishing detection quality and inference time under the same evaluation conditions?

## Research questions
- RQ1: How does model choice affect accuracy, precision, recall and F1?
- RQ2: How does feature selection affect F1 and computational efficiency?
- RQ3: What trade-off exists between F1 and inference time across models?

## System requirements
Docker Desktop with Linux containers, or Python 3.11 and pip.
The Docker image is configured for Python 3.11.14 and exactly pinned direct Python packages.

## Quickstart (2 commands)
From the repository root:

```bash
docker build -t phishing-url-benchmark .
docker run --rm -v "${PWD}/outputs:/app/outputs" phishing-url-benchmark
```

On Windows PowerShell, `${PWD}` can be used for the bind-mount source.
Results are written to `outputs/benchmark_results.csv` and `outputs/run_metadata.json`.

## Alternative local run
```bash
python -m pip install -r requirements.txt
python src/benchmark.py --config configs/config.yaml
```

## Repository structure
```text
.
├── README.md
├── LICENSE
├── .gitignore
├── .dockerignore
├── Dockerfile
├── requirements.txt
├── configs/
│   └── config.yaml
├── src/
│   └── benchmark.py
├── data/
│   └── sample/
│       └── urls.csv
├── docs/
│   └── methodology.md
├── notebooks/
└── tests/
```

## Planned benchmark matrix
| Factor | Values | Measured outputs |
|---|---|---|
| Algorithm | Logistic Regression, Random Forest, SVM, XGBoost | Accuracy, precision, recall, F1 |
| Feature set | Full 16 URL features; selected 7 features | F1, training and inference time |
| Repetition | 3 fixed-seed runs | Metric variability |
| Comparison baseline | Logistic Regression with all 16 features | Difference in F1 and latency |

**Primary metric:** phishing-class F1-score (label 1).  
**Guardrails:** inference time <= 100 ms/URL, phishing recall threshold configurable;
the sample configuration sets minimum recall to 0.0 (no binding recall constraint).
These thresholds are preliminary engineering criteria, not validated production limits.

## Sample data and limitations
The 10-row dataset is **illustrative synthetic/safe test data**, used solely to
check execution. It does not establish real-world accuracy, statistical significance,
or model superiority. All results from this file are smoke-test results only.
For the actual study, select and document a real labeled dataset, its license,
deduplication, leakage prevention, stratified splitting, and test-set isolation.
The full-vs-selected feature subsets are fixed preliminary settings; research-grade
feature selection must be fit using training data only.
Use larger held-out data and repeated stratified cross-validation or independent
seeds before hypothesis testing; do not infer significance from the sample.

## Reproducibility
Configuration is stored in `configs/config.yaml`. Outputs include run metadata.
Use the same dataset, split, hardware and software versions for fair comparisons.
The container base image uses a fixed version tag; for long-term bitwise
reproducibility, lock its image digest and transitive dependency hashes as well.

## Citation / License
If referencing this repository, cite: Gabdylshukir Dariyana and Zhanna (2026),
*Comparative Evaluation of Machine Learning Models for Phishing URL Detection*,
GitHub repository.
Code licensed under MIT; see [LICENSE](LICENSE).
