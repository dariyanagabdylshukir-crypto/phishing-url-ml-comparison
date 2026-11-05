"""Organize existing results without deleting source measurements or running experiments."""
from pathlib import Path
import gzip
import hashlib
import shutil
import json

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'data/review_runs/20261105T122952Z_dbea27e6'
ARCHIVE = ROOT / 'archive/task3_batch'


def digest(path, compressed=False):
    h = hashlib.sha256()
    opener = gzip.open if compressed else open
    with opener(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    if (ARCHIVE/'README.md').exists():
        print('Historical results already archived. No changes made.')
        return
    meta = json.loads((RUN/'metadata.json').read_text(encoding='utf-8'))
    if meta.get('status') != 'complete':
        raise ValueError('Expected a completed run')
    raw, compressed = RUN/'raw.jsonl', RUN/'raw.jsonl.gz'
    if raw.exists():
        if not compressed.exists():
            temp = compressed.with_suffix('.gz.tmp')
            try:
                with raw.open('rb') as source, gzip.open(temp, 'wb', compresslevel=6) as target:
                    shutil.copyfileobj(source, target)
                if digest(raw) != digest(temp, compressed=True):
                    raise ValueError('Compressed log verification failed')
                temp.replace(compressed)
            finally:
                if temp.exists(): temp.unlink()
        elif digest(raw) != digest(compressed, compressed=True):
            raise ValueError('Existing compressed log differs from original')
        print('Verified compressed raw log:', compressed.stat().st_size, 'bytes')
        print('Original raw.jsonl retained locally and ignored by Git.')
    elif not compressed.exists():
        raise FileNotFoundError('No raw log found')
    # Check every destination before moving any historical files.
    paths = [
        'data/raw/test_run.jsonl',
        'data/processed/metrics_summary.csv',
        'data/processed/latency_summary.csv',
        'reports/figures/fig1_latency_vs_load.pdf',
        'reports/figures/fig1_latency_vs_load.png',
        'reports/figures/fig2_distribution_boxplot.pdf',
        'reports/figures/fig2_distribution_boxplot.png',
        'reports/TASK3_report.pdf',
        'src/run_experiment.py', 'src/process_data.py', 'src/visualize.py',
        'configs/experiment.yaml',
    ]
    for relative in paths:
        source, target = ROOT/relative, ARCHIVE/relative
        if source.exists() and target.exists():
            raise FileExistsError('Refusing to overwrite archive: '+str(target))
    for relative in paths:
        source, target = ROOT/relative, ARCHIVE/relative
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            print('Archived:', relative)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    (ARCHIVE/'README.md').write_text(
        '# Historical batch-size experiment\n\n'
        'Superseded Task 3 outputs and report. These are not the current RPS results.\n'
        'The historical scripts retain their original relative paths. To rerun them, '
        'copy this tree to an isolated working folder and provide the original '
        'data/sample/urls_research_sample.csv. Do not run them in the current project root.\n',
        encoding='utf-8')
    rules = [
        '/task3_cleanup_update/',
        '!data/review_runs/**/raw.jsonl.gz',
        '!archive/task3_batch/data/raw/test_run.jsonl',
        '!archive/task3_batch/data/processed/metrics_summary.csv',
        '!archive/task3_batch/data/processed/latency_summary.csv',
    ]
    ignore = ROOT/'.gitignore'
    existing = ignore.read_text(encoding='utf-8-sig')
    missing = [line for line in rules if line not in existing.splitlines()]
    if missing:
        with ignore.open('a', encoding='utf-8') as stream:
            stream.write('\n# Organized current and historical evidence\n'+'\n'.join(missing)+'\n')
    print('Organization complete. No experiment was rerun; no source measurement was deleted.')


if __name__ == '__main__':
    main()
