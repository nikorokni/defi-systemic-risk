"""Comparable tabular, recurrent and directed-weighted graph models."""

from dataclasses import dataclass

import numpy as np
import torch
from lightgbm import LGBMClassifier
from scipy.optimize import minimize
from scipy.special import expit, logit
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from torch import nn
from torch.nn import functional as F

EPS = 1e-6


def stack_inputs(views, market=True, graph=False, extra=None):
    blocks = [views.local]
    if market:
        blocks.append(views.market)
    if graph:
        blocks.append(views.graph_summary)
    if extra is not None:
        blocks.append(extra)
    return np.column_stack(blocks)


class Scaling:
    def fit(self, x):
        valid = np.isfinite(x)
        count = valid.sum(axis=0).clip(min=1)
        self.mean = np.where(valid, x, 0).sum(axis=0) / count
        sq = np.where(valid, (x - self.mean) ** 2, 0).sum(axis=0) / count
        self.scale = np.maximum(np.sqrt(sq), 1e-6)
        return self

    def transform(self, x):
        valid = np.isfinite(x)
        values = np.where(valid, (x - self.mean) / self.scale, 0).clip(-12, 12)
        return np.column_stack([values, ~valid]).astype(np.float32)


def fit_tabular(kind, x, y):
    if kind == "logistic":
        return LogisticRegression(C=0.35, max_iter=500).fit(x, y)
    if kind == "lightgbm":
        # Conservative depth and leaf sizes for the small daily panel.
        return LGBMClassifier(
            n_estimators=140, learning_rate=0.025, num_leaves=7, max_depth=3,
            min_child_samples=30, reg_lambda=2.0, subsample=1.0,
            colsample_bytree=1.0, random_state=19, n_jobs=1, verbosity=-1,
        ).fit(x, y)
    raise ValueError(f"Unknown tabular model {kind}")


@dataclass(frozen=True)
class NeuralSpec:
    graph: bool
    market: bool = True
    static: bool = False
    augment: bool = False


class StressNet(nn.Module):
    def __init__(self, inputs, hidden, graph):
        super().__init__()
        self.graph = graph
        if graph:
            self.peer_maps = nn.ModuleList([
                nn.Sequential(nn.Linear(3, 8), nn.ReLU(), nn.Linear(8, 8))
                for _ in range(2)
            ])
        self.input_layer = nn.Sequential(
            nn.Linear(inputs + 16 * graph, hidden), nn.LayerNorm(hidden), nn.ReLU()
        )
        self.history = nn.GRU(hidden, hidden, batch_first=True)
        self.head = nn.Sequential(nn.Dropout(0.1), nn.Linear(hidden, 1))

    def forward(self, x, weights, peers):
        if self.graph:
            neighbour_means = []
            for direction, encoder in enumerate(self.peer_maps):
                w = weights[:, :, direction, :, None]
                share = w / w.sum(dim=2, keepdim=True).clamp_min(1e-12)
                neighbour_means.append((encoder(peers[:, :, direction]) * share).sum(dim=2))
            x = torch.cat([x, *neighbour_means], dim=-1)
        h, _ = self.history(self.input_layer(x))
        return self.head(h[:, -1]).squeeze(-1)


class TorchInput:
    def __init__(self, inputs, views, spec, scaling, sequence_days):
        self.inputs = inputs
        self.sequence_days = sequence_days
        design = stack_inputs(views, market=spec.market, graph=spec.graph)
        self.tabular = torch.as_tensor(scaling.transform(design), dtype=torch.float32)
        self.weights = torch.from_numpy(views.graph_weights) if spec.graph else None
        self.peers = torch.from_numpy(views.graph_peers) if spec.graph else None

    def batch(self, rows):
        history = self.inputs.window_rows(rows)[:, -self.sequence_days:]
        if (history < 0).any():
            raise ValueError("History extends before the prepared input buffer")
        x = self.tabular[history]
        return x, self.weights[history] if self.weights is not None else None, self.peers[history] if self.peers is not None else None


def predict_member(model, data, rows):
    model.eval()
    with torch.inference_mode():
        batches = [
            torch.sigmoid(model(*data.batch(rows[i:i + 256]))).numpy()
            for i in range(0, len(rows), 256)
        ]
    return np.concatenate(batches).astype(np.float64)


def train_member(seed, train, tuning, labels, clean, augmented, spec, config):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = StressNet(clean.tabular.shape[-1], config["hidden"], spec.graph)
    opt = torch.optim.AdamW(
        model.parameters(), lr=config["learning_rate"], weight_decay=config["weight_decay"]
    )
    label_tensor = torch.tensor(labels, dtype=torch.float32)
    best_loss = np.inf
    best_weights = None
    best_epoch = 0
    batch_size = config["batch_size"]
    for epoch in range(1, config["epochs"] + 1):
        model.train()
        permutation = rng.permutation(train)
        for i in range(0, len(permutation), batch_size):
            rows = permutation[i:i + batch_size]
            y = label_tensor[rows]
            loss = F.binary_cross_entropy_with_logits(model(*clean.batch(rows)), y)
            if augmented is not None:
                shifted_loss = F.binary_cross_entropy_with_logits(model(*augmented.batch(rows)), y)
                loss = (loss + shifted_loss) / 2
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            opt.step()
        validation = predict_member(model, clean, tuning)
        error = log_loss(labels[tuning], np.clip(validation, EPS, 1 - EPS), labels=[0, 1])
        if error < best_loss - 1e-5:
            best_loss = error
            best_weights = {key: value.detach().clone() for key, value in model.state_dict().items()}
            best_epoch = epoch
        if epoch - best_epoch >= config["patience"]:
            break
    model.load_state_dict(best_weights)
    return model, best_epoch


class Platt:
    """Positive-slope logistic recalibration with weak identity shrinkage."""

    def fit(self, p, y):
        z = logit(np.clip(p, EPS, 1 - EPS))
        target = y.astype(float)

        def objective(parameters):
            intercept, slope = parameters
            shifted = intercept + slope * z
            d = expit(shifted) - target
            value = np.logaddexp(0, shifted).sum() - (target * shifted).sum() + 0.5 * (slope - 1) ** 2
            jac = np.array([d.sum(), (d * z).sum() + slope - 1])
            return value, jac

        solution = minimize(
            objective, np.array([0.0, 1.0]), jac=True,
            bounds=[(-12, 12), (0.005, 12)], method="L-BFGS-B",
        )
        if not solution.success:
            raise ValueError(f"Platt fit failed: {solution.message}")
        self.intercept, self.slope = solution.x
        return self

    def predict(self, p):
        p = np.clip(p, EPS, 1 - EPS)
        return np.clip(expit(self.intercept + self.slope * logit(p)), EPS, 1 - EPS)


def fit_calibrators(p, y):
    return {
        "platt": Platt().fit(p, y),
        "isotonic": IsotonicRegression(out_of_bounds="clip", y_min=EPS, y_max=1 - EPS).fit(p, y),
    }
