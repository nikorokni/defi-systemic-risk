"""Insert measured values into the manuscript and generate standalone LaTeX."""

import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd


def table(headers, rows, numeric=(), widths=None):
    widths = widths or [3] * len(headers)
    alignment = ["-" * width + ":" if i in numeric else ":" + "-" * width
                 for i, width in enumerate(widths)]
    lines = [headers, alignment, *rows]
    return "\n".join("| " + " | ".join(map(str, row)) + " |" for row in lines)


def fill(results, paper):
    def data(name):
        return pd.read_csv(results / f"{name}.csv")

    def fmt(n):
        return f"{n:.4f}"

    metrics = data("metrics").set_index(["model", "scenario"])
    fits = data("metrics_by_fold").set_index(["fold", "model", "scenario"])
    diffs = data("paired_differences").set_index(["left", "right", "scenario", "block_days"])
    alerts = data("alerts").set_index(["model", "scenario", "policy"])
    historical = data("historical_windows").set_index(["window", "version", "model"])
    version_scores = data("metrics_by_version").set_index(["version", "model"])
    coverage = data("risk_coverage")
    sensitivity = data("label_sensitivity").set_index(["target", "model"])
    run = json.loads((results / "primary" / "run.json").read_text())
    graph, gru, robust = "graph_platt", "gru", "robust_graph"

    def clean(model):
        return metrics.loc[(model, "clean"), :]

    def difference(left, right, metric, scenario="clean"):
        row = diffs.loc[(left, right, scenario, 14), :]
        return f"{fmt(row[f'{metric}_delta'])} [{fmt(row[f'{metric}_lo'])}, {fmt(row[f'{metric}_hi'])}]"

    scoring = clean(graph)
    raw = clean("graph_raw")
    conventional = clean(gru)
    alert = alerts.loc[(graph, "clean", "alert"), :]
    review = alerts.loc[(graph, "clean", "alert_with_review"), :]
    c90 = coverage.loc[np.isclose(coverage.coverage, 0.9, atol=0.001)].set_index("uncertainty_score")
    u = c90.loc["disagreement_rank"]
    entropy = c90.loc["predictive_entropy"]

    variables = {
        "test_n": f"{int(scoring.rows):,}",
        "test_positive": str(int(scoring.positive)),
        "prevalence": f"{scoring.prevalence:.1%}",
        "graph_ap": fmt(scoring.ap),
        "graph_brier": fmt(scoring.brier),
        "gru_ap": fmt(conventional.ap),
        "gru_brier": fmt(conventional.brier),
        "abstract_result": "The paired 14-day block intervals for the score differences included zero, with point estimates favouring the recurrent benchmark.",
        "abstract_robust": "the graph's average precision fell further, and augmentation had mixed effects across ranking and probability loss.",
        "v3_positive": int(version_scores.loc[("v3", graph), "positive"]),
        "pers_ap": fmt(clean("persistence").ap),
        "main_ap_difference": difference(graph, gru, "ap"),
        "main_brier_difference": difference(graph, gru, "brier"),
        "market_ap_difference": difference(graph, "graph_local", "ap"),
        "sequence_brier_difference": difference(graph, "graph_no_sequence", "brier"),
        "raw_brier": fmt(raw.brier),
        "raw_logloss": fmt(raw.logloss),
        "graph_logloss": fmt(scoring.logloss),
        "calibration_brier_difference": difference(graph, "graph_raw", "brier"),
        "raw_ece": fmt(raw.ece_10),
        "calibrated_ece": fmt(scoring.ece_10),
        "raw_mean": f"{raw.mean_forecast:.1%}",
        "calibrated_mean": f"{scoring.mean_forecast:.1%}",
        "isotonic_logloss": fmt(clean("graph_isotonic").logloss),
        "coverage_90": f"{u.coverage:.1%}",
        "selective_u_brier": fmt(u.brier),
        "selective_u_positive": int(u.retained_positives),
        "selective_entropy_brier": fmt(entropy.brier),
        "selective_entropy_positive": int(entropy.retained_positives),
        "combined_graph_ap": fmt(metrics.loc[(graph, "combined"), "ap"]),
        "robust_clean_ap": fmt(clean(robust).ap),
        "robust_combined_ap": fmt(metrics.loc[(robust, "combined"), "ap"]),
        "robust_combined_brier_difference": difference(robust, graph, "brier", "combined"),
        "graph_alert_n": int(alert.alerts),
        "graph_detected": int(alert.onsets_alerted),
        "episode_n": int(alert.onsets),
        "graph_lead": f"{alert.median_onset_lead_hours:.2f}",
        "graph_actual_alert_rate": f"{alert.alerts / scoring.rows:.1%}",
        "graph_no_review_false": int(alert.false_alerts),
        "graph_review_false": int(review.false_alerts),
        "graph_review_detected": int(review.onsets_alerted),
        "review_n": int(review.review_flags),
        "review_onsets": int(review.reviewed_onsets),
        "august_v3_total": f"{historical.loc[('august_2024', 'v3', graph), 'total_liquidation_usd'] / 1e6:.1f}",
        "other_version_brier_difference": difference("spillover_unweighted", "logistic", "brier"),
        "other_version_ap_difference": difference("spillover_unweighted", "logistic", "ap"),
    }

    names = {
        "prior": "Training prior", "persistence": "Prior-day liquidation",
        "logistic_local": "Local logit", "logistic": "Market and local logit",
        "lightgbm": "LightGBM", "lightgbm_graph": "LightGBM + graph summaries",
        gru: "GRU + Platt", "static_graph": "Static graph + Platt",
        "graph_local": "Graph without market block",
        "graph_no_sequence": "Graph without sequence",
        "graph_seed": "Graph, single seed", "graph_raw": "Graph, raw ensemble",
        graph: "Temporal graph + Platt", "graph_isotonic": "Graph + isotonic",
        robust: "Augmented graph + Platt",
    }
    variables["table_scores"] = table(["Model", "AP", "AUROC", "Brier", "Log loss"], [
        [label, *[fmt(clean(key)[column]) for column in ("ap", "auroc", "brier", "logloss")]]
        for key, label in names.items()
    ], numeric=(1, 2, 3, 4)) + "\n\n: Nominal test results across the three folds. Higher AP and AUROC, lower Brier and log loss are preferable."

    split_rows = []
    for name, fold in run["folds"].items():
        block = fold["test"]
        first, last = pd.to_datetime([block["first"], block["last"]])
        dates = f"{first.strftime('%d %b')} to {last.strftime('%d %b %Y')}"
        cutoffs = [f"{fold['cutoff'][v] / 1e3:,.0f}" for v in ("v2", "v3")]
        split_rows.append([name, dates, fold["train"]["rows"], f"{block['positives']}/{block['rows']}", *cutoffs])
    variables["table_splits"] = table(["Fold", "Test origins (UTC)", "Train $n$", "Test + / $n$", "V2 q95", "V3 q95"],
                                     split_rows, numeric=(2, 3, 4, 5), widths=[5, 26, 9, 11, 8, 8]) + "\n\n: Primary folds and training thresholds (USD thousands). Origin date ranges are inclusive."

    variables["table_folds"] = table(["Fold", "Graph AP", "GRU AP", "Graph Brier", "GRU Brier"], [
        [fold, *[fmt(fits.loc[(fold, model, "clean"), metric])
                 for metric in ("ap", "brier") for model in (graph, gru)]]
        for fold in run["folds"]
    ], numeric=(1, 2, 3, 4)) + "\n\n: Primary paired comparison shown separately by test fold."

    scenarios = {
        "clean": "Clean", "thin_10": "Thin 10%", "thin_30": "Thin 30%", "thin_50": "Thin 50%",
        "oracle_lag_1d": "Oracle delay (+1 d)", "graph_lag_7d": "Graph delay (+7 d)", "combined": "Combined",
    }
    variables["table_shift"] = table(["Observation", "Graph AP", "Graph Brier", "Aug. AP", "Aug. Brier", "GRU AP"], [
        [label, *[fmt(metrics.loc[(model, key), metric]) for model, metric in (
            (graph, "ap"), (graph, "brier"), (robust, "ap"), (robust, "brier"), (gru, "ap"),
        )]]
        for key, label in scenarios.items()
    ], numeric=(1, 2, 3, 4, 5)) + "\n\n: Input disruption under fixed calibration, with the augmented graph labelled Aug."

    variables["table_alerts"] = table(["Model and rule", "Alerts", "False per week", "Onsets hit", "Reviews", "Lead (h)"], [
        [names[model] + rule, int(row.alerts), f"{row.false_alerts_per_week:.2f}",
         f"{int(row.onsets_alerted)}/{int(row.onsets)}", int(row.review_flags), f"{row.median_onset_lead_hours:.2f}"]
        for model, policy, rule in (
            (graph, "alert", ""), (graph, "alert_with_review", " with review"),
            (gru, "alert", ""), ("lightgbm", "alert", ""),
            (robust, "alert", ""), (robust, "alert_with_review", " with review"),
        )
        for row in [alerts.loc[(model, "clean", policy), :]]
    ], numeric=(1, 2, 3, 4, 5), widths=[34, 7, 10, 10, 8, 8]) + "\n\n: Nominal alert performance. Onsets hit counts automated warnings on the first positive origin of a run. Lead is the median among those onsets."

    variables["table_events"] = table(["Window", "Version", "USD m", "Positive days", "Graph hits", "GRU hits"], [
        [title, v.upper(), f"{a.total_liquidation_usd / 1e6:.2f}", int(a.positives), int(a.positive_alerts), int(b.positive_alerts)]
        for key, title in (("august_2024", "2–8 Aug 2024"), ("february_2025", "2–5 Feb 2025"))
        for v in ("v2", "v3")
        for a, b in [(historical.loc[(key, v, graph), :], historical.loc[(key, v, gru), :])]
    ], numeric=(2, 3, 4, 5)) + "\n\n: Externally dated stress windows. A hit is an automated probability-only alert on a positive day."

    variables["table_sensitivity"] = table(["Label and horizon", "Test + / $n$", "Graph AP", "GRU AP", "Graph Brier", "GRU Brier"], [
        [label, f"{int(a.positive)}/{int(a.rows)}", fmt(a.ap), fmt(b.ap), fmt(a.brier), fmt(b.brier)]
        for key, label in (("usd_24h", "USD, 24 hours"), ("six_hour", "USD, 6 hours"),
                           ("seven_day", "USD, 7 days"), ("borrowing_scaled", "Borrowing ratio, 24 hours"))
        for a, b in [(sensitivity.loc[(key, graph), :], sensitivity.loc[(key, gru), :])]
    ], numeric=(1, 2, 3, 4, 5), widths=[27, 11, 8, 8, 10, 9]) + "\n\n: Models refitted to each sensitivity definition. Compare models within rows because the event rate changes with the target."

    template = (paper / "manuscript.template.md").read_text(encoding="utf-8")
    manuscript = re.sub(r"\{\{([a-z0-9_]+)\}\}", lambda match: str(variables[match.group(1)]), template)
    available = set(re.findall(r"\{\{([a-z0-9_]+)\}\}", template))
    if available != set(variables):
        raise ValueError("Template and value keys are out of sync")
    (paper / "manuscript.md").write_text(manuscript, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results"))
    parser.add_argument("--paper", type=Path, default=Path("paper"))
    parser.add_argument("--markdown-only", action="store_true")
    args = parser.parse_args()
    fill(args.results, args.paper)
    if not args.markdown_only:
        paper = args.paper
        md = (paper / "manuscript.md").read_text()
        md = re.sub(r"\.\./figures/([a-z_]+)\.png", r"figures/\1.pdf", md)
        md = md.replace("## Label sensitivity and cross-version association",
                        "\\Needspace{12\\baselineskip}\n\n## Label sensitivity and cross-version association")
        subprocess.run([
            "pandoc", "--from=markdown", "--to=latex", "--standalone", "--citeproc", "--number-sections",
            "--bibliography", str(paper / "references.bib"),
            "--include-in-header", str(paper / "preamble.tex"),
            "-V", "papersize=a4", "-V", "fontsize=11pt", "-V", "geometry=margin=26mm",
            "-V", "mainfont=Latin Modern Roman", "-V", "sansfont=Latin Modern Sans",
            "-V", "mathfont=Latin Modern Math", "-V", "colorlinks=true", "-V", "urlcolor=teal",
            "--output", str(paper / "main.tex"),
        ], input=md, text=True, check=True)


if __name__ == "__main__":
    main()
