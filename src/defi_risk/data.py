"""Verify upstream data and build strictly timestamped forecast inputs."""

import hashlib
import json
import math
import shutil
import urllib.request
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import ijson
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

DAY = pd.Timedelta(days=1)
HOUR = pd.Timedelta(hours=1)
AAVE = "data/AAVE"
ORACLE = "data/ETH_blocks/Chainlink"


def utc(value):
    return pd.Timestamp(value, tz="UTC")


def hash_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def fetch(sources, raw):
    raw.mkdir(parents=True, exist_ok=True)
    for name, metadata in sources["files"].items():
        path = raw / name
        expected = metadata.get("sha256")
        if path.exists() and (expected is None or hash_file(path) == expected):
            continue
        temporary = path.with_suffix(path.suffix + ".part")
        request = urllib.request.Request(metadata["url"], headers={"User-Agent": "AaveResearchBenchmark/0.1"})
        print(f"Fetching {name}", flush=True)
        try:
            with urllib.request.urlopen(request, timeout=90) as response, temporary.open("wb") as target:
                shutil.copyfileobj(response, target, length=1024 * 1024)
            if expected and hash_file(temporary) != expected:
                raise ValueError(f"SHA-256 mismatch for {name}")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def parquet_member(archive, name, columns):
    return pq.read_table(BytesIO(archive.read(name)), columns=columns).to_pandas(ignore_metadata=True)


def asof(frame, grid, max_age, source_col="timestamp"):
    """Return last observations strictly before each query, with true source timestamps."""
    inputs = frame.sort_values(source_col, kind="stable")
    query = pd.DataFrame({"origin": grid})
    matched = pd.merge_asof(
        query, inputs, left_on="origin", right_on=source_col,
        allow_exact_matches=False, tolerance=max_age,
    )
    return matched.set_index("origin")


def oracle_features(archive, grid):
    # Raw update times implement the information set. Hourly publisher bars use their
    # own timestamp convention and are never inputs to this transformation.
    hours = pd.date_range(grid[0] - 9 * DAY, grid[-1], freq="h")
    result = pd.DataFrame(index=grid)
    audit = {}
    for asset in ("eth", "btc"):
        filename = f"{ORACLE}/{asset}usd_oracle_events.parquet"
        ticks = parquet_member(archive, filename, ["timestamp", "price_usd"])
        ticks["timestamp"] = pd.to_datetime(ticks["timestamp"], unit="s", utc=True)
        invalid = ~np.isfinite(ticks["price_usd"]) | (ticks["price_usd"] <= 0)
        invalid_in_grid = invalid & ticks.timestamp.between(hours[0], hours[-1])
        if invalid_in_grid.any():
            raise ValueError(f"invalid {asset} oracle prices inside analysis window")
        ticks = ticks.loc[~invalid]
        series = asof(ticks, hours, 3 * HOUR)
        log_price = np.log(series["price_usd"])
        hourly_returns = log_price.diff()
        result[f"{asset}_return_1d"] = log_price.diff(24).reindex(grid)
        result[f"{asset}_return_7d"] = log_price.diff(168).reindex(grid)
        result[f"{asset}_rv_1d"] = np.sqrt(hourly_returns.pow(2).rolling(24).sum()).reindex(grid)
        result[f"{asset}_return_min_1d"] = hourly_returns.rolling(24).min().reindex(grid)
        result[f"{asset}_price_age_hours"] = (
            (series.index - series["timestamp"]) / HOUR
        ).reindex(grid)
        audit[asset] = {
            "valid_updates_in_release": len(ticks), "excluded_invalid_updates_outside_window": int(invalid.sum()),
            "first": str(ticks.timestamp.min()), "last": str(ticks.timestamp.max()),
        }
    return result, audit


def dated_borrowing(path, grid, node_id):
    """Approximate version-wide Ethereum active borrowing, for sensitivity only."""
    protocol = json.loads(path.read_text())
    if str(protocol["id"]) != node_id:
        raise ValueError(f"Unexpected DefiLlama protocol ID in {path}")
    debt = pd.DataFrame(protocol["chainTvls"]["Ethereum-borrowed"]["tvl"])
    debt["timestamp"] = pd.to_datetime(debt.pop("date"), unit="s", utc=True)
    debt = debt.loc[debt["timestamp"].dt.floor("D").eq(debt["timestamp"])]
    if debt["timestamp"].duplicated().any():
        raise ValueError(f"Ambiguous daily timestamps in {path}")
    debt.loc[debt["totalLiquidityUSD"] <= 0, "totalLiquidityUSD"] = np.nan
    return asof(debt, grid, 2 * DAY)["totalLiquidityUSD"]


def window_totals(times, values, starts, ends):
    left = np.searchsorted(times, starts, side="left")
    right = np.searchsorted(times, ends, side="left")
    cumulative = np.r_[0.0, np.cumsum(values)]
    return cumulative[right] - cumulative[left], right - left


def liquidation_panel(archive, grid, version, study):
    base = f"{AAVE}/liquidations/aave_{version}_eth"
    events = parquet_member(archive, f"{base}_liquidation_events.parquet", [
        "timestamp", "datetime", "amountUSD", "id", "hash", "logIndex",
    ])
    events["timestamp"] = pd.to_datetime(events["timestamp"], unit="s", utc=True)
    events["datetime"] = pd.to_datetime(events["datetime"], utc=True)
    if not events.timestamp.eq(events.datetime).all():
        raise ValueError(f"{version} event timestamp fields disagree")
    if events.id.duplicated().any() or events.duplicated(["hash", "logIndex"]).any():
        raise ValueError(f"Duplicate event identifiers in {version}")
    amounts = events["amountUSD"]
    if not np.isfinite(amounts).all() or (amounts < 0).any():
        raise ValueError(f"Invalid liquidation USD in {version}")
    hourly = parquet_member(archive, f"{base}_liquidations_hourly.parquet", [
        "__index_level_0__", "liquidation_usd", "liquidation_count",
    ]).rename(columns={"__index_level_0__": "hour"})
    hourly["hour"] = pd.to_datetime(hourly["hour"], utc=True)
    if hourly.hour.duplicated().any() or not hourly.hour.eq(hourly.hour.dt.floor("h")).all():
        raise ValueError(f"Invalid publisher aggregate grid in {version}")

    start = utc(study["sample_start"])
    stop = utc(study["sample_stop"])
    expected_hours = pd.date_range(start - 29 * DAY, stop + 7 * DAY, freq="h", inclusive="left")
    effective_hours = hourly.set_index("hour").reindex(expected_hours)
    if effective_hours.isna().any().any():
        raise ValueError(f"Publisher aggregate coverage gap in {version}")
    study_events = events.loc[events.timestamp.between(start, stop, inclusive="left")]
    actual = events.groupby(events.timestamp.dt.floor("h"))["amountUSD"].agg(["sum", "size"])
    check = actual.reindex(expected_hours, fill_value=0)
    parity_count = int(np.count_nonzero(check["size"] != effective_hours["liquidation_count"]))
    parity_usd = int(np.count_nonzero(~np.isclose(
        check["sum"], effective_hours["liquidation_usd"], rtol=1e-8, atol=1e-5
    )))
    if parity_count or parity_usd:
        raise ValueError(f"{version} event and publisher hourly tables disagree in counts ({parity_count}) or USD ({parity_usd})")

    events = events.sort_values(["timestamp", "logIndex"], kind="stable")
    ts = events["timestamp"].array.asi8
    y = events["amountUSD"].to_numpy(dtype=np.float64)
    source_times = grid.asi8
    frame = pd.DataFrame(index=grid)
    for days in (1, 3, 7):
        usd, counts = window_totals(ts, y, source_times - (days * DAY).value, source_times)
        frame[f"past_usd_{days}d"] = np.log1p(usd.clip(min=0))
        frame[f"past_count_{days}d"] = np.log1p(counts)
    for hours in (6, 24, 168):
        usd, counts = window_totals(ts, y, source_times, source_times + (hours * HOUR).value)
        frame[f"future_usd_{hours}h"] = usd.clip(min=0)
        frame[f"future_count_{hours}h"] = counts
    condensed = events[["timestamp", "amountUSD"]].loc[
        events.timestamp.between(start, stop + 7 * DAY, inclusive="left")
    ].reset_index(drop=True)
    audit = {
        "event_rows_in_release": len(events), "event_rows_in_issue_dates": len(study_events),
        "first_event": str(events.timestamp.min()), "last_event": str(events.timestamp.max()),
        "distinct_utc_hours_checked": len(expected_hours), "count_mismatch_hours": parity_count,
        "usd_mismatch_hours": parity_usd, "zero_usd_rows_in_release": int((amounts == 0).sum()),
        "liquidated_usd_in_issue_dates": float(study_events.amountUSD.sum()),
    }
    return frame, condensed, audit


def reserve_features(archive, grid, version, assets):
    result = pd.DataFrame(index=grid)
    audit = {}
    for asset in assets:
        observations = parquet_member(archive, f"{AAVE}/aave_{version}_{asset}_eth.parquet", [
            "timestamp", "borrowed_USD", "supplied_USD",
        ])
        observations["timestamp"] = pd.to_datetime(observations["timestamp"], unit="s", utc=True)
        state = asof(observations, grid, 2 * DAY)
        borrowed = state["borrowed_USD"].where(state["borrowed_USD"] >= 0)
        supplied = state["supplied_USD"].where(state["supplied_USD"] > 0)
        result[f"{asset}_log_borrowed"] = np.log1p(borrowed)
        result[f"{asset}_utilisation"] = borrowed / supplied
        audit[asset] = {
            "rows": len(observations), "first": str(observations.timestamp.min()),
            "last": str(observations.timestamp.max()),
            "missing_issue_inputs": int(borrowed.isna().sum()),
        }
    return result, audit


def extract_graph(raw, processed, study):
    mapping = json.loads((raw / "dexposure_mapping.json").read_text())
    versions = study["versions"]
    for version, node_id in versions.items():
        if mapping[node_id]["name"].casefold() != f"aave {version}":
            raise ValueError(f"Unexpected graph node identity for {version}")
    ids_to_version = {node_id: version for version, node_id in versions.items()}
    first = utc(study["sample_start"]) - 45 * DAY
    stop = utc(study["sample_stop"])
    all_dates = []
    edges = []
    nodes = []
    with (raw / "dexposure.json").open("rb") as source:
        for day, snapshot in ijson.kvitems(source, "data", use_float=True):
            date = utc(day)
            all_dates.append(date)
            if not first <= date < stop:
                continue
            unique_edges = {}
            for source_node in snapshot["nodes"]:
                node_id = str(source_node["id"])
                size = float(source_node["size"])
                if node_id in mapping and math.isfinite(size) and size >= 0:
                    nodes.append((date, node_id, size))
            for link in snapshot["links"]:
                weight = float(link["size"])
                sender, receiver = str(link["source"]), str(link["target"])
                if (sender == receiver or sender not in mapping or receiver not in mapping
                        or not math.isfinite(weight) or weight <= 0):
                    continue
                if sender in ids_to_version:
                    key = (ids_to_version[sender], "out", receiver)
                    unique_edges[key] = unique_edges.get(key, 0.0) + weight
                if receiver in ids_to_version:
                    key = (ids_to_version[receiver], "in", sender)
                    unique_edges[key] = unique_edges.get(key, 0.0) + weight
            edges.extend((date, *key, weight) for key, weight in unique_edges.items())
    if all_dates != list(pd.date_range(all_dates[0], all_dates[-1], freq="7D")):
        raise ValueError("DeXposure weeks are non-consecutive or repeated")
    node_table = pd.DataFrame(nodes, columns=["snapshot", "node", "size"])
    if node_table.duplicated(["snapshot", "node"]).any():
        raise ValueError("Repeated node in graph snapshot")
    edge_table = pd.DataFrame(edges, columns=["snapshot", "version", "direction", "peer", "weight"])
    edge_table = edge_table.sort_values(
        ["snapshot", "version", "direction", "weight", "peer"],
        ascending=[True, True, True, False, True],
    )
    node_table.to_parquet(processed / "graph_nodes.parquet", index=False)
    edge_table.to_parquet(processed / "graph_edges.parquet", index=False)
    return {
        "full_snapshot_count": len(all_dates), "first": str(all_dates[0]), "last": str(all_dates[-1]),
        "retained_weeks": node_table.snapshot.nunique(), "ego_edges_by_version": edge_table.groupby("version").size().to_dict(),
        "graph_node_mapping": {v: {"id": i, "name": mapping[i]["name"]} for v, i in versions.items()},
    }


def prepare(sources, raw, processed, study):
    processed.mkdir(parents=True, exist_ok=True)
    audit = {"input_sha256": {}, "liquidations": {}, "reserves": {}}
    for name, metadata in sources["files"].items():
        observed = hash_file(raw / name)
        if metadata.get("sha256", observed) != observed:
            raise ValueError(f"SHA-256 mismatch for {name}")
        audit["input_sha256"][name] = observed
    start, stop = utc(study["sample_start"]), utc(study["sample_stop"])
    grid = pd.date_range(start - 23 * DAY, stop, freq="D", inclusive="left")
    with ZipFile(raw / "eth_blocks_data.zip") as archive:
        market, audit["oracle"] = oracle_features(archive, grid)
    panels = []
    with ZipFile(raw / "aave_data.zip") as archive:
        for version, node_id in study["versions"].items():
            labels, condensed, audit["liquidations"][version] = liquidation_panel(archive, grid, version, study)
            reserves, audit["reserves"][version] = reserve_features(archive, grid, version, study["assets"])
            debt = dated_borrowing(raw / f"aave-{version}-llama.json", grid, node_id)
            panel = pd.concat([labels, reserves, market], axis=1)
            panel["borrowing_scale_usd"] = debt
            panel["version"] = version
            panel["is_v3"] = float(version == "v3")
            panels.append(panel.reset_index(names="origin"))
            condensed.to_parquet(processed / f"{version}_liquidation_times.parquet", index=False)
    panel = pd.concat(panels, ignore_index=True).sort_values(["origin", "version"]).reset_index(drop=True)
    panel.to_parquet(processed / "panel.parquet", index=False)
    audit["analysis_rows"] = int(panel.origin.ge(start).sum())
    audit["graph"] = extract_graph(raw, processed, study)
    audit["derived_sha256"] = {path.name: hash_file(path) for path in sorted(processed.glob("*.parquet"))}
    write_json(processed / "data_audit.json", audit)
