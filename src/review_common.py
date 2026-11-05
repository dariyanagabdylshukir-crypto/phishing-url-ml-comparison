"""Shared validation, registrable-domain grouping and lexical features."""
import ipaddress
import re
from urllib.parse import urlsplit
import numpy as np
import pandas as pd
import tldextract
from sklearn.model_selection import GroupShuffleSplit

# Use the package's bundled PSL snapshot: no network calls, including private suffixes.
EXTRACT = tldextract.TLDExtract(suffix_list_urls=(), include_psl_private_domains=True)
SELECTED = [0, 2, 3, 4, 8, 10, 11]

def hostname(url):
    host = urlsplit(url if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*://', url) else '//'+url).hostname
    if not host or any(c.isspace() for c in host):
        raise ValueError('URL has no valid hostname')
    return host.lower().rstrip('.').encode('idna').decode('ascii')

def domain(url):
    host = hostname(url)
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        parsed = EXTRACT(host)
        if not parsed.suffix or not parsed.domain:
            raise ValueError('Hostname has no recognised public suffix')
        return parsed.top_domain_under_public_suffix

def features(url):
    s = url.lower()
    return [len(s), len(hostname(s)), s.count('.'), s.count('-'), s.count('/'),
            s.count('?'), s.count('='), sum(c.isdigit() for c in s),
            int(s.startswith('https://')), int('@' in s),
            *[int(w in s) for w in ['login','verify','account','secure','confirm','update']]]

def load_dataset(path):
    df = pd.read_csv(path, dtype={'url':'string'})
    if not {'url','label'} <= set(df):
        raise ValueError('Expected url and label columns')
    original = len(df)
    df = df.dropna(subset=['url','label']).copy()
    df['url'] = df['url'].str.strip()
    df = df[df['url'].ne('')].copy()
    if not df['label'].isin([0,1]).all():
        raise ValueError('Labels must be exactly 0=benign and 1=malicious')
    conflicts = df.groupby('url')['label'].nunique()
    conflicting = set(conflicts[conflicts>1].index)
    df = df[~df.url.isin(conflicting)].drop_duplicates('url').copy()
    domains = []
    for u in df.url:
        try: domains.append(domain(u))
        except (ValueError, UnicodeError): domains.append(None)
    df['domain'] = domains
    invalid = int(df.domain.isna().sum())
    df = df.dropna(subset=['domain']).reset_index(drop=True)
    df['label'] = df.label.astype(int)
    if set(df.label) != {0,1}: raise ValueError('Both classes required')
    audit = {'source_rows':original, 'retained_rows':len(df),
             'excluded_rows':original-len(df), 'invalid_domain_rows':invalid,
             'conflicting_urls':len(conflicting), 'unique_domains':df.domain.nunique(),
             'class_counts':{str(k):int(v) for k,v in df.label.value_counts().items()},
             'positive_class':'malicious; no phishing-specific label'}
    return df, audit

def split_indices(df, seed, test_fraction):
    # Fraction applies to groups, not rows; record the achieved row fraction.
    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=test_fraction,
                                   random_state=seed).split(df, df.label, df.domain))
    if set(df.iloc[tr].domain)&set(df.iloc[te].domain): raise AssertionError('Domain leakage')
    if set(df.iloc[tr].label)!={0,1} or set(df.iloc[te].label)!={0,1}:
        raise ValueError('A split lacks a class; do not silently choose a better split')
    return tr, te
