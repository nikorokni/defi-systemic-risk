"""Walk-forward estimates on fixed, non-overlapping test intervals."""

import platform
from dataclasses import dataclass
from importlib.metadata import version as pkg_version

import numpy as np
import pandas as pd
import torch

from .data import DAY, HOUR, utc, write_json
from .inputs import CLEAN, SCENARIOS, ForecastInputs
from .models import (
    EPS, NeuralSpec, Scaling, TorchInput, fit_calibrators, fit_tabular,
    predict_member, stack_inputs, train_member,
)


@dataclass
class Split:
    name: str
    train: np.ndarray
    tune: np.ndarray
    calibrate: np.ndarray
    test: np.ndarray
    labels: np.ndarray
    cutoffs: dict
    lead: np.ndarray


def lead_time_hours(processed, frame, test_rows, labels, cutoffs, scaled, hours):
    lead = np.full(len(frame), np.nan)
    for version, cutoff in cutoffs.items():
        events = pd.read_parquet(processed / f"{version}_liquidation_times.parquet")
        event_times = events.timestamp.array.asi8
        amounts = events.amountUSD.to_numpy()
        selection = test_rows[(labels[test_rows] == 1) & (frame.version.iloc[test_rows].to_numpy() == version)]
        for row in selection:
            origin = frame.origin.iat[row].value
            end = origin + (HOUR * hours).value
            first, stop = np.searchsorted(event_times, [origin, end], side="left")
            hurdle = cutoff * frame.borrowing_scale_usd.iat[row] if scaled else cutoff
            above = np.flatnonzero(np.cumsum(amounts[first:stop]) > hurdle)
            if len(above):
                lead[row] = (event_times[first + above[0]] - origin) / HOUR.value
            else:
                raise ValueError(f"Positive label has no threshold crossing at row {row}")
    return lead


def create_split(processed, panel, cfg, fold, hours, scaled):
    start, development, test, stop = map(utc, (
        cfg["sample_start"], fold["development_start"], fold["test_start"], fold["test_stop"],
    ))
    tune_stop = development + ((test - development).days // 2) * DAY
    buffer = cfg["boundary_buffer_days"] * DAY
    end = panel.origin + hours * HOUR
    magnitude = panel[f"future_usd_{hours}h"]
    if scaled:
        magnitude = magnitude / panel.borrowing_scale_usd
    valid = np.isfinite(magnitude)

    def rows(left, right, embargo=buffer):
        return np.flatnonzero((panel.origin >= left) & (end <= right - embargo) & valid)

    train = rows(start, development)
    tune = rows(development, tune_stop)
    calibrate = rows(tune_stop, test)
    held_out = rows(test, stop, embargo=0 * DAY)
    labels = np.full(len(panel), -1, dtype=np.int8)
    cutoffs = {}
    for version in cfg["versions"]:
        select = panel.version.eq(version)
        cutoff = float(np.quantile(magnitude.iloc[train][select.iloc[train]], cfg["tail_quantile"]))
        labels[select & valid] = (magnitude[select & valid] > cutoff).astype(np.int8)
        cutoffs[version] = cutoff
    for name, selection in (("train", train), ("tune", tune), ("calibration", calibrate), ("test", held_out)):
        if len(selection) == 0:
            raise ValueError(f"{fold['id']} {name} is empty for horizon {hours}")
        if name in {"train", "calibration"} and set(labels[selection]) != {0, 1}:
            raise ValueError(f"{fold['id']} {name} does not have both classes for horizon {hours}")
    lead = lead_time_hours(processed, panel, held_out, labels, cutoffs, scaled, hours)
    return Split(fold["id"], train, tune, calibrate, held_out, labels, cutoffs, lead)


def append_forecast(records, panel, split, hours, model, scenario, p, reference,
                    config, uncertainty=None, reference_u=None):
    true = split.labels[split.test]
    threshold = float(np.quantile(reference, 1 - config["alert_validation_fraction"]))
    alert = p > threshold
    if uncertainty is None:
        uncertainty = np.full(len(p), np.nan)
        rank = uncertainty
        review = np.zeros(len(p), dtype=bool)
    else:
        rank = np.searchsorted(np.sort(reference_u), uncertainty, side="right") / len(reference_u)
        review = uncertainty > np.quantile(reference_u, 1 - config["review_validation_fraction"])
    origin = panel.iloc[split.test]
    records.append(pd.DataFrame({
        "origin": origin.origin.dt.strftime("%Y-%m-%d").to_numpy(),
        "version": origin.version.to_numpy(), "fold": split.name, "model": model, "scenario": scenario,
        "actual": true, "probability": np.clip(p, EPS, 1 - EPS),
        "uncertainty": uncertainty, "uncertainty_rank": rank,
        "p_threshold": threshold, "alert": alert.astype(np.int8),
        "review": review.astype(np.int8), "alert_with_review": (alert & ~review).astype(np.int8),
        "liquidation_usd": origin[f"future_usd_{hours}h"].to_numpy(),
        "true_lead_hours": split.lead[split.test],
    }))


def tabular_predictions(inputs, split, hours, features, config, records, full):
    clean = inputs.arrays()
    panel = inputs.panel
    y = split.labels
    tr, ca, ts = split.train, split.calibrate, split.test
    prior = {
        v: (y[tr][panel.version.iloc[tr] == v].sum() + 1) / (panel.version.iloc[tr].eq(v).sum() + 2)
        for v in inputs.versions
    }
    append_forecast(
        records, panel, split, hours, "prior", CLEAN,
        panel.version.iloc[ts].map(prior).to_numpy(), panel.version.iloc[ca].map(prior).to_numpy(), config,
    )
    local = clean.local
    past = local[:, [inputs.local_cols.index("past_usd_1d"), inputs.local_cols.index("is_v3")]]
    specifications = [
        ("persistence", "logistic", past, False),
        ("logistic_local", "logistic", local, False),
        ("logistic", "logistic", stack_inputs(clean), False),
        ("lightgbm", "lightgbm", stack_inputs(clean), False),
    ]
    if full:
        specifications.extend([
            ("lightgbm_graph", "lightgbm", stack_inputs(clean, graph=True), True),
            ("spillover_unweighted", "logistic", stack_inputs(clean, extra=features[:, :1]), False),
            ("spillover_weighted", "logistic", stack_inputs(clean, extra=features), False),
        ])
    for model_name, algorithm, x, graph in specifications:
        scaling = Scaling().fit(x[tr])
        model = fit_tabular(algorithm, scaling.transform(x[tr]), y[tr])

        def probabilities(matrix, rows):
            transformed = scaling.transform(matrix[rows])
            if algorithm == "lightgbm":
                return model.booster_.predict(transformed)
            return model.predict_proba(transformed)[:, 1]

        reference = probabilities(x, ca)
        scenarios = [CLEAN]
        if full and model_name in {"lightgbm", "lightgbm_graph"}:
            scenarios.extend(name for name in SCENARIOS if name not in (CLEAN, "augmentation"))
        for scenario in scenarios:
            x_scenario = x if scenario == CLEAN else stack_inputs(inputs.arrays(scenario), graph=graph)
            append_forecast(
                records, panel, split, hours, model_name, scenario,
                probabilities(x_scenario, ts), reference, config,
            )


def neural_predictions(inputs, split, hours, config, records, full):
    variants = {
        "gru": NeuralSpec(graph=False),
        "graph": NeuralSpec(graph=True),
    }
    if full:
        variants.update({
            "static_graph": NeuralSpec(graph=True, static=True),
            "graph_local": NeuralSpec(graph=True, market=False),
            "graph_no_sequence": NeuralSpec(graph=True),
            "robust_graph": NeuralSpec(graph=True, augment=True),
        })
    epochs = {}
    for name, spec in variants.items():
        clean_views = inputs.arrays(static=spec.static)
        x = stack_inputs(clean_views, market=spec.market, graph=spec.graph)
        scaling = Scaling().fit(x[split.train])
        sequence_days = 1 if name == "graph_no_sequence" else config["history_days"]
        clean = TorchInput(inputs, clean_views, spec, scaling, sequence_days)
        augmented = TorchInput(inputs, inputs.arrays("augmentation"), spec, scaling, sequence_days) if spec.augment else None
        epochs[name] = []
        ensemble = []
        for seed in config["seeds"]:
            model, epoch = train_member(
                seed, split.train, split.tune, split.labels, clean, augmented, spec, config,
            )
            epochs[name].append(epoch)
            ensemble.append(model)
        validation = np.array([predict_member(model, clean, split.calibrate) for model in ensemble])
        ref, ref_u = validation.mean(axis=0), validation.var(axis=0)
        calibrators = fit_calibrators(ref, split.labels[split.calibrate])
        scenarios = [CLEAN]
        if full and name in {"gru", "graph", "robust_graph"}:
            scenarios.extend(scenario for scenario in SCENARIOS if scenario not in (CLEAN, "augmentation"))
        for scenario in scenarios:
            data = clean if scenario == CLEAN else TorchInput(inputs, inputs.arrays(scenario), spec, scaling, sequence_days)
            members = np.array([predict_member(model, data, split.test) for model in ensemble])
            p, u = members.mean(axis=0), members.var(axis=0)
            if name == "graph" and scenario == CLEAN:
                for key, score, reference in (
                    ("graph_seed", members[0], validation[0]),
                    ("graph_raw", p, ref),
                    ("graph_isotonic", calibrators["isotonic"].predict(p), calibrators["isotonic"].predict(ref)),
                ):
                    append_forecast(records, inputs.panel, split, hours, key, scenario, score, reference, config)
            model_name = "graph_platt" if name == "graph" else name
            calibration = calibrators["platt"]
            append_forecast(
                records, inputs.panel, split, hours, model_name, scenario,
                calibration.predict(p), calibration.predict(ref), config, u, ref_u,
            )
        print(f"{split.name} {name} epochs {epochs[name]}", flush=True)
    return epochs


def evaluate(processed, out, cfg, hours=24, scaled=False):
    out.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    panel = pd.read_parquet(processed / "panel.parquet")
    inputs = ForecastInputs(processed, panel, cfg)
    associations = inputs.other_version_signal()
    full = hours == cfg["primary_horizon_hours"] and not scaled
    forecasts = []
    bookkeeping = {
        "target": "borrowing_scaled" if scaled else "usd", "horizon_hours": hours,
        "static_graph_anchor": inputs.anchor.isoformat(),
        "software": {name: pkg_version(name) for name in (
            "numpy", "pandas", "pyarrow", "scikit-learn", "torch", "lightgbm", "scipy",
        )},
        "python": platform.python_version(), "folds": {},
        "observed_directed_share": {
            v: int(np.count_nonzero(associations[panel.version.eq(v), 1])) for v in inputs.versions
        },
    }
    for fold in cfg["folds"]:
        split = create_split(processed, panel, cfg, fold, hours, scaled)
        fold_info = {"cutoff": split.cutoffs}
        for part in ("train", "tune", "calibrate", "test"):
            rows = getattr(split, part)
            row_panel = panel.iloc[rows]
            fold_info[part] = {
                "first": row_panel.origin.min().date().isoformat(),
                "last": row_panel.origin.max().date().isoformat(),
                "rows": len(rows), "positives": int(split.labels[rows].sum()),
                "positives_by_version": {
                    v: int(split.labels[rows][row_panel.version == v].sum()) for v in inputs.versions
                },
            }
        print(f"Starting {split.name}: {fold_info['test']}", flush=True)
        tabular_predictions(inputs, split, hours, associations, cfg, forecasts, full)
        fold_info["selected_epochs"] = neural_predictions(inputs, split, hours, cfg, forecasts, full)
        bookkeeping["folds"][split.name] = fold_info
    book = out / "run.json"
    write_json(book, bookkeeping)
    prediction = pd.concat(forecasts, ignore_index=True).sort_values(
        ["model", "scenario", "origin", "version"], kind="stable",
    )
    prediction.to_csv(
        out / "predictions.csv.gz", index=False, float_format="%.14g",
        compression={"method": "gzip", "compresslevel": 9, "mtime": 0},
    )
    return prediction
