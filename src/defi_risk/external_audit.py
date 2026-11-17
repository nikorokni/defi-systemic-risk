"""Strict quality gates for independent deployments and historical Aave health factors.

These tools validate *supplied* datasets. They do not generate or claim
historical observations, and they reject missing core identifiers.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

EVENT_COLS = [
    "chain_id", "protocol", "deployment_address", "tx_hash", "log_index",
    "block_number", "block_timestamp_utc", "liquidated_debt_token",
    "liquidated_debt_amount", "debt_price_usd_asof", "liquidated_debt_usd",
    "source_snapshot", "source_hash",
]
HF_COLS = [
    "chain_id", "protocol", "deployment_address", "account", "block_number",
    "block_timestamp_utc", "origin_utc", "collateral_liquidation_weighted_usd",
    "total_debt_usd", "computed_health_factor", "reference_health_factor",
]


def _require(frame, columns):
    absent = sorted(set(columns) - set(frame.columns))
    if absent:
        raise ValueError(f"Missing required fields: {absent}")
    if frame.empty:
        raise ValueError("Empty input")


def audit_events(frame):
    _require(frame, EVENT_COLS)
    x = frame.copy()
    if x[EVENT_COLS].isna().any().any():
        raise ValueError("Unresolved null in required event data")
    keys = ["chain_id", "tx_hash", "log_index"]
    if x.duplicated(keys).any():
        raise ValueError("Duplicate canonical chain/transaction/log event identifier")
    x["block_timestamp_utc"] = pd.to_datetime(x.block_timestamp_utc, utc=True, errors="raise")
    x["debt_price_usd_asof"] = pd.to_datetime(x.debt_price_usd_asof, utc=True, errors="raise")
    if (x.debt_price_usd_asof > x.block_timestamp_utc).any():
        raise ValueError("Future price used to value a historical debt liquidation")
    if (x[["liquidated_debt_amount","liquidated_debt_usd"]].astype(float) < 0).any().any():
        raise ValueError("Negative liquidation size")
    return {
        "rows":len(x), "protocols":sorted(x.protocol.unique().tolist()),
        "deployments":int(x[["chain_id","protocol","deployment_address"]].drop_duplicates().shape[0]),
        "start_utc":str(x.block_timestamp_utc.min()),
        "end_utc":str(x.block_timestamp_utc.max()),
        "note":"No contract-event completeness or external price reconciliation is implied by schema validation."
    }


def audit_health_factors(frame, max_abs_tolerance=0.005):
    _require(frame, HF_COLS)
    x=frame.copy()
    x["block_timestamp_utc"]=pd.to_datetime(x.block_timestamp_utc,utc=True)
    x["origin_utc"]=pd.to_datetime(x.origin_utc,utc=True)
    if (x.block_timestamp_utc >= x.origin_utc).any():
        raise ValueError("HF observations are not strictly pre-decision")
    if x.duplicated(["chain_id","protocol","deployment_address","account","origin_utc"]).any():
        raise ValueError("Repeated account at the same origin")
    debt=x.total_debt_usd.astype(float).to_numpy()
    coll=x.collateral_liquidation_weighted_usd.astype(float).to_numpy()
    if np.any(debt<0) or np.any(coll<0):
        raise ValueError("Negative debt or risk-weighted collateral")
    computed=x.computed_health_factor.astype(float).to_numpy()
    eligible=debt>0
    expected=coll[eligible]/debt[eligible]
    if not np.allclose(expected,computed[eligible],atol=1e-8,rtol=1e-6):
        raise ValueError("Computed HF disagrees with provided debt/collateral decomposition")
    reference=x.reference_health_factor.astype(float).to_numpy()
    if not np.isfinite(reference[eligible]).all():
        raise ValueError("Missing independent reference HF on positive-debt rows")
    errors=np.abs(computed[eligible]-reference[eligible])
    if not len(errors):
        raise ValueError("No positive-debt accounts")
    return {
        "accounts_with_debt":int(eligible.sum()),
        "reference_abs_error_median":float(np.median(errors)),
        "reference_abs_error_p95":float(np.quantile(errors,.95)),
        "share_exceeding_abs_tolerance":float(np.mean(errors>max_abs_tolerance)),
        "hf_below_1":int(np.sum(computed[eligible]<1.0)),
        "hf_1_to_1_05":int(np.sum((computed[eligible]>=1.0)&(computed[eligible]<1.05))),
        "hf_1_05_to_1_1":int(np.sum((computed[eligible]>=1.05)&(computed[eligible]<1.1))),
        "warning":"Comparing to a reference provided in the same file does not independently establish reference provenance."
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("kind",choices=("events","health"))
    p.add_argument("input",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    frame=pd.read_parquet(args.input) if args.input.suffix==".parquet" else pd.read_csv(args.input)
    report=audit_events(frame) if args.kind=="events" else audit_health_factors(frame)
    payload=json.dumps(report,indent=2,ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(payload+"\n",encoding="utf8")
    print(payload)


if __name__=="__main__":
    main()
