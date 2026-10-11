"""Reproducible smoke-test benchmark; sample metrics are NOT research findings."""
import argparse
import csv
import json
import platform
import time
from pathlib import Path
import numpy as np
import yaml
import sklearn
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from xgboost import XGBClassifier

def features(url):
    s=url.lower()
    host=s.split('://')[-1].split('/')[0]
    return [
        len(s), len(host), s.count('.'), s.count('-'), s.count('/'),
        s.count('?'), s.count('='), sum(c.isdigit() for c in s),
        int(s.startswith('https://')), int('@' in s),
        int('login' in s), int('verify' in s), int('account' in s),
        int('secure' in s), int('confirm' in s), int('update' in s),
    ]

def build_model(name, seed):
    if name == 'logistic_regression':
        return make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, random_state=seed))
    if name == 'random_forest':
        return RandomForestClassifier(n_estimators=30, random_state=seed, n_jobs=1)
    if name == 'svm':
        return make_pipeline(StandardScaler(), SVC(kernel='rbf', random_state=seed))
    if name == 'xgboost':
        return XGBClassifier(n_estimators=30, max_depth=3, learning_rate=0.1,
                             random_state=seed, n_jobs=1, eval_metric='logloss')
    raise ValueError(f'Unknown model: {name}')

def run(config_path):
    config_path = Path(config_path).resolve()
    project = config_path.parent.parent
    cfg = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    data_path = project / cfg['dataset']
    with data_path.open(newline='', encoding='utf-8') as fh:
        rows = list(csv.DictReader(fh))
    if not rows or not {'url', 'label'} <= set(rows[0]):
        raise ValueError('Dataset must contain url and label columns')
    x = np.array([features(r['url']) for r in rows], dtype=float)
    y = np.array([int(r['label']) for r in rows])
    if set(y) != {0, 1}:
        raise ValueError('Expected binary labels 0 and 1')
    train_idx, test_idx = train_test_split(
        np.arange(len(y)), test_size=cfg['test_size'],
        random_state=cfg['seed'], stratify=y)
    output = project / cfg['output_dir']
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for feature_set in cfg['feature_sets']:
        cols = list(range(x.shape[1])) if feature_set == 'full' else [0, 2, 3, 4, 8, 10, 11]
        for name in cfg['models']:
            for run_id in range(cfg['runs']):
                model = build_model(name, cfg['seed'] + run_id)
                start = time.perf_counter()
                model.fit(x[train_idx][:, cols], y[train_idx])
                training_ms = (time.perf_counter() - start) * 1000
                start = time.perf_counter()
                pred = model.predict(x[test_idx][:, cols])
                inference_ms = (time.perf_counter() - start) * 1000 / len(test_idx)
                record = {
                    'model': name, 'feature_set': feature_set, 'run': run_id + 1,
                    'n_train': len(train_idx), 'n_test': len(test_idx),
                    'accuracy': float(accuracy_score(y[test_idx], pred)),
                    'precision': float(precision_score(y[test_idx], pred, zero_division=0)),
                    'recall': float(recall_score(y[test_idx], pred, zero_division=0)),
                    'f1': float(f1_score(y[test_idx], pred, zero_division=0)),
                    'training_ms': round(training_ms, 4),
                    'inference_ms_per_url': round(inference_ms, 4),
                }
                record['guardrail_latency_pass'] = inference_ms <= cfg['max_inference_ms_per_url']
                record['guardrail_recall_pass'] = record['recall'] >= cfg['min_phishing_recall']
                records.append(record)
                print(f"{name:20} {feature_set:8} run={run_id+1} F1={record['f1']:.3f}")
    with (output / 'benchmark_results.csv').open('w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    metadata = {
        'sample_only': True, 'note': 'Synthetic illustrative sample; not research evidence',
        'seed': cfg['seed'], 'python': platform.python_version(),
        'scikit_learn': sklearn.__version__, 'records': len(records),
        'dataset': str(data_path.relative_to(project)),
    }
    (output / 'run_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(f"Saved {len(records)} rows to {output / 'benchmark_results.csv'}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/config.yaml')
    args = parser.parse_args()
    run(args.config)
