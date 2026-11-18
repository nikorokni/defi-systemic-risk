<p align="center"><img src="assets/aave-liquidation-stress-banner.jpg" alt="Aave liquidation stress research" width="100%"></p>

# Early Warning of Aave Liquidation Stress under Delayed and Incomplete Network Data

A retrospective study of Ethereum Aave V2/V3, with an audited original benchmark, a later chronological fusion test and conditional source-weight transfer to published Compound histories.

**Research-review version, 17 November 2026.** Independent Compound contract reconciliation and a representative historical Aave Health Factor panel remain incomplete. The manuscript does not claim network value beyond validated account-health information or readiness for journal submission.

[Manuscript PDF](paper/manuscript.pdf) · [LaTeX](paper/main.tex) · [Persian change report](revision/CHANGELOG_FA.pdf) · [Evidence status](revision/results/task_status.json) · [Colab notebook](revision/Reproduce_Validated_Revision.ipynb)

## Results and their limits

| Original test: 1,022 forecasts / 110 positives | AP | Brier |
|:---|---:|---:|
| Prior-day liquidation | 0.3127 | 0.0918 |
| Market + local GRU | 0.2479 | 0.0904 |
| Temporal graph + Platt | 0.1954 | 0.0939 |

The graph-minus-GRU AP difference is -0.0525 with a 14-day paired block interval of [-0.1488, 0.0161]. A full primary-model refit gives graph AP 0.1949; its separate ledger is retained. All 47 supplied primary metric rows and the stratified, sensitivity and operational tables were independently recomputed from saved predictions.

| Later holdout: 744 forecasts / 40 positives | AP | Brier |
|:---|---:|---:|
| GRU | 0.324161 | 0.046263 |
| Learned reliability gate | 0.322987 | 0.046439 |
| Fixed half mixture | 0.330924 | 0.047430 |
| Graph-expiry heuristic | 0.324193 | 0.046262 |

The later calendar is 25 August 2025-31 August 2026. It is a new chronological test within the same Aave source, not prospective deployment or an independent chain dataset. The pinned graph ages from 7 to 378 days. Four negative ETH/USD source updates in September 2026 caused September-November to be quarantined before later-window scoring. See the [analysis specification](revision/later_holdout_plan.json).

Actual transfer was executed for newly trained shared-feature GRU and graph models. Aave weights, scaling and calibration are frozen when predicting Compound. Historical target q95 defines the target/units, so this is not a claim of zero target-domain information. On Compound V3, transferred GRU/graph AP is 0.1109/0.0921 versus 0.1982/0.1972 for separately trained target references. Five publisher-removed dates, including 5 August 2024, invalidate affected calendar histories; only 196 target test days remain per version. UTC day and valuation semantics remain unverified assumptions. [Transfer metadata](revision/results/transfer/run.json)

## Reproduce

Use Python 3.12. Install the recorded refit environment and the package from this checkout:

```bash
python -m pip install -r revision/requirements-lock.txt
python -m pip install --no-deps -e .
python -m unittest discover -s tests -v
python revision/scripts/audit_results.py
python revision/scripts/audit_remaining_tables.py
```

The audit commands use bundled forecast ledgers and do not retrain the original models. To refit from hash-checked upstream archives (the graph is approximately 1.13 GB):

```bash
python -m defi_risk fetch
python -m defi_risk prepare
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m defi_risk evaluate --out revision/results/reproduction
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python revision/scripts/transfer_experiment.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python revision/scripts/later_holdout.py
python revision/scripts/make_figures.py
python revision/scripts/make_review_report.py
python paper/build_manuscript.py
```

The paper builder requires Pandoc and working XeLaTeX/TeX Live or Tectonic. Scientific tables are generated from scored CSV files. The original `results/` folder is retained as a separate historical run; revised claims use `revision/results/` and the explicitly identified supplied ledger.

## Chain access and Health Factor

[Read-only validation code](revision/scripts/historical_validation.py) supports a specified Compound III USDC event history and basic legacy Aave account reconstruction. No transaction is signed or sent. It checks block coverage/identity and refuses unsupported eMode/ABI states. Selected-account mechanics checks do not supply a whole-market borrower panel.

`ETH_ARCHIVE_RPC` must permit historical `eth_call` and `eth_getLogs`; `ETH_VALIDATION_RPC` can provide a second independent provider. Put credentials in environment variables or Colab Secrets, never the repository. Public historical queries were denied HTTP 403 in this session. [Access report](revision/results/access/status.json)

The older Cred sample contains no observations overlapping the primary study. No HF-augmented forecasting result or complete independent Compound validation is asserted.

## Research materials

| Path | Contents |
|:---|:---|
| `paper/` | Revised manuscript, LaTeX, bibliography and builder |
| `revision/scripts/` | Audit, refit extension, transfer, figures and chain validation |
| `revision/results/` | Metrics, paired intervals, full ledgers, weights and metadata |
| `revision/inputs/` | Supplied review materials preserved separately |
| `revision/data/` | Small derived inputs and selected mechanics-check requests |
| `configs/` | Original pinned source hashes and model settings |
| `tests/` | Fourteen software tests, including temporal pairing and HF arithmetic |

[Sources and verification record](revision/source_verification.csv) · [Submission requirements](paper/submission_notes.md) · [Companion governance research](https://github.com/nikorokni/local-currency-defi-adaptive-governance)

The companion repository is a separate modelling project and does not independently validate these forecasts. Negative results and unresolved work are retained.