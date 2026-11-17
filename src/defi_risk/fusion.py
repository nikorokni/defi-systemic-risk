"""Prespecified, label-blind graph/local forecast fusion.

This is a benchmark, not a fitted or validated causal mechanism.
All weights are declared before reading the held-out outcomes.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss

JOIN = ["fold", "origin", "version", "scenario"]
EPS = 1e-6


def mix_forecasts(graph: pd.DataFrame, local: pd.DataFrame, weight: float = 0.5) -> pd.DataFrame:
    """Pair the same held-out target, then compute fixed and reliability-weighted mixtures."""
    required = set(JOIN + ["actual", "probability"])
    if not required.issubset(graph) or not required.issubset(local):
        raise ValueError("Missing required prediction columns")
    if not 0 <= weight <= 1:
        raise ValueError("weight must lie between 0 and 1")
    g = graph.copy()
    l = local.copy()
    if g.duplicated(JOIN).any() or l.duplicated(JOIN).any():
        raise ValueError("Duplicate forecast keys")
    paired = g.merge(l[JOIN + ["actual", "probability"]], on=JOIN, how="inner",
                     validate="one_to_one", suffixes=("_graph", "_local"))
    if len(paired) != len(g) or len(paired) != len(l):
        raise ValueError("Both models must cover identical origin/version/scenario rows")
    if not np.array_equal(paired.actual_graph.to_numpy(), paired.actual_local.to_numpy()):
        raise ValueError("Different labels for the same forecast")
    p_g = paired.probability_graph.to_numpy(float)
    p_l = paired.probability_local.to_numpy(float)
    if not np.isfinite(p_g).all() or not np.isfinite(p_l).all():
        raise ValueError("Nonfinite probability")
    # Existing ledger reports empirical disagreement percentile from calibration (no test labels).
    # The fixed 0.5 multiplier is NOT tuned on the test data.
    if "uncertainty_rank" not in paired:
        raise ValueError("Graph calibration-based uncertainty_rank is required")
    r = paired.uncertainty_rank.to_numpy(float)
    if not np.isfinite(r).all() or np.any((r < 0) | (r > 1)):
        raise ValueError("Invalid uncertainty percentile")
    quality_weight = weight * (1.0 - r)
    paired["p_graph"] = p_g
    paired["p_local"] = p_l
    paired["p_fixed"] = np.clip(weight*p_g + (1-weight)*p_l, EPS, 1-EPS)
    paired["graph_weight"] = quality_weight
    paired["p_reliability"] = np.clip(quality_weight*p_g + (1-quality_weight)*p_l, EPS, 1-EPS)
    paired["actual"] = paired.actual_graph.astype(int)
    return paired


def score(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for scenario, frame in df.groupby("scenario", sort=True):
        y = frame.actual.to_numpy()
        for model, col in [("graph", "p_graph"), ("local", "p_local"),
                           ("fixed_half", "p_fixed"), ("uncertainty_gate", "p_reliability")]:
            p = frame[col].to_numpy()
            records.append({"scenario":scenario, "model":model, "n":len(y),
                            "positives":int(y.sum()),
                            "ap":float(average_precision_score(y, p)) if y.any() else np.nan,
                            "brier":float(brier_score_loss(y,p)),
                            "logloss":float(log_loss(y,p,labels=[0,1]))})
    return pd.DataFrame(records)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", type=Path, default=Path("results/primary/predictions.csv.gz"))
    ap.add_argument("--out", type=Path, default=Path("results/fusion"))
    args = ap.parse_args()
    x = pd.read_csv(args.ledger)
    g = x[x.model.eq("graph_platt")].copy()
    l = x[x.model.eq("gru")].copy()
    # Comparison across matching scenarios only. No tuning on test labels.
    matched = sorted(set(g.scenario.unique()) & set(l.scenario.unique()))
    result = mix_forecasts(g[g.scenario.isin(matched)], l[l.scenario.isin(matched)])
    args.out.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.out/"paired_predictions.csv", index=False)
    scores = score(result)
    scores.to_csv(args.out/"scores.csv", index=False)
    print(scores.to_string(index=False))
    print("Prespecified exploratory post-hoc benchmark only; not an unbiased trained gate.")


if __name__ == "__main__":
    main()
