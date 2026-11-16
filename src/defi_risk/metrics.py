"""Probability scores, blocked comparisons and alert evaluation."""

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score


def reliability_table(y, p):
    bins = np.minimum(np.floor(10 * p).astype(int), 9)
    items = []
    for i in range(10):
        present = bins == i
        if present.any():
            items.append({
                "bin": i, "n": int(present.sum()), "forecast": float(p[present].mean()),
                "observed": float(y[present].mean()),
            })
    return pd.DataFrame(items)


def probability_scores(y, p):
    base_rate = y.mean()
    table = reliability_table(y, p)
    err = table.forecast - table.observed
    weights = table.n / len(y)
    reliability = float(np.sum(weights * err ** 2))
    resolution = float(np.sum(weights * (table.observed - base_rate) ** 2))
    uncertainty = float(base_rate * (1 - base_rate))
    return {
        "rows": len(y), "positive": int(y.sum()), "prevalence": float(base_rate),
        "ap": float(average_precision_score(y, p)) if y.any() else None,
        "auroc": float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else None,
        "logloss": float(log_loss(y, p, labels=[0, 1])),
        "brier": float(brier_score_loss(y, p)),
        "ece_10": float(np.sum(weights * np.abs(err))),
        "mean_forecast": float(p.mean()), "reliability_binned": reliability,
        "resolution_binned": resolution, "uncertainty_binned": uncertainty,
        "brier_binned": reliability - resolution + uncertainty,
    }


def paired_trials(left, right, length, repeats):
    columns = ["fold", "origin", "version"]
    a = left.sort_values(columns).reset_index(drop=True)
    b = right.sort_values(columns).reset_index(drop=True)
    if not a[columns + ["actual"]].equals(b[columns + ["actual"]]):
        raise ValueError("Paired contrasts require identical observations and labels")
    bootstrap = []
    for _, fold in a.groupby("fold", sort=True):
        days = list(fold.groupby("origin", sort=True).indices.values())
        actual_positions = fold.index.to_numpy()
        block_days = min(length, len(days))
        n_blocks = (len(days) + block_days - 1) // block_days
        bootstrap.append((days, actual_positions, block_days, n_blocks))
    rng = np.random.default_rng(21531)
    out = []
    y, pa, pb = a.actual.to_numpy(), a.probability.to_numpy(), b.probability.to_numpy()
    for _ in range(repeats):
        indices = []
        for days, positions, block_days, n_blocks in bootstrap:
            starts = rng.integers(0, len(days) - block_days + 1, n_blocks)
            sampled = np.concatenate([np.arange(v, v + block_days) for v in starts])[:len(days)]
            indices.extend(positions[np.concatenate([days[i] for i in sampled])])
        yi, p1, p2 = y[indices], pa[indices], pb[indices]
        if yi.any() and yi.sum() < len(yi):
            out.append([
                average_precision_score(yi, p1) - average_precision_score(yi, p2),
                brier_score_loss(yi, p1) - brier_score_loss(yi, p2),
                log_loss(yi, p1, labels=[0, 1]) - log_loss(yi, p2, labels=[0, 1]),
            ])
    estimates = [probability_scores(y, p) for p in (pa, pb)]
    result = {"retained_bootstrap_replicates": len(out)}
    for i, metric in enumerate(("ap", "brier", "logloss")):
        interval = np.quantile(np.array(out)[:, i], [0.025, 0.975])
        result.update({f"{metric}_delta": estimates[0][metric] - estimates[1][metric],
                       f"{metric}_lo": interval[0], f"{metric}_hi": interval[1]})
    return result


def alert_scores(forecasts, policy):
    data = forecasts.sort_values(["fold", "version", "origin"]).copy()
    prior = data.groupby(["fold", "version"])[["actual", "origin"]].shift()
    dates = pd.to_datetime(data.origin)
    consecutive = dates.sub(pd.to_datetime(prior.origin)).dt.days.eq(1)
    onset = data.actual.eq(1) & ~(prior.actual.eq(1) & consecutive)
    flags = data[policy].eq(1)
    true = data.actual.eq(1)
    detected = onset & flags
    weeks = dates.nunique() / 7
    return {
        "policy": policy, "alerts": int(flags.sum()), "false_alerts": int((flags & ~true).sum()),
        "false_alerts_per_week": float((flags & ~true).sum() / weeks),
        "precision": float((flags & true).sum() / flags.sum()) if flags.any() else None,
        "daily_recall": float((flags & true).sum() / true.sum()) if true.any() else None,
        "onsets": int(onset.sum()), "onsets_alerted": int(detected.sum()),
        "onset_recall": float(detected.sum() / onset.sum()) if onset.any() else None,
        "median_onset_lead_hours": float(data.loc[detected, "true_lead_hours"].median()) if detected.any() else None,
        "review_flags": int(data.review.sum()) if policy == "alert_with_review" else 0,
        "reviewed_positive_origins": int((data.review.eq(1) & true).sum()) if policy == "alert_with_review" else 0,
        "reviewed_onsets": int((data.review.eq(1) & onset).sum()) if policy == "alert_with_review" else 0,
    }


def risk_coverage(forecasts):
    x = forecasts.sort_values(["origin", "version"]).reset_index(drop=True)
    q = x.probability.to_numpy()
    entropy = -(q * np.log(q) + (1 - q) * np.log1p(-q))
    # Stable order makes ties reproducible. Risk includes both positive and negative labels.
    ordering = {
        "disagreement_rank": x.uncertainty_rank.to_numpy(),
        "predictive_entropy": entropy,
    }
    loss = (x.actual.to_numpy() - q) ** 2
    for fraction in (1.0, 0.95, 0.9, 0.8, 0.7, 0.6, 0.5):
        retained = max(1, round(len(x) * fraction))
        for name, score in ordering.items():
            selection = np.argsort(score, kind="stable")[:retained]
            yield {
                "uncertainty_score": name, "coverage": retained / len(x), "brier": loss[selection].mean(),
                "retained_positives": int(x.actual.iloc[selection].sum()),
            }
        yield {
            "uncertainty_score": "random_expected", "coverage": retained / len(x), "brier": loss.mean(),
            "retained_positives": retained * x.actual.mean(),
        }
