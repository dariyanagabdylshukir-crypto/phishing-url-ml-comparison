"""Raw-log ingestion, warm-up filtering and repeat-level statistical aggregation."""
import gzip
import json
from pathlib import Path
import numpy as np
import pandas as pd

def mean_ci(values, b, seed):
    values=np.asarray(values,dtype=float)
    rng=np.random.default_rng(seed)
    return np.quantile(rng.choice(values,(b,len(values))).mean(axis=1),[.025,.975])

def load_raw(folder):
    folder=Path(folder)
    meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    if meta['status'] != 'complete': raise ValueError('Incomplete experiment')
    plain=folder/'raw.jsonl'
    handle=plain.open('rt',encoding='utf-8') if plain.exists() else gzip.open(folder/'raw.jsonl.gz','rt',encoding='utf-8')
    with handle:
        records=[json.loads(line) for line in handle if line.strip()]
    quality=pd.DataFrame(r for r in records if r['type']=='quality')
    calls=pd.DataFrame(r for r in records if r['type']=='request')
    return meta, quality, calls


def remove_warmup(calls):
    if not calls.phase.isin(['warmup','eval']).all(): raise ValueError('Unknown phase')
    return calls.loc[calls.phase.eq('eval')].copy()


def aggregate(meta, quality_records, evaluation_calls):
    cfg=meta['config'];b=cfg['bootstrap_resamples'];seed=cfg['seed']
    q=quality_records.copy();req=evaluation_calls.copy()
    for timing in ['latency_ms','response_ms','service_ms','queue_ms','scheduler_lag_ms']:
        if not np.isfinite(req[timing]).all() or (req[timing]<0).any():
            raise ValueError('Invalid timing values')
    if not np.allclose(req.latency_ms,req.scheduler_lag_ms+req.queue_ms+req.service_ms):
        raise ValueError('Latency components do not add up')
    expected=cfg['repeats']*len(cfg['models'])*len(cfg['feature_sets'])
    if len(q)!=expected or len(req)!=expected*len(cfg['rps_levels'])*cfg['requests_per_level']:
        raise ValueError('Missing quality records or requests')
    counts=req.groupby(['model','feature_set','repeat','target_rps']).size()
    if not counts.eq(cfg['requests_per_level']).all():raise ValueError('Incomplete series')
    if not q.status.eq('ok').all():raise ValueError('Quality errors present')
    if not all(s['shared_domains']==0 for s in meta['splits']):raise ValueError('Domain leakage')
    for col,den in [('precision',q.tp+q.fp),('recall',q.tp+q.fn),('f1',2*q.tp+q.fp+q.fn)]:
        numerator=2*q.tp if col=='f1' else q.tp
        q[col]=np.divide(numerator,den,out=np.zeros(len(q)),where=den.to_numpy()!=0)
    q['accuracy']=(q.tp+q.tn)/q.n_test
    quality=[]
    for (model,fs),g in q.groupby(['model','feature_set']):
        row={'model':model,'feature_set':fs,'role':'baseline' if (model,fs)==('logistic_regression','full') else 'proposed'}
        for metric in ['f1','recall','precision','accuracy','majority_accuracy']:
            lo,hi=mean_ci(g[metric],b,seed)
            row.update({metric+'_mean':g[metric].mean(),metric+'_sd':g[metric].std(),metric+'_ci_low':lo,metric+'_ci_high':hi})
        quality.append(row)
    quality=pd.DataFrame(quality)
    # Compute each quantile within a repeat, then average repeat-level quantiles.
    # CI resamples repeat-level statistics, not requests treated as independent.
    repeat_stats=[]
    for (model,fs,rep,rate),g in req.groupby(['model','feature_set','repeat','target_rps']):
        ok=g[g.status.eq('ok')]
        if ok.empty:raise ValueError('No successful calls in a series')
        row={'model':model,'feature_set':fs,'repeat':rep,'target_rps':rate,
             'error_rate':1-len(ok)/len(g),'n':len(g),'n_success':len(ok),
             'actual_submission_rps':g.actual_submission_rps.iloc[0],
             'throughput_rps':g.throughput_rps.iloc[0],
             'scheduler_lag_p95_ms':g.scheduler_lag_ms.quantile(.95),
             'queue_p95_ms':g.queue_ms.quantile(.95),
             'service_p50_ms':ok.service_ms.median()}
        for p in [50,95,99]:row[f'p{p}_ms']=ok.latency_ms.quantile(p/100)
        repeat_stats.append(row)
    repeat_stats=pd.DataFrame(repeat_stats)
    latency=[]
    for (model,fs,rate),g in repeat_stats.groupby(['model','feature_set','target_rps']):
        row={'model':model,'feature_set':fs,'target_rps':rate,'n':int(g.n.sum())}
        for metric in ['p50_ms','p95_ms','p99_ms','error_rate','actual_submission_rps','throughput_rps','scheduler_lag_p95_ms','queue_p95_ms','service_p50_ms']:
            lo,hi=mean_ci(g[metric],b,seed)
            row.update({metric:g[metric].mean(),metric+'_ci_low':lo,metric+'_ci_high':hi})
        # Apply p99 guardrail to worst repeat, not the averaged p99.
        row['worst_repeat_p99_ms']=g.p99_ms.max()
        row['total_errors']=int(g.n.sum()-g.n_success.sum())
        latency.append(row)
    latency=pd.DataFrame(latency)
    guard=latency.merge(quality[['model','feature_set','recall_mean']],on=['model','feature_set'])
    guard['recall_ok']=guard.recall_mean>=cfg['guardrails']['min_malicious_recall']
    guard['latency_ok']=guard.worst_repeat_p99_ms<=cfg['guardrails']['max_p99_ms']
    guard['errors_ok']=guard.error_rate<=cfg['guardrails']['max_error_rate']
    guard['passed']=guard[['recall_ok','latency_ok','errors_ok']].all(axis=1)
    paired=q.pivot(index=['model','repeat'],columns='feature_set',values='f1')
    if {'full','selected'} <= set(paired):
        paired=paired.assign(selected_minus_full=paired.selected-paired.full).reset_index()
    else: paired=pd.DataFrame()
    return {'quality_repeats':q, 'quality_summary':quality,
            'latency_repeats':repeat_stats,'rps_summary':latency,
            'guardrails':guard,'paired_feature_effects':paired}


def export_tables(tables, folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    for name, data in tables.items(): data.to_csv(folder/(name+'.csv'),index=False)
    # Required benchmark summary: one row per model, feature set and offered rate.
    summary=tables['quality_summary'].merge(tables['rps_summary'],on=['model','feature_set'])
    summary.to_csv(folder/'metrics_summary.csv',index=False)
    return summary
