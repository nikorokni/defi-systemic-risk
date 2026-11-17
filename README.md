<p align="center">
  <img src="assets/aave-liquidation-stress-banner.jpg" alt="Aave liquidation stress cover with a stylised network and dashed links representing delayed observations" width="100%">
</p>

<h1 align="center">Early Warning of Aave Liquidation Stress under Delayed and Incomplete Network Data</h1>

<p align="center">A retrospective walk-forward study of Ethereum Aave V2 and V3</p>

<p align="center">
  <a href="paper/manuscript.pdf"><strong>Read the manuscript</strong></a> ·
  <a href="#results"><strong>See the results</strong></a> ·
  <a href="data/README.md"><strong>Inspect the data</strong></a> ·
  <a href="#reproduce-the-study"><strong>Reproduce the study</strong></a>
</p>

## Research question

Does a weekly graph of global DeFi exposures improve the next-day warning of liquidations in Aave V2 and V3 on Ethereum? The study compares models with and without graph information, then measures what happens when oracle prices arrive late, network snapshots are stale, or the graph loses links. It also tests how an uncertainty-based review queue changes the number of warnings an analyst would see.

The strongest pooled ranking came from the prior day's liquidation volume. The calibrated temporal graph ensemble ranked below the market-augmented GRU, with uncertainty around the difference. Platt calibration improved the graph's probability scores, and a combined input disruption weakened its ranking further.

| Study at a glance | Details |
|:---|:---|
| Forecast unit | One Aave version on Ethereum at UTC midnight |
| Study calendar | 1 March 2023 to 24 August 2025 |
| Primary target | Whether USD liquidation volume in the next 24 hours exceeds the version-specific 95th percentile estimated in that fold’s training data |
| Evaluation | Three disjoint test windows, 1,022 forecasts and 110 positive outcomes |
| Robustness checks | Edge thinning, oracle delay, extra graph delay, alternate horizons and a borrowing-scaled target |

## Data and evaluation design

| Input | How it enters the forecast |
|:---|:---|
| [Aave liquidation and reserve records](https://doi.org/10.5281/zenodo.24245638) | Prior liquidation volumes and counts, plus borrowing and utilisation for DAI, USDC, USDT and WETH. Future liquidation events supply the outcome. |
| [Chainlink ETH/USD and BTC/USD histories](https://doi.org/10.5281/zenodo.24245638) | Returns, realised volatility and observation ages from timestamped oracle updates. |
| [DeXposure weekly snapshots](https://github.com/dthinkr/DeXposure/tree/79071f26ddb3cf59adb433fb277bc820732bf863) | Directed exposures around global Aave V2 and V3 nodes. The latest eligible snapshot is dated at least seven days before the forecast. |
| [DefiLlama borrowing history](https://docs.llama.fi/list-your-project/what-to-include-as-tvl) | Lagged Ethereum borrowing as the denominator of a sensitivity target. Its pool coverage is broader than the liquidation feed. |

Each fold uses earlier observations for training and later development windows for tuning and calibration. The target cutoff is fitted on training data for each Aave version and horizon. Market and reserve features use source timestamps strictly before the forecast origin. A one-day buffer separates training, tuning and calibration label windows from the next partition. The August 2024 and February 2025 episodes are examined within the held-out windows.

~~~mermaid
flowchart TD
    L["Aave events and reserve data"] --> F["Features available at UTC midnight"]
    P["Chainlink oracle updates"] --> F
    L --> Y["Next-day stress labels"]
    F --> B["Market-augmented GRU"]
    F --> G["Temporal graph ensemble"]
    N["Lagged DeXposure snapshots"] --> G
    B --> E["Walk-forward test"]
    G --> E
    Y --> E
    E --> R["Ranking, calibration and alert burden"]
    E --> S["Delayed and missing inputs"]
~~~

The graph model aggregates up to 16 weighted neighbours in each direction and processes 14 daily feature vectors per forecast. The GRU comparison uses the same sequence length and local and market inputs. Five independently seeded members contribute to each recurrent ensemble. The experiment also evaluates a training prior, prior-day liquidation, logistic models, LightGBM, and graph ablations. The implementation and exact timing rules are in the [manuscript](paper/manuscript.pdf), [study configuration](configs/study.json), and [data audit](results/data_audit.json).

## Results

### Next-day forecasts

Higher average precision (AP) means stronger ranking for rare stress outcomes. Lower Brier scores mean smaller probability error.

| Model | Average precision ↑ | Brier score ↓ |
|:---|---:|---:|
| Training prior | 0.1150 | 0.0990 |
| Prior-day liquidation | **0.3127** | 0.0918 |
| LightGBM | 0.2574 | 0.0907 |
| LightGBM + graph summaries | 0.2200 | 0.0926 |
| Market-augmented GRU + Platt | 0.2479 | 0.0904 |
| Temporal graph, raw ensemble | 0.1926 | 0.0963 |
| Temporal graph + Platt | 0.1949 | 0.0938 |
| Augmented graph + Platt | 0.2155 | 0.0921 |

The graph minus GRU AP difference was **−0.0530**, with a paired 95% interval of **[−0.1459, 0.0159]** using 14-day time blocks. The graph led on AP in April–July and August–December 2024. The GRU led in January–August 2025, the largest test fold. Across the alternate six-hour, seven-day and borrowing-scaled targets, the matched GRU also had higher pooled AP and lower Brier scores. [All model scores](results/metrics.csv) · [Fold results](results/metrics_by_fold.csv) · [Paired differences](results/paired_differences.csv) · [Sensitivity results](results/label_sensitivity.csv)

### Data outages and review

The combined stress test removes 30% of retained graph links in expectation, adds a one-day oracle delay and adds seven days to the graph lag. Temporal graph AP fell from **0.1949** on clean data to **0.1339**. Training with perturbed inputs raised combined-case AP to **0.1436**. Combined-case Brier was **0.0971** for the augmented graph and **0.0962** for the original graph. The disruption therefore affected ranking and probability accuracy differently. [Perturbation scores](results/metrics.csv) · [Edge-thinning figure](figures/edge_thinning.pdf)

Platt calibration reduced the graph ensemble's Brier score from **0.0963** to **0.0938** on clean test data. The separate review gate assigns high-disagreement forecasts to a queue before automated alerting. The review queue includes 24 episode onsets.

| Temporal graph alert rule | Automated alerts | False alerts | Onsets alerted | Reviews |
|:---|---:|---:|---:|---:|
| Probability threshold | 189 | 152 | 16/70 | 0 |
| Probability threshold with review | 36 | 26 | 6/70 | 245 |

<p align="center">
  <a href="figures/reliability.pdf"><img src="figures/reliability.png" width="570" alt="Reliability diagram comparing predicted stress probabilities with observed frequencies"></a>
</p>

[Alert accounting and lead times](results/alerts.csv) · [Risk–coverage](figures/risk_coverage.pdf) · [Historical stress windows](figures/historical_windows.pdf)

## Scope and connection to governance

The target is realised liquidation volume on Ethereum. DeXposure links describe global, weekly token-mediated exposures. The mapping joins by Aave version and supports an incremental forecasting comparison. Establishing causal contagion would require independently labelled outcomes at linked pools and a strategy to account for common shocks.

The warning estimates can serve as inputs to a risk-governance policy. The companion study examines how policy responds to oracle latency and financial stress. [Adaptive Governance, Oracle Latency, and Automated Risk Engine Design](https://github.com/nikorokni/local-currency-defi-adaptive-governance)

## Reproduce the study

The reference run used Python 3.12 and a CPU build of PyTorch 2.7.1. Allow about 1.3 GB for the upstream archives and additional space for prepared tables. Run these commands from the repository root.

~~~bash
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
~~~

The four evaluation commands refit the respective targets. For data stored elsewhere, put the global options before the subcommand.

~~~bash
python -m defi_risk --raw /path/to/raw --processed /path/to/processed prepare
~~~

To regenerate the manuscript tables and PDF, install Pandoc 3 and TeX Live with XeLaTeX and Latin Modern fonts.

~~~bash
python paper/build_manuscript.py
mkdir -p build
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build paper/main.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build paper/main.tex
cp build/main.pdf paper/manuscript.pdf
~~~

## Repository guide

| Location | Contents |
|:---|:---|
| [paper/](paper/) | Research manuscript, LaTeX source, analysis plan and bibliography |
| [data/](data/) | Source provenance and notes on reconstructing the inputs |
| [configs/](configs/) | Data hashes, model settings, test windows and perturbation parameters |
| [src/defi_risk/](src/defi_risk/) | Data preparation, models, evaluation and figure generation |
| [results/primary/run.json](results/primary/run.json) | Fold counts, target cutoffs and fit metadata |
| [results/primary/predictions.csv.gz](results/primary/predictions.csv.gz) | Held-out probabilities, outcomes, automated alerts and review decisions |
| [figures/](figures/) | Reproducible charts with matching PDF and PNG versions |

For research citations, use the full manuscript title and the commit used. Upstream attribution and licence information are in the [bibliography](paper/references.bib) and [data provenance](data/README.md). [Journal targeting and submission notes](paper/submission_notes.md)

## Research extensions — implementation status (17 November 2026)

The following analyses are **not** included in the published manuscript's original empirical results. New model scores must not be asserted until these commands are executed on the pinned source archives.

**Independent-seed edge-thinning experiment.** The original deterministic mask remains unchanged for reproducibility; the new command retrains the graph ensemble per chronological fold, then compares 100 independent thinning masks for each corruption rate. It saves every held-out forecast, seed-specific AP and Brier score, and variation across masks.

```bash
python -m defi_risk.edge_monte_carlo --processed data/processed --repetitions 100
```

**Exploratory graph/local fusion.** This analysis pairs existing held-out Graph+Platt and GRU+Platt predictions by date, fold and Aave version. The fixed 50% mixture is compared to a *predeclared heuristic* that reduces graph weight as calibration-based ensemble disagreement increases. This is not a trained neural gating network and is **not** an independently pre-registered new test: the ledger was previously inspected. Do not call it a demonstrated novel method without a fresh out-of-sample evaluation.

```bash
python -m defi_risk.fusion --ledger results/primary/predictions.csv.gz --out results/fusion
```

**Learned chronological reliability gate.** A/B held-out forecasts train a four-parameter regularised mixture gate; only later fold C is used for its evaluation. This is still exploratory because the hypothesis was formulated after the original results were seen.\n\n```bash\npython -m defi_risk.chronological_gate --ledger results/primary/predictions.csv.gz\n```\n\n**External data and Health Factor audit.** Candidate independent protocol data and requirements for reconstructing historical Aave account risk are documented in [the validation protocol](paper/external_validation_protocol.md). The strict validators can check a *supplied* independent event table or health-factor cross-check; they cannot supply those records themselves.

```bash
python -m defi_risk.external_audit events /path/to/independent_liquidations.parquet --output results/external_audit.json
python -m defi_risk.external_audit health /path/to/historical_health_factors.parquet --output results/health_audit.json
```

The source validity and publication status of the [adaptive-governance research manuscript](https://github.com/nikorokni/local-currency-defi-adaptive-governance) are kept distinct from the present retrospective benchmark. No independent-protocol transfer or historical HF validation result is currently claimed. Any journal-submission declaration must follow the selected venue's policy.
