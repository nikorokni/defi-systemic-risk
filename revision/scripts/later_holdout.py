"""Previously unscored later Aave holdout with a frozen meta gate and graph expiry.

The analysis specification is revision/later_holdout_plan.json. The pinned
network has no later snapshots; this is explicitly an out-of-support freshness
test, not evidence about a continually updated graph.
"""
from pathlib import Path
import hashlib
import json
import sys
from zipfile import ZipFile

import numpy as np
import pandas as pd
import torch
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"src"))
sys.path.insert(0, str(Path(__file__).parent))
from defi_risk.data import (oracle_features, reserve_features, parquet_member, window_totals, DAY,
                            HOUR, dated_borrowing)
from defi_risk.inputs import ForecastInputs
from defi_risk.models import (NeuralSpec, Scaling, TorchInput, stack_inputs, train_member, predict_member, Platt)
from audit_results import scores, paired, fit_gate, gate_design, block_delta, sha

BASE = ROOT/"revision"
OUT = BASE/"results/later_holdout"
PROC = BASE/"data/later_holdout"


def make_panel():
    grid = pd.date_range("2023-02-06", "2026-09-01", freq="D", inclusive="left", tz="UTC")
    with ZipFile(ROOT/"data/raw/eth_blocks_data.zip") as z:
        market, oa = oracle_features(z, grid)
    frames, event_audits = [], {}
    with ZipFile(ROOT/"data/raw/aave_data.zip") as z:
        for v in ["v2", "v3"]:
            name = f"data/AAVE/liquidations/aave_{v}_eth_liquidation_events.parquet"
            ev = parquet_member(z, name, ["timestamp", "amountUSD", "hash", "logIndex"])
            ev = ev.sort_values(["timestamp", "logIndex"])
            if ev.duplicated(["hash", "logIndex"]).any():
                raise ValueError("Duplicate raw events")
            t = pd.to_datetime(ev.timestamp, unit="s", utc=True).array.asi8
            values = ev.amountUSD.to_numpy(float)
            f = pd.DataFrame(index=grid)
            for n in [1, 3, 7]:
                usd, count = window_totals(t, values, grid.asi8-(n*DAY).value, grid.asi8)
                f[f"past_usd_{n}d"] = np.log1p(np.maximum(usd, 0))
                f[f"past_count_{n}d"] = np.log1p(count)
            f["future_usd_24h"] = np.maximum(window_totals(t, values, grid.asi8, grid.asi8+DAY.value)[0], 0)
            # Check completeness from publisher hourly coverage, including zero-event hours.
            hourname = f"data/AAVE/liquidations/aave_{v}_eth_liquidations_hourly.parquet"
            hourly = parquet_member(z, hourname, ["__index_level_0__", "liquidation_usd", "liquidation_count"])
            hourly.index = pd.to_datetime(hourly.pop("__index_level_0__"), utc=True)
            # The first buffered origins are not fitted or scored. Validate the
            # complete hourly record from the buffer start; all used 14-day
            # histories start later and therefore have full prior-event support.
            required = pd.date_range(grid[0], grid[-1]+DAY, freq="h", inclusive="left")
            hh = hourly.reindex(required)
            if hh.isna().any().any():
                raise ValueError("Incomplete hours in later target or inputs")
            recomputed = pd.DataFrame(dict(timestamp=pd.to_datetime(ev.timestamp, unit="s", utc=True), amount=values))
            check = recomputed.groupby(recomputed.timestamp.dt.floor("h")).amount.agg(["sum", "size"]).reindex(required, fill_value=0)
            if not np.isclose(check["sum"], hh.liquidation_usd, rtol=1e-8, atol=1e-5).all() or not (check["size"].to_numpy() == hh.liquidation_count.to_numpy()).all():
                raise ValueError("Events/hourly aggregate mismatch")
            local, ra = reserve_features(z, grid, v, ["dai", "usdc", "usdt", "weth"])
            f = pd.concat([f, local, market], axis=1)
            f["version"] = v
            f["is_v3"] = float(v == "v3")
            frames.append(f.reset_index(names="origin"))
            event_audits[v] = dict(rows=len(ev), hourly_coverage_start=str(required[0]),
                hourly_coverage_stop=str(required[-1]), all_hourly_totals_match=True,
                last_event_utc=str(pd.to_datetime(ev.timestamp.max(), unit="s", utc=True)))
    panel = pd.concat(frames).sort_values(["origin", "version"]).reset_index(drop=True)
    panel.to_parquet(PROC/"panel.parquet", index=False)
    (OUT/"source_coverage.json").write_text(json.dumps(event_audits, indent=2))
    return panel


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)
    spec_path = BASE/"later_holdout_plan.json"
    specification_hash = sha(spec_path)
    # Capture immutable specification hash before any later-holdout scoring.
    (OUT/"specification_sha256.txt").write_text(specification_hash+"\n")
    panel = make_panel()
    for n in ["graph_nodes.parquet", "graph_edges.parquet"]:
        import shutil
        shutil.copyfile(ROOT/"data/processed"/n, PROC/n)
    cfg = json.loads((ROOT/"configs/study.json").read_text())
    inp = ForecastInputs(PROC, panel, cfg)
    views = inp.arrays()
    dates = panel.origin
    def rows(start, stop):
        return np.flatnonzero(dates.ge(pd.Timestamp(start, tz="UTC")) & dates.lt(pd.Timestamp(stop, tz="UTC")))
    train = rows("2023-03-01", "2025-04-30")
    tune = rows("2025-05-01", "2025-06-27")
    cal = rows("2025-06-28", "2025-08-24")
    test = rows("2025-08-25", "2026-09-01")
    y = np.zeros(len(panel), np.int8)
    thresholds = {}
    for v in cfg["versions"]:
        cutoff = float(np.quantile(panel.future_usd_24h.iloc[train][panel.version.iloc[train].eq(v)], .95))
        thresholds[v] = cutoff
        sel = panel.version.eq(v)
        y[sel] = panel.future_usd_24h[sel].gt(cutoff)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    result = panel.iloc[test][["origin", "version"]].copy()
    result["actual"] = y[test]
    result["fold"] = "D_later"
    fitting = []
    for name, graph in [("gru", False), ("graph", True)]:
        spec = NeuralSpec(graph=graph)
        scaling = Scaling().fit(stack_inputs(views, graph=graph)[train])
        data = TorchInput(inp, views, spec, scaling, cfg["history_days"])
        ensemble, epochs = [], []
        for seed in cfg["seeds"]:
            model, epoch = train_member(seed, train, tune, y, data, None, spec, cfg)
            torch.save(model.state_dict(), OUT/f"{name}_{seed}.pt")
            ensemble.append(model)
            epochs.append(epoch)
        refm = np.stack([predict_member(m, data, cal) for m in ensemble])
        ref, refu = refm.mean(axis=0), refm.var(axis=0)
        platt = Platt().fit(ref, y[cal])
        m = np.stack([predict_member(net, data, test) for net in ensemble])
        result[name] = platt.predict(m.mean(axis=0))
        if graph:
            result["uncertainty_rank"] = np.searchsorted(np.sort(refu), m.var(axis=0), side="right")/len(refu)
        fitting.append(dict(model=name, epochs=epochs, scaling_mean=scaling.mean.tolist(),
            scaling_scale=scaling.scale.tolist(), platt_intercept=float(platt.intercept), platt_slope=float(platt.slope)))
        print("later_holdout", name, "epochs", epochs, flush=True)
    # Historical meta forecasts have already been scored. They are all strictly
    # earlier than D and are the only outcomes used to learn this gate.
    old = pd.read_csv(BASE/"inputs/Aave_Results_For_Review/results/primary/predictions.csv.gz")
    meta = paired(old, "graph_platt", "gru")
    select = pd.read_csv(BASE/"results/gate_B_hyperparameter_selection.csv")
    penalty = float(select.sort_values(["logloss", "penalty"], ascending=[True, False]).penalty.iloc[0])
    theta = fit_gate(meta, penalty)
    result["a"], result["b"] = result.graph, result.gru
    result["gate_weight"] = expit(gate_design(result)@theta)
    result["learned_gate"] = result.gate_weight*result.graph+(1-result.gate_weight)*result.gru
    result["fixed_half"] = .5*(result.graph+result.gru)
    w = .5*(1-result.uncertainty_rank)
    result["reliability_heuristic"] = w*result.graph+(1-w)*result.gru
    snap = inp.snapshot_dates(cfg["graph_lag_days"])
    result["graph_age_days"] = [(d-snap.loc[d]).days for d in result.origin]
    capped = np.where(result.graph_age_days <= 28, w, 0.)
    result["freshness_capped_heuristic"] = capped*result.graph+(1-capped)*result.gru
    result.to_csv(OUT/"predictions.csv", index=False)
    names = ["graph", "gru", "fixed_half", "reliability_heuristic", "learned_gate", "freshness_capped_heuristic"]
    table = pd.DataFrame([dict(model=m, **scores(result.actual, result[m])) for m in names])
    table.to_csv(OUT/"scores.csv", index=False)
    intervals = [dict(model=m, comparator="gru", **r) for m in names if m != "gru"
                 for r in block_delta(result, m, "gru", repeats=2000)]
    pd.DataFrame(intervals).to_csv(OUT/"paired_intervals.csv", index=False)
    (OUT/"run.json").write_text(json.dumps(dict(specification_sha256=specification_hash, thresholds=thresholds,
        source_archives={n:sha(ROOT/"data/raw"/n) for n in ["aave_data.zip", "eth_blocks_data.zip"]},
        fitting=fitting, train_rows=len(train), tuning_rows=len(tune), calibration_rows=len(cal), test_rows=len(test),
        test_start=str(dates.iloc[test].min()), test_end=str(dates.iloc[test].max()), gate_theta=theta.tolist(),
        gate_penalty=penalty, gate_meta_folds=["A", "B", "C"],
        graph_age_min_days=int(result.graph_age_days.min()), graph_age_max_days=int(result.graph_age_days.max()),
        fresh_independent_calendar=True, independent_data_source=False, prospective_deployment=False,
        externally_preregistered=False), indent=2))
    print(table.to_string(index=False), flush=True)


if __name__ == "__main__":
    run()