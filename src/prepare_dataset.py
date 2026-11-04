"""Downloads the public URL dataset and makes the research sample.

Source: github.com/faizann24/Using-machine-learning-to-detect-malicious-URLs (data/data.csv).
The full file (~22 MB) goes to data/external/ (not in git). We remove duplicates
and take a stratified sample of 20 000 URLs -> data/sample/urls_research_sample.csv
"""
import argparse
import urllib.request
from pathlib import Path

import pandas as pd

SOURCE_URL = ("https://raw.githubusercontent.com/faizann24/"
              "Using-machine-learning-to-detect-malicious-URLs/master/data/data.csv")
PROJECT = Path(__file__).resolve().parents[1]


def main(n_samples: int, seed: int) -> None:
    external = PROJECT / "data" / "external" / "malicious_urls_full.csv"
    external.parent.mkdir(parents=True, exist_ok=True)
    if not external.exists():
        print(f"Downloading {SOURCE_URL}")
        urllib.request.urlretrieve(SOURCE_URL, external)
    df = pd.read_csv(external)
    n_raw = len(df)
    df["url"] = df["url"].astype(str).str.strip()
    df = df[df["url"].str.len() > 0]
    # Leakage prevention: one row per unique URL; conflicting labels are dropped.
    conflicts = df.groupby("url")["label"].nunique()
    df = df[~df["url"].isin(conflicts[conflicts > 1].index)].drop_duplicates("url")
    df["label"] = (df["label"] == "bad").astype(int)  # 1 = phishing / malicious
    sample = (df.groupby("label", group_keys=False)
                .sample(frac=n_samples / len(df), random_state=seed)
                .sample(frac=1.0, random_state=seed)
                .reset_index(drop=True))
    out = PROJECT / "data" / "sample" / "urls_research_sample.csv"
    sample.to_csv(out, index=False)
    print(f"raw rows={n_raw}, unique clean rows={len(df)}, sample rows={len(sample)}, "
          f"phishing share={sample['label'].mean():.3f} -> {out.relative_to(PROJECT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-samples", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    main(args.n_samples, args.seed)
