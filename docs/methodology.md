# Methodology Passport Card

**Title:** Comparative Evaluation of Machine Learning Models for Phishing URL Detection  
**Authors:** Gabdylshukir Dariyana and Zhanna  
**GitHub:** https://github.com/dariyanagabdylshukir-crypto/phishing-url-ml-comparison

## Research type
Quantitative experimental study: controlled model comparisons use numerical
classification and runtime measurements.

## Hypotheses (based on Task 1)
**RQ1** H0: Evaluated algorithms do not differ significantly in phishing-class F1-score.
H1: At least one evaluated algorithm differs significantly in phishing-class F1-score.

**RQ2** H0: Feature selection does not significantly change phishing-class F1-score
or inference time. H1: Feature selection significantly changes F1-score and/or inference time.

**RQ3** H0: Evaluated algorithms do not differ significantly in the joint
F1-score/inference-time trade-off. H1: At least one algorithm has a significantly
different F1-score/inference-time trade-off.

## Variable matrix
| Category | Variables |
|---|---|
| Independent | Model (Logistic Regression, Random Forest, SVM, XGBoost); feature set (full vs selected) |
| Dependent | Accuracy, precision, recall, phishing F1; training time (ms); inference time (ms/URL) |
| Controlled | Identical dataset and labels, stratified split, preprocessing, random seeds, evaluation protocol, fixed hardware/OS/library versions |

## Metrics and baseline
**Primary:** phishing-class F1-score; balances precision and recall.
**Secondary:** accuracy, precision, recall, training time, inference time (ms/URL).
**Guardrails:** inference time <= 100 ms/URL and minimum phishing recall set before
the full experiment (the smoke-test default is 0.0 and is not a meaningful recall bound).
**Baseline:** Logistic Regression trained with the full URL feature set using the same split.
**Experimental plan:** compare four models and two feature sets, with repeated runs.
For the full study, use adequate held-out data and appropriate paired statistical tests
with correction for multiple comparisons where needed.

## Week 6 implementation status
The pipeline runs on 10 illustrative URLs and produces CSV and JSON outputs.
These smoke-test results are not scientific findings. The real dataset, validated
feature-selection strategy, statistical testing and full-scale experiments remain future work.
