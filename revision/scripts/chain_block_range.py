"""Resolve historic Ethereum mainnet block-number bounds from actual UTC timestamps.

Authenticated historical RPC required; never log or commit credentials.
Run with --start-utc 2024-08-01 --end-utc 2024-08-09 (exclusive end).
"""
import argparse
from datetime import datetime,timezone
import json,os
from pathlib import Path
from urllib.request import Request,urlopen


def rpc(endpoint,method,params):
    payload=json.dumps(dict(jsonrpc="2.0",id=1,method=method,params=params)).encode()
    with urlopen(Request(endpoint,data=payload,headers={"Content-Type":"application/json"}),timeout=40) as response:
        result=json.load(response)
    if result.get("error") or result.get("result") is None:
        raise RuntimeError("Historical RPC unavailable or denied: "+str(result.get("error")))
    return result["result"]


def timestamp(t):
    d=datetime.fromisoformat(t.replace("Z","+00:00"))
    if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
    return int(d.timestamp())


def first_block_at_or_after(t,last,read):
    lo,hi=0,last+1
    while lo<hi:
        mid=(lo+hi)//2
        if read(mid)<t:lo=mid+1
        else:hi=mid
    return lo


def resolve(endpoint,start,end):
    if int(rpc(endpoint,"eth_chainId",[]),16)!=1:
        raise ValueError("Ethereum mainnet chain 1 required")
    last=int(rpc(endpoint,"eth_blockNumber",[]),16)
    cached={}
    def read(b):
        if b not in cached:
            header=rpc(endpoint,"eth_getBlockByNumber",[hex(b),False])
            if int(header["number"],16)!=b:raise RuntimeError("Wrong block")
            cached[b]=int(header["timestamp"],16)
        return cached[b]
    a,b=timestamp(start),timestamp(end)
    if b<=a or a<=read(0) or b>read(last):
        raise ValueError("Out-of-bounds UTC interval")
    first=first_block_at_or_after(a,last,read)
    stop=first_block_at_or_after(b,last,read)
    if read(first-1)>=a or read(first)<a or read(stop-1)>=b or read(stop)<b:
        raise RuntimeError("Incorrect historic boundary")
    return dict(chain_id=1,start_utc=start,end_utc_exclusive=end,
                first_inclusive_block=first,last_inclusive_block=stop-1,
                note="Block bounds only; independent log reconciliation still required")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start-utc",required=True)
    p.add_argument("--end-utc",required=True)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    endpoint=os.environ.get("ETH_ARCHIVE_RPC")
    if not endpoint:raise RuntimeError("ETH_ARCHIVE_RPC missing: use Colab Secrets")
    result=resolve(endpoint,a.start_utc,a.end_utc)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
