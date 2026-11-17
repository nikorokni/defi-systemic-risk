# External protocol and health-factor validation protocol

**Status: DATASET IDENTIFIED; NOT INGESTED; NO RESULTS CLAIMED.** This document specifies independently reproducible eligibility tests for expanding the Aave V2/V3 Ethereum benchmark. It deliberately does not imply that the additional data have already been analysed.

## Candidate data sources (verify licences and actual downloadable coverage first)

1. Fan and Sun, *A Cross-Chain Event-Driven Data Infrastructure for Aave Protocol Analytics and Applications*, arXiv:2512.11363 (six Aave V3 chains, through October 2025). Candidate for deployment-level transfer testing, **not independent lending-protocol families**.
2. Compound protocol event logs, indexed from Ethereum contract addresses and liquidation event signatures. Candidate *independent protocol family*. Verify deployment start/end and independently reconstructed USD value before use.
3. Cred Protocol, *Aave V2 Health Factor Dataset*, github.com/credprotocol/Aave-V2-Health-Factor-Dataset — candidate third-party historical HF cross-check; scope may not match the existing origin calendar.
4. Aave official contract state and oracle observations, plus historical index/parameter changes — necessary for authoritative HF reconstruction. No user HF is directly emitted on chain as a canonical historical time-series.

## Minimum accepted independent protocol schema

Create a separate verified record with:
`chain_id, protocol, deployment_address, tx_hash, log_index, block_number, block_timestamp_utc, liquidated_debt_token, liquidated_debt_amount, debt_price_usd_asof, liquidated_debt_usd, source_snapshot, source_hash`.

Do not silently equate collateral seized USD with debt repaid USD. Handle duplicates using (chain_id, tx_hash, log_index) and check token decimals. Record source coverage by deployment **before** applying the model. Obtain an independent historical prices source, using actual observation timestamps (no later revisions).

## Predeclared transfer benchmark

- Training: Aave V2/V3 Ethereum, with existing chronological folds.
- External test: Compound on Ethereum, **only after** identical label definition and feature availability are established.
- Additional test: Aave V3 on another chain (deployment transfer, not cross-protocol independence).
- Report source-specific missingness, deployment dates, on-chain reconciliation and calendar overlap.
- If no common predictors are available at historical forecast origins, declare the transfer test infeasible instead of imputing future information.

## Position-level health-factor (HF) validation

Aave HF is conceptually (sum over collateral assets of collateral value times *the asset-specific applicable liquidation threshold*) divided by debt value. For each UTC decision origin:

1. Select an Ethereum block timestamped **strictly earlier** than the origin.
2. Reconstruct account debt and eligible collateral balances at that block, including interest indexes and scaled balances.
3. Apply the liquidation threshold, collateral activation/collateral usage flags, E-mode and isolation rules applicable at that historical block.
4. Reconstruct historical oracle prices with their decimals and oracle configuration effective at the block.
5. Compute finite HF for accounts with positive debt; treat debt-free accounts as non-at-risk rather than assigning a finite HF.
6. Verify the reconstruction against historical contract calls at matched block numbers and, where possible, an independent data provider. Report absolute/relative errors separately for V2 and V3.
7. Aggregate only positions reconstructed at origin time into counts/borrow-weighted exposure at HF <1, [1,1.05), [1.05,1.1), and >=1.1. Never use later liquidation eligibility to fill past HF.
8. Create a new secondary target for undercollateralisation or impaired liquidation execution; do not rename *realised liquidation volume* as a complete measure of financial stress.

**Current limitation:** the project’s uploaded/public replication artifacts include event, reserve and oracle aggregates, but no verified complete historical per-account HF panel. No HF-based performance claim is currently valid.

## Risk controls

Avoid mapping global weekly DeXposure version nodes to Ethereum-specific exposures without an explicit coverage diagnostic. Weekly graph information cannot prove directed causal contagion; separate common collateral price shocks from network exposure mechanisms. Out-of-time and out-of-protocol tests should remain untouched until feature engineering and thresholds are frozen.
