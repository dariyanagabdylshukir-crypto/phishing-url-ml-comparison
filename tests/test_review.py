"""Checks for leakage, embedded schemes, invalid labels and explicit worker errors."""
import sys
import tempfile
import unittest
from pathlib import Path
from queue import Queue
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from review_common import domain,load_dataset,split_indices
from run_review import worker

class FailingModel:
    def predict(self,x):raise RuntimeError('intentional verification error')

class ReviewTests(unittest.TestCase):
    def test_registrable_groups(self):
        self.assertEqual(domain('https://a.example.co.uk/path'),domain('b.example.co.uk'))
        self.assertNotEqual(domain('a.blogspot.com'),domain('b.blogspot.com'))
        self.assertEqual(domain('example.com/path?next=https://other.net'),'example.com')
    def test_unknown_label_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.csv';p.write_text('url,label\nexample.com,2\n')
            with self.assertRaises(ValueError):load_dataset(p)
    def test_worker_failure_is_not_benign_prediction(self):
        import time
        incoming,outgoing=Queue(),Queue();t=time.perf_counter_ns()
        incoming.put((1,'example.com',t,t));incoming.put(None)
        worker(FailingModel(),list(range(16)),incoming,outgoing)
        self.assertTrue(outgoing.get()['ready']);row=outgoing.get()
        self.assertEqual(row['status'],'error');self.assertIsNone(row['prediction'])
    def test_real_data_splits(self):
        p=Path(__file__).resolve().parents[1]/'data/sample/urls_research_sample.csv'
        df,_=load_dataset(p)
        for seed in range(42,52):
            tr,te=split_indices(df,seed,.3)
            self.assertFalse(set(df.iloc[tr].domain)&set(df.iloc[te].domain))
            self.assertEqual(len(tr)+len(te),len(df))

if __name__=='__main__':unittest.main()
