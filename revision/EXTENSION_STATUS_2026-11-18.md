# Research extension: 18 November 2026

## Executed (frozen, held-out Aave predictions)

An additional **unitless decision-cost sensitivity** study uses 1,022 original Aave forecasts (110 positives) and 744 later Aave forecasts (40 positives). The analytical cost-ratio cutoff `p >= 1/(1+r)` is specified without tuning test thresholds; false alert cost is one unit and a missed positive day's cost is `r` units, with `r=2,5,10,20,50,100`. These are *scenario* costs, not measured governance or liquidation costs. Predictions remain frozen and block bootstrap intervals condition on fitted models.

For illustrative ratio 20 (cost per 1,000 forecasts):

| Cohort | Model | FP | FN | Cost / 1,000 |
|---|---|---:|---:|---:|
| Original | GRU | 676 | 6 | 778.9 |
| Original | Graph+Platt | 889 | 1 | 889.4 |
| Later | GRU | 109 | 11 | 442.2 |
| Later | Learned Gate | 106 | 11 | 438.2 |

For ratio 5, original GRU costs 444.2 per 1,000 versus graph 510.8; later GRU 236.6 versus learned gate 235.2.

Conditional 14-day date-block 2,000-resample intervals for cost-per-1,000 differences (first model minus GRU):
- Original Graph+Platt, ratio 20: **+110.6**, percentile interval **[+5.9,+201.6]**
- Original Graph+Platt, ratio 5: **+66.5**, interval **[-2.0,+135.1]**
- Later Learned Gate, ratio 20: **-4.0**, interval **[-9.4,0.0]**
- Later Learned Gate, ratio 5: **-1.3**, interval **[-4.0,0.0]**

The small later-Gate gains do **not** establish superiority. The original graph does not outperform GRU on this decision metric. The cost-ratio scenarios are illustrative, retrospective and hypothesis-selection-sensitive.

Run:
```bash
python revision/scripts/decision_utility.py --reps 2000
python -m unittest tests.test_decision_utility tests.test_chain_block_range -v
python revision/scripts/build_paper.py
```

The manuscript template and builder generate decision-utility tables from newly computed CSVs; stale static tables should not be pasted into manuscript files. These results do not justify causal contagion or financial benefit claims.

## Implemented but access-blocked

**Compound chain-event reconciliation:** the previous Work run's unauthenticated RPC requests returned HTTP 403. The new `revision/scripts/chain_block_range.py` resolves exact Ethereum block numbers for historical UTC windows using an authenticated archive RPC. It does not itself validate Compound events, and existing `revision/scripts/historical_validation.py` covers **one Compound III USDC deployment**, not all Compound V2/V3 liquidation mechanisms. Independently verify event completeness, source UTC alignment and USD valuation before calling transferred performance chain-validated. Five publisher-removed 2024 dates remain, including 2024-08-05.

**Aave historical Health Factor:** the existing validation script supports targeted historic account checks and aborts on unsupported layouts/eMode. The included ten 2023 accounts are **not** a representative whole-market panel; no empirical HF results were obtained without authenticated archive `eth_call`. Only an independently validated debt-weighted position panel would support the HF-augmented incremental graph experiment.

### Secure, reproducible next steps

Store authenticated provider URLs as Colab **Secrets**, not in source files or GitHub. The `ETH_ARCHIVE_RPC` endpoint must support historic state reads and `eth_getLogs`. An independent `ETH_VALIDATION_RPC` is preferred.

```bash
python revision/scripts/chain_block_range.py --start-utc 2024-08-01 --end-utc 2024-08-09 --out revision/results/chain_validation/august_2024_bounds.json
# Pass returned inclusive block bounds:
python revision/scripts/historical_validation.py compound --start-block START --stop-block STOP
python revision/scripts/historical_validation.py health --accounts revision/data/hf_spotcheck_requests.csv
```

**Neither command has successfully produced authenticated chain results in this research environment.** Do not confuse an implementation, a saved account list or a failed provider request with independent validation.

## Scientific status

- Primary Aave calibration and graph-negative evidence are preserved.
- Cross-protocol transfer remains conditional on a filtered publisher dataset.
- Historical on-chain HF reconstruction and independent Compound event validation remain prerequisites for stronger claims.
- Q1 admission is not established by document length, model count or journal ranking.
- Follow the selected publisher's required author, data-availability, conflict, funding and tool-use disclosures.
