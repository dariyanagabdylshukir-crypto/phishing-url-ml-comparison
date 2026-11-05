"""Clean a local original good/bad CSV and sample an exact count. No download."""
import argparse
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split

def prepare(source,output,count,seed):
    source,output=Path(source),Path(output)
    if output.exists():raise FileExistsError('Choose a new output path; refusing overwrite')
    df=pd.read_csv(source,dtype={'url':'string','label':'string'}).dropna(subset=['url','label'])
    df['url']=df.url.str.strip();df['label']=df.label.str.strip()
    df=df[df.url.ne('')].copy()
    if not df.label.isin(['good','bad']).all():raise ValueError('Expected good/bad labels; unknown labels must not become benign')
    conflicts=df.groupby('url').label.nunique()
    df=df[~df.url.isin(conflicts[conflicts>1].index)].drop_duplicates('url').copy()
    df['label']=df.label.map({'good':0,'bad':1})
    if count<=0 or count>len(df):raise ValueError('Invalid sample size')
    if count<len(df):df,_=train_test_split(df,train_size=count,stratify=df.label,random_state=seed)
    df=df.sample(frac=1,random_state=seed).reset_index(drop=True)
    output.parent.mkdir(parents=True,exist_ok=True);df.to_csv(output,index=False)
    print(f'Saved {len(df)} rows; malicious share={df.label.mean():.6f}: {output}')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    p.add_argument('--count',type=int,default=20000);p.add_argument('--seed',type=int,default=42)
    a=p.parse_args();prepare(a.source,a.output,a.count,a.seed)
