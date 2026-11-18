"""Unit tests for frozen-forecast operational-loss analysis."""
import importlib.util
from pathlib import Path
import unittest
import pandas as pd

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("decision_utility",root/"revision/scripts/decision_utility.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class LossTests(unittest.TestCase):
    def test_analytic_loss(self):
        frame=pd.DataFrame({"cohort":["test"]*4,"model":["a"]*4,"actual":[1,0,1,0],
                            "probability":[.8,.6,.2,.1]})
        row=m.calculate(frame).query("c_fn_over_c_fp==2").iloc[0]
        self.assertEqual((row.true_alerts,row.false_alerts,row.missed_positives),(1,1,1))
        self.assertEqual(row.cost_units,3)
    def test_frozen_inputs(self):
        if (root/"results/primary/predictions.csv.gz").exists():
            x=m.load_ledgers(root)
            self.assertEqual(len(x[(x.cohort=="later_2025_2026") & (x.model=="gru")]),744)
            self.assertEqual(len(x[(x.cohort=="original_2024_2025") & (x.model=="gru")]),1022)
    def test_aligned_bootstrap(self):
        dates=pd.date_range("2024-01-01",periods=20,tz="UTC")
        data=[dict(cohort="test",origin=d,version="v2",actual=int(d.day%4==0),
                  model=model,probability=p) for d in dates for model,p in [("a",.4),("b",.8)]]
        x=pd.DataFrame(data)
        r1=m.paired_interval(x,"test","a","b",5,replicates=20,seed=6)
        r2=m.paired_interval(x,"test","a","b",5,replicates=20,seed=6)
        self.assertEqual(r1,r2)

if __name__=="__main__":unittest.main()
