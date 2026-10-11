# Comparative Evaluation of Machine Learning Models for Phishing URL Detection

**Authors:** Gabdylshukir Dariyana and Zhanna  
**Research type:** Quantitative experimental study  
**Repository:** https://github.com/dariyanagabdylshukir-crypto/phishing-url-ml-comparison

## Overview
This research compares Logistic Regression, Random Forest, Support Vector Machine (SVM) and XGBoost for binary phishing URL detection. It studies model choice, feature selection, F1-score and computational efficiency.

## Research Questions
- RQ1: How does the choice of algorithm affect accuracy, precision, recall and F1-score?
- RQ2: How does feature selection affect F1-score and computational efficiency?
- RQ3: What is the relationship between detection quality and inference time across models?

## System Requirements
Docker Desktop with Linux containers, or Python 3.11 with pip. Docker uses Python 3.11.14. Direct dependencies have exact version pins in `requirements.txt`.

## Quickstart (2 commands)
Run from the repository root in Windows PowerShell:

```powershell
docker build -t phishing-url-benchmark .
docker run --rm -v "${PWD}/outputs:/app/outputs" phishing-url-benchmark
```

Outputs: `outputs/benchmark_results.csv` and `outputs/run_metadata.json`.

## Repository Structure
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
└── docs/
    └── methodology.md
```

## Planned Benchmark Matrix
| Factor | Values | Output |
|---|---|---|
| Model | Logistic Regression, Random Forest, SVM, XGBoost | Accuracy, precision, recall, F1 |
| Feature set | Full 16 features, selected 7 features | F1, training time, inference latency |
| Repetitions | 3 fixed-seed runs | Variation in measured outputs |
| Baseline | Logistic Regression with full features | F1 and latency differences |

## Metrics and Baseline
**Primary metric:** Phishing-class F1-score (positive label = 1).  
**Secondary metrics:** Accuracy, precision, recall, training time (ms), inference time (ms/URL).  
**Guardrails:** Preliminary average inference latency <= 100 ms/URL. Proposed minimum phishing recall for the later full-scale study: 0.80, subject to validation. The Week 6 configuration uses recall threshold 0.0 for smoke testing only; it is not a meaningful safety constraint.  
**Baseline:** Logistic Regression with all 16 URL features under the same train/test split.

## Smoke Test vs Research Results
The 10-row URL sample is illustrative and used solely to verify that the code executes and saves results. The resulting scores, including perfect F1 or zero F1, are **not scientific evidence** about model performance. Larger real datasets, leakage prevention, training-only feature selection and suitable statistical tests are required in later research stages.

## Reproducibility
The experiment parameters are in `configs/config.yaml`. Use the same dataset, split, preprocessing, OS/container, hardware and library versions for fair comparison. The container successfully built and the script produced 24 benchmark records during the local Week 6 smoke test. Exact pins cover listed direct dependencies; complete transitive lockfiles/image digests would be needed for stronger long-term reproducibility.

## Citation and License
Gabdylshukir Dariyana and Zhanna (2026). *Comparative Evaluation of Machine Learning Models for Phishing URL Detection*. GitHub repository.  
MIT License — see [LICENSE](LICENSE).
