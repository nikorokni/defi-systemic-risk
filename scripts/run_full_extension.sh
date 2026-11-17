#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON=${PYTHON:-python3.12}
if ! command -v "$PYTHON" >/dev/null 2>&1; then PYTHON=python3; fi
"$PYTHON" - <<'PY'
import importlib
missing=[]
for pkg in ['numpy','pandas','scipy','sklearn','torch','lightgbm','ijson','pyarrow']:
    try: importlib.import_module(pkg)
    except ImportError: missing.append(pkg)
if missing: raise SystemExit("Missing: "+", ".join(missing)+"; pip install -e .")
PY
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1} OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}
"$PYTHON" -m defi_risk fetch
"$PYTHON" -m defi_risk prepare
"$PYTHON" -m unittest discover -s tests -v
"$PYTHON" -m defi_risk evaluate
"$PYTHON" -m defi_risk.edge_monte_carlo --processed data/processed --repetitions 100
"$PYTHON" -m defi_risk.fusion
"$PYTHON" -m defi_risk.chronological_gate
"$PYTHON" -m defi_risk report
echo "Completed; inspect new result tables before updating the manuscript."
