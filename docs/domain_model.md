# Domain Model (ML track)

## 1. Task

The broader research topic is phishing detection. However, the current dataset labels URLs as malicious or benign and does not provide a separate phishing label.

Each URL has a label: y = 1 for malicious and y = 0 for benign. These results therefore measure malicious-URL classification, not phishing-specific detection performance.

We extract 16 lexical URL features, such as length, number of dots and digits, and the presence of words like `login`. We compare the full feature vector with a selected seven-feature vector.

Each model returns a class label through its `predict` method. Logistic Regression, Random Forest and XGBoost use probability-based class decisions. The SVM uses its decision function; probability estimation is disabled. We do not apply a common probability threshold to all four models.

## 2. Loss function

The Logistic Regression baseline minimises binary log-loss with L2 regularisation:

$$
L_{\mathrm{data}} =
-\frac{1}{n}\sum_{i=1}^{n}
\left[y_i\log p_i+(1-y_i)\log(1-p_i)\right]
$$

Here, p_i is the estimated probability that URL i is malicious. Confident incorrect predictions receive a larger loss. The training objective also penalises the size of the model weights.

SVM uses a regularised margin-based objective with hinge loss. Random Forest selects tree splits using Gini impurity. XGBoost uses a binary logistic objective with regularisation on the trees.

## 3. Metrics

The positive class is malicious (y = 1).

$$
Precision = \frac{TP}{TP+FP}
\qquad
Recall = \frac{TP}{TP+FN}
\qquad
F_1 = \frac{2TP}{2TP+FP+FN}
$$

- Recall: the proportion of malicious URLs correctly detected.
- Precision: the proportion of predicted malicious URLs that are actually malicious.
- F1-score: the harmonic mean of precision and recall, used as the main quality metric.

Quality metrics are calculated separately for each of the 10 repeated stratified hold-out splits. We report the mean and sample standard deviation across repeats.


### Current rerun protocol

The completed run uses 19,979 URLs after excluding 21 rows whose domains could not be validated, from the original 20,000-URL sample. There are 3,211 malicious and 16,768 benign URLs, grouped into 10,858 domains. Domain validation is a selection rule and may affect representativeness.

Four models and two feature sets are evaluated on ten GroupShuffleSplit partitions (seeds 42-51). Each partition holds out 30% of domain groups; the test URL fraction varies from 27.27% to 33.99%. Splits are not stratified. No registrable domain occurs in both training and test within a repeat. Private public-suffix rules are included using the offline snapshot bundled with tldextract 5.4.0. The same split is used across configurations. The seven features are predefined, without test-set feature selection.

Latency uses one URL per request at scheduled arrival rates of 50, 200 and 500 requests/s. Each configuration and rate has 20 warm-up and 1,000 evaluation calls per repeat: 240,000 evaluation calls in total. A single local worker extracts features and predicts labels; numerical libraries are limited to one thread. This is not an HTTP or network service benchmark. Model training and warm-up are excluded.

Latency is completion time minus intended arrival time, including scheduler lag, queueing and service time. Recorded service time includes feature extraction and prediction. Request submission rate and successful completion throughput are reported separately. The finite trials drain their queues after arrivals stop; they do not establish indefinitely sustainable capacity.

Quality summaries report mean and sample SD across repeats. Latency p50, p95 and p99 are computed within each repeat, then averaged across repeats. A reported mean p99 is not a pooled-request p99. Percentile bootstrap intervals resample the ten repeat-level statistics, using 2,000 resamples and seed 42. Repeats share observations: intervals describe variability conditional on this dataset and protocol, without a formal significance test.

Guardrails require mean malicious recall at least 0.80, worst repeat-level p99 at most 100 ms at the specified arrival rate, and recorded operational error rate zero. Operational errors are execution failures, not classification errors.

### Feature selection implementation

The selected vector uses zero-based indices 0, 2, 3, 4, 8, 10, 11: URL length, dot count, hyphen count, slash count, HTTPS prefix, `login`, `verify`. The timed path computes all 16 lexical features before subsetting. Thus it does not measure an optimized seven-feature extraction implementation.

### Timing notation

| Symbol | Meaning |
|---|---|
| RPS | Scheduled single-URL arrivals per second |
| t | Completion minus intended arrival, milliseconds |
| p50, p95, p99 | Within-repeat latency percentiles; summary tables average these across repeats |
| B | 2,000 bootstrap resamples |
| CI | 2.5th and 97.5th percentiles of bootstrap means |

## Mathematical notation

| Symbol | Definition |
|---|---|
| $x$ | URL feature vector with 16 or 7 values |
| $y$ | True label: malicious 1, benign 0 |
| $p_i$ | Estimated malicious probability where provided |
| $n$ | Training observations |
| $L_{data}$ | Mean binary log-loss, before L2 regularisation |
| $TP,FN$ | Correctly detected and missed malicious URLs |
| $FP,TN$ | Incorrectly flagged and correctly classified benign URLs |
| $F_1$ | Malicious-class harmonic mean of precision and recall |
| $r$ | Repeat index, 1 through 10 |
| $\lambda$ | Scheduled arrival rate: 50, 200 or 500 requests/s |
| $a,s,u,c$ | Intended arrival, submission, service start, completion time |
| $t=c-a$ | Scheduled-arrival latency, converted to ms |
| $s-a,u-s,c-u$ | Scheduler lag, queue time, service time |
| $q_{r,k}$ | Within-repeat latency percentile k |
| $\bar q_k$ | Mean of ten repeat-level percentile estimates |
| $B$ | 2,000 bootstrap resamples, seed 42 |
| $CI_{95\%}$ | 2.5th and 97.5th percentiles of bootstrap means |

$$\bar q_k=\frac{1}{10}\sum_{r=1}^{10}q_{r,k},\qquad CI_{95\%}=[Q_{0.025},Q_{0.975}].$$

The notebook uses the complete compressed raw log. A small JSONL sample is supplied only to illustrate the raw schema.
