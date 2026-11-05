"""Validate and summarize a completed review run; make 300 dpi PNG/vector PDF figures."""
import argparse
import gzip
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

NAMES={'logistic_regression':'Logistic Regression','random_forest':'Random Forest','svm':'SVM','xgboost':'XGBoost'}

def mean_ci(values, b, seed):
    values=np.asarray(values,dtype=float)
    rng=np.random.default_rng(seed)
    return np.quantile(rng.choice(values,(b,len(values))).mean(axis=1),[.025,.975])

def analyze(folder):
    folder=Path(folder).resolve()
    meta=json.loads((folder/'metadata.json').read_text())
    if meta['status']!='complete':raise ValueError('Refusing incomplete experiment')
    cfg=meta['config'];b=cfg['bootstrap_resamples'];seed=cfg['seed']
    raw = folder/'raw.jsonl'
    if raw.exists():
        handle = raw.open('rt', encoding='utf-8')
    else:
        handle = gzip.open(folder/'raw.jsonl.gz', 'rt', encoding='utf-8')
    with handle:
        rows=[json.loads(line) for line in handle if line.strip()]
    q=pd.DataFrame([r for r in rows if r['type']=='quality'])
    req=pd.DataFrame([r for r in rows if r['type']=='request' and r['phase']=='eval'])
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
    out=folder/'processed';out.mkdir(exist_ok=True)
    for name,data in [('quality_repeats',q),('quality_summary',quality),('latency_repeats',repeat_stats),('rps_summary',latency),('guardrails',guard)]:
        data.to_csv(out/f'{name}.csv',index=False)
    # Paired descriptive feature effects; no unperformed significance tests.
    paired=q.pivot(index=['model','repeat'],columns='feature_set',values='f1')
    if {'full','selected'}<=set(paired):
        (paired.assign(selected_minus_full=paired.selected-paired.full).reset_index()).to_csv(out/'paired_feature_effects.csv',index=False)
    sns.set_theme(style='whitegrid',palette='colorblind')
    colors=dict(zip(cfg['models'],sns.color_palette('colorblind',len(cfg['models']))))
    figures=folder/'figures';figures.mkdir(exist_ok=True)
    mark='SMOKE TEST - NOT RESEARCH RESULTS\n' if cfg.get('smoke_only') else ''
    fig,axes=plt.subplots(2,3,figsize=(12,7),squeeze=False)
    for i,fs in enumerate(['full','selected']):
        for j,p in enumerate([50,95,99]):
            ax=axes[i,j]
            for model in cfg['models']:
                d=latency[(latency.model==model)&(latency.feature_set==fs)].sort_values('target_rps')
                if d.empty:continue
                # Draw CI endpoints directly; do not assume a percentile CI encloses its estimate.
                ax.plot(d.target_rps,d[f'p{p}_ms'],marker=['o','s','^','D'][cfg['models'].index(model)],linestyle=['-','--','-.',':'][cfg['models'].index(model)],color=colors[model],label=NAMES[model])
                ax.vlines(d.target_rps,d[f'p{p}_ms_ci_low'],d[f'p{p}_ms_ci_high'],color=colors[model])
            ax.set_xlim(left=0)
            ax.set(title=f'{fs}: mean repeat p{p}',xlabel='Offered load (requests/s)',ylabel='Scheduled-arrival latency (ms)',yscale='log')
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=4)
    fig.suptitle(mark+'Local single-worker inference, one URL/request; 95% repeat-bootstrap CI')
    fig.tight_layout(rect=[0,.06,1,.94])
    save(fig,figures/'fig1_latency_vs_rps')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    sns.boxplot(data=q,x='model',y='f1',hue='feature_set',order=cfg['models'],hue_order=['full','selected'],ax=axes[0],showfliers=True)
    sns.stripplot(data=q,x='model',y='f1',hue='feature_set',order=cfg['models'],hue_order=['full','selected'],dodge=True,ax=axes[0],palette=['.2','.2'],legend=False,size=3)
    axes[0].set(ylabel='Malicious-class F1',xlabel='Model',ylim=(0,1),title='Domain-disjoint test: repeated scores')
    low=req[(req.target_rps==min(cfg['rps_levels']))&req.status.eq('ok')]
    sns.boxplot(data=low,x='model',y='latency_ms',hue='feature_set',order=cfg['models'],hue_order=['full','selected'],ax=axes[1],showfliers=True,fliersize=1)
    axes[1].set(ylabel='Scheduled-arrival latency (ms)',xlabel='Model',yscale='log',title=f'Lowest offered load: {min(cfg["rps_levels"])} RPS')
    for ax in axes:
        ax.set_xticks(range(len(cfg['models'])),[NAMES[m] for m in cfg['models']],rotation=20)
        for patch in ax.patches[len(cfg['models']):2*len(cfg['models'])]:patch.set_hatch('//')
    fig.suptitle(mark+'Full (16) and selected (7) features; baseline = Logistic Regression full')
    fig.tight_layout();save(fig,figures/'fig2_distributions')
    (out/'INTERPRETATION.txt').write_text(
        'New domain-grouped experiment. Never pool with previous batch results.\n'
        'Latency summaries are means of repeat-level percentiles, not pooled percentiles.\n'
        'CI resamples repeat summaries; conditional descriptive uncertainty, not a formal hypothesis test.\n'
        'Failed calls are excluded from latency quantiles and separately counted in error rates.\n'
        'Inspect actual_submission_rps and scheduler_lag_p95_ms: offered load is not guaranteed achieved load.\n'
        'Guardrails apply separately at each RPS; p99 threshold uses worst repeat.\n'
        'Low recall is a measured result, not a coding defect. Do not tune on test labels.\n',encoding='utf-8')
    print(quality[['model','feature_set','f1_mean','recall_mean']].to_string(index=False))
    print('Saved CSV and figures:',folder)
    return quality,latency,guard

def save(fig,path):
    fig.savefig(path.with_suffix('.png'),dpi=300,bbox_inches='tight')
    fig.savefig(path.with_suffix('.pdf'),bbox_inches='tight');plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True)
    analyze(p.parse_args().run_dir)
