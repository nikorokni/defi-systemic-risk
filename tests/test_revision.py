"""Integrity tests for research failure modes; fixtures below are synthetic.

These are software tests, not observations or scientific HF validation results.
"""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"revision/scripts"))
from historical_validation import rebuild_basic_hf, UnsupportedState
from audit_results import block_delta, paired


class ResearchIntegrity(unittest.TestCase):
    def test_hf_common_price_units_cancel_and_large_integers_remain_exact(self):
        # A position with 2000 collateral units, 1000 debt and an 80% threshold.
        c = dict(decimals=18, price_base=10**18, collateral_balance_raw=2000*10**18,
                 stable_debt_raw=0, variable_debt_raw=1000*10**18,
                 liquidation_threshold_bps=8000, collateral_enabled=True)
        self.assertEqual(rebuild_basic_hf([c])["health_factor_wad"], 16*10**17)
        c["price_base"] = 10**8
        self.assertEqual(rebuild_basic_hf([c])["health_factor_wad"], 16*10**17)

    def test_health_factor_is_not_defined_for_debt_free_accounts(self):
        c = dict(decimals=6, price_base=10**8, collateral_balance_raw=10**12,
                 stable_debt_raw=0, variable_debt_raw=0,
                 liquidation_threshold_bps=8000, collateral_enabled=True)
        self.assertIsNone(rebuild_basic_hf([c])["health_factor_wad"])

    def test_emode_fails_closed_and_disabled_collateral_is_not_counted(self):
        c = dict(decimals=6, price_base=10**8, collateral_balance_raw=10**12,
                 stable_debt_raw=10**10, variable_debt_raw=0,
                 liquidation_threshold_bps=8000, collateral_enabled=False)
        self.assertEqual(rebuild_basic_hf([c])["health_factor_wad"], 0)
        c["emode_category"] = 1
        with self.assertRaises(UnsupportedState):
            rebuild_basic_hf([c])

    def test_calendar_gap_is_not_a_previous_day(self):
        s = pd.Series([10., 20., 30.], index=pd.to_datetime(["2024-08-03", "2024-08-04", "2024-08-06"]))
        daily = s.reindex(pd.date_range(s.index.min(), s.index.max()))
        self.assertTrue(pd.isna(daily.shift(1).loc["2024-08-06"]))
        self.assertEqual(len(daily), 4)

    def test_paired_bootstrap_identical_models_gives_exactly_zero(self):
        d = pd.DataFrame(dict(origin=np.repeat(pd.date_range("2024-01-01", periods=30).astype(str), 2),
            version=["v2", "v3"]*30, fold=["test"]*60,
            actual=([0, 0, 0, 1, 0, 0]*10), a=np.tile([.1,.2,.3,.4,.5,.6],10)))
        d["b"] = d.a
        r = block_delta(d, "a", "b", repeats=100)
        self.assertTrue(all(x["difference"] == x["low"] == x["high"] == 0 for x in r))

    def test_outcome_pairing_refuses_missing_or_conflicting_cases(self):
        d = pd.DataFrame([dict(fold="A",origin="2024-04-01",version="v2",model=m,scenario="clean",
            actual=y, probability=.1, uncertainty_rank=.2) for m,y in [("one",0),("two",1)]])
        with self.assertRaises(ValueError):
            paired(d,"one","two")


if __name__ == "__main__":
    unittest.main()
