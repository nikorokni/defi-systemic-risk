---
title: "Early Warning of Aave Liquidation Stress under Delayed and Incomplete Network Data"
subtitle: "Chronological forecasting, reliability-aware fusion and conditional cross-protocol transfer"
date: "Revised research manuscript - 17 November 2026"
lang: en-GB
fontsize: 10pt
papersize: a4
geometry: margin=23mm
mainfont: Latin Modern Roman
sansfont: Latin Modern Sans
monofont: Latin Modern Mono
colorlinks: true
linkcolor: teal
urlcolor: teal
reference-section-title: References
abstract: |
  Network measurements can inform liquidation monitoring only if they add predictive value to timely local information and remain useful when observations deteriorate. We evaluate daily tail-volume warnings for the Ethereum Aave V2 and V3 series using event-level liquidation records, timestamped reserve and oracle inputs, and weekly global protocol-exposure graphs. Three chronological test folds contain 1,022 forecasts and 110 positive outcomes. Recomputed average precision is 0.1954 for a calibrated temporal graph ensemble, 0.2479 for the matched market-augmented GRU and 0.3127 for prior-day liquidation. The graph-minus-GRU AP difference is -0.0525, with a paired 14-day block interval of [-0.1488, 0.0161]. Across 100 edge-removal masks per rate, ranking and probability accuracy respond differently. A previously unscored later Aave window contains 744 forecasts and 40 positives: a learned reliability gate obtains AP 0.3230 and Brier 0.04644, versus 0.3242 and 0.04626 for the GRU. Newly trained common-schema models are transferred with frozen source weights to published Compound histories. Ranking transfer is weak, but inference is conditional on an outlier-filtered daily dataset with five missing dates, including 5 August 2024. Independent contract reconciliation and a representative historical Health Factor baseline remain unresolved. The evidence documents conditional forecasting performance and failure modes, rather than a demonstrated network or fusion advantage.
keywords: [decentralised finance, liquidation stress, temporal graphs, calibration, transfer learning, data provenance]
---

# Introduction

Public blockchain records expose events that are difficult to observe in conventional credit markets. That visibility does not make tomorrow's aggregate liquidation volume straightforward to predict. Position eligibility depends on collateral, debt, prices and protocol rules; realised liquidation additionally depends on borrower adjustments, execution incentives and available liquidity. Empirical work documents liquidation incentives and execution frictions [@qin2021; @schuler2026]. An early-warning study must therefore define its outcome precisely. Here it is unusually large *realised, source-reported USD liquidation volume*, not the probability that an individual borrower becomes insolvent.

The potential contribution of network information is conditional. A token-mediated link might contain information beyond recent liquidations, reserve conditions and market prices. It might instead reflect common price movements, protocol scale or retrospective data construction. DeXposure supplies historical measurements of global inter-protocol exposure [@wu2025]. Matching them to Ethereum Aave outcomes permits a predictive comparison under an explicit lag assumption. It does not identify causal transmission or establish that a published historical graph was obtainable on each forecast date.

We ask whether a temporal graph improves ranking or probability loss over the same timed local/market inputs; whether disagreement-based fusion protects forecasts when network observations deteriorate; and whether common-schema Aave models transfer to Compound. The last question is conditional because the available Compound dataset has material provenance and calendar limitations. A fourth question is specified but remains untested: whether networks add information after a representative historical borrower Health Factor panel is included.

The contribution is an auditable benchmark and a set of negative or qualified findings. We distinguish score recomputation from model refitting, corruption draws from independent training repetitions, chronological novelty from independent source validation, and actual weight transfer from a separately fitted external benchmark. A later Aave holdout extends evaluation beyond the previously inspected calendar. Every reported result comes from a saved ledger; unfinished analyses are listed explicitly.

# Related research

## Liquidation mechanisms and realised distress

@qin2021 compare liquidation mechanisms and examine incentives and borrower losses. @lehar2022 study interactions between liquidation and decentralised trading. These mechanisms motivate monitoring aggregate pressure but require more evidence than a forecasting coefficient to establish contagion. @chiu2026 document leverage and concentrated liquidation waves in Aave V3. @schuler2026 distinguish undercollateralisation from subsequent execution in Aave V2. Our daily outcome aggregates such processes rather than estimating account-level transition probabilities.

The cross-version study of @iftikhar2025 uses daily Aave and Compound data for panel regression. Its repository supplies our external series. Regression and tail-warning studies have different data requirements: removing extreme observations may be a regression robustness choice, while removing a crisis day directly compromises a stress benchmark. We therefore inspect the full calendar and retain the fact of exclusion in every transfer interpretation. A named liquidation column is not treated as contract-level validation.

## Network learning and transfer

DeXposure reconstructs global token-mediated relationships and benchmarks clustering, exposure dynamics and link prediction [@wu2025]. DeXposure-FM extends this setting to flow and graph forecasting [@shu2026]. Their outcomes differ from realised next-day liquidation warnings. We use a weighted inductive neighbour encoder inspired by GraphSAGE [@hamilton2017] followed by a GRU [@cho2014]. The non-graph GRU is the central matched comparator. Predicting topology well does not guarantee incremental liquidation information conditional on local histories and prices.

Transfer is more demanding than evaluating models on two datasets. Source weights, feature transforms, stopping rules and calibration must remain fixed during target prediction. Feature meanings and target definitions must also be aligned. We train new shared-schema variants and distinguish them from the original reserve-augmented models. The experiment tests that common representation under documented assumptions; it does not establish portability of every original predictor or checkpoint.

## Calibration, disagreement and decisions

Average precision (AP) measures rare-event ranking, while Brier score and log loss measure probability quality [@saito2015; @gneiting2007]. These objectives can disagree. Calibration can improve probability loss without creating new information [@guo2017]. Deep ensembles measure variation across fitted members [@lakshminarayanan2017], but their spread is not a complete uncertainty measure. All members can share a misspecification or use the same obsolete graph. Distribution-shift evidence motivates evaluation beyond the original calendar [@ovadia2019].

Selective classification studies retained coverage and error [@geifman2017]. A monitoring interface must additionally count manual review and missed episode onsets. We distinguish a review queue, which defers a case, from a probability mixture, which changes its forecast. Neither is considered useful merely because it lowers a conditional error or marginally improves one ranking score.

# Data, provenance and timing

## Primary Aave cohort

The primary calendar is 1 March 2023-24 August 2025. Each forecast concerns one archive-labelled Ethereum Aave version at UTC midnight. The pinned Chaffard release supplies liquidation events, paired hourly aggregates, reserve histories and Chainlink oracle updates [@chaffard2026]. Reserve inputs cover DAI, USDC, USDT and WETH. Event IDs and transaction-hash/log-index pairs are unique. Event sums and counts reconcile to the publisher's hourly tables. This is internal consistency, not independent reconstruction of every contract log or USD valuation.

The graph is pinned to DeXposure commit `79071f26ddb3cf59adb433fb277bc820732bf863`, with 283 weekly snapshots through 18 August 2025. AAVE V2 is node 111 and AAVE V3 node 1599. Global protocol coverage is broader than Ethereum outcomes. Self-links, unmapped entities and nonpositive/nonfinite weights are excluded, repeated pairs are summed and up to 16 neighbours per direction are retained by weight. A snapshot is eligible only when it is at least seven days old.

| Input | Forecast-time restriction | Interpretation |
|:---|:---|:---|
| Liquidation history | Events strictly before midnight | Prior realised activity |
| Reserve state | Strictly prior observation; maximum age two days | Selected reserve conditions |
| Oracle updates | Strictly prior actual update; maximum age three hours | Returns, volatility, freshness |
| Exposure graph | Snapshot dated at least seven days earlier | Lagged global context |
| Future events | Following 24 hours | Outcome only |

These are retrospective releases. Source-event timestamp eligibility and historical public availability are distinct. The seven-day graph lag is an operational assumption, not a verified publication-time history. Historically deployable performance would require revision-aware acquisition logs. Mutable DefiLlama borrowing histories enter only the original borrowing-scaled sensitivity, with their downloaded hashes recorded separately.

## Run identity and reproduction

The supplied main ledger and the existing GitHub ledger have identical keys and labels, but 18,011 of 48,034 probabilities differ by more than $10^{-8}$. We use the supplied ledger consistently for the primary results because its fusion and 100-mask extensions refer to that run; columns from different runs are not mixed. All 47 model/scenario metric rows recompute within $8.4\times10^{-17}$ of the supplied tables. This verifies score arithmetic and pairing, not unseen training-data provenance.

A complete primary-model refit was executed from hash-matched raw archives. Its temporal-graph AP rounds to 0.1949, versus 0.1954 in the supplied ledger. The GRU, persistence and LightGBM headline scores agree at reported precision. A neural stopping epoch differs in fold C, and software environments differ. The subsequently available full aave.zip upload contains all six original raw-file hashes. Its processed graph values agree exactly with the reconstruction; panel differences are at floating-point round-off scale. Both ledgers remain available; byte-identical parquet or neural output is not asserted across Python and numerical-library versions. These small headline differences leave the interpretation unchanged.

## Compound source audit

The external CSV contains 1,456 rows from 1 January 2021 to 31 December 2024. Its date column is `Date`; the earlier feasibility manifest incorrectly recorded a missing date field. The absent dates are 5 July, 1 August, 5 August, 25 November and 20 December 2024. The source paper states that five outlier observations were removed [@iftikhar2025]. We reindex the full calendar, preserve missing values and exclude forecasts with an incomplete 14-step feature sequence. Because each step includes a seven-day aggregate, validity can require 20 prior raw days. This leaves 196 scored days per Compound version in April-December 2024.

Excluding the missing 5 August neighbourhood does not repair an unfiltered crisis benchmark: it defines a sample omitting an important stress episode. On 667 overlapping dates per Aave version, the external Aave values and the pinned archive agree within USD 1. This establishes numerical compatibility but does not prove independent ingestion or validate Compound. Daily UTC alignment, exact deployment coverage and contract-specific USD semantics remain assumptions for transfer.

## A previously unscored later window

A separate specification was recorded before scoring 25 August 2025-31 August 2026. The window contains 744 forecasts. Preparation of a longer window first failed on four negative ETH/USD source observations on 15, 21 and 22 September 2026. Before generating later-window scores, we capped evaluation at the last preceding complete calendar month. September-November 2026 are quarantined. The amendment and final specification hash accompany the results.

This uses the same Aave source: it is a new chronological test, not an independent dataset or prospective deployment. No graph snapshots are invented after the pinned release ends. Snapshot age grows from 7 to 378 days, deliberately creating a stale-feed regime. Performance here cannot establish results with continuously refreshed networks.

# Methods

## Outcome and chronological separation

Let $V_{i,t}^{24}$ be source-reported liquidation USD for version $i$ in $[t,t+24\mathrm{h})$. The fold-specific target is
$$y_{i,t}^{(f)}=\mathbb{1}\{V_{i,t}^{24}>q_{i,f}\},\qquad q_{i,f}=Q_{0.95}\{V_{i,s}^{24}:s\in\mathcal T_f\}.$$
Thresholds use training outcomes only and differ by version. Tail activity is relative to historical scale, not a universal insolvency boundary. Thresholds and prevalence can change between folds.

Features include prior one-, three- and seven-day liquidation sums/counts, borrowing and utilisation in four reserves, and a version indicator. ETH/BTC channels contain one-/seven-day returns, daily realised volatility, minimum hourly return and observation age. A tuning interval selects neural stopping epochs; a subsequent calibration block fits probability maps and warning cutoffs. Training, tuning and calibration label windows end at least one day before the next partition. Test outcome windows remain within their fold. Fourteen-day input histories may precede a partition boundary because those observations are already known; future outcomes never enter inputs.

{{FOLDS}}

## Models and fitting

Benchmarks include a smoothed training prior, a logistic persistence predictor using prior-day liquidation, local/market logistic models and shallow LightGBM with and without graph summaries [@ke2017]. The neural comparison uses the same 14-day history and a 24-unit GRU. Five seeds (19, 43, 71, 101, 137) form each ensemble. Training uses unweighted binary cross-entropy, AdamW at learning rate 0.001/weight decay 0.001, batch size 64, gradient norm cap 2, at most 36 epochs and tuning-loss patience seven.

The graph encoder transforms neighbour log size, log weight and an availability flag through direction-specific multilayer maps. Normalised exposure weights form incoming/outgoing means. These are joined with local/market inputs and graph statistics: own size, age, total exposure, retained degree, concentration and mean peer size. A linear layer, layer normalisation and ReLU precede the GRU. Training-only scaling clips standardised inputs to $[-12,12]$ and represents missing values with zeros plus indicators. This tests a particular feature/model combination rather than all graph architectures.

Static topology, one-step graph input, removal of market channels and augmented training diagnose specific components. One-step models retain engineered historical features and therefore are not information-free about the past. No positive directed edge connects the two labelled Aave version nodes in this extraction. The weighted cross-version interaction consequently has no identifying variation and cannot support a causal spillover estimate.

## Calibration, corruption and review

The raw ensemble probability is the mean of five members; disagreement is their variance. A positive-slope ridge Platt map is fitted on calibration data and frozen. Probabilities are clipped to $[10^{-6},1-10^{-6}]$ for log loss. An isotonic sensitivity remains in the original ledgers.

Edge thinning removes retained links with probabilities 0.10, 0.30 or 0.50. Each mask is fixed within snapshot, version, direction and neighbour slot. One fitted ensemble per fold is evaluated under 100 masks per rate; rates share nested draws. Empirical mask percentiles describe corruption variability conditional on fixed weights, not population confidence intervals or 100 training repetitions. Other original scenarios add one oracle day, seven graph days, or both with 30% thinning. Outcomes are held fixed; these are observation disruptions, not market shocks.

An alert fires above the calibration-probability 90th percentile. A separate review queue first defers cases above the calibration-disagreement 90th percentile. Deferral does not count as automated warning or successful analyst detection. Onsets are first positive days after a nonpositive day or fold boundary. Lead time is measured to cumulative target-volume threshold crossing, not necessarily to the first liquidation.

## Reliability-aware fusion

For calibrated graph/local forecasts $p_G,p_L$ and graph disagreement percentile $r$, the fixed mixture uses $w=1/2$ and the heuristic uses $w=(1-r)/2$:
$$p_F=w p_G+(1-w)p_L.$$
The learned gate is
$$w_\theta=\operatorname{sigmoid}(\theta_0+\theta_1r+\theta_2|p_G-p_L|+\theta_3p_G).$$
It minimises summed binary cross-entropy plus $\lambda\|\theta-\theta^{\mathrm{prior}}\|_2^2/2$, with prior $(-1.5,-1,0,0)$. Original A predictions fit candidates and B selects $\lambda\in\{0.1,1,10,100\}$ by log loss; the selected value is 0.1. For exploratory C evaluation, the gate is refitted on A/B. For the later window, it is refitted on earlier A/B/C out-of-sample predictions. C was already inspected when fusion was proposed, so C is not a fresh discovery test.

The later base experts train through 29 April 2025, tune on 1 May-26 June and calibrate on 28 June-23 August. Later outcomes do not fit experts, calibration, gate parameters or expiry rules. A specified freshness comparator sets heuristic graph weight to zero when graph age exceeds 28 days. This probes conservative fallback rather than learning an optimal expiry. The later specification is retrospective and not externally preregistered.

## Executed source-weight transfer

Transfer variants replace reserve-specific channels with three shared lagged-volume features,
$$x_{i,t}^{(k)}=\log\left(1+\frac{\sum_{j=1}^{k}V_{i,t-j}}{q_{i,\mathrm{train}}}\right),\quad k\in\{1,3,7\},$$
plus the same timed ETH/BTC inputs. The identity channel is constant zero. Graph variants use the same neighbour encoder, with Compound nodes 114/2088. Aave alone fits source scaling, neural weights, stopping rules and Platt calibration. Training covers 1 March-30 December 2023, tuning 1 January-13 February 2024, calibration 15 February-30 March and testing April-December 2024.

Compound's 2023 q95 defines its target and unit normalisation. This use of target history is explicit: the experiment is source-weight transfer with target historical scaling, not zero information about the target. No Compound label fits the transferred weights or calibration. Separately trained Compound models provide supervised references under the same chronology. They are distinct estimators, not fine-tuned source models selected on target test scores. Paired comparisons use the same valid target dates. The original reserve-augmented checkpoints are not claimed to have been transferred.

## Scores and uncertainty

We compute AP, Brier, log loss and AUROC from paired ledgers. A moving-block bootstrap samples contiguous dates within each fold, carrying both Aave versions and both models together [@kunsch1989]. Main contrasts retain 2,000 valid 14-day draws; original graph/GRU comparisons also use seven-/28-day blocks. Percentile intervals condition on fitted forecasts and observed regimes, omit refitting uncertainty and are pointwise rather than simultaneous across all contrasts. Further ablations and transfer contrasts are exploratory. Failure to show a gain is not proof of equivalence.

# Results

## Original cohort and incremental graph information

The three original tests contain 1,022 cases and 110 positives. Persistence has the strongest pooled AP among the listed original predictors; the GRU has lower Brier loss than persistence. The temporal graph does not establish incremental value over the GRU or graph-summary tree comparison.

{{PRIMARY_RESULTS}}

{{PRIMARY_INTERVALS}}

Graph/GRU AP and Brier intervals include zero, while graph log loss is worse in the conditional comparison. This pointwise result is not a universal statement about financial networks. The graph ranks ahead in A/B; the GRU leads in the largest fold C. Pooled AP reflects both within-fold ordering and cross-fold probability alignment.

{{FOLD_SCORES}}

![Recomputed clean primary scores from one supplied forecast ledger. Both horizontal scales begin at zero.](../revision/figures/primary_performance.pdf){width=100%}

Static and one-step graph variants rank ahead of the full temporal graph in the pooled sample. Adding graph summaries to LightGBM lowers its AP point estimate. These observations constrain claims about the selected representation but do not distinguish uninformative links from redundant inputs, small sample size, weak peer attributes or scope mismatch. They do not answer the comparison with borrower Health Factor, which remains unavailable.

## Calibration, masks and analyst workload

The supplied raw and calibrated graph forecasts yield the following clean-score comparison.

{{CALIBRATION}}

![Equal-width reliability bins from the same clean ledger. Marker area reflects occupancy; sparse upper bins remain uncertain.](../revision/figures/calibration_recomputed.pdf){width=78%}

Mean AP changes under thinning are slightly positive at each rate, but some masks worsen ranking. Probability error moves in the opposite direction: 99 of 100 masks at 50% thinning worsen Brier loss. A favourable deterministic mask would therefore give an incomplete account of robustness.

{{MASK_RESULTS}}

![Mask variation conditional on fitted ensembles. Whiskers span empirical 2.5th-97.5th percentiles, not confidence intervals for future markets.](../revision/figures/mask_sensitivity.pdf){width=100%}

Original delayed-input scenarios and alternative horizons remain in the replication tables. They are covariate interventions on observed outcomes. Review additionally trades fewer automated false warnings against fewer automated onset detections and a large manual queue. Without an analyst experiment, reviewed cases cannot be counted as recovered events.

{{ALERTS}}

## Fusion on C and a later chronological test

The existing gate and nested selection have little ranking separation from the GRU on C. As fusion was developed after seeing the original benchmark, these C results support exploratory estimation only.

{{GATE_C}}

The later test has 744 cases/40 positives (5.38%). Its training q95 thresholds are USD 691,427 for V2 and USD 2,716,455 for V3. These differ from original C, so prevalence changes are not statements about an unchanged physical stress boundary.

{{LATER_RESULTS}}

{{LATER_INTERVALS}}

The later learned gate has AP 0.3230 versus GRU 0.3242, with a positive Brier difference. A 50/50 mixture improves the AP point estimate but worsens Brier/log loss; its AP interval spans zero. Marginal ranking movement does not establish better probability quality. The freshness-capped heuristic is almost identical to the GRU because it ignores the graph for most of this stale-feed regime. Near-equality is evidence of fallback behaviour, not a new source of predictive information.

![Later forecasts and measured graph age. Weekly means aid display only; scores use unsmoothed daily version-level predictions.](../revision/figures/later_holdout_history.pdf){width=100%}

![Later paired differences from GRU, using 2,000 14-day moving-block draws with both versions clustered by date.](../revision/figures/later_holdout_differences.pdf){width=100%}

The experiment tests a frozen gate with renewed expert fits and a changing age distribution. It cannot isolate age causally from evolving market regimes. It nevertheless directly challenges the idea that disagreement alone makes fusion robust to obsolete network observations. Source freshness is independently observable and should accompany a learned uncertainty measure.

## Conditional Compound transfer

Frozen-source predictions were actually generated. Both Compound versions have 196 valid test days, with 12 V2/19 V3 positives. Ranking transfer is weak, especially for the graph. On V3 both source models rank below target-supervised references, while probability-loss differences are smaller. On V2 a source model can have lower Brier error despite weaker ranking, illustrating separate effects of base-rate alignment and ordering.

{{TRANSFER_RESULTS}}

![Executed transfer scores. Dashed lines give target test prevalence as an uninformative-ranking reference. Missing crisis neighbourhoods are excluded.](../revision/figures/transfer_performance.pdf){width=100%}

On V3, source-minus-target AP differences are -0.0873 for GRU and -0.1051 for graph, with conditional intervals [-0.1758, -0.0239] and [-0.1929, -0.0316]. These exploratory results show that transfer was executed and failed to match supervised ranking in the filtered cohort. They do not establish chain-validated external performance, a crisis-inclusive benchmark or coverage of every Compound deployment.

# Historical account health and independent validation

## Health Factor remains a missing benchmark

For a basic position, the conceptual Health Factor is
$$\mathrm{HF}_{u,t}=\frac{\sum_a C_{u,a,t}P_{a,t}\mathrm{LT}_{a,t}}{\sum_a D_{u,a,t}P_{a,t}}.$$
Contract values additionally depend on units, integer rounding, eligibility and historical implementation rules. Official Aave interfaces expose account data, and its logic includes version/eMode behaviour [@aavepool; @aavelogic]. Reserve utilisation and governance thresholds are not account HF. Liquidated-account samples are not representative borrower cross-sections.

The supplied Cred sample has 75 observations from January 2021-June 2022 and zero overlap with the primary interval [@credhf]. Its aggregate collateral/debt arithmetic reproduces supplied HF values, which is an algebraic identity within one dataset, not chain-state validation or a contemporary risk panel.

Delivered reconstruction code reads token balances, prices, collateral flags and configuration at an exact block, applies supported basic legacy integer rules and compares against `getUserAccountData`. Debt-free HF is undefined; unsupported eMode/ABI cases fail explicitly. Ten training-era account/block requests are included for mechanics checks. No real historical HF output was generated because archive calls were denied. Software tests are not represented as empirical validation.

## The required incremental-information comparison

A suitable panel must enumerate borrowers as known at each origin, not select future liquidation recipients. At a block strictly before midnight it should measure debt-weighted HF shares, buffer distributions and coverage. For example,
$$S_t(\tau)=\frac{\sum_u D_{u,t}\mathbb{1}\{\mathrm{HF}_{u,t}<\tau\}}{\sum_u D_{u,t}}$$
requires a documented borrower denominator. The next comparison must hold cohort, target, dates and calibration fixed across local/market, local/market/HF and local/market/HF/graph models. This ablation has not run. Current findings concern network value relative to the available local inputs, not the best obtainable loan-health information.

## Compound semantics and access

Compound V2 emits `LiquidateBorrow`; Compound III uses absorption and later collateral-sale mechanics [@compoundv2; @compoundv3]. Its `AbsorbDebt` event contains `basePaidOut` and `usdValue` [@cometcode]. We retain the emitted valuation without automatically renaming it borrower principal or seized collateral. Reconciliation must specify which quantity a published daily column measures, deployment coverage and UTC boundaries. V2 repayment and seized collateral also need separate historical valuation paths.

Network identity and a historical block header were obtainable. Historical state/log requests returned HTTP 403 on the tested routes, and no authenticated archive endpoint was configured. Access reports distinguish failure from an empty history. The supplied read-only collector checks continuous block coverage, event uniqueness, removed-log flags and block hashes and can compare a second endpoint. It covers a specified Ethereum Compound III USDC deployment, not complete V2/V3 reconciliation, and has no claimed executed validation result.

# Discussion

## Interpreting the negative evidence

The original and later tests constrain a practical claim: this network representation and disagreement gate do not establish a stable advantage over timely local/market forecasting. The evidence includes exact score recomputation, a full primary refit, multiple corruption masks and a previously unscored calendar. It is weaker than a universal assertion that financial networks are uninformative. Only two source-labelled Aave series, one graph construction and a small family of encoders are tested.

Local liquidation history may already encode pressure associated with exposure links. Weekly global measurements may be too coarse for next-day account events. Peer attributes describe scale/exposure rather than independently labelled distress. Additional complexity competes with few independent stress episodes. Global graph coverage and Ethereum outcomes are imperfectly aligned. The present design cannot identify the relative contribution of these explanations, and absent HF controls prevent a stronger conditional-information claim.

Thinning separates sensitivity from economic information. Removing links can attenuate unhelpful messages and improve some ranks while worsening probability magnitude. This does not mean data loss is intrinsically protective. It argues for reporting distributions across specified masks and calibration diagnostics under the same frozen forecast rule.

## Reliability needs source metadata

Ensemble disagreement is not a certificate of input validity. Members can agree on stale or mismeasured data. The later window deliberately exposes this problem. Its expiry comparator mostly reproduces local forecasts: a conservative behaviour, not a demonstrated network gain. Monitoring should display age, coverage and supported-regime flags alongside probabilities. Governance policies also need intervention costs and financial consequences, which forecast scores alone cannot establish.

The companion local-currency adaptive-governance repository concerns policy responses to delayed observations. It is a separate modelling project, not independent empirical evidence for these forecasts. Neither predictive differences nor directed aggregate exposures alone justify an assertion of causal contagion or a welfare-improving parameter intervention.

## Selection and measurement

Transfer is a real procedure with saved weights, but deleting a crisis day is particularly damaging to a tail estimand. The 196-day cohort is explicit about eligibility yet remains selected by publisher filtering. It must not be advertised as a fully validated cross-protocol warning system. Matching published Aave series can establish compatibility while leaving common upstream dependencies unresolved. Independent verification requires event identities and a declared valuation map, not high correlation alone.

HF reconstruction has an analogous boundary: an equation is insufficient when balances accrue interest, collateral eligibility changes and protocol implementations evolve. Unsupported components must remain missing rather than become reassuring zeros. Selected-account checks can validate mechanics but cannot supply a representative risk distribution without an enumerated borrower universe.

## Statistical and submission limits

Effective information is closer to independent stress episodes than total version-days. Moving blocks preserve local clustering but cannot guarantee coverage under future regimes. The later window has only 40 positives and an increasingly obsolete graph. AP depends on prevalence; thresholds differ across cohorts. All source-quality decisions and model fits are retained, but no independent preregistration is claimed.

Independent Compound reconciliation and a representative validated HF comparison remain material evidence gaps. A claim of network value beyond loan health cannot be made without the latter. This is a revised research manuscript for scientific review, with completed and blocked tasks separated below. Journal quartile and acceptance are not inferred from architecture complexity or document formatting.

# Conclusion

The selected temporal graph and reliability gate do not demonstrate stable improvement over local/market alternatives across the original Aave study and a later chronological window. Prior liquidation is a strong ranking comparator; calibration affects probability error; missing-link ranking changes can diverge from probability quality. Executed source-weight transfer is weak and conditional on important calendar/measurement assumptions. The package preserves negative results, distinct runs and unfinished validation. Additional network value relative to historical borrower health remains an empirical question.

# Reproducibility and evidence status

{{EVIDENCE_STATUS}}

The package contains forecast ledgers, original sensitivity outputs, source hashes, transfer/later-window weights, scaling/calibration metadata, specifications, code and tests. Large upstream archives are downloaded from cited sources; small derived panels/graphs accompany the review package. Credentials are read from environment variables and excluded from the repository. Original and refitted primary ledgers stay separate. Tables are generated directly from score files.

The authors must confirm final authorship, affiliations, funding/competing-interest statements and the selected journal's disclosure requirements before submission. No external journal submission is performed by this revision.

\newpage

# References
