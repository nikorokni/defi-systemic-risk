"""Directed ego graphs and time-windowed inputs for the forecast models."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import DAY

CLEAN = "clean"
SCENARIOS = {
    "clean": (0.0, 0, 0),
    "thin_10": (0.1, 0, 0),
    "thin_30": (0.3, 0, 0),
    "thin_50": (0.5, 0, 0),
    "oracle_lag_1d": (0.0, 1, 0),
    "graph_lag_7d": (0.0, 0, 7),
    "combined": (0.3, 1, 7),
    "augmentation": (0.3, 1, 0),
}


@dataclass
class Views:
    local: np.ndarray
    market: np.ndarray
    graph_summary: np.ndarray
    graph_weights: np.ndarray
    graph_peers: np.ndarray


class ForecastInputs:
    def __init__(self, processed, panel, config):
        self.panel = panel
        self.versions = list(config["versions"])
        self.ids = config["versions"]
        self.n_versions = len(self.versions)
        self.lookback = config["history_days"]
        self.k = config["top_neighbours"]
        self.lag = config["graph_lag_days"]
        self.days = pd.DatetimeIndex(panel.origin.drop_duplicates())
        self.local_cols = [
            col for col in panel if col.startswith("past_") or col.endswith(("_utilisation", "_log_borrowed"))
        ] + ["is_v3"]
        self.market_cols = [
            col for col in panel if col.startswith(("eth_", "btc_"))
        ]
        nodes = pd.read_parquet(processed / "graph_nodes.parquet")
        edges = pd.read_parquet(processed / "graph_edges.parquet")
        self.sizes = {
            date: dict(zip(frame.node, frame["size"], strict=True))
            for date, frame in nodes.groupby("snapshot")
        }
        self.edges = {
            key: list(zip(frame.peer, frame.weight, strict=True))
            for key, frame in edges.groupby(["snapshot", "version", "direction"], sort=False)
        }
        self.snapshots = pd.DatetimeIndex(sorted(self.sizes))
        self.anchor = self.snapshot_dates(self.lag).iloc[0]
        if pd.isna(self.anchor):
            raise ValueError("Graph does not reach the first buffered origin")
        if list(panel.version) != self.versions * len(self.days):
            raise ValueError("Panel is not a complete sorted day-by-version grid")
        self.cache = {}

    def snapshot_dates(self, delay):
        cutoffs = self.days - delay * DAY
        row = self.snapshots.searchsorted(cutoffs, side="right") - 1
        result = self.snapshots.take(row).to_series(index=self.days)
        return result.mask(row < 0, pd.NaT)

    def arrays(self, scenario=CLEAN, static=False):
        key = (scenario, static)
        if key in self.cache:
            return self.cache[key]
        prob, oracle_lag, graph_delay = SCENARIOS[scenario]
        selected = self.snapshot_dates(self.lag + graph_delay)
        directions = ("in", "out")
        shape = (len(self.panel), len(directions), self.k)
        weights = np.zeros(shape, dtype=np.float32)
        peers = np.zeros((*shape, 3), dtype=np.float32)
        context = np.full((len(self.panel), 2), np.nan, dtype=np.float32)
        masks = {}
        rng = np.random.default_rng(3107 if scenario == "augmentation" else 2048)
        for d, (origin, date) in enumerate(selected.items()):
            if pd.isna(date):
                continue
            topology = self.anchor if static else date
            for v, version in enumerate(self.versions):
                row = d * self.n_versions + v
                own_size = self.sizes[date].get(self.ids[version], np.nan)
                context[row] = [np.log1p(own_size), (origin - date) / DAY]
                for s, direction in enumerate(directions):
                    connections = self.edges.get((topology, version, direction), [])[:self.k]
                    mask_key = (date, version, direction)
                    if mask_key not in masks:
                        masks[mask_key] = rng.random(self.k)
                    keep = masks[mask_key]
                    for j, (peer, weight) in enumerate(connections):
                        if keep[j] < prob:
                            continue
                        weights[row, s, j] = weight
                        size = self.sizes[date].get(peer)
                        peers[row, s, j] = [
                            np.log1p(size) / 20 if size is not None else 0.0,
                            np.log1p(weight) / 20,
                            float(size is not None),
                        ]
        total = weights.sum(axis=-1)
        share = weights / np.where(total > 0, total, 1)[..., None]
        summary = np.column_stack([
            context,
            np.log1p(total),
            np.count_nonzero(weights, axis=-1),
            (share ** 2).sum(axis=-1),
            (share * peers[..., 0]).sum(axis=-1) * 20,
        ])
        market = self.panel[self.market_cols].to_numpy(dtype=np.float32)
        if oracle_lag:
            lag_rows = oracle_lag * self.n_versions
            market = np.vstack([np.full_like(market[:lag_rows], np.nan), market[:-lag_rows]])
        result = Views(self.panel[self.local_cols].to_numpy(np.float32), market, summary, weights, peers)
        self.cache[key] = result
        return result

    def other_version_signal(self):
        """Contemporaneously available prior event totals and cross-version graph share."""
        dates = self.snapshot_dates(self.lag)
        previous = self.panel["past_usd_1d"].to_numpy().reshape(-1, self.n_versions)
        features = []
        for day, date in enumerate(dates):
            for v, version in enumerate(self.versions):
                other_index = 1 - v
                peer = self.ids[self.versions[other_index]]
                incoming = self.edges.get((date, version, "in"), [])
                denominator = sum(weight for _, weight in incoming)
                share = sum(weight for node, weight in incoming if node == peer) / denominator if denominator else 0.0
                other_stress = previous[day, other_index]
                features.append((other_stress, share, share * other_stress))
        return np.asarray(features, dtype=np.float64)

    def window_rows(self, rows):
        return rows[:, None] - self.n_versions * np.arange(self.lookback - 1, -1, -1)
