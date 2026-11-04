"""Task 3 experiment. Writes the raw log data/raw/test_run.jsonl.

Record types in the log:
  meta    - environment and config (first line)
  train   - training time of a model
  quality - confusion matrix on the test split
  latency - one inference request; phase = "warmup" (first 5 calls) or "eval"
"""
import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import xgboost
import yaml
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

PROJECT = Path(__file__).resolve().parents[1]

FEATURE_NAMES = [
    "url_length", "host_length", "n_dots", "n_hyphens", "n_slashes",
    "n_question", "n_equals", "n_digits", "is_https", "has_at",
    "kw_login", "kw_verify", "kw_account", "kw_secure", "kw_confirm", "kw_update",
]
# Same 7 features as in TASK 2 (fixed a priori, so no selection leakage).
SELECTED_IDX = [0, 2, 3, 4, 8, 10, 11]


def url_features(url: str) -> list:
    """16 lexical URL features, identical to src/benchmark.py (TASK 2)."""
    s = url.lower()
    host = s.split("://")[-1].split("/")[0]
    return [
        len(s), len(host), s.count("."), s.count("-"), s.count("/"),
        s.count("?"), s.count("="), sum(c.isdigit() for c in s),
        int(s.startswith("https://")), int("@" in s),
        int("login" in s), int("verify" in s), int("account" in s),
        int("secure" in s), int("confirm" in s), int("update" in s),
    ]


def featurize(urls, cols) -> np.ndarray:
    return np.asarray([url_features(u) for u in urls], dtype=float)[:, cols]


def build_model(name: str, seed: int):
    if name == "logistic_regression":
        return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=seed))
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=100, random_state=seed, n_jobs=1)
    if name == "svm":
        return make_pipeline(StandardScaler(), SVC(kernel="rbf", random_state=seed))
    if name == "xgboost":
        return XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                             random_state=seed, n_jobs=1, eval_metric="logloss")
    raise ValueError(f"Unknown model: {name}")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def run(config_path: Path) -> None:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    df = pd.read_csv(PROJECT / cfg["dataset"])
    urls, y = df["url"].astype(str).to_numpy(), df["label"].to_numpy()
    log_path = PROJECT / cfg["raw_log"]
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8") as log:
        def emit(rec):
            log.write(json.dumps(rec) + "\n")

        emit({"type": "meta", "ts": now(), "python": platform.python_version(),
              "platform": platform.platform(), "processor": platform.processor(),
              "numpy": np.__version__, "sklearn": sklearn.__version__,
              "xgboost": xgboost.__version__, "n_urls": int(len(y)),
              "phishing_share": float(y.mean()), "config": cfg})

        for rep in range(cfg["repeats"]):
            seed = cfg["seed"] + rep
            rng = np.random.default_rng(seed)
            tr, te = train_test_split(np.arange(len(y)), test_size=cfg["test_size"],
                                      random_state=seed, stratify=y)
            for fs in cfg["feature_sets"]:
                cols = list(range(16)) if fs == "full" else SELECTED_IDX
                x_tr, x_te = featurize(urls[tr], cols), featurize(urls[te], cols)
                for name in cfg["models"]:
                    base = {"model": name, "feature_set": fs, "repeat": rep + 1, "seed": seed}
                    model = build_model(name, seed)
                    t0 = time.perf_counter()
                    model.fit(x_tr, y[tr])
                    emit({"type": "train", "ts": now(), **base, "n_train": int(len(tr)),
                          "train_ms": (time.perf_counter() - t0) * 1000})

                    errors = 0
                    try:
                        pred = model.predict(x_te)
                    except Exception:  # pipeline failure counts towards the guardrail
                        pred, errors = np.zeros_like(y[te]), 1
                    tn, fp, fn, tp = confusion_matrix(y[te], pred, labels=[0, 1]).ravel()
                    emit({"type": "quality", "ts": now(), **base, "n_test": int(len(te)),
                          "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
                          "pipeline_errors": errors})

                    for bs in cfg["batch_sizes"]:
                        n_calls = cfg["warmup_calls"] + cfg["eval_calls"]
                        for call in range(n_calls):
                            batch = urls[te][rng.choice(len(te), size=bs, replace=False)]
                            status = "ok"
                            t0 = time.perf_counter()
                            try:
                                model.predict(featurize(batch, cols))
                            except Exception:
                                status = "error"
                            ms = (time.perf_counter() - t0) * 1000
                            emit({"type": "latency", "ts": now(), **base, "batch_size": bs,
                                  "call": call + 1,
                                  "phase": "warmup" if call < cfg["warmup_calls"] else "eval",
                                  "latency_ms": round(ms, 5), "status": status})
                    print(f"repeat={rep+1:2d} {fs:8s} {name:20s} done", flush=True)
    print(f"Raw log written to {log_path.relative_to(PROJECT)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/experiment.yaml")
    run(PROJECT / p.parse_args().config)
