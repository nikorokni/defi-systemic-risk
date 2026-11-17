"""Check raw data provenance without downloading or changing sources."""
import hashlib
import json
from pathlib import Path
files=json.loads(Path("configs/sources.json").read_text())["files"]
root=Path("data/raw")
for name,spec in files.items():
    path=root/name
    if not path.exists():
        print(f"MISSING {name} — {spec['url']}")
        continue
    with path.open("rb") as handle:
        checksum=hashlib.file_digest(handle,"sha256").hexdigest()
    expected=spec.get("sha256")
    print("PASS" if expected==checksum else "NOT PINNED" if not expected else "HASH MISMATCH",name,checksum)
