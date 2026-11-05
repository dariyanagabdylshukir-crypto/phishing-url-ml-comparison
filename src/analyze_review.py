"""Recompute published tables and figures from a completed plain or compressed run."""
import argparse
from pathlib import Path
from process_data import load_raw, remove_warmup, aggregate, export_tables
from visualize import plot_results


def analyze(folder, publish_root=None):
    folder=Path(folder).resolve()
    meta, quality, calls=load_raw(folder)
    evaluation=remove_warmup(calls)
    tables=aggregate(meta,quality,evaluation)
    export_tables(tables,folder/'processed')
    plot_results(meta,tables,evaluation,folder/'figures')
    if publish_root is not None:
        publish_root=Path(publish_root)
        export_tables(tables,publish_root/'data/processed')
        plot_results(meta,tables,evaluation,publish_root/'reports/figures')
    print('Excluded warm-up:',len(calls)-len(evaluation))
    print('Evaluation calls:',len(evaluation))
    print(tables['quality_summary'][['model','feature_set','f1_mean','recall_mean']].to_string(index=False))
    return tables


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',required=True)
    parser.add_argument('--publish-root')
    args=parser.parse_args()
    analyze(args.run_dir,args.publish_root)
