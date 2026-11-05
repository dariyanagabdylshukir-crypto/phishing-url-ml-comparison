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

### Latency

Latency t is the time required to extract features and predict labels for one request containing b URLs, measured in milliseconds. It excludes model training. Warm-up calls are excluded from latency summaries.

We report the median, p25, p75, p95 and p99 for each model, feature set and batch size. Batch sizes are 1, 10, 100 and 1000 URLs per request. Batch size is not request arrival rate (RPS).

### Confidence intervals

We use percentile bootstrap intervals with B = 10,000 resamples and seed 42.

For mean F1, we resample the 10 repeat-level F1 values with replacement and calculate their mean.

For median latency, we use a two-stage bootstrap. First, we sample repeats with replacement. Within each selected repeat, we sample its evaluation calls with replacement, preserving its call count. We then calculate the median of the combined sampled calls.

The interval endpoints are the 2.5th and 97.5th percentiles of the bootstrap statistics:

$$
CI_{95\%} = [Q_{2.5\%}, Q_{97.5\%}]
$$

These intervals describe variability in the recorded experiment. Repeated hold-out splits share observations, so the F1 intervals do not represent results from independent datasets. No formal hypothesis test is performed.

### Guardrails

The predefined thresholds are:

- Mean recall across repeats at least 0.80.
- Single-URL p99 latency at most 100 ms.
- Recorded operational error rate equal to zero.

Operational errors are failures during execution, not incorrect class predictions. Meeting the operational thresholds alone does not establish detection quality.

## 4. Notation

| Symbol | Meaning |
|---|---|
| x | URL feature vector with 16 or 7 values |
| y | True label: 1 = malicious, 0 = benign |
| p | Estimated malicious-class probability for models that provide probabilities |
| n | Number of training URLs |
| L_data | Mean binary log-loss before regularisation |
| TP | Malicious URLs correctly classified as malicious |
| FN | Malicious URLs incorrectly classified as benign |
| FP | Benign URLs incorrectly classified as malicious |
| TN | Benign URLs correctly classified as benign |
| F1 | Main classification quality metric |
| t | Latency of one request, in milliseconds |
| b | URLs per request: 1, 10, 100 or 1000 |
| p25, p75 | 25th and 75th percentiles of recorded latency |
| p95, p99 | 95th and 99th percentiles of recorded latency |
| B | Number of bootstrap resamples: 10,000 |
| CI | Confidence interval |
