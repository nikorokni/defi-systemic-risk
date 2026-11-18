# Reproduce the 17 November 2026 research revision

**Status:** Work revision source, figures, the 16-page revised PDF, printed results tables, frozen model checkpoints and the original-source provenance are preserved on this branch. Independent Compound on-chain reconciliation and market-wide historical Aave Health Factor validation **are not** complete.

## What is in the repository

- [Revised manuscript PDF](../paper/manuscript.pdf); [LaTeX](../paper/main.tex); [editable source](../paper/manuscript.md); [bibliography](../paper/references.bib)
- [Source-code and results archive](Work_Revision_Validated_Results_Code.zip): compact ZIP of research scripts, most audited output tables, test code and frozen specifications
- [LaTeX source bundle](Aave_LaTeX_Source.zip): complete paper sources and vector figures
- [Later Aave checkpoints and ledger](Work_holdout_checkpoints.zip): 744 later forecasts, 40 positives; includes weights and matching predictions
- [Aave→Compound checkpoints and ledger](Work_transfer_checkpoints.zip): frozen source and independently fitted target reference weights, probability scores and metadata
- [Persian research audit](CHANGELOG_FA.pdf), [evidence status](results/task_status.json), [integrity audit](results/integrity_audit.json)
- Six vector PDFs in [figures/](figures/) needed to rebuild the LaTeX article.

## Dependencies and data

Use Python 3.12 and the pinned version requirements in [requirements-lock.txt](requirements-lock.txt). Full historical source data were not republished on GitHub; `configs/sources.json` records the source URLs and pinned input hashes. Retrieve the original Aave/Chainlink/DeXposure data with:

```bash
python -m pip install -r revision/requirements-lock.txt
python -m pip install --no-deps -e .
python -m defi_risk fetch
python -m defi_risk prepare
python revision/scripts/fetch_work_inputs.py
```

The last step downloads the published Aave/Compound daily CSV and checks its original SHA256. If the publisher changes the file, stop and re-audit; do not change the expected hash to make the check pass. No secret archive-RPC credentials belong in GitHub.

The original Work archive also retains additional early-upload input and derivative tables. The compact GitHub package does not contain the large publisher source ledgers, graph extracts or every intermediate parquet; re-running the corresponding pipelines requires regenerating them, or providing the retained original Work archive. This is a real reproducibility limitation, not permission to claim the unexecuted parts were run.

## Analysis and manuscript

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -m defi_risk evaluate
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python revision/scripts/transfer_experiment.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python revision/scripts/later_holdout.py
python revision/scripts/make_figures.py
python revision/scripts/build_paper.py
```

**Important:** the revision-specific builder is `revision/scripts/build_paper.py`, not the older `paper/build_manuscript.py` from the primary benchmark. The revised builder reads the frozen revision ledgers and distinguishes the old and newly scored windows. Some complete refits require prepared data and records from the original Work package; do not represent them as newly executed merely because scripts are available.

The source compiles to a 16-page A4 PDF in an environment with Pandoc, XeLaTeX and Latin Modern fonts available to fontconfig. On a minimal TeX Live host where fontspec cannot discover Latin Modern although its OTF files exist, use a local fontconfig that includes `/usr/share/texmf/fonts/opentype/public/lm`, then rerun XeLaTeX twice. The existing `paper/manuscript.pdf` is the Work-validated compiled artifact.

## Limitations for journal submission

- Reported negative graph/fusion performance is preserved.
- Compound transfer results are conditional on a publisher-filtered sample with **five missing 2024 dates**, including 5 August.
- The `q95` Compound target uses historic Compound target data for scale/label definition; it is **not** target-domain information-free.
- The post-2025 Aave holdout uses historical source data and a graph aging to 378 days; it is not a prospective monitoring trial.
- Compound contract-log reconciliation returned HTTP 403 in the last Work run. This **does not** mean zero events.
- The historical Health Factor work includes defensive code and selected account requests, but **not** validated representative 2023–2025 HF predictions.
- Claims about causal cross-protocol contagion or superior performance beyond these cohorts are unsupported.
- The submitting authors must complete journal-required contribution, funding, competing-interest and tool-use declarations per the selected publisher's policy.

## Verification

A recovered Work session reported 14 software tests passing with its pinned environment. In the current recovery container the full test suite cannot be independently rerun because `pyarrow`, `ijson` and `eth-hash` are unavailable. The revised LaTeX itself was rebuilt and checked as 16-page A4 with the Latin Modern fontconfig workaround. Tests or independent chain validation are **not** falsely described as newly passed.

## 18 November 2026 extension: decision utility and historic block bounds

The executed analysis of cost-sensitive alerts is described in
[EXTENSION_STATUS_2026-11-18.md](EXTENSION_STATUS_2026-11-18.md).

```bash
python revision/scripts/decision_utility.py --reps 2000
python -m unittest tests.test_decision_utility tests.test_chain_block_range -v
python revision/scripts/build_paper.py
```

An authenticated archive RPC is still required to validate actual historic
Compound logs and selected Aave account Health Factors. The new
`revision/scripts/chain_block_range.py` can determine historic block bounds,
but neither contract-log validation nor representative borrower-health analysis
is completed simply by executing a script. Do not publish RPC credentials.
