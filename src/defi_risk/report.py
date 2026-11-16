"""Generate paper tables and figures from the written forecast ledger."""

import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .metrics import alert_scores, paired_trials, probability_scores, reliability_table, risk_coverage

GRAPH = "graph_platt"
ROBUST = "robust_graph"
CORE = ("prior", "persistence", "logistic", "lightgbm", "gru", GRAPH, ROBUST)
COLORS = {GRAPH: "#006f73", ROBUST: "#713a80", "gru": "#1e4d88", "lightgbm": "#ae4f19"}
NAMES = {GRAPH: "Temporal graph + Platt", ROBUST: "Augmented graph + Platt", "gru": "GRU + Platt",
         "lightgbm": "LightGBM", "lightgbm_graph": "LightGBM + graph summaries"}
PALETTE = ["#006f73", "#ad531d", "#1e4d88"]


def metrics_table(predictions, groups):
    items = []
    for key, part in predictions.groupby(groups, sort=True):
        key = key if isinstance(key, tuple) else (key,)
        items.append(dict(zip(groups, key, strict=True)) | probability_scores(
            part.actual.to_numpy(), part.probability.to_numpy(),
        ))
    return pd.DataFrame(items)


def event_windows(p, cfg):
    report = []
    for window in cfg["historical_windows"]:
        found = p.loc[(p.origin >= window["start"]) & (p.origin < window["stop"])]
        for (version, model), frame in found.groupby(["version", "model"]):
            report.append({
                "window": window["id"], "version": version, "model": model,
                "n_origins": len(frame), "positives": int(frame.actual.sum()),
                "total_liquidation_usd": frame.liquidation_usd.sum(),
                "peak_daily_liquidation_usd": frame.liquidation_usd.max(),
                "daily_alerts": int(frame.alert.sum()),
                "positive_alerts": int((frame.alert.astype(bool) & frame.actual.astype(bool)).sum()),
                "brier": np.square(frame.probability - frame.actual).mean(),
            })
    return pd.DataFrame(report)


def save_figure(fig, directory, name):
    fig.savefig(directory / f"{name}.pdf", bbox_inches="tight", metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(directory / f"{name}.png", bbox_inches="tight", dpi=205)
    plt.close(fig)


def figures(ledger, result, coverage, cfg, directory):
    directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
        "axes.spines.right": False, "axes.labelcolor": "#192a39", "text.color": "#192a39",
        "xtick.color": "#425465", "ytick.color": "#425465",
    })

    nominal = ledger.loc[ledger.scenario.eq("clean")]
    fig, ax = plt.subplots(figsize=(6.4, 3.55), layout="constrained")
    ax.plot([0, 1], [0, 1], linestyle="--", color="#a4adb6", linewidth=1)
    for model in (GRAPH, ROBUST, "gru", "lightgbm"):
        block = nominal[nominal.model.eq(model)]
        bins = reliability_table(block.actual.to_numpy(), block.probability.to_numpy())
        ax.plot(bins.forecast, bins.observed, color=COLORS[model], linewidth=0.9, alpha=0.75)
        ax.scatter(bins.forecast, bins.observed, s=8 + 2.5 * np.sqrt(bins.n), color=COLORS[model],
                   alpha=0.85, label=NAMES[model], edgecolors="white", linewidth=0.3)
    ax.set(xlabel="Mean predicted probability in bin", ylabel="Observed stress frequency",
           xlim=(-0.025, 1.015), ylim=(-0.025, 1.015))
    ax.grid(alpha=0.15)
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    save_figure(fig, directory, "reliability")

    fig, axes = plt.subplots(1, 2, figsize=(8.1, 3.15), layout="constrained")
    order = ["clean", "thin_10", "thin_30", "thin_50"]
    for model in (GRAPH, ROBUST, "gru", "lightgbm"):
        scores = result.loc[result.model.eq(model)].set_index("scenario").loc[order]
        for ax, metric in zip(axes, ("ap", "brier"), strict=True):
            ax.plot([0, 10, 30, 50], scores[metric], "o-", lw=1.25, ms=4,
                    label=NAMES[model], color=COLORS[model])
            ax.set_xlabel("Probability of removing each retained edge (%)")
            ax.grid(alpha=0.18)
    axes[0].set_ylabel("Average precision ↑")
    axes[1].set_ylabel("Brier score ↓")
    axes[0].legend(frameon=False, fontsize=7)
    save_figure(fig, directory, "edge_thinning")

    fig, ax = plt.subplots(figsize=(6.4, 3.35), layout="constrained")
    label_map = {"disagreement_rank": "Ensemble disagreement", "predictive_entropy": "Predictive entropy",
                 "random_expected": "Random deferral (expected)"}
    for color, (key, points) in zip(PALETTE, coverage.groupby("uncertainty_score"), strict=True):
        ax.plot(100 * points.coverage, points.brier, "o-", ms=3.5, lw=1.2, label=label_map[key], color=color)
    ax.set(xlabel="Forecasts retained for automation (%)", ylabel="Brier score among retained forecasts")
    ax.legend(frameon=False)
    ax.grid(alpha=0.18)
    save_figure(fig, directory, "risk_coverage")

    windows = cfg["historical_windows"]
    fig, axes = plt.subplots(2, len(windows), figsize=(8.7, 5.0), layout="constrained")
    models = nominal[nominal.model.isin((GRAPH, "gru"))]
    for column, event in enumerate(windows):
        for line, version in enumerate(("v2", "v3")):
            view = models[(models.origin >= event["start"]) & (models.origin < event["stop"])
                          & models.version.eq(version)]
            panel = axes[line, column]
            dollars = view[view.model.eq(GRAPH)]
            days = pd.to_datetime(dollars.origin)
            panel.bar(days, dollars.liquidation_usd / 1e6, width=0.65, color="#4e7887", alpha=0.45, label="Realised USD")
            panel.set_ylabel(f"Aave {version.upper()} (USD m)")
            panel.tick_params(axis="x", rotation=25)
            panel.set_xticks(days)
            panel.set_xticklabels([v.strftime("%d %b") for v in days], fontsize=7)
            p_axis = panel.twinx()
            p_axis.spines["right"].set_visible(True)
            for model in (GRAPH, "gru"):
                score = view[view.model.eq(model)]
                p_axis.plot(pd.to_datetime(score.origin), score.probability, "o-", lw=1.25, ms=3.5,
                            label=NAMES[model], color=COLORS[model])
            p_axis.set_ylim(0, 1.02)
            if column == len(windows) - 1:
                p_axis.set_ylabel("Predicted probability")
            if line == 0:
                panel.set_title(event["id"].replace("_", " ").title(), loc="left")
                p_axis.legend(loc="upper left", frameon=False, fontsize=7)
    save_figure(fig, directory, "historical_windows")


def run_report(results, processed, figure_dir, cfg):
    p = pd.read_csv(results / "primary" / "predictions.csv.gz", dtype={"origin": str})
    clean = p[p.scenario.eq("clean")]
    total = metrics_table(p, ["model", "scenario"])
    total.to_csv(results / "metrics.csv", index=False)
    metrics_table(p, ["fold", "model", "scenario"]).to_csv(results / "metrics_by_fold.csv", index=False)
    metrics_table(clean, ["version", "model"]).to_csv(results / "metrics_by_version.csv", index=False)
    calibration = []
    for name, item in clean.groupby("model"):
        entries = reliability_table(item.actual.to_numpy(), item.probability.to_numpy()).assign(model=name)
        calibration.append(entries)
    pd.concat(calibration).to_csv(results / "reliability_bins.csv", index=False)

    scenarios = ("clean", "thin_30", "combined")
    comparisons = [
        (GRAPH, "gru", ("clean",)), (GRAPH, "graph_local", ("clean",)),
        (GRAPH, "static_graph", ("clean",)), (GRAPH, "graph_no_sequence", ("clean",)),
        (GRAPH, "lightgbm", ("clean",)), (GRAPH, "graph_raw", ("clean",)),
        ("graph_raw", "graph_seed", ("clean",)), (GRAPH, "graph_isotonic", ("clean",)),
        (ROBUST, GRAPH, scenarios), ("spillover_weighted", "spillover_unweighted", ("clean",)),
        ("spillover_unweighted", "logistic", ("clean",)),
    ]
    pairs = []
    for left, right, selected in comparisons:
        for scenario in selected:
            shifted = p[p.scenario.eq(scenario)]
            for days in ([7, cfg["bootstrap_block_days"], 28] if (left, right) == (GRAPH, "gru") else [cfg["bootstrap_block_days"]]):
                effect = paired_trials(shifted[shifted.model.eq(left)], shifted[shifted.model.eq(right)],
                                       days, cfg["bootstrap_replicates"])
                pairs.append({"left": left, "right": right, "scenario": scenario, "block_days": days} | effect)
    pd.DataFrame(pairs).to_csv(results / "paired_differences.csv", index=False)

    queues = []
    for (model, scenario), frame in p[p.model.isin(CORE)].groupby(["model", "scenario"]):
        policies = ["alert", "alert_with_review"] if frame.uncertainty.notna().all() else ["alert"]
        for policy in policies:
            queues.append({"model": model, "scenario": scenario} | alert_scores(frame, policy))
    pd.DataFrame(queues).to_csv(results / "alerts.csv", index=False)
    coverage = pd.DataFrame(risk_coverage(clean[clean.model.eq(GRAPH)]))
    coverage.to_csv(results / "risk_coverage.csv", index=False)
    event_windows(clean[clean.model.isin(CORE)], cfg).to_csv(results / "historical_windows.csv", index=False)

    checks = [total[total.scenario.eq("clean")].assign(target="usd_24h")]
    for folder in ("six_hour", "seven_day", "borrowing_scaled"):
        directory = results / folder
        if directory.exists() and (directory / "predictions.csv.gz").exists():
            view = pd.read_csv(directory / "predictions.csv.gz")
            checks.append(metrics_table(view, ["model", "scenario"]).assign(target=folder))
    pd.concat(checks, ignore_index=True).to_csv(results / "label_sensitivity.csv", index=False)
    shutil.copyfile(processed / "data_audit.json", results / "data_audit.json")
    figures(p, total, coverage, cfg, figure_dir)
