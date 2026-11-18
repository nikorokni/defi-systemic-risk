"""Read-only chain reconciliation. No transactions are constructed or broadcast.

Requires ETH_ARCHIVE_RPC; ETH_VALIDATION_RPC supplies an independent endpoint.
Examples:
  python revision/scripts/historical_validation.py compound --start-block ... --stop-block ...
  python revision/scripts/historical_validation.py health --accounts revision/data/hf_spotcheck_requests.csv

AbsorbDebt.usdValue is retained as the contract's emitted value, not relabelled
as borrower principal or seized collateral. HF reconstruction below supports
the legacy basic V2/V3 formula and fails closed on eMode or layout mismatches.
It cannot establish a representative whole-market position panel from selected
accounts. No empirical HF output is generated when historical access fails.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import urllib.request

import pandas as pd
from eth_hash.auto import keccak

ROOT = Path(__file__).resolve().parents[2]
POOLS = {"v2":"0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",
         "v3":"0x87870Bca3F3fD6335C3F4cE8392D69350B4fa4E2"}
COMET_USDC = "0xc3d688B66703497DAA19211EEdff47f25384cdc3"
WAD = 10**18


class UnsupportedState(ValueError):
    pass


def rpc(endpoint, method, params):
    req = urllib.request.Request(endpoint, data=json.dumps(dict(jsonrpc="2.0", id=1,
        method=method, params=params)).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=40) as response:
        result = json.load(response)
    if "error" in result:
        raise RuntimeError(str(result["error"]))
    if "result" not in result or result["result"] is None:
        raise RuntimeError("Missing RPC result; null is not a zero balance")
    return result["result"]


def words(result):
    data = result.removeprefix("0x")
    if len(data) % 64:
        raise ValueError("Malformed ABI word response")
    return [int(data[i:i+64], 16) for i in range(0, len(data), 64)]


def address(n):
    return "0x"+format(n, "040x")[-40:]


def call(endpoint, target, signature, args, block):
    encoded = "0x"+keccak(signature.encode()).hex()[:8]+"".join(format(int(v, 16) if isinstance(v, str) else v, "064x") for v in args)
    return words(rpc(endpoint, "eth_call", [dict(to=target, data=encoded), hex(block)]))


def rebuild_basic_hf(components):
    """Integer arithmetic used by the basic legacy GenericLogic formula.

    Inputs are raw balances and common-base oracle prices at one exact block.
    Debt-free accounts return None. Decimal conversion never passes through float.
    """
    collateral, debt, weighted = 0, 0, 0
    for r in components:
        if r.get("emode_category", 0) != 0:
            raise UnsupportedState("eMode requires historical implementation-specific rules")
        scale = 10**int(r["decimals"])
        price = int(r["price_base"])
        if price <= 0:
            raise ValueError("Nonpositive oracle value")
        cb, db = int(r["collateral_balance_raw"]), int(r["stable_debt_raw"])+int(r["variable_debt_raw"])
        if min(cb, db) < 0:
            raise ValueError("Negative raw balances")
        lt = int(r["liquidation_threshold_bps"])
        if not 0 <= lt <= 10000:
            raise ValueError("Invalid liquidation threshold")
        debt += price*db//scale
        if r["collateral_enabled"] and lt > 0:
            value = price*cb//scale
            collateral += value
            weighted += value*lt
    average_lt = weighted//collateral if collateral else 0
    discounted = (collateral*average_lt+5000)//10000
    hf = (discounted*WAD+debt//2)//debt if debt else None
    return dict(collateral_base=collateral, debt_base=debt, average_liquidation_threshold_bps=average_lt,
                health_factor_wad=hf, health_factor_decimal=str(Decimal(hf)/WAD) if hf is not None else None)


def reconstruct_account(endpoint, version, user, block, origin):
    pool = POOLS[version]
    header = rpc(endpoint, "eth_getBlockByNumber", [hex(block), False])
    btime = pd.Timestamp(int(header["timestamp"], 16), unit="s", tz="UTC")
    if btime >= pd.to_datetime(origin, utc=True):
        raise ValueError("Snapshot is not strictly before forecast origin")
    if version == "v3" and call(endpoint, pool, "getUserEMode(address)", [user], block)[0] != 0:
        raise UnsupportedState("Historical eMode account not supported by the basic reconstruction")
    provider = address(call(endpoint, pool, "getAddressesProvider()" if version == "v2" else "ADDRESSES_PROVIDER()", [], block)[0])
    oracle = address(call(endpoint, provider, "getPriceOracle()", [], block)[0])
    reserve_words = call(endpoint, pool, "getReservesList()", [], block)
    if reserve_words[0] != 32 or len(reserve_words) != reserve_words[1]+2:
        raise UnsupportedState("Unexpected reserve list ABI")
    reserves = [address(w) for w in reserve_words[2:]]
    user_config = call(endpoint, pool, "getUserConfiguration(address)", [user], block)[0]
    components = []
    for asset in reserves:
        state = call(endpoint, pool, "getReserveData(address)", [asset], block)
        if version == "v2":
            if len(state) != 12:
                raise UnsupportedState("V2 reserve layout mismatch")
            ai, si, vi, ri = 7, 8, 9, 11
        else:
            if len(state) != 15:
                raise UnsupportedState("Historical V3 reserve layout must match the audited legacy 15-word ABI")
            ai, si, vi, ri = 8, 9, 10, 7
        config, rid = state[0], state[ri]
        enabled = bool((user_config >> (2*rid+1)) & 1)
        a = call(endpoint, address(state[ai]), "balanceOf(address)", [user], block)[0]
        sd = call(endpoint, address(state[si]), "balanceOf(address)", [user], block)[0] if state[si] else 0
        vd = call(endpoint, address(state[vi]), "balanceOf(address)", [user], block)[0] if state[vi] else 0
        if not (a or sd or vd):
            continue
        price = call(endpoint, oracle, "getAssetPrice(address)", [asset], block)[0]
        components.append(dict(asset=asset, decimals=(config >> 48) & 255,
            liquidation_threshold_bps=(config >> 16) & 65535, collateral_enabled=enabled,
            collateral_balance_raw=str(a), stable_debt_raw=str(sd), variable_debt_raw=str(vd),
            price_base=str(price), emode_category=0))
    rebuilt = rebuild_basic_hf(components)
    ref = call(endpoint, pool, "getUserAccountData(address)", [user], block)
    if len(ref) != 6:
        raise UnsupportedState("Unexpected Pool account ABI")
    mismatches = {"collateral_base":ref[0]-rebuilt["collateral_base"],
                  "debt_base":ref[1]-rebuilt["debt_base"],
                  "health_factor_wad":0 if rebuilt["health_factor_wad"] is None and ref[1] == 0 else ref[5]-rebuilt["health_factor_wad"]}
    return dict(version=version, account=user, block_number=block, block_hash=header["hash"],
        block_utc=str(btime), origin_utc=origin, components=components, reconstructed=rebuilt,
        pool_reference_wad=str(ref[5]), exact_differences=mismatches,
        exact_match=all(n == 0 for n in mismatches.values()))


def compound_events(endpoint, start, stop):
    topic = "0x"+keccak(b"AbsorbDebt(address,address,uint256,uint256)").hex()
    all_logs, coverage = [], []
    def collect(a, b):
        try:
            logs = rpc(endpoint, "eth_getLogs", [dict(address=COMET_USDC, fromBlock=hex(a), toBlock=hex(b), topics=[topic])])
            if len(logs) >= 1000:
                raise RuntimeError("Possible provider truncation")
            return logs, [(a, b)]
        except Exception:
            if b-a < 1000:
                raise
            m = (a+b)//2
            l, lc = collect(a, m)
            r, rc = collect(m+1, b)
            return l+r, lc+rc
    for a in range(start, stop+1, 20000):
        logs, ranges = collect(a, min(stop, a+19999))
        all_logs.extend(logs)
        coverage.extend(ranges)
    coverage.sort()
    if coverage[0][0] != start or coverage[-1][1] != stop or any(coverage[i][1]+1 != coverage[i+1][0] for i in range(len(coverage)-1)):
        raise ValueError("Nonexhaustive block coverage")
    headers = {}
    rows = []
    for log in all_logs:
        block = int(log["blockNumber"], 16)
        if block not in headers:
            headers[block] = rpc(endpoint, "eth_getBlockByNumber", [hex(block), False])
        if log.get("removed") or log["blockHash"].lower() != headers[block]["hash"].lower():
            raise ValueError("Removed log or block-hash mismatch")
        data = words(log["data"])
        if len(data) != 2 or len(log["topics"]) != 3:
            raise ValueError("Unexpected AbsorbDebt ABI")
        rows.append(dict(transaction_hash=log["transactionHash"], log_index=int(log["logIndex"],16),
            block_number=block, block_hash=log["blockHash"], contract=COMET_USDC,
            timestamp_utc=str(pd.Timestamp(int(headers[block]["timestamp"],16),unit="s",tz="UTC")),
            absorber="0x"+log["topics"][1][-40:], borrower="0x"+log["topics"][2][-40:],
            base_paid_out_raw=str(data[0]), emitted_usd_value_raw=str(data[1]),
            emitted_usd_value=str(Decimal(data[1])/10**8)))
    return rows, coverage


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="task", required=True)
    c = sub.add_parser("compound")
    c.add_argument("--start-block", type=int, required=True)
    c.add_argument("--stop-block", type=int, required=True)
    h = sub.add_parser("health")
    h.add_argument("--accounts", type=Path, required=True)
    p.add_argument("--out", type=Path, default=ROOT/"revision/results/chain_validation")
    a = p.parse_args()
    ep = os.environ.get("ETH_ARCHIVE_RPC")
    independent = os.environ.get("ETH_VALIDATION_RPC")
    if not ep:
        raise RuntimeError("ETH_ARCHIVE_RPC is not configured; no empirical validation has run")
    if int(rpc(ep, "eth_chainId", []), 16) != 1:
        raise ValueError("Require Ethereum mainnet")
    a.out.mkdir(parents=True, exist_ok=True)
    if a.task == "compound":
        rows, coverage = compound_events(ep, a.start_block, a.stop_block)
        data = pd.DataFrame(rows)
        if not data.empty and data.duplicated(["transaction_hash", "log_index"]).any():
            raise ValueError("Duplicate chain event")
        compared = False
        if independent:
            other, _ = compound_events(independent, a.start_block, a.stop_block)
            if sorted(rows, key=lambda r:(r["transaction_hash"],r["log_index"])) != sorted(other,key=lambda r:(r["transaction_hash"],r["log_index"])):
                raise ValueError("Independent event providers disagree")
            compared = True
        data.to_csv(a.out/"compound_v3_usdc_absorb_debt.csv", index=False)
        (a.out/"compound_coverage.json").write_text(json.dumps(dict(block_ranges=coverage,
            independent_second_provider_match=compared, source_scope="Ethereum Comet USDC only",
            publisher_series_reconciliation_complete=False),indent=2))
    else:
        requests = pd.read_csv(a.accounts)
        output = []
        for r in requests.itertuples():
            record = reconstruct_account(ep, r.version, r.account, int(r.block_number), r.origin_utc)
            if independent:
                second = reconstruct_account(independent, r.version, r.account, int(r.block_number), r.origin_utc)
                if record != second:
                    raise ValueError("Independent historical states disagree")
            output.append(record)
        (a.out/"selected_account_hf.json").write_text(json.dumps(dict(records=output,
            independent_provider_checked=bool(independent), representative_full_market_panel=False),indent=2))


if __name__ == "__main__":
    main()