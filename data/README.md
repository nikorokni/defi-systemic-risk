# Data provenance

The full input manifests and their SHA-256 fingerprints are in [configs/sources.json](../configs/sources.json). The data audit records the downloaded digests and extraction counts. It was generated after a complete parse of the frozen snapshots and a cross-check of event-derived and publisher hourly aggregates. [Data audit](../results/data_audit.json)

| Input | Exact archive or extraction | Use |
|:---|:---|:---|
| Chaffard, Aave and Chainlink | Zenodo 10.5281/zenodo.24245638, v192 (2026-11-15), CC BY 4.0 | Outcomes, reserve covariates and oracle update times |
| Wu et al., DeXposure | Git commit 79071f26ddb3cf59adb433fb277bc820732bf863, weekly LFS object aa330bbb8fbf99719fc85d49625d7df7bd68f2b042f5806ded080cec99bad3f8, and matching ID map | Global, token-mediated version-level exposure covariates |
| DefiLlama | The aave-v2 and aave-v3 historical protocol API extracts, downloaded 2026-11-16 | Daily Ethereum-borrowed field in a secondary label |

The event table is joined by publisher chain (Ethereum) and version (V2 or V3). Graph IDs 111 and 1599 represent global versions. There is no one-to-one contract or reserve mapping to global graph nodes. The DefiLlama adapters cover multiple Ethereum pool contracts, including the V2 AMM path. Their chain-wide numbers serve as an approximate scaling quantity. [DeXposure release](https://github.com/dthinkr/DeXposure/tree/79071f26ddb3cf59adb433fb277bc820732bf863) · [DefiLlama API](https://github.com/DefiLlama/api-docs/blob/main/llms-free.txt) · [DefiLlama TVL definitions](https://docs.llama.fi/list-your-project/what-to-include-as-tvl)

As-of market and reserve queries require actual source timestamps strictly earlier than the query. Graph dates are offset by a conservative seven-day assumption. Historical providers may reconstruct or revise information, so a timestamped replay of the dataset is distinct from a replay of live data ingestion. Source event volumes and source event counts agree with the corresponding hourly aggregates at every hour checked. Those sources share an indexer and can share omissions. [Zenodo source](https://doi.org/10.5281/zenodo.24245638)

The immutable archives and mapping are required to match the hashes. The unversioned protocol API can change, including revisions to older observations. The reference API digests identify the specific full responses used here. The benchmark's primary results, six-hour results and seven-day results use no API values for model inputs or labels. The shipped borrowing-ratio forecast ledger preserves the original sensitivity scores and labels so the published scoring run can be verified if the API revisions alter a new fit.

Raw upstream records stay in the local data directory. The reported prediction CSVs include only dates, version tags, aggregate realised USD amounts, fitted scores and derived decisions. The datasets keep their upstream terms and attribution.
