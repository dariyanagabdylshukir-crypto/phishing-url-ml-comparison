# Domain Model (ML track)

## 1. Task

Each URL gets a label $y$: $y = 1$ if it is phishing, $y = 0$ if it is benign.
From each URL we calculate 16 simple features (length, number of dots, digits, words like `login`) and put them in a vector $x$.
The model looks at $x$ and gives the probability $p$ that the URL is phishing. If $p \geq 0.5$, the model says "phishing".

## 2. Loss function

The baseline model (Logistic Regression) is trained by minimising the log-loss:

$$
L = -\frac{1}{n}\sum_{i=1}^{n}\Big[\, y_i \log p_i + (1 - y_i)\log(1 - p_i) \,\Big]
$$

In simple words: if the model gives a high probability to the correct answer, the loss is small; if it is confident and wrong, the loss is large. Training finds the weights that make $L$ as small as possible. (scikit-learn also adds a small L2 penalty on the weights.)

The other models use their own standard criteria: SVM uses hinge loss, Random Forest uses Gini impurity, XGBoost uses log-loss with a penalty for tree complexity.

## 3. Metrics

$$
Precision = \frac{TP}{TP + FP} \qquad Recall = \frac{TP}{TP + FN} \qquad F_1 = \frac{2TP}{2TP + FP + FN}
$$

- Recall: what part of phishing URLs the model found.
- Precision: what part of URLs marked as phishing are really phishing.
- **F1** is the main metric: it combines precision and recall.

**Latency** $t$ is the time of one request with $b$ URLs (feature extraction + prediction), in ms. We report the median and the percentiles $p95$, $p99$.

**95% confidence interval** (bootstrap): we resample the results $B = 10\,000$ times with replacement, calculate the mean (for F1) or the median (for latency) each time, and take the 2.5% and 97.5% percentiles:

$$
CI_{95\%} = \big[\, Q_{2.5\%},\ Q_{97.5\%} \,\big]
$$

**Guardrails** (minimum requirements):

$$
Recall \geq 0.80 \qquad p99\ latency \leq 100\ ms \qquad error\ rate = 0
$$

## 4. Notation

| Symbol | Meaning |
|---|---|
| $x$ | features of a URL (16 or 7 numbers) |
| $y$ | true label: 1 = phishing, 0 = benign |
| $p$ | predicted probability of phishing |
| $n$ | number of URLs in the training set |
| $L$ | loss function |
| $TP$ | phishing URLs found by the model |
| $FN$ | phishing URLs missed by the model |
| $FP$ | benign URLs marked as phishing |
| $TN$ | benign URLs marked as benign |
| $F_1$ | F1-score, main metric |
| $t$ | latency of one request, ms |
| $b$ | batch size, URLs per request (1, 10, 100, 1000) |
| $p95$, $p99$ | 95% / 99% of requests are faster than this time |
| $B$ | number of bootstrap resamples (10 000) |
| $CI_{95\%}$ | 95% confidence interval |
