import unittest
import numpy as np
import pandas as pd

from defi_risk.fusion import mix_forecasts, score


class FusionTests(unittest.TestCase):
    def setUp(self):
        base = pd.DataFrame({
            "fold":["A","A","B","B"],"origin":["2024-01-01","2024-01-02","2025-01-01","2025-01-02"],
            "version":["v2","v3","v2","v3"],"scenario":["clean"]*4,"actual":[0,1,0,1]})
        self.graph=base.assign(probability=[.15,.75,.3,.8],uncertainty_rank=[0,.25,.5,1])
        self.local=base.assign(probability=[.1,.6,.2,.7])

    def test_fixed_and_reliability(self):
        result=mix_forecasts(self.graph,self.local)
        np.testing.assert_allclose(result.p_fixed,[.125,.675,.25,.75])
        np.testing.assert_allclose(result.graph_weight,[.5,.375,.25,0])
        np.testing.assert_allclose(result.p_reliability,[.125,.65625,.225,.7])
        self.assertEqual(set(score(result).model),{"graph","local","fixed_half","uncertainty_gate"})

    def test_no_label_mismatch(self):
        modified=self.local.copy()
        modified.loc[1,"actual"]=0
        with self.assertRaises(ValueError):
            mix_forecasts(self.graph,modified)

    def test_no_missing_origins(self):
        with self.assertRaises(ValueError):
            mix_forecasts(self.graph,self.local.iloc[:3])

    def test_no_duplicate_keys(self):
        with self.assertRaises(ValueError):
            mix_forecasts(pd.concat([self.graph,self.graph.iloc[:1]]),self.local)

if __name__=="__main__":
    unittest.main()
