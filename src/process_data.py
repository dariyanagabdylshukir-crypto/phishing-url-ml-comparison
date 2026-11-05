"""Data processing and statistics.

Input:  data/raw/test_run.jsonl
Output: data/processed/metrics_summary.csv, data/processed/latency_summary.csv
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_LOG = ROOT / "data" / "raw" / "test_run.jsonl"
OUT_DIR = ROOT / "data" / "processed"

SEED = 42
N_BOOT = 10000
MODELS = ["logistic_regression", "random_forest", "svm", "xgboost"]
NAMES = {"logistic_regression": "Logistic Regression", "random_forest": "Random Forest",
         "svm": "SVM", "xgboost": "XGBoost"}
BASELINE = ("logistic_regression", "full")

# guardrails from the methodology
MIN_RECALL = 0.80
MAX_P99_MS = 100
MAX_ERROR_RATE = 0.0


def load_raw(path=RAW_LOG):
    """Read the jsonl log and split records by type."""
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    data = {}
    for t in ["train", "quality", "latency"]:
        data[t] = pd.DataFrame([r for r in rows if r["type"] == t])
    data["meta"] = rows[0]
    return data


def remove_warmup(latency):
    """Keep only evaluation calls without errors (first 5 calls are warm-up)."""
    lat = latency[(latency["phase"] == "eval") & (latency["status"] == "ok")].copy()
    lat["ms_per_url"] = lat["latency_ms"] / lat["batch_size"]
    return lat


def add_metrics(quality):
    """Precision, recall, F1 and accuracy from the confusion matrix."""
    q = quality.copy()
    q["precision"] = q["tp"] / (q["tp"] + q["fp"])
    q["recall"] = q["tp"] / (q["tp"] + q["fn"])
    q["f1"] = 2 * q["tp"] / (2 * q["tp"] + q["fp"] + q["fn"])
    q["accuracy"] = (q["tp"] + q["tn"]) / (q["tp"] + q["fp"] + q["fn"] + q["tn"])
    return q


def bootstrap_ci(values, stat=np.mean, n_boot=N_BOOT, seed=SEED):
    """95% confidence interval by percentile bootstrap."""
    values = np.asarray(values)
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(n_boot, len(values)), replace=True)
    stats = stat(samples, axis=1)
    return np.percentile(stats, 2.5), np.percentile(stats, 97.5)


def latency_table(lat):
    """Latency statistics with a bootstrap over repeats and calls."""
    rows = []

    for (model, fs, bs), g in lat.groupby(
        ["model", "feature_set", "batch_size"]
    ):
        v = g["latency_ms"]
        groups = [
            part["latency_ms"].to_numpy(dtype=float)
            for _, part in g.groupby("repeat", sort=True)
        ]

        if len(groups) < 2:
            raise ValueError("At least two repeats are required for the CI")

        rng = np.random.default_rng(SEED)
        boot_medians = np.empty(N_BOOT)

        for i in range(N_BOOT):
            chosen = rng.integers(0, len(groups), size=len(groups))
            sample = np.concatenate([
                rng.choice(groups[j], size=len(groups[j]), replace=True)
                for j in chosen
            ])
            boot_medians[i] = np.median(sample)

        lo, hi = np.percentile(boot_medians, [2.5, 97.5])

        rows.append({
            "model": model,
            "feature_set": fs,
            "batch_size": bs,
            "n": len(v),
            "median": v.median(),
            "p25": v.quantile(0.25),
            "p75": v.quantile(0.75),
            "p95": v.quantile(0.95),
            "p99": v.quantile(0.99),
            "ci_low": lo,
            "ci_high": hi,
        })

    return pd.DataFrame(rows)


def check_guardrails(q, latency_raw, lat):
    """Error rate, recall and p99 latency (1 URL) for every configuration."""
    rows = []
    for (model, fs), g in q.groupby(["model", "feature_set"]):
        calls = latency_raw[(latency_raw["model"] == model) & (latency_raw["feature_set"] == fs)]
        errors = g["pipeline_errors"].sum() + (calls["status"] != "ok").sum()
        one = lat[(lat["model"] == model) & (lat["feature_set"] == fs) & (lat["batch_size"] == 1)]
        p99 = one["latency_ms"].quantile(0.99)
        rows.append({"model": model, "feature_set": fs,
                     "error_rate": errors / (len(g) + len(calls)),
                     "recall": g["recall"].mean(), "p99_ms": p99,
                     "recall_ok": g["recall"].mean() >= MIN_RECALL,
                     "latency_ok": p99 <= MAX_P99_MS,
                     "errors_ok": errors / (len(g) + len(calls)) <= MAX_ERROR_RATE})
    return pd.DataFrame(rows)


def make_summary(q, lat_tab, guard):
    """One row per model and feature set -> metrics_summary.csv"""
    rows = []
    for (model, fs), g in q.groupby(["model", "feature_set"]):
        lo, hi = bootstrap_ci(g["f1"])
        l1 = lat_tab[(lat_tab["model"] == model) & (lat_tab["feature_set"] == fs)
                     & (lat_tab["batch_size"] == 1)].iloc[0]
        gr = guard[(guard["model"] == model) & (guard["feature_set"] == fs)].iloc[0]
        rows.append({
            "model": model, "feature_set": fs,
            "role": "baseline" if (model, fs) == BASELINE else "proposed",
            "f1_mean": g["f1"].mean(), "f1_sd": g["f1"].std(), "f1_ci_low": lo, "f1_ci_high": hi,
            "f1_median": g["f1"].median(), "f1_p25": g["f1"].quantile(0.25),
            "f1_p75": g["f1"].quantile(0.75),
            "precision_mean": g["precision"].mean(),
            "recall_mean": g["recall"].mean(), "recall_sd": g["recall"].std(),
            "accuracy_mean": g["accuracy"].mean(),
            "latency_median_ms": l1["median"], "latency_p25_ms": l1["p25"],
            "latency_p75_ms": l1["p75"], "latency_p95_ms": l1["p95"],
            "latency_p99_ms": l1["p99"], "latency_ci_low": l1["ci_low"],
            "latency_ci_high": l1["ci_high"],
            "error_rate": gr["error_rate"],
            "guardrails_passed": bool(gr["recall_ok"] and gr["latency_ok"] and gr["errors_ok"]),
        })
    s = pd.DataFrame(rows)
    s["model"] = pd.Categorical(s["model"], MODELS)
    return s.sort_values(["feature_set", "model"]).reset_index(drop=True)


def results_table(s):
    """Markdown table for README."""
    lines = ["| Model | Features | Role | F1 (Mean ± SD) | F1 95% CI | Recall (Mean ± SD) "
             "| Latency 1 URL, ms (Median, p25–p75) | p99, ms |",
             "|---|---|---|---|---|---|---|---|"]
    for _, r in s.iterrows():
        role = "**Baseline**" if r["role"] == "baseline" else "Proposed"
        lines.append(f"| {NAMES[r['model']]} | {r['feature_set']} | {role} "
                     f"| {r['f1_mean']:.3f} ± {r['f1_sd']:.3f} "
                     f"| [{r['f1_ci_low']:.3f}, {r['f1_ci_high']:.3f}] "
                     f"| {r['recall_mean']:.3f} ± {r['recall_sd']:.3f} "
                     f"| {r['latency_median_ms']:.2f} ({r['latency_p25_ms']:.2f}–{r['latency_p75_ms']:.2f}) "
                     f"| {r['latency_p99_ms']:.2f} |")
    return "\n".join(lines)


def run():
    np.random.seed(SEED)
    raw = load_raw()
    q = add_metrics(raw["quality"])
    lat = remove_warmup(raw["latency"])
    lat_tab = latency_table(lat)
    guard = check_guardrails(q, raw["latency"], lat)
    summary = make_summary(q, lat_tab, guard)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT_DIR / "metrics_summary.csv", index=False, float_format="%.4f")
    lat_tab.to_csv(OUT_DIR / "latency_summary.csv", index=False, float_format="%.4f")
    return raw, q, lat, lat_tab, guard, summary


if __name__ == "__main__":
    *_, summary = run()
    print(results_table(summary))
