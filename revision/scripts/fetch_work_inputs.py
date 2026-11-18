"""Fetch/verify the pinned Compound publisher series required by transfer_experiment.py.

This fetch does not independently validate publisher numbers against chain logs.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import os
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "revision/inputs/Compound_2023_2024_Data_Feasibility_Audit/dataRegression.csv"
SOURCE = "https://raw.githubusercontent.com/ErumIftikhar/DefiLending_Data_Code/main/dataRegression.csv"
EXPECTED_SHA256 = "5255b787ee3c298dfd6985a973baa50abec77ec2738782641f4ff43489d3d4c2"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(verify_only: bool = False):
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    if DESTINATION.exists():
        got = digest(DESTINATION)
        if got == EXPECTED_SHA256:
            print("Verified pinned Compound CSV:", DESTINATION)
            return
        raise RuntimeError(
            "Existing Compound data have an unexpected SHA256; do not silently overwrite "
            f"or relabel this input. Found {got}, expected {EXPECTED_SHA256}"
        )
    if verify_only:
        raise FileNotFoundError(f"Required pinned Compound CSV missing: {DESTINATION}")
    request = urllib.request.Request(SOURCE, headers={"User-Agent": "DeFi-research-reproduction/1.0"})
    with tempfile.NamedTemporaryFile(dir=DESTINATION.parent, prefix="compound_", delete=False) as tmp:
        temporary = Path(tmp.name)
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    tmp.write(block)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    observed = digest(temporary)
    if observed != EXPECTED_SHA256:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"Publisher bytes changed: observed SHA256={observed}, "
            f"expected={EXPECTED_SHA256}. Re-audit instead of changing the pinned hash."
        )
    with temporary.open("r", encoding="utf-8-sig", newline="") as f:
        columns = next(csv.reader(f))
    for required in ("Date", "Liquidate_Compoundv2ethereum", "Liquidate_Compoundv3ethereum"):
        if required not in columns:
            temporary.unlink(missing_ok=True)
            raise ValueError(f"Required source column absent: {required}")
    os.replace(temporary, DESTINATION)
    print("Downloaded and verified publisher CSV:", DESTINATION)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    fetch(args.verify_only)
