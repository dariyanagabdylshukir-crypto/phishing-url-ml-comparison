# Task 3 methodology - completed rerun

The completed run uses 19,979 URLs after excluding 21 rows whose domains could not be validated, from the original 20,000-URL sample. There are 3,211 malicious and 16,768 benign URLs, grouped into 10,858 domains. Domain validation is a selection rule and may affect representativeness.

Four models and two feature sets are evaluated on ten GroupShuffleSplit partitions (seeds 42-51). Each partition holds out 30% of domain groups; the test URL fraction varies from 27.27% to 33.99%. Splits are not stratified. No registrable domain occurs in both training and test within a repeat. Private public-suffix rules are included using the offline snapshot bundled with tldextract 5.4.0. The same split is used across configurations. The seven features are predefined, without test-set feature selection.

Latency uses one URL per request at scheduled arrival rates of 50, 200 and 500 requests/s. Each configuration and rate has 20 warm-up and 1,000 evaluation calls per repeat: 240,000 evaluation calls in total. A single local worker extracts features and predicts labels; numerical libraries are limited to one thread. This is not an HTTP or network service benchmark. Model training and warm-up are excluded.

Latency is completion time minus intended arrival time, including scheduler lag, queueing and service time. Recorded service time includes feature extraction and prediction. Request submission rate and successful completion throughput are reported separately. The finite trials drain their queues after arrivals stop; they do not establish indefinitely sustainable capacity.

Quality summaries report mean and sample SD across repeats. Latency p50, p95 and p99 are computed within each repeat, then averaged across repeats. A reported mean p99 is not a pooled-request p99. Percentile bootstrap intervals resample the ten repeat-level statistics, using 2,000 resamples and seed 42. Repeats share observations: intervals describe variability conditional on this dataset and protocol, without a formal significance test.

Guardrails require mean malicious recall at least 0.80, worst repeat-level p99 at most 100 ms at the specified arrival rate, and recorded operational error rate zero. Operational errors are execution failures, not classification errors.

## Variables

| Type | Variables |
|---|---|
| Independent | Model, feature set, scheduled request rate |
| Dependent | Malicious-class F1, precision, recall, accuracy; latency p50/p95/p99, throughput and operational error rate |
| Controlled | Dataset, shared partition within each repeat, workload, fixed model settings, one worker, numerical thread limits and environment |

## Historical Task 2 plan

The original plan below is retained for traceability. Its phishing-specific hypotheses, proposed tests, timing definitions and smoke protocol do not describe the completed rerun. No formal hypothesis test was performed in the rerun.

---

# Methodology Passport Card - Task 2

**Title:** Comparative Evaluation of Machine Learning Models for Phishing URL Detection  
**Authors:** Dariyana Gabdylshukir and Zhanna Azatkyzy  
**Repository:** https://github.com/dariyanagabdylshukir-crypto/phishing-url-ml-comparison

## 1. Research type
Quantitative experimental research. Four machine learning algorithms are compared using numerical detection metrics and runtime measurements under matched experimental conditions.

## 2. Hypotheses
**RQ1 — Model choice:** H0: The evaluated algorithms do not differ significantly in phishing-class F1-score. H1: At least one algorithm differs significantly in phishing-class F1-score.

**RQ2a — Feature selection, quality:** H0: Full and selected feature sets do not differ significantly in phishing-class F1-score. H1: The feature sets differ significantly in phishing-class F1-score.

**RQ2b — Feature selection, efficiency:** H0: Full and selected feature sets do not differ significantly in inference time. H1: The feature sets differ significantly in inference time.

*(Revised in TASK 3: the former combined RQ2 hypothesis was split into two single-outcome hypotheses.)*

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

**Guardrails:** Maximum average inference latency of 100 ms/URL (preliminary engineering threshold). A target minimum phishing recall of 0.80 is proposed for the full experiment, to be validated before large-scale evaluation. **The Week 6 smoke-test configuration uses recall threshold 0.0 only to verify execution; it is not a meaningful safety threshold.** The 0.80 target is not asserted as a validated production standard. **TASK 3 update:** the full experiment (`configs/experiment.yaml`) applies the real recall guardrail of 0.80.

**Baseline:** Logistic Regression trained using the full 16-feature URL representation on the same split as other models.

## 5. Protocol and scope
The Week 6 executable benchmark runs four models, two feature sets and three fixed-seed repetitions, and writes CSV and JSON results. The 10-row synthetic sample verifies the pipeline only; it is not suitable for scientific conclusions or statistical hypothesis testing. The same split is used across model comparisons. For the full study, use a real labeled dataset, prevent duplicate and train-test leakage, select features on training data only, and apply paired statistical comparisons across adequately sized held-out or cross-validation folds. Record hardware, OS and dependency versions for the full experiment.
