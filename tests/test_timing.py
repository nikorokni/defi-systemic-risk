import unittest

import numpy as np
import pandas as pd

from defi_risk.data import HOUR, asof, utc, window_totals
from defi_risk.metrics import paired_trials
from defi_risk.models import Platt


class Invariants(unittest.TestCase):
    def test_asof_is_strict_and_bounded(self):
        t = utc("2024-03-01")
        observations = pd.DataFrame({
            "timestamp": [t - 3 * HOUR, t, t + 3 * HOUR],
            "price": [100, 101, 102],
        })
        got = asof(observations, pd.DatetimeIndex([t, t + HOUR]), 2 * HOUR)
        self.assertTrue(pd.isna(got.price.iloc[0]))
        self.assertEqual(got.price.iloc[1], 101)

    def test_window_boundary_has_one_owner(self):
        times = np.array([10, 11, 15, 20])
        amounts = np.array([1.0, 2.0, 5.0, 10.0])
        totals, counts = window_totals(times, amounts, np.array([10, 15]), np.array([15, 20]))
        np.testing.assert_array_equal(totals, [3.0, 5.0])
        np.testing.assert_array_equal(counts, [2, 1])

    def test_platt_is_order_preserving(self):
        x = np.array([0.08, 0.2, 0.3, 0.4, 0.5, 0.65])
        y = np.array([0, 0, 1, 0, 1, 1])
        out = Platt().fit(x, y).predict(x)
        self.assertTrue(np.all(np.diff(out) > 0))
        self.assertTrue(np.all((out > 0) & (out < 1)))

    def test_bootstrap_preserves_paired_outcomes(self):
        frame = pd.DataFrame({
            "fold": "A", "origin": np.repeat(["2024-01-01", "2024-01-02", "2024-01-03"], 2),
            "version": ["v2", "v3"] * 3, "actual": [0, 1, 1, 0, 0, 1],
            "probability": [0.1, 0.8, 0.75, 0.2, 0.4, 0.6],
        })
        result = paired_trials(frame, frame, length=2, repeats=20)
        self.assertEqual(result["ap_delta"], 0.0)
        self.assertEqual(result["brier_hi"], 0.0)
        broken = frame.copy()
        broken.loc[0, "actual"] = 1
        with self.assertRaisesRegex(ValueError, "identical observations"):
            paired_trials(frame, broken, length=2, repeats=20)


if __name__ == "__main__":
    unittest.main()
