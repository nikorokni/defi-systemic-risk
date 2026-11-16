# Early Warning of Aave Liquidation Stress

A reproducible walk-forward study of whether weekly DeXposure links improve daily warning probabilities for the Ethereum Aave V2 and V3 liquidation series. The study covers 1 March 2023 through 24 August 2025. The three test periods contain 1,022 version-day predictions and 110 positives under cutoffs fixed from the corresponding training data.

[Read the manuscript PDF](paper/manuscript.pdf) · [Analysis plan](paper/analysis_plan.md) · [Source provenance](data/README.md) · [Submission notes](paper/submission_notes.md)

## Results

| 24-hour test model | Average precision | Brier score |
|:---|---:|---:|
| Prior-day liquidation | 0.3127 | 0.0918 |
| LightGBM | 0.2574 | 0.0907 |
| Market-augmented GRU + Platt | 0.2479 | 0.0904 |
| Temporal graph + Platt | 0.1949 | 0.0938 |

For graph minus GRU, the blocked 95% AP interval is [−0.1460, 0.0159]. The scheduled robustness tests place extra reporting lags and missing graph links on the held-out inputs. Test probabilities, outcome labels, false alerts and review decisions are published under [results](results). The precise results and scope are described in the manuscript.

## Run from the repository root

Python 3.12 and a CPU build of PyTorch 2.7.1 were used. Allow roughly 1.3 GB of download space for the source archives and additional room for prepared tables. Each of the four evaluation commands refits its respective target and uses five fixed seeds for recurrent ensembles.

    python3.12 -m venv .venv
    source .venv/bin/activate
    python -m pip install 'torch==2.7.1+cpu' --index-url https://download.pytorch.org/whl/cpu
    python -m pip install -e .

    python -m defi_risk fetch
    python -m defi_risk prepare
    python -m unittest discover -s tests -v

    export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
    python -m defi_risk evaluate
    python -m defi_risk evaluate --hours 6
    python -m defi_risk evaluate --hours 168
    python -m defi_risk evaluate --scaled
    python -m defi_risk report

Pass a different workspace dataset directory using the global options before the subcommand, for example:

    python -m defi_risk --raw /path/to/raw --processed /path/to/processed prepare

To regenerate the manuscript tables and review PDF, install Pandoc 3 and a TeX Live distribution with XeLaTeX and Latin Modern fonts. Compile from the repository root so the LaTeX can resolve the figure paths.

    python paper/build_manuscript.py
    mkdir -p build
    xelatex -interaction=nonstopmode -halt-on-error -output-directory=build paper/main.tex
    xelatex -interaction=nonstopmode -halt-on-error -output-directory=build paper/main.tex
    cp build/main.pdf paper/manuscript.pdf

## Where to inspect the evidence

| Path | Contents |
|:---|:---|
| [configs/study.json](configs/study.json) | Dates, horizon, early stopping, seeds and test perturbations |
| [configs/sources.json](configs/sources.json) | Verified upstream URLs and content hashes |
| [results/data_audit.json](results/data_audit.json) | Source counts, event-to-hourly parity and prepared-data hashes |
| [results/primary/run.json](results/primary/run.json) | Primary fold samples, cutoffs and stored stopping epochs |
| [results/primary/predictions.csv.gz](results/primary/predictions.csv.gz) | Frozen held-out forecast ledger with labels and routing decisions |
| [results/paired_differences.csv](results/paired_differences.csv) | Paired moving-block model differences |
| [results/alerts.csv](results/alerts.csv) | Automated warnings, false alerts, reviews and onset lead time |
| [results/label_sensitivity.csv](results/label_sensitivity.csv) | Six-hour, seven-day and broad borrowing-ratio sensitivity |
| [figures](figures) | Vector and raster versions of four result figures |

The event target is a training-defined tail of observed USD liquidation volume. The graph is global and weekly, while the outcome is Ethereum-specific. These differences shape how the forecasting evidence should be used in a governance study. The archive contains two labelled version series, so the empirical generalisation claim is limited to that cohort.
