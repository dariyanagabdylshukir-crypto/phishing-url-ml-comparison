"""Publication exports for the completed RPS experiment."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
NAMES={'logistic_regression':'Logistic Regression','random_forest':'Random Forest','svm':'SVM','xgboost':'XGBoost'}


def plot_results(meta, tables, evaluation_calls, figures):
    cfg=meta['config'];q=tables['quality_repeats'];req=evaluation_calls
    quality=tables['quality_summary'];latency=tables['rps_summary']
    sns.set_theme(style='whitegrid',palette='colorblind')
    colors=dict(zip(cfg['models'],sns.color_palette('colorblind',len(cfg['models']))))
    figures=Path(figures);figures.mkdir(parents=True,exist_ok=True)
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
    save(fig,figures/'fig1_latency_vs_load')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    sns.boxplot(data=q,x='model',y='f1',hue='feature_set',order=cfg['models'],hue_order=['full','selected'],ax=axes[0],showfliers=True)
    sns.stripplot(data=q,x='model',y='f1',hue='feature_set',order=cfg['models'],hue_order=['full','selected'],dodge=True,ax=axes[0],palette=['.2','.2'],legend=False,size=3)
    axes[0].set(ylabel='Malicious-class F1',xlabel='Model',ylim=(0,1),title='Domain-disjoint test: repeated scores')
    low=req[(req.target_rps==min(cfg['rps_levels']))&req.status.eq('ok')]
    sns.boxplot(data=low,x='model',y='latency_ms',hue='feature_set',order=cfg['models'],hue_order=['full','selected'],ax=axes[1],showfliers=True,fliersize=1)
    axes[1].set(ylabel='Scheduled-arrival latency (ms)',xlabel='Model',yscale='log',title=f'Lowest offered load: {min(cfg["rps_levels"])} RPS')
    for ax, metric in [(axes[0], 'f1'), (axes[1], 'latency_ms')]:
        if metric == 'f1':
            summaries=quality
        else:
            summaries=latency[latency.target_rps.eq(min(cfg['rps_levels']))]
        for i, model in enumerate(cfg['models']):
            for j, fs in enumerate(['full','selected']):
                row=summaries[(summaries.model==model)&(summaries.feature_set==fs)].iloc[0]
                key='f1_mean' if metric=='f1' else 'p50_ms'
                lowkey='f1_ci_low' if metric=='f1' else 'p50_ms_ci_low'
                highkey='f1_ci_high' if metric=='f1' else 'p50_ms_ci_high'
                x=i+(-.2 if j==0 else .2)
                ax.vlines(x,row[lowkey],row[highkey],color='black',linewidth=2.5,zorder=9)
                ax.scatter([x],[row[key]],marker='D',s=20,color='black',zorder=10)
        for k, patch in enumerate(ax.patches[:2*len(cfg['models'])]):
            if k >= len(cfg['models']): patch.set_hatch('//')
    for ax in axes:
        ax.set_xticks(range(len(cfg['models'])),[NAMES[m] for m in cfg['models']],rotation=20)
        for patch in ax.patches[len(cfg['models']):2*len(cfg['models'])]:patch.set_hatch('//')
    fig.suptitle(mark+'Full (16) and selected (7) features; baseline = Logistic Regression full')
    fig.tight_layout();save(fig,figures/'fig2_distribution_boxplot')
    return [figures/'fig1_latency_vs_load.png', figures/'fig2_distribution_boxplot.png']

def save(fig,path):
    fig.savefig(path.with_suffix('.png'),dpi=300,bbox_inches='tight')
    fig.savefig(path.with_suffix('.pdf'),bbox_inches='tight');plt.close(fig)

