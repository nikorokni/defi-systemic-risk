"""Recompute supplied results without refitting the original forecast models.

Run from the repository root: python revision/scripts/audit_results.py
All confidence intervals are conditional on the archived fitted forecasts.
"""
from pathlib import Path
import hashlib
import json
import sys
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "revision"
INPUT = BASE / "inputs/Aave_Results_For_Review/results"
OUT = BASE / "results"
OUT.mkdir(parents=True, exist_ok=True)
EPS = 1e-6


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def scores(y, p):
    y, p = np.asarray(y), np.asarray(p, float)
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Invalid probabilities")
    return dict(n=len(y), positives=int(y.sum()), prevalence=float(y.mean()),
                ap=float(average_precision_score(y, p)) if y.any() else None,
                brier=float(brier_score_loss(y, p)),
                logloss=float(log_loss(y, np.clip(p, EPS, 1-EPS), labels=[0, 1])),
                auroc=float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None)


def block_delta(frame, a, b, block=14, repeats=2000, seed=20261117):
    """Moving calendar-day blocks, stratified by fold; same indices for both models.

    The two protocol versions on one date always travel together. Block endpoints
    never bridge a fold boundary. Duplicate sampled dates are intentionally retained.
    """
    x = frame.sort_values(["fold", "origin", "version"]).reset_index(drop=True)
    groups = []
    for _, g in x.groupby("fold", sort=True):
        days = [g.index[g.origin.eq(d)].to_numpy() for d in sorted(g.origin.unique())]
        L = min(block, len(days))
        groups.append((days, L))
    y, pa, pb = x.actual.to_numpy(), x[a].to_numpy(), x[b].to_numpy()
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(repeats):
        parts = []
        for days, L in groups:
            starts = rng.integers(0, len(days)-L+1, int(np.ceil(len(days)/L)))
            dd = np.concatenate([np.arange(t, t+L) for t in starts])[:len(days)]
            parts.extend(days[t] for t in dd)
        ix = np.concatenate(parts)
        if y[ix].sum() in (0, len(ix)):
            continue
        s1, s2 = scores(y[ix], pa[ix]), scores(y[ix], pb[ix])
        draws.append([s1[m]-s2[m] for m in ("ap", "brier", "logloss")])
    s1, s2 = scores(y, pa), scores(y, pb)
    arr = np.array(draws)
    return [dict(metric=m, difference=s1[m]-s2[m], low=float(np.quantile(arr[:, i], .025)),
                 high=float(np.quantile(arr[:, i], .975)), block_days=block,
                 valid_replicates=len(arr), requested_replicates=repeats)
            for i, m in enumerate(("ap", "brier", "logloss"))]


def paired(x, model_a, model_b, scenario="clean"):
    keys = ["fold", "origin", "version"]
    aa = x[(x.model == model_a) & (x.scenario == scenario)]
    bb = x[(x.model == model_b) & (x.scenario == scenario)]
    p = aa[keys+["actual", "probability", "uncertainty_rank"]].merge(
        bb[keys+["actual", "probability"]], on=keys, validate="one_to_one", suffixes=("_a", "_b"))
    if len(p) != len(aa) or len(p) != len(bb) or not (p.actual_a == p.actual_b).all():
        raise ValueError("Unpaired observations")
    return p.rename(columns={"actual_a": "actual", "probability_a": "a", "probability_b": "b"})


def gate_design(d):
    return np.column_stack([np.ones(len(d)), d.uncertainty_rank, np.abs(d.a-d.b), d.a])


def fit_gate(d, penalty):
    prior = np.array([-1.5, -1.0, 0.0, 0.0])
    z, y, a, b = gate_design(d), d.actual.to_numpy(), d.a.to_numpy(), d.b.to_numpy()
    def obj(t):
        w = expit(z@t)
        p = np.clip(w*a+(1-w)*b, EPS, 1-EPS)
        return -(y*np.log(p)+(1-y)*np.log1p(-p)).sum() + .5*penalty*np.square(t-prior).sum()
    fit = minimize(obj, prior, method="L-BFGS-B")
    if not fit.success:
        raise RuntimeError(str(fit.message))
    return fit.x


def run():
    x = pd.read_csv(INPUT/"primary/predictions.csv.gz")
    keys = ["fold", "origin", "version", "model", "scenario"]
    if x.duplicated(keys).any():
        raise ValueError("Duplicate forecast keys")
    consistency = x.groupby(["fold", "origin", "version"]).actual.nunique()
    if consistency.max() != 1:
        raise ValueError("Inconsistent outcome labels across models")
    rows = []
    for (model, scenario), g in x.groupby(["model", "scenario"]):
        rows.append(dict(model=model, scenario=scenario, **scores(g.actual, g.probability)))
    all_scores = pd.DataFrame(rows)
    all_scores.to_csv(OUT/"recomputed_metrics.csv", index=False)
    reported = pd.read_csv(INPUT/"metrics.csv")
    parity = all_scores.merge(reported, on=["model", "scenario"], suffixes=("_new", "_reported"))
    for m in ["ap", "brier", "logloss", "auroc"]:
        parity[m+"_abs_error"] = (parity[m+"_new"]-parity[m+"_reported"]).abs()
    parity.to_csv(OUT/"reported_metric_parity.csv", index=False)
    byfold = [dict(model=m, fold=f, **scores(g.actual, g.probability))
              for (m, f), g in x[x.scenario.eq("clean")].groupby(["model", "fold"])]
    pd.DataFrame(byfold).to_csv(OUT/"recomputed_by_fold.csv", index=False)
    git = pd.read_csv(ROOT/"results/primary/predictions.csv.gz")
    diff = x.merge(git, on=keys, validate="one_to_one", suffixes=("_attachment", "_github"))
    diff["absolute_probability_difference"] = (diff.probability_attachment-diff.probability_github).abs()
    dp = diff.groupby(["model", "scenario"]).agg(n=("actual_attachment", "size"),
          max_probability_difference=("absolute_probability_difference", "max"),
          changed_probabilities=("absolute_probability_difference", lambda s: int((s > 1e-8).sum())))
    dp.reset_index().to_csv(OUT/"attachment_vs_github.csv", index=False)
    contrasts = []
    for a, b in [("graph_platt", "gru"), ("graph_platt", "static_graph"),
                 ("graph_platt", "graph_no_sequence"), ("graph_platt", "graph_local"),
                 ("lightgbm_graph", "lightgbm"), ("persistence", "gru"),
                 ("graph_platt", "graph_raw")]:
        pp = paired(x, a, b)
        for L in ([7, 14, 28] if (a, b) == ("graph_platt", "gru") else [14]):
            contrasts.extend(dict(left=a, right=b, **r) for r in block_delta(pp, "a", "b", L))
    pd.DataFrame(contrasts).to_csv(OUT/"paired_block_intervals.csv", index=False)
    pp = paired(x, "graph_platt", "gru")
    A, B, C = [pp[pp.fold.eq(f)].copy() for f in "ABC"]
    if not (pd.to_datetime(A.origin).max() < pd.to_datetime(B.origin).min() < pd.to_datetime(C.origin).min()):
        raise ValueError("Invalid meta-learning chronology")
    tune = []
    for pen in [.1, 1., 10., 100.]:
        theta = fit_gate(A, pen)
        p = expit(gate_design(B)@theta)*B.a+(1-expit(gate_design(B)@theta))*B.b
        tune.append(dict(penalty=pen, **scores(B.actual, p)))
    tuned = min(tune, key=lambda r: (r["logloss"], -r["penalty"]))["penalty"]
    theta = fit_gate(pd.concat([A, B]), tuned)
    C["p_nested_gate"] = expit(gate_design(C)@theta)*C.a+(1-expit(gate_design(C)@theta))*C.b
    old_theta = fit_gate(pd.concat([A, B]), 10.)
    C["p_existing_gate_refit"] = expit(gate_design(C)@old_theta)*C.a+(1-expit(gate_design(C)@old_theta))*C.b
    C["p_half"] = .5*(C.a+C.b)
    C["p_heuristic"] = (.5*(1-C.uncertainty_rank))*C.a+(1-.5*(1-C.uncertainty_rank))*C.b
    C.to_csv(OUT/"chronological_gate_predictions.csv", index=False)
    models = [("graph", "a"), ("gru", "b"), ("half_fixed", "p_half"),
              ("reliability_heuristic", "p_heuristic"), ("learned_gate_penalty10", "p_existing_gate_refit"),
              ("nested_selected_gate", "p_nested_gate")]
    pd.DataFrame([dict(model=m, **scores(C.actual, C[col])) for m, col in models]).to_csv(
        OUT/"chronological_gate_scores.csv", index=False)
    pd.DataFrame(tune).to_csv(OUT/"gate_B_hyperparameter_selection.csv", index=False)
    intervals = []
    for m, col in models[2:]:
        intervals.extend(dict(model=m, comparator="gru", **r) for r in block_delta(C, col, "b"))
    pd.DataFrame(intervals).to_csv(OUT/"gate_block_intervals.csv", index=False)
    (OUT/"gate_fit.json").write_text(json.dumps(dict(selected_penalty=tuned, theta=theta.tolist(),
        selection_fold="B", meta_training_folds=["A", "B"], evaluation_fold="C",
        hypothesis_status="exploratory: all original test outcomes were inspected before this revision",
        fresh_independent_test=False), indent=2))
    mc = pd.read_csv(INPUT/"edge_monte_carlo/predictions.csv.gz")
    if mc.duplicated(["fold", "origin", "version", "scenario", "iteration"]).any():
        raise ValueError("Duplicate mask predictions")
    ms = pd.DataFrame([dict(scenario=s, iteration=i, **scores(g.actual, g.probability))
                       for (s, i), g in mc.groupby(["scenario", "iteration"])])
    ms.to_csv(OUT/"mask_scores_recomputed.csv", index=False)
    clean = ms[ms.scenario.eq("clean")].iloc[0]
    masks = []
    for scenario, g in ms[~ms.scenario.eq("clean")].groupby("scenario"):
        da, db = g.ap-clean.ap, g.brier-clean.brier
        masks.append(dict(scenario=scenario, masks=len(g), mean_ap_delta=da.mean(),
            ap_delta_p025=da.quantile(.025), ap_delta_p975=da.quantile(.975), fraction_ap_worse=(da<0).mean(),
            mean_brier_delta=db.mean(), brier_delta_p025=db.quantile(.025), brier_delta_p975=db.quantile(.975),
            fraction_brier_worse=(db>0).mean()))
    pd.DataFrame(masks).to_csv(OUT/"mask_paired_changes.csv", index=False)
    external = BASE/"inputs/Compound_2023_2024_Data_Feasibility_Audit/dataRegression.csv"
    ed = pd.read_csv(external)
    dates = pd.to_datetime(ed.Date, dayfirst=True)
    missing = pd.date_range(dates.min(), dates.max()).difference(dates).strftime("%Y-%m-%d").tolist()
    hf = pd.read_csv(BASE/"inputs/Aave_Q1_Additional_Validated_Results/results/q1_extensions/cred_aave_v2_sample.csv")
    hfdt = pd.to_datetime(hf.block_timestamp)
    overlap = hfdt.between("2023-03-01", "2025-08-25", inclusive="left").sum()
    computed = hf.sum_total_collateral_eth_x_LT/hf.total_debt_eth.replace(0, np.nan)
    report = dict(ledger_sha256=sha(INPUT/"primary/predictions.csv.gz"),
        github_ledger_sha256=sha(ROOT/"results/primary/predictions.csv.gz"),
        forecast_rows=len(x), unique_clean_forecasts=len(pp), positive_forecasts=int(pp.actual.sum()),
        primary_metric_max_absolute_error={m:float(parity[m+"_abs_error"].max()) for m in ["ap", "brier", "logloss", "auroc"]},
        attachment_github_label_mismatches=int((diff.actual_attachment != diff.actual_github).sum()),
        attachment_github_probability_changes=int((diff.absolute_probability_difference > 1e-8).sum()),
        compound_file_sha256=sha(external), compound_date_column="Date", compound_rows=len(ed),
        compound_missing_dates=missing, compound_gaps_are_not_zero_volume=True,
        cred_sample_rows=len(hf), cred_first_date=str(hfdt.min()), cred_last_date=str(hfdt.max()),
        cred_rows_overlapping_study=int(overlap),
        cred_algebraic_hf_max_error=float((computed-hf.HF).abs().max()),
        cred_sample_independent_chain_validation=False,
        original_base_models_refitted_by_this_script=False)
    (OUT/"integrity_audit.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)
    print(all_scores[(all_scores.scenario == "clean") & all_scores.model.isin(
        ["graph_platt", "gru", "persistence", "lightgbm"])].to_string(index=False), flush=True)


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=UserWarning)
    run()