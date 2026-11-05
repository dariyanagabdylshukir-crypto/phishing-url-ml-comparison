"""Domain-disjoint quality evaluation and local open-loop RPS benchmark.
One request = one URL; one inference worker; no requests to URL destinations.
Existing batch logs and figures are never overwritten.
"""
import os
for name in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[name] = '1'
import argparse
import hashlib
import json
import multiprocessing as mp
import platform
import queue
import time
import uuid
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import numpy as np
import yaml
from sklearn.metrics import confusion_matrix
from threadpoolctl import threadpool_limits
from review_models import build_model
from review_common import load_dataset, split_indices, features, SELECTED

ROOT = Path(__file__).resolve().parents[1]

def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding='utf-8')

def worker(model, cols, incoming, outgoing):
    with threadpool_limits(limits=1):
        outgoing.put({'ready':True})
        while True:
            job = incoming.get()
            if job is None: break
            number, url, scheduled, submitted = job
            start = time.perf_counter_ns()
            error = None
            try:
                prediction = int(model.predict(np.asarray([features(url)],dtype=float)[:,cols])[0])
            except Exception as exc:
                error = {'type':type(exc).__name__, 'message':str(exc)}
                prediction = None
            end = time.perf_counter_ns()
            outgoing.put({'call':number, 'status':'error' if error else 'ok',
                'error':error, 'prediction':prediction, 'scheduled_ns':scheduled,
                'submitted_ns':submitted, 'started_ns':start, 'completed_ns':end,
                'latency_ms':(end-scheduled)/1e6, 'response_ms':(end-submitted)/1e6,
                'service_ms':(end-start)/1e6, 'queue_ms':(start-submitted)/1e6,
                'scheduler_lag_ms':(submitted-scheduled)/1e6})

def trial(proc, incoming, outgoing, workload, rate, timeout):
    count = len(workload)
    start = time.perf_counter_ns()+50_000_000
    submissions = []
    for i,u in enumerate(workload):
        scheduled = start+round(i*1e9/rate)
        left = (scheduled-time.perf_counter_ns())/1e9
        if left>0: time.sleep(left)
        submitted = time.perf_counter_ns()
        submissions.append(submitted)
        incoming.put((i+1,str(u),scheduled,submitted))
    rows=[]
    deadline=time.monotonic()+timeout
    while len(rows)<count:
        left=deadline-time.monotonic()
        if left<=0 or not proc.is_alive():
            raise RuntimeError('Incomplete trial: worker stopped or drain deadline exceeded')
        try: rows.append(outgoing.get(timeout=min(left,1)))
        except queue.Empty: continue
    rows.sort(key=lambda r:r['call'])
    elapsed=(max(r['completed_ns'] for r in rows)-start)/1e9
    actual=(count-1)/((submissions[-1]-submissions[0])/1e9) if count>1 else None
    for row in rows:
        row.update(target_rps=float(rate), actual_submission_rps=actual,
                   trial_elapsed_s=elapsed, n_requests=count,
                   throughput_rps=sum(r['status']=='ok' for r in rows)/elapsed)
    return rows

def run(config):
    cfg=yaml.safe_load(config.read_text(encoding='utf-8'))
    if cfg['repeats']<2 or cfg['requests_per_level']<100 or min(cfg['rps_levels'])<=0:
        raise ValueError('Need >=2 repeats, >=100 calls per level and positive RPS')
    if set(cfg['feature_sets'])-{'full','selected'}: raise ValueError('Unknown feature set')
    path=ROOT/cfg['dataset']
    df,audit=load_dataset(path)
    print(json.dumps(audit),flush=True)
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]
    out=ROOT/cfg['output_root']/run_id
    out.mkdir(parents=True)
    df.to_csv(out/'cleaned_dataset.csv',index=False)
    meta={'status':'running','run_id':run_id,'config':cfg,'audit':audit,
          'dataset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
          'python':platform.python_version(),'platform':platform.platform(),
          'processor':platform.processor(),'logical_cpus':os.cpu_count(),
          'packages':{n:version(n) for n in ['numpy','pandas','scikit-learn','xgboost','tldextract','threadpoolctl','PyYAML']},
          'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')},
          'split_method':'GroupShuffleSplit by registrable domain, private PSL suffixes included; 30% groups, row ratio may differ',
          'timing_scope':'Local one-worker inference including feature extraction; no HTTP/network; 1 thread for numerical libraries',
          'latency_definition':'completion minus intended arrival (scheduler lag + queue + service)',
          'ci_scope':'Conditional on this dataset and repeated domain splits; repeats share observations',
          'splits':[]}
    write_json(out/'metadata.json',meta)
    urls=df.url.to_numpy(); y=df.label.to_numpy()
    x=np.asarray([features(u) for u in urls],dtype=float)
    ctx=mp.get_context('spawn')
    try:
        with (out/'raw.jsonl').open('w',encoding='utf-8') as log:
            def emit(row): log.write(json.dumps(row)+'\n');log.flush()
            for rep in range(cfg['repeats']):
                seed=cfg['seed']+rep
                tr,te=split_indices(df,seed,cfg['test_domain_fraction'])
                split={'repeat':rep+1,'seed':seed,'n_train':len(tr),'n_test':len(te),
                    'test_row_fraction':len(te)/len(df),'shared_domains':0,
                    'train_positive_share':float(y[tr].mean()),'test_positive_share':float(y[te].mean())}
                meta['splits'].append(split);write_json(out/'metadata.json',meta)
                # Save exact membership for audit, independent of future library versions.
                np.savez_compressed(out/f'split_{rep+1:02d}.npz',train=tr,test=te)
                rng=np.random.default_rng(seed)
                conditions=[(fs,m) for fs in cfg['feature_sets'] for m in cfg['models']]
                rng.shuffle(conditions)
                # Same requests per repeat and rate for every configuration.
                workloads={float(r):urls[te][np.random.default_rng(seed+int(r)).choice(len(te),cfg['requests_per_level'],replace=True)] for r in cfg['rps_levels']}
                for fs,name in conditions:
                    cols=list(range(16)) if fs=='full' else SELECTED
                    base={'repeat':rep+1,'seed':seed,'model':name,'feature_set':fs}
                    model=build_model(name,seed)
                    try:
                        with threadpool_limits(limits=1):
                            t0=time.perf_counter();model.fit(x[tr][:,cols],y[tr]);train_ms=(time.perf_counter()-t0)*1000
                            pred=model.predict(x[te][:,cols])
                    except Exception as exc:
                        emit(dict(base,type='quality',status='error',error=repr(exc)))
                        raise RuntimeError('Training/quality failed; no invented predictions') from exc
                    tn,fp,fn,tp=map(int,confusion_matrix(y[te],pred,labels=[0,1]).ravel())
                    emit(dict(base,type='quality',status='ok',tn=tn,fp=fp,fn=fn,tp=tp,
                              n_test=len(te),train_ms=train_ms,majority_accuracy=float(max(y[te].mean(),1-y[te].mean()))))
                    incoming=ctx.Queue();outgoing=ctx.Queue()
                    proc=ctx.Process(target=worker,args=(model,cols,incoming,outgoing));proc.start()
                    try:
                        if not outgoing.get(timeout=90).get('ready'):raise RuntimeError('Worker not ready')
                        for rate in rng.permutation(cfg['rps_levels']):
                            rate=float(rate)
                            warm=urls[te][:cfg['warmup_calls']]
                            for phase,work in [('warmup',warm),('eval',workloads[rate])]:
                                rows=trial(proc,incoming,outgoing,work,rate,cfg['drain_timeout_s'])
                                for row in rows:emit(dict(base,type='request',phase=phase,**row))
                            print(f'repeat={rep+1}/{cfg["repeats"]} {fs} {name} {rate:g} RPS done',flush=True)
                    finally:
                        incoming.put(None);proc.join(timeout=5)
                        if proc.is_alive():proc.terminate();proc.join()
                        incoming.close();outgoing.close()
        meta['status']='complete'
    except Exception as exc:
        meta['status']='failed';meta['error']=repr(exc)
        raise
    finally: write_json(out/'metadata.json',meta)
    print('Saved:',out,flush=True)
    return out

if __name__=='__main__':
    mp.freeze_support()
    p=argparse.ArgumentParser();p.add_argument('--config',default='configs/review_smoke.yaml')
    run(ROOT/p.parse_args().config)
