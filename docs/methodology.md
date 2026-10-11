# Methodology Passport Card — Task 2

**Title:** Comparative Evaluation of Machine Learning Models for Phishing URL Detection  
**Authors:** Gabdylshukir Dariyana and Zhanna  
**Repository:** https://github.com/dariyanagabdylshukir-crypto/phishing-url-ml-comparison

## 1. Research type
Quantitative experimental research. Four machine learning algorithms are compared using numerical detection metrics and runtime measurements under matched experimental conditions.

## 2. Hypotheses
**RQ1 — Model choice:** H0: The evaluated algorithms do not differ significantly in phishing-class F1-score. H1: At least one algorithm differs significantly in phishing-class F1-score.

**RQ2 — Feature selection:** H0: Full and selected feature sets do not differ significantly in phishing-class F1-score or inference time. H1: The feature sets differ significantly in F1-score and/or inference time.

**RQ3 — Performance-efficiency comparison:** H0: There is no statistically significant difference between algorithms in inference time when compared under the same experimental conditions. H1: At least one algorithm has significantly different inference time. F1-score is reported alongside inference time to describe the performance-efficiency trade-off; no separate significance claim is made about a composite trade-off score.

## 3. Variable matrix
| Type | Variables |
|---|---|
| Independent | Algorithm: Logistic Regression, Random Forest, SVM, XGBoost; feature set: full (16 URL features) or selected (7 URL features). |
| Dependent | Phishing-class F1-score, accuracy, precision, recall, training time (ms), inference latency (ms/URL). |
| Controlled | Same labeled dataset, train/test split, preprocessing, evaluation protocol, seed, fixed software versions, OS/container environment and hardware during comparisons. |

## 4. Metrics and baseline
**Primary metric:** Phishing-class F1-score (positive label = 1). It balances precision and recall.

**Secondary metrics:** Accuracy, precision, recall, training time in milliseconds and inference time in milliseconds per URL.

**Guardrails:** Maximum average inference latency of 100 ms/URL (preliminary engineering threshold). A target minimum phishing recall of 0.80 is proposed for the full experiment, to be validated before large-scale evaluation. **The Week 6 smoke-test configuration uses recall threshold 0.0 only to verify execution; it is not a meaningful safety threshold.** The 0.80 target is not asserted as a validated production standard.

**Baseline:** Logistic Regression trained using the full 16-feature URL representation on the same split as other models.

## 5. Protocol and scope
The Week 6 executable benchmark runs four models, two feature sets and three fixed-seed repetitions, and writes CSV and JSON results. The 10-row synthetic sample verifies the pipeline only; it is not suitable for scientific conclusions or statistical hypothesis testing. The same split is used across model comparisons. For the full study, use a real labeled dataset, prevent duplicate and train-test leakage, select features on training data only, and apply paired statistical comparisons across adequately sized held-out or cross-validation folds. Record hardware, OS and dependency versions for the full experiment.
