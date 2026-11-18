"""Executed shared-feature Aave-to-Compound transfer, conditional on publisher data.

This is a newly trained, common-schema GRU/graph experiment. It is NOT transfer
of the original reserve-augmented checkpoints, which were not supplied. Target
history estimates the target's stress definition, but never fits source-model
weights, stopping epochs, probability calibration or hyperparameters.

Daily Compound definitions are publisher-reported, with an assumed UTC day
alignment. Missing dates remain missing and invalidate affected 14-day windows.
"""
from pathlib import Path
from dataclasses import asdict
import hashlib
import json
import sys
import platform
import warnings

import ijson
import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"src"))
sys.path.insert(0, str(Path(__file__).parent))
from defi_risk.inputs import ForecastInputs
from defi_risk.models import (NeuralSpec, Scaling, TorchInput, stack_inputs,
                             train_member, predict_member, Platt)
from audit_results import scores, block_delta, sha

BASE = ROOT/"revision"
OUT = BASE/"results/transfer"
PROC = BASE/"data/transfer"
VERSIONS = {"v2": "111", "v3": "1599", "c2": "114", "c3": "2088"}


def make_graph():
    if (PROC/"graph_edges.parquet").exists():
        return
    mapping = json.loads((ROOT/"data/raw/dexposure_mapping.json").read_text())
    inverse = {n: v for v, n in VERSIONS.items()}
    names = {v: mapping[n]["name"] for v, n in VERSIONS.items()}
    if names != {"v2": "AAVE V2", "v3": "AAVE V3", "c2": "Compound V2", "c3": "Compound V3"}:
        raise ValueError(str(names))
    nodes, edges = [], []
    with (ROOT/"data/raw/dexposure.json").open("rb") as f:
        for day, snapshot in ijson.kvitems(f, "data", use_float=True):
            d = pd.Timestamp(day, tz="UTC")
            if not pd.Timestamp("2023-01-01", tz="UTC") <= d < pd.Timestamp("2025-01-01", tz="UTC"):
                continue
            for n in snapshot["nodes"]:
                if str(n["id"]) in mapping and np.isfinite(float(n["size"])) and float(n["size"]) >= 0:
                    nodes.append((d, str(n["id"]), float(n["size"])))
            ee = {}
            for link in snapshot["links"]:
                s, t, w = str(link["source"]), str(link["target"]), float(link["size"])
                if s == t or s not in mapping or t not in mapping or not np.isfinite(w) or w <= 0:
                    continue
                if s in inverse:
                    key = (inverse[s], "out", t)
                    ee[key] = ee.get(key, 0.)+w
                if t in inverse:
                    key = (inverse[t], "in", s)
                    ee[key] = ee.get(key, 0.)+w
            edges.extend((d, *k, w) for k, w in ee.items())
    pd.DataFrame(nodes, columns=["snapshot", "node", "size"]).to_parquet(PROC/"graph_nodes.parquet", index=False)
    pd.DataFrame(edges, columns=["snapshot", "version", "direction", "peer", "weight"]).sort_values(
        ["snapshot", "version", "direction", "weight", "peer"], ascending=[True, True, True, False, True]
    ).to_parquet(PROC/"graph_edges.parquet", index=False)


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    PROC.mkdir(parents=True, exist_ok=True)
    aave = pd.read_parquet(ROOT/"data/processed/panel.parquet")
    ed = pd.read_csv(BASE/"inputs/Compound_2023_2024_Data_Feasibility_Audit/dataRegression.csv")
    ed.index = pd.to_datetime(ed.Date, dayfirst=True, utc=True)
    if ed.index.duplicated().any():
        raise ValueError("Duplicate Compound dates")
    grid = pd.date_range("2023-02-06", "2025-01-01", freq="D", inclusive="left", tz="UTC")
    market_cols = [c for c in aave if c.startswith(("eth_", "btc_"))]
    market = aave[aave.version.eq("v2")].set_index("origin")[market_cols].reindex(grid)
    panels, thresholds = [], {}
    for v in VERSIONS:
        if v.startswith("v"):
            vol = aave[aave.version.eq(v)].set_index("origin").future_usd_24h.reindex(grid)
        else:
            vol = ed["Liquidate_Compoundv"+v[1]+"ethereum"].reindex(grid)
        training = vol.loc["2023-03-01":"2023-12-30"].dropna()
        cutoff = float(training.quantile(.95))
        if cutoff <= 0:
            raise ValueError("Nonpositive stress cutoff")
        thresholds[v] = cutoff
        d = pd.DataFrame(index=grid)
        for lag in [1, 3, 7]:
            total = vol.shift(1).rolling(lag, min_periods=lag).sum()
            d[f"past_usd_{lag}d"] = np.log1p(total/cutoff)
        d["future_usd_24h"] = vol
        d["label"] = np.where(vol.notna(), (vol > cutoff).astype(int), -1)
        d["version"] = v
        # Identity channel disabled for all domains; no Aave/Compound identifiers.
        d["is_v3"] = 0.
        d = pd.concat([d, market], axis=1)
        panels.append(d.reset_index(names="origin"))
    panel = pd.concat(panels).sort_values(["origin", "version"], key=lambda s: s.map(
        {v:i for i, v in enumerate(VERSIONS)}) if s.name == "version" else s).reset_index(drop=True)
    panel.to_parquet(PROC/"panel.parquet", index=False)
    make_graph()
    (OUT/"thresholds.json").write_text(json.dumps(thresholds, indent=2))
    # Same-day public datasets have distinct possible units/scope. This is a
    # provenance check, NOT independent chain reconciliation.
    check = []
    for v in ["v2", "v3"]:
        raw = aave[aave.version.eq(v)].set_index("origin").future_usd_24h
        ext = ed["Liquidate_Aave"+v+"ethereum"]
        z = pd.concat([raw.rename("archive_usd"), ext.rename("external_usd")], axis=1).dropna()
        z = z.loc["2023-03-01":"2024-12-31"]
        z["version"] = v
        check.append(z.reset_index(names="origin"))
    pd.concat(check).to_csv(OUT/"aave_publisher_overlap.csv", index=False)
    return panel, thresholds


def run():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    panel, cutoffs = prepare()
    cfg = dict(versions=VERSIONS, history_days=14, top_neighbours=16, graph_lag_days=7,
               hidden=24, batch_size=64, epochs=36, patience=7,
               learning_rate=.001, weight_decay=.001, seeds=[19, 43, 71, 101, 137])
    inp = ForecastInputs(PROC, panel, cfg)
    views = inp.arrays()
    local = panel[inp.local_cols].to_numpy()
    hist = inp.window_rows(np.arange(len(panel)))
    hist_valid = (hist >= 0).all(axis=1)
    hist_valid[hist_valid] &= np.isfinite(local[hist[hist_valid]]).all(axis=(1, 2))
    eligible = hist_valid & panel.label.ge(0).to_numpy()
    y = panel.label.to_numpy(np.int8)
    date = panel.origin
    def rows(start, stop, domain):
        return np.flatnonzero(eligible & date.ge(pd.Timestamp(start, tz="UTC")) &
            date.lt(pd.Timestamp(stop, tz="UTC")) & panel.version.isin(domain))
    source, target = ["v2", "v3"], ["c2", "c3"]
    test = rows("2024-04-01", "2025-01-01", list(VERSIONS))
    records, fits = [], []
    for domain_name, domain in [("aave_source_only", source), ("compound_supervised_reference", target)]:
        train = rows("2023-03-01", "2023-12-31", domain)
        tune = rows("2024-01-01", "2024-02-14", domain)
        cal = rows("2024-02-15", "2024-03-31", domain)
        if not (date.iloc[train].max()+pd.Timedelta(days=1) < date.iloc[tune].min() and
                date.iloc[cal].max()+pd.Timedelta(days=1) < date.iloc[test].min()):
            raise ValueError("Missing purge at source boundary")
        for model_name, graph in [("shared_gru", False), ("shared_graph", True)]:
            spec = NeuralSpec(graph=graph)
            scaling = Scaling().fit(stack_inputs(views, graph=graph)[train])
            data = TorchInput(inp, views, spec, scaling, cfg["history_days"])
            models, epochs = [], []
            for seed in cfg["seeds"]:
                net, ep = train_member(seed, train, tune, y, data, None, spec, cfg)
                torch.save(net.state_dict(), OUT/f"{domain_name}_{model_name}_{seed}.pt")
                models.append(net)
                epochs.append(ep)
            pcal = np.stack([predict_member(net, data, cal) for net in models]).mean(axis=0)
            calibration = Platt().fit(pcal, y[cal])
            pp = np.stack([predict_member(net, data, test) for net in models])
            pr = calibration.predict(pp.mean(axis=0))
            frame = panel.iloc[test][["origin", "version"]].copy()
            frame["actual"] = y[test]
            frame["probability"] = pr
            frame["raw_probability"] = pp.mean(axis=0)
            frame["uncertainty"] = pp.var(axis=0)
            frame["training_domain"] = domain_name
            frame["model"] = model_name
            records.append(frame)
            fits.append(dict(training_domain=domain_name, model=model_name, train_n=len(train), tune_n=len(tune),
                calibration_n=len(cal), train_positives=int(y[train].sum()), selected_epochs=epochs,
                scaling_mean=scaling.mean.tolist(), scaling_scale=scaling.scale.tolist(),
                platt_intercept=float(calibration.intercept), platt_slope=float(calibration.slope)))
            print(domain_name, model_name, "epochs", epochs, flush=True)
    preds = pd.concat(records, ignore_index=True)
    preds.to_csv(OUT/"predictions.csv.gz", index=False, compression={"method":"gzip", "mtime":0})
    table = []
    for (domain, model, version), g in preds.groupby(["training_domain", "model", "version"]):
        table.append(dict(training_domain=domain, model=model, version=version, **scores(g.actual, g.probability)))
    pd.DataFrame(table).to_csv(OUT/"scores.csv", index=False)
    # Source frozen predictions are paired against a supervised target reference.
    paired_results = []
    for model in ["shared_gru", "shared_graph"]:
        for v in target:
            g = preds[(preds.model == model) & (preds.version == v)]
            z = g[g.training_domain.eq("aave_source_only")].merge(
                g[g.training_domain.eq("compound_supervised_reference")],
                on=["origin", "version", "actual"], validate="one_to_one", suffixes=("_source", "_target"))
            z["fold"] = "external_2024"
            paired_results.extend(dict(model=model, version=v, contrast="source_minus_target_supervised", **r)
                for r in block_delta(z, "probability_source", "probability_target", repeats=2000))
    pd.DataFrame(paired_results).to_csv(OUT/"transfer_block_intervals.csv", index=False)
    pd.DataFrame(fits).to_json(OUT/"fitting_metadata.json", orient="records", indent=2)
    with (OUT/"run.json").open("w") as f:
        json.dump(dict(config=cfg, python=platform.python_version(), torch=torch.__version__,
             source_training="2023-03-01 to 2023-12-30", source_tuning="2024-01-01 to 2024-02-13",
             source_calibration="2024-02-15 to 2024-03-30", test="2024-04-01 to 2024-12-31",
             source_weights_frozen_for_target=True, original_reserve_models_transferred=False,
             target_history_use="2023 quantile for unit scaling and stress label, plus pre-origin lagged inputs",
             target_labels_used_in_source_model_fitting=False,
             target_supervised_models_are_separate_reference=True,
             independent_onchain_validation_completed=False,
             daily_timestamp_semantics="UTC assumed for publisher Date; not independently established",
             selection_caveat="Publisher removed five dates; incomplete 14-day calendar histories excluded, including crisis neighbourhoods",
             hypothesis_status="exploratory retrospective transfer",
             external_input_sha256=sha(BASE/"inputs/Compound_2023_2024_Data_Feasibility_Audit/dataRegression.csv")), f, indent=2)
    print(pd.DataFrame(table).to_string(index=False), flush=True)


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=UserWarning)
    run()