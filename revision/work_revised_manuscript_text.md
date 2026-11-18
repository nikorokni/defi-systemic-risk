# Work-revised manuscript — text extraction (not LaTeX source)

This file preserves extracted full text from the 16-page research revision PDF (2026-11-17). For publication typesetting, use the original manuscript/LaTeX in the independent research archive. Extraction may change mathematical glyphs or linebreaks. No unfinished historical HF or on-chain Compound validation is claimed.

---

<PARSED TEXT FOR PAGE: 1 / 16>
    Early Warning of Aave Liquidation Stress under Delayed and
                     Incomplete Network Data
 Chronological forecasting, reliability-aware fusion and conditional cross-protocol transfer




                         Revised research manuscript - 17 November 2026

                                                   Abstract
         Network measurements can inform liquidation monitoring only if they add predictive value to timely
     local information and remain useful when observations deteriorate. We evaluate daily tail-volume
     warnings for the Ethereum Aave V2 and V3 series using event-level liquidation records, timestamped
     reserve and oracle inputs, and weekly global protocol-exposure graphs. Three chronological test folds
     contain 1,022 forecasts and 110 positive outcomes. Recomputed average precision is 0.1954 for a
     calibrated temporal graph ensemble, 0.2479 for the matched market-augmented GRU and 0.3127 for
     prior-day liquidation. The graph-minus-GRU AP difference is -0.0525, with a paired 14-day block
     interval of [-0.1488, 0.0161]. Across 100 edge-removal masks per rate, ranking and probability accuracy
     respond differently. A previously unscored later Aave window contains 744 forecasts and 40 positives:
     a learned reliability gate obtains AP 0.3230 and Brier 0.04644, versus 0.3242 and 0.04626 for the
     GRU. Newly trained common-schema models are transferred with frozen source weights to published
     Compound histories. Ranking transfer is weak, but inference is conditional on an outlier-filtered daily
     dataset with five missing dates, including 5 August 2024. Independent contract reconciliation and a
     representative historical Health Factor baseline remain unresolved. The evidence documents conditional
     forecasting performance and failure modes, rather than a demonstrated network or fusion advantage.


1 Introduction
Public blockchain records expose events that are diﬀicult to observe in conventional credit markets. That
visibility does not make tomorrow’s aggregate liquidation volume straightforward to predict. Position
eligibility depends on collateral, debt, prices and protocol rules; realised liquidation additionally depends on
borrower adjustments, execution incentives and available liquidity. Empirical work documents liquidation
incentives and execution frictions (Qin et al. 2021; Schuler 2026). An early-warning study must therefore
define its outcome precisely. Here it is unusually large realised, source-reported USD liquidation volume, not
the probability that an individual borrower becomes insolvent.
The potential contribution of network information is conditional. A token-mediated link might contain
information beyond recent liquidations, reserve conditions and market prices. It might instead reflect
common price movements, protocol scale or retrospective data construction. DeXposure supplies historical
measurements of global inter-protocol exposure (Wu et al. 2025). Matching them to Ethereum Aave
outcomes permits a predictive comparison under an explicit lag assumption. It does not identify causal
transmission or establish that a published historical graph was obtainable on each forecast date.
We ask whether a temporal graph improves ranking or probability loss over the same timed local/market
inputs; whether disagreement-based fusion protects forecasts when network observations deteriorate; and
whether common-schema Aave models transfer to Compound. The last question is conditional because
the available Compound dataset has material provenance and calendar limitations. A fourth question is
specified but remains untested: whether networks add information after a representative historical borrower
Health Factor panel is included.
The contribution is an auditable benchmark and a set of negative or qualified findings. We distinguish score


                                                       1
<PARSED TEXT FOR PAGE: 2 / 16>
Aave Liquidation Stress                                                                        Research revision



recomputation from model refitting, corruption draws from independent training repetitions, chronological
novelty from independent source validation, and actual weight transfer from a separately fitted external
benchmark. A later Aave holdout extends evaluation beyond the previously inspected calendar. Every
reported result comes from a saved ledger; unfinished analyses are listed explicitly.


2 Related research
2.1 Liquidation mechanisms and realised distress
Qin et al. (2021) compare liquidation mechanisms and examine incentives and borrower losses. Lehar
and Parlour (2022) study interactions between liquidation and decentralised trading. These mechanisms
motivate monitoring aggregate pressure but require more evidence than a forecasting coeﬀicient to establish
contagion. Chiu and Danisman (2026) document leverage and concentrated liquidation waves in Aave V3.
Schuler (2026) distinguish undercollateralisation from subsequent execution in Aave V2. Our daily outcome
aggregates such processes rather than estimating account-level transition probabilities.
The cross-version study of Iftikhar, Wei, and Cartlidge (2025) uses daily Aave and Compound data for panel
regression. Its repository supplies our external series. Regression and tail-warning studies have different
data requirements: removing extreme observations may be a regression robustness choice, while removing
a crisis day directly compromises a stress benchmark. We therefore inspect the full calendar and retain the
fact of exclusion in every transfer interpretation. A named liquidation column is not treated as contract-level
validation.

2.2 Network learning and transfer
DeXposure reconstructs global token-mediated relationships and benchmarks clustering, exposure dynamics
and link prediction (Wu et al. 2025). DeXposure-FM extends this setting to flow and graph forecasting
(Shu et al. 2026). Their outcomes differ from realised next-day liquidation warnings. We use a weighted
inductive neighbour encoder inspired by GraphSAGE (Hamilton, Ying, and Leskovec 2017) followed by a
GRU (Cho et al. 2014). The non-graph GRU is the central matched comparator. Predicting topology well
does not guarantee incremental liquidation information conditional on local histories and prices.
Transfer is more demanding than evaluating models on two datasets. Source weights, feature transforms,
stopping rules and calibration must remain fixed during target prediction. Feature meanings and target
definitions must also be aligned. We train new shared-schema variants and distinguish them from the
original reserve-augmented models. The experiment tests that common representation under documented
assumptions; it does not establish portability of every original predictor or checkpoint.

2.3 Calibration, disagreement and decisions
Average precision (AP) measures rare-event ranking, while Brier score and log loss measure probability
quality (Saito and Rehmsmeier 2015; Gneiting and Raftery 2007). These objectives can disagree. Calibration
can improve probability loss without creating new information (Guo et al. 2017). Deep ensembles measure
variation across fitted members (Lakshminarayanan, Pritzel, and Blundell 2017), but their spread is not a
complete uncertainty measure. All members can share a misspecification or use the same obsolete graph.
Distribution-shift evidence motivates evaluation beyond the original calendar (Ovadia et al. 2019).
Selective classification studies retained coverage and error (Geifman and El-Yaniv 2017). A monitoring
interface must additionally count manual review and missed episode onsets. We distinguish a review queue,
which defers a case, from a probability mixture, which changes its forecast. Neither is considered useful
merely because it lowers a conditional error or marginally improves one ranking score.


3 Data, provenance and timing



                                                                                                              2
<PARSED TEXT FOR PAGE: 3 / 16>
Aave Liquidation Stress                                                                          Research revision



3.1 Primary Aave cohort
The primary calendar is 1 March 2023-24 August 2025. Each forecast concerns one archive-labelled Ethereum
Aave version at UTC midnight. The pinned Chaffard release supplies liquidation events, paired hourly
aggregates, reserve histories and Chainlink oracle updates (Chaffard 2026). Reserve inputs cover DAI,
USDC, USDT and WETH. Event IDs and transaction-hash/log-index pairs are unique. Event sums and
counts reconcile to the publisher’s hourly tables. This is internal consistency, not independent reconstruction
of every contract log or USD valuation.
The graph is pinned to DeXposure commit 79071f26ddb3cf59adb433fb277bc820732bf863, with 283 weekly
snapshots through 18 August 2025. AAVE V2 is node 111 and AAVE V3 node 1599. Global protocol
coverage is broader than Ethereum outcomes. Self-links, unmapped entities and nonpositive/nonfinite
weights are excluded, repeated pairs are summed and up to 16 neighbours per direction are retained by
weight. A snapshot is eligible only when it is at least seven days old.

Input                                 Forecast-time restriction              Interpretation
Liquidation history                   Events strictly before midnight        Prior realised activity
Reserve state                         Strictly prior observation;            Selected reserve conditions
                                      maximum age two days
Oracle updates                        Strictly prior actual update;          Returns, volatility, freshness
                                      maximum age three hours
Exposure graph                        Snapshot dated at least seven          Lagged global context
                                      days earlier
Future events                         Following 24 hours                     Outcome only


These are retrospective releases. Source-event timestamp eligibility and historical public availability are
distinct. The seven-day graph lag is an operational assumption, not a verified publication-time history.
Historically deployable performance would require revision-aware acquisition logs. Mutable DefiLlama
borrowing histories enter only the original borrowing-scaled sensitivity, with their downloaded hashes
recorded separately.

3.2 Run identity and reproduction
The supplied main ledger and the existing GitHub ledger have identical keys and labels, but 18,011 of
48,034 probabilities differ by more than 10−8 . We use the supplied ledger consistently for the primary
results because its fusion and 100-mask extensions refer to that run; columns from different runs are not
mixed. All 47 model/scenario metric rows recompute within 8.4 × 10−17 of the supplied tables. This verifies
score arithmetic and pairing, not unseen training-data provenance.
A complete primary-model refit was executed from hash-matched raw archives. Its temporal-graph AP
rounds to 0.1949, versus 0.1954 in the supplied ledger. The GRU, persistence and LightGBM headline
scores agree at reported precision. A neural stopping epoch differs in fold C, and software environments
differ. The subsequently available full aave.zip upload contains all six original raw-file hashes. Its processed
graph values agree exactly with the reconstruction; panel differences are at floating-point round-off scale.
Both ledgers remain available; byte-identical parquet or neural output is not asserted across Python and
numerical-library versions. These small headline differences leave the interpretation unchanged.

3.3 Compound source audit
The external CSV contains 1,456 rows from 1 January 2021 to 31 December 2024. Its date column is Date;
the earlier feasibility manifest incorrectly recorded a missing date field. The absent dates are 5 July, 1 August,
5 August, 25 November and 20 December 2024. The source paper states that five outlier observations were
removed (Iftikhar, Wei, and Cartlidge 2025). We reindex the full calendar, preserve missing values and
exclude forecasts with an incomplete 14-step feature sequence. Because each step includes a seven-day



                                                                                                                3
<PARSED TEXT FOR PAGE: 4 / 16>
Aave Liquidation Stress                                                                             Research revision



aggregate, validity can require 20 prior raw days. This leaves 196 scored days per Compound version in
April-December 2024.
Excluding the missing 5 August neighbourhood does not repair an unfiltered crisis benchmark: it defines
a sample omitting an important stress episode. On 667 overlapping dates per Aave version, the external
Aave values and the pinned archive agree within USD 1. This establishes numerical compatibility but does
not prove independent ingestion or validate Compound. Daily UTC alignment, exact deployment coverage
and contract-specific USD semantics remain assumptions for transfer.

3.4 A previously unscored later window
A separate specification was recorded before scoring 25 August 2025-31 August 2026. The window contains
744 forecasts. Preparation of a longer window first failed on four negative ETH/USD source observations
on 15, 21 and 22 September 2026. Before generating later-window scores, we capped evaluation at the last
preceding complete calendar month. September-November 2026 are quarantined. The amendment and final
specification hash accompany the results.
This uses the same Aave source: it is a new chronological test, not an independent dataset or prospective
deployment. No graph snapshots are invented after the pinned release ends. Snapshot age grows from
7 to 378 days, deliberately creating a stale-feed regime. Performance here cannot establish results with
continuously refreshed networks.


4 Methods
4.1 Outcome and chronological separation
      24
Let 𝑉𝑖,𝑡 be source-reported liquidation USD for version 𝑖 in [𝑡, 𝑡 + 24h). The fold-specific target is
                                (𝑓)       24                               24
                               𝑦𝑖,𝑡 = 𝟙{𝑉𝑖,𝑡 > 𝑞𝑖,𝑓 },     𝑞𝑖,𝑓 = 𝑄0.95 {𝑉𝑖,𝑠 ∶ 𝑠 ∈ 𝒯𝑓 }.

Thresholds use training outcomes only and differ by version. Tail activity is relative to historical scale, not
a universal insolvency boundary. Thresholds and prevalence can change between folds.
Features include prior one-, three- and seven-day liquidation sums/counts, borrowing and utilisation in
four reserves, and a version indicator. ETH/BTC channels contain one-/seven-day returns, daily realised
volatility, minimum hourly return and observation age. A tuning interval selects neural stopping epochs;
a subsequent calibration block fits probability maps and warning cutoffs. Training, tuning and calibration
label windows end at least one day before the next partition. Test outcome windows remain within their
fold. Fourteen-day input histories may precede a partition boundary because those observations are already
known; future outcomes never enter inputs.

               Table 2: Original folds; exact inclusive dates and unrounded thresholds are in run.json.

                                                                                               V2/V3 q95 (USD
Fold                      Test origins           Train n                 Test + / n            thousands)
A                         Apr-Jul 2024           610                     33 / 244              493 / 106
B                         Aug-Dec 2024           852                     24 / 306              617 / 416
C                         Jan-Aug 2025           1158                    53 / 472              670 / 815


4.2 Models and fitting
Benchmarks include a smoothed training prior, a logistic persistence predictor using prior-day liquidation,
local/market logistic models and shallow LightGBM with and without graph summaries (Ke et al. 2017).
The neural comparison uses the same 14-day history and a 24-unit GRU. Five seeds (19, 43, 71, 101, 137)
form each ensemble. Training uses unweighted binary cross-entropy, AdamW at learning rate 0.001/weight
decay 0.001, batch size 64, gradient norm cap 2, at most 36 epochs and tuning-loss patience seven.


                                                                                                                   4
<PARSED TEXT FOR PAGE: 5 / 16>
Aave Liquidation Stress                                                                          Research revision



The graph encoder transforms neighbour log size, log weight and an availability flag through direction-
specific multilayer maps. Normalised exposure weights form incoming/outgoing means. These are joined
with local/market inputs and graph statistics: own size, age, total exposure, retained degree, concentration
and mean peer size. A linear layer, layer normalisation and ReLU precede the GRU. Training-only scaling
clips standardised inputs to [−12, 12] and represents missing values with zeros plus indicators. This tests a
particular feature/model combination rather than all graph architectures.
Static topology, one-step graph input, removal of market channels and augmented training diagnose specific
components. One-step models retain engineered historical features and therefore are not information-free
about the past. No positive directed edge connects the two labelled Aave version nodes in this extraction.
The weighted cross-version interaction consequently has no identifying variation and cannot support a causal
spillover estimate.

4.3 Calibration, corruption and review
The raw ensemble probability is the mean of five members; disagreement is their variance. A positive-slope
ridge Platt map is fitted on calibration data and frozen. Probabilities are clipped to [10−6 , 1 − 10−6 ] for log
loss. An isotonic sensitivity remains in the original ledgers.
Edge thinning removes retained links with probabilities 0.10, 0.30 or 0.50. Each mask is fixed within
snapshot, version, direction and neighbour slot. One fitted ensemble per fold is evaluated under 100 masks
per rate; rates share nested draws. Empirical mask percentiles describe corruption variability conditional on
fixed weights, not population confidence intervals or 100 training repetitions. Other original scenarios add
one oracle day, seven graph days, or both with 30% thinning. Outcomes are held fixed; these are observation
disruptions, not market shocks.
An alert fires above the calibration-probability 90th percentile. A separate review queue first defers cases
above the calibration-disagreement 90th percentile. Deferral does not count as automated warning or
successful analyst detection. Onsets are first positive days after a nonpositive day or fold boundary. Lead
time is measured to cumulative target-volume threshold crossing, not necessarily to the first liquidation.

4.4 Reliability-aware fusion
For calibrated graph/local forecasts 𝑝𝐺 , 𝑝𝐿 and graph disagreement percentile 𝑟, the fixed mixture uses
𝑤 = 1/2 and the heuristic uses 𝑤 = (1 − 𝑟)/2:

                                            𝑝𝐹 = 𝑤𝑝𝐺 + (1 − 𝑤)𝑝𝐿 .

The learned gate is
                                𝑤𝜃 = sigmoid(𝜃0 + 𝜃1 𝑟 + 𝜃2 |𝑝𝐺 − 𝑝𝐿 | + 𝜃3 𝑝𝐺 ).
It minimises summed binary cross-entropy plus 𝜆‖𝜃 − 𝜃prior ‖22 /2, with prior (−1.5, −1, 0, 0). Original A
predictions fit candidates and B selects 𝜆 ∈ {0.1, 1, 10, 100} by log loss; the selected value is 0.1. For
exploratory C evaluation, the gate is refitted on A/B. For the later window, it is refitted on earlier A/B/C
out-of-sample predictions. C was already inspected when fusion was proposed, so C is not a fresh discovery
test.
The later base experts train through 29 April 2025, tune on 1 May-26 June and calibrate on 28 June-23
August. Later outcomes do not fit experts, calibration, gate parameters or expiry rules. A specified freshness
comparator sets heuristic graph weight to zero when graph age exceeds 28 days. This probes conservative
fallback rather than learning an optimal expiry. The later specification is retrospective and not externally
preregistered.

4.5 Executed source-weight transfer
Transfer variants replace reserve-specific channels with three shared lagged-volume features,
                                                    𝑘
                                                  ∑𝑗=1 𝑉𝑖,𝑡−𝑗
                                𝑥𝑖,𝑡 = log ⎛                    ⎞
                                 (𝑘)
                                           ⎜1 +                 ⎟,   𝑘 ∈ {1, 3, 7},
                                                    𝑞𝑖,train
                                           ⎝                    ⎠

                                                                                                                5
<PARSED TEXT FOR PAGE: 6 / 16>
Aave Liquidation Stress                                                                         Research revision



plus the same timed ETH/BTC inputs. The identity channel is constant zero. Graph variants use the same
neighbour encoder, with Compound nodes 114/2088. Aave alone fits source scaling, neural weights, stopping
rules and Platt calibration. Training covers 1 March-30 December 2023, tuning 1 January-13 February 2024,
calibration 15 February-30 March and testing April-December 2024.
Compound’s 2023 q95 defines its target and unit normalisation. This use of target history is explicit: the
experiment is source-weight transfer with target historical scaling, not zero information about the target. No
Compound label fits the transferred weights or calibration. Separately trained Compound models provide
supervised references under the same chronology. They are distinct estimators, not fine-tuned source models
selected on target test scores. Paired comparisons use the same valid target dates. The original reserve-
augmented checkpoints are not claimed to have been transferred.

4.6 Scores and uncertainty
We compute AP, Brier, log loss and AUROC from paired ledgers. A moving-block bootstrap samples
contiguous dates within each fold, carrying both Aave versions and both models together (Künsch 1989).
Main contrasts retain 2,000 valid 14-day draws; original graph/GRU comparisons also use seven-/28-day
blocks. Percentile intervals condition on fitted forecasts and observed regimes, omit refitting uncertainty
and are pointwise rather than simultaneous across all contrasts. Further ablations and transfer contrasts
are exploratory. Failure to show a gain is not proof of equivalence.


5 Results
5.1 Original cohort and incremental graph information
The three original tests contain 1,022 cases and 110 positives. Persistence has the strongest pooled AP
among the listed original predictors; the GRU has lower Brier loss than persistence. The temporal graph
does not establish incremental value over the GRU or graph-summary tree comparison.

 Table 3: Primary clean scores recomputed from the supplied ledger; AP higher and losses lower are preferable.

                          Model                            AP        Brier    Log loss
                          Training prior                   0.1150    0.0990   0.3645
                          Prior-day liquidation            0.3127    0.0918   0.3220
                          Local logit                      0.2373    0.1038   0.3434
                          LightGBM                         0.2574    0.0907   0.3264
                          LightGBM + graph summaries       0.2200    0.0926   0.3281
                          Market + local GRU               0.2479    0.0904   0.3129
                          Static graph                     0.2324    0.0915   0.3176
                          One-step graph                   0.2442    0.0906   0.3170
                          Graph without market             0.2226    0.0902   0.3100
                          Graph raw                        0.1930    0.0962   0.3626
                          Temporal graph + Platt           0.1954    0.0939   0.3319
                          Augmented graph                  0.2153    0.0921   0.3186




                                                                                                                 6
<PARSED TEXT FOR PAGE: 7 / 16>
Aave Liquidation Stress                                                                                                                Research revision



    Table 4: Conditional paired 14-day block intervals, 2,000 replications. Positive loss differences favour GRU.

                                          Graph minus GRU                 Estimate and 95% interval
                                          AP                              -0.0525 [-0.1488, 0.0161]
                                          brier                           0.0034 [-0.0012, 0.0086]
                                          logloss                         0.0191 [0.0053, 0.0328]


Graph/GRU AP and Brier intervals include zero, while graph log loss is worse in the conditional comparison.
This pointwise result is not a universal statement about financial networks. The graph ranks ahead in A/B;
the GRU leads in the largest fold C. Pooled AP reflects both within-fold ordering and cross-fold probability
alignment.

                                    Table 5: Same source ledger, separated by original test fold.

                                   Fold       Graph AP            GRU AP          Graph Brier            GRU Brier
                                   A          0.2114              0.1670          0.1162                 0.1162
                                   B          0.2924              0.2555          0.0670                 0.0668
                                   C          0.1975              0.3115          0.0998                 0.0924




 Prior-day liquidation                                                        Prior-day liquidation

           LightGBM                                                                     LightGBM

 Market + local GRU                                                           Market + local GRU

         Static graph                                                                 Static graph

     One-step graph                                                               One-step graph

     Temporal graph                                                               Temporal graph

  Augmented graph                                                              Augmented graph

                     0.00   0.05 0.10 0.15 0.20 0.25                   0.30                       0.00     0.02          0.04       0.06        0.08
                                Average precision (higher is better)                                              Brier score (lower is better)

Figure 1: Recomputed clean primary scores from one supplied forecast ledger. Both horizontal scales begin at zero.


Static and one-step graph variants rank ahead of the full temporal graph in the pooled sample. Adding
graph summaries to LightGBM lowers its AP point estimate. These observations constrain claims about
the selected representation but do not distinguish uninformative links from redundant inputs, small sample
size, weak peer attributes or scope mismatch. They do not answer the comparison with borrower Health
Factor, which remains unavailable.

5.2 Calibration, masks and analyst workload
The supplied raw and calibrated graph forecasts yield the following clean-score comparison.




                                                                                                                                                       7
<PARSED TEXT FOR PAGE: 8 / 16>
Aave Liquidation Stress                                                                                                            Research revision



                                           Table 6: Calibration uses earlier calibration blocks; it is frozen during testing.

                                                           Graph probability          AP         Brier       Log loss
                                                           Raw ensemble               0.1930     0.0962      0.3626
                                                           Platt calibrated           0.1954     0.0939      0.3319
                                                           Isotonic                   0.1617     0.0952      0.3562



                                          0.7
                                                    Graph raw
                                                    Graph calibrated
                                          0.6       GRU calibrated

                                          0.5
              Observed stress frequency




                                          0.4

                                          0.3

                                          0.2

                                          0.1

                                          0.0
                                             0.0        0.1            0.2          0.3           0.4          0.5      0.6        0.7
                                                                             Mean predicted stress probability

Figure 2: Equal-width reliability bins from the same clean ledger. Marker area reflects occupancy; sparse upper
bins remain uncertain.


Mean AP changes under thinning are slightly positive at each rate, but some masks worsen ranking.
Probability error moves in the opposite direction: 99 of 100 masks at 50% thinning worsen Brier loss.
A favourable deterministic mask would therefore give an incomplete account of robustness.

            Table 7: 100 mask draws per rate. All changes are paired with the same fitted clean graph.

Removal                                            Mean AP change            AP worse / 100              Mean Brier change    Brier worse / 100
10%                                                +0.00216                  27                          +0.000026            58
30%                                                +0.00424                  24                          +0.000157            87
50%                                                +0.00346                  36                          +0.000343            99




                                                                                                                                                  8
<PARSED TEXT FOR PAGE: 9 / 16>
Aave Liquidation Stress                                                                                                                                Research revision



                                                       100 mask draws per rate; conditional on fitted models
                                                                                                         0.0008
                        0.02
                                                                                                         0.0006




                                                                               Brier change from clean
AP change from clean




                        0.01
                                                                                                         0.0004
                        0.00                                                                             0.0002

                        0.01                                                                             0.0000
                                                                                                         0.0002
                        0.02
                                  10%              30%               50%                                                  10%              30%               50%
                                        Expected edge-removal rate                                                              Expected edge-removal rate

Figure 3: Mask variation conditional on fitted ensembles. Whiskers span empirical 2.5th-97.5th percentiles, not
confidence intervals for future markets.


Original delayed-input scenarios and alternative horizons remain in the replication tables. They are covariate
interventions on observed outcomes. Review additionally trades fewer automated false warnings against
fewer automated onset detections and a large manual queue. Without an analyst experiment, reviewed
cases cannot be counted as recovered events.

                       Table 8: Operational counts from the same supplied primary ledger. Reviews are not successful detections.

                                    Rule                   Automated alerts                              False alerts      Onsets hit      Reviews
                                    Graph                  188                                           151               16/70           0
                                    Graph + review         36                                            25                6/70            241
                                    GRU                    184                                           138               20/70           0


5.3 Fusion on C and a later chronological test
The existing gate and nested selection have little ranking separation from the GRU on C. As fusion was
developed after seeing the original benchmark, these C results support exploratory estimation only.

                                        Table 9: Exploratory original C results, 472 forecasts and 53 positives.

                                             C-only predictor                             AP                      Brier         Log loss
                                             Graph                                        0.1975                  0.099751      0.351594
                                             GRU                                          0.3115                  0.092422      0.312513
                                             Fixed half                                   0.3059                  0.093687      0.321133
                                             Disagreement heuristic                       0.3096                  0.093002      0.317223
                                             Original gate (penalty 10)                   0.3112                  0.092402      0.313454
                                             Nested selected gate                         0.3113                  0.092263      0.313368


The later test has 744 cases/40 positives (5.38%). Its training q95 thresholds are USD 691,427 for V2 and
USD 2,716,455 for V3. These differ from original C, so prevalence changes are not statements about an
unchanged physical stress boundary.




                                                                                                                                                                      9
<PARSED TEXT FOR PAGE: 10 / 16>
Aave Liquidation Stress                                                                                                                      Research revision



                            Table 10: Previously unscored later calendar, 744 forecasts and 40 positives; no independent-source claim.

                                                  Later predictor               AP              Brier          Log loss
                                                  Graph                         0.307427        0.048868       0.191485
                                                  GRU                           0.324161        0.046263       0.171444
                                                  Fixed half                    0.330924        0.047430       0.179051
                                                  Disagreement heuristic        0.324353        0.046305       0.171762
                                                  Learned gate                  0.322987        0.046439       0.172463
                                                  Expiry + heuristic            0.324193        0.046262       0.171428


                            Table 11: Paired 14-day intervals conditional on the later fitted forecasts. Small magnitudes are retained.

Minus GRU                                                      AP difference [95%]                            Brier difference [95%]
Graph                                                          -0.0167 [-0.0752, 0.0754]                      0.002605 [0.000900, 0.004972]
Fixed half                                                     0.0068 [-0.0170, 0.0660]                       0.001167 [0.000334, 0.002317]
Disagreement heuristic                                         0.0002 [-0.0030, 0.0038]                       0.000042 [0.000005, 0.000086]
Learned gate                                                   -0.0012 [-0.0155, 0.0088]                      0.000177 [0.000030, 0.000377]
Expiry + heuristic                                             0.0000 [-0.0001, 0.0007]                       -0.000001 [-0.000010, 0.000000]


The later learned gate has AP 0.3230 versus GRU 0.3242, with a positive Brier difference. A 50/50 mixture
improves the AP point estimate but worsens Brier/log loss; its AP interval spans zero. Marginal ranking
movement does not establish better probability quality. The freshness-capped heuristic is almost identical
to the GRU because it ignores the graph for most of this stale-feed regime. Near-equality is evidence of
fallback behaviour, not a new source of predictive information.

                                                                                        Graph        GRU            Learned gate         Observed (weekly mean)
                            0.4
  Probability / frequency




                            0.3

                            0.2

                            0.1

                            0.0
Graph age (days)




                        200


                             0
                                   2025-09        2025-11         2026-01             2026-03             2026-05                  2026-07            2026-09
                                                                    Later holdout: August 2025 to August 2026

Figure 4: Later forecasts and measured graph age. Weekly means aid display only; scores use unsmoothed daily
version-level predictions.




                                                                                                                                                                  10
<PARSED TEXT FOR PAGE: 11 / 16>
Aave Liquidation Stress                                                                                                                                Research revision




                                  Graph                                                                                  Graph

                           50/50 mixture                                                                          50/50 mixture

      Disagreement heuristic                                                                Disagreement heuristic

                           Learned gate                                                                           Learned gate

                      Expiry + heuristic                                                                     Expiry + heuristic
                                           0.075 0.050 0.025 0.000 0.025 0.050 0.075                                              0.000 0.001 0.002 0.003 0.004 0.005
                                                     AP difference from GRU                                                                Brier difference from GRU

Figure 5: Later paired differences from GRU, using 2,000 14-day moving-block draws with both versions clustered
by date.


The experiment tests a frozen gate with renewed expert fits and a changing age distribution. It cannot isolate
age causally from evolving market regimes. It nevertheless directly challenges the idea that disagreement
alone makes fusion robust to obsolete network observations. Source freshness is independently observable
and should accompany a learned uncertainty measure.

5.4 Conditional Compound transfer
Frozen-source predictions were actually generated. Both Compound versions have 196 valid test days, with
12 V2/19 V3 positives. Ranking transfer is weak, especially for the graph. On V3 both source models rank
below target-supervised references, while probability-loss differences are smaller. On V2 a source model
can have lower Brier error despite weaker ranking, illustrating separate effects of base-rate alignment and
ordering.

              Table 12: Conditional publisher-cohort transfer, 196 days per version. Target-history q95 scaling is declared.

Target / model                                 Frozen-source AP          Target-fit AP                                   Source Brier             Target Brier
V2 GRU                                         0.0677                    0.1500                                          0.0639                   0.0689
V2 Graph                                       0.0604                    0.1063                                          0.0711                   0.0937
V3 GRU                                         0.1109                    0.1982                                          0.0899                   0.0885
V3 Graph                                       0.0921                    0.1972                                          0.0940                   0.0929



                                           Compound V2 (196 days)                                                                 Compound V3 (196 days)
                                Test prevalence
                                Aave weights frozen
                    0.20        Target supervised reference                                                0.20
Average precision




                                                                                       Average precision




                    0.15                                                                                   0.15


                    0.10                                                                                   0.10


                    0.05                                                                                   0.05


                    0.00                                                                                   0.00
                                  Shared GRU                      Shared graph                                           Shared GRU                   Shared graph

Figure 6: Executed transfer scores. Dashed lines give target test prevalence as an uninformative-ranking reference.
Missing crisis neighbourhoods are excluded.


                                                                                                                                                                     11
<PARSED TEXT FOR PAGE: 12 / 16>
Aave Liquidation Stress                                                                       Research revision



On V3, source-minus-target AP differences are -0.0873 for GRU and -0.1051 for graph, with conditional
intervals [-0.1758, -0.0239] and [-0.1929, -0.0316]. These exploratory results show that transfer was executed
and failed to match supervised ranking in the filtered cohort. They do not establish chain-validated external
performance, a crisis-inclusive benchmark or coverage of every Compound deployment.


6 Historical account health and independent validation
6.1 Health Factor remains a missing benchmark
For a basic position, the conceptual Health Factor is
                                                  ∑𝑎 𝐶𝑢,𝑎,𝑡 𝑃𝑎,𝑡 LT𝑎,𝑡
                                        HF𝑢,𝑡 =                        .
                                                   ∑𝑎 𝐷𝑢,𝑎,𝑡 𝑃𝑎,𝑡

Contract values additionally depend on units, integer rounding, eligibility and historical implementation
rules. Oﬀicial Aave interfaces expose account data, and its logic includes version/eMode behaviour (Aave
2026, 2025). Reserve utilisation and governance thresholds are not account HF. Liquidated-account samples
are not representative borrower cross-sections.
The supplied Cred sample has 75 observations from January 2021-June 2022 and zero overlap with the
primary interval (Cred Protocol n.d.). Its aggregate collateral/debt arithmetic reproduces supplied HF
values, which is an algebraic identity within one dataset, not chain-state validation or a contemporary risk
panel.
Delivered reconstruction code reads token balances, prices, collateral flags and configuration at an exact
block, applies supported basic legacy integer rules and compares against getUserAccountData. Debt-free
HF is undefined; unsupported eMode/ABI cases fail explicitly. Ten training-era account/block requests
are included for mechanics checks. No real historical HF output was generated because archive calls were
denied. Software tests are not represented as empirical validation.

6.2 The required incremental-information comparison
A suitable panel must enumerate borrowers as known at each origin, not select future liquidation recipients.
At a block strictly before midnight it should measure debt-weighted HF shares, buffer distributions and
coverage. For example,
                                               ∑ 𝐷𝑢,𝑡 𝟙{HF𝑢,𝑡 < 𝜏 }
                                      𝑆𝑡 (𝜏 ) = 𝑢
                                                   ∑𝑢 𝐷𝑢,𝑡
requires a documented borrower denominator. The next comparison must hold cohort, target, dates and
calibration fixed across local/market, local/market/HF and local/market/HF/graph models. This ablation
has not run. Current findings concern network value relative to the available local inputs, not the best
obtainable loan-health information.

6.3 Compound semantics and access
Compound V2 emits LiquidateBorrow; Compound III uses absorption and later collateral-sale mechanics
(Compound 2026b, 2026a). Its AbsorbDebt event contains basePaidOut and usdValue (Compound Finance
2026). We retain the emitted valuation without automatically renaming it borrower principal or seized
collateral. Reconciliation must specify which quantity a published daily column measures, deployment
coverage and UTC boundaries. V2 repayment and seized collateral also need separate historical valuation
paths.
Network identity and a historical block header were obtainable. Historical state/log requests returned
HTTP 403 on the tested routes, and no authenticated archive endpoint was configured. Access reports
distinguish failure from an empty history. The supplied read-only collector checks continuous block coverage,
event uniqueness, removed-log flags and block hashes and can compare a second endpoint. It covers a
specified Ethereum Compound III USDC deployment, not complete V2/V3 reconciliation, and has no
claimed executed validation result.


                                                                                                            12
<PARSED TEXT FOR PAGE: 13 / 16>
Aave Liquidation Stress                                                                        Research revision




7 Discussion
7.1 Interpreting the negative evidence
The original and later tests constrain a practical claim: this network representation and disagreement gate
do not establish a stable advantage over timely local/market forecasting. The evidence includes exact score
recomputation, a full primary refit, multiple corruption masks and a previously unscored calendar. It is
weaker than a universal assertion that financial networks are uninformative. Only two source-labelled Aave
series, one graph construction and a small family of encoders are tested.
Local liquidation history may already encode pressure associated with exposure links. Weekly global
measurements may be too coarse for next-day account events. Peer attributes describe scale/exposure
rather than independently labelled distress. Additional complexity competes with few independent stress
episodes. Global graph coverage and Ethereum outcomes are imperfectly aligned. The present design
cannot identify the relative contribution of these explanations, and absent HF controls prevent a stronger
conditional-information claim.
Thinning separates sensitivity from economic information. Removing links can attenuate unhelpful messages
and improve some ranks while worsening probability magnitude. This does not mean data loss is intrinsically
protective. It argues for reporting distributions across specified masks and calibration diagnostics under the
same frozen forecast rule.

7.2 Reliability needs source metadata
Ensemble disagreement is not a certificate of input validity. Members can agree on stale or mismeasured
data. The later window deliberately exposes this problem. Its expiry comparator mostly reproduces local
forecasts: a conservative behaviour, not a demonstrated network gain. Monitoring should display age,
coverage and supported-regime flags alongside probabilities. Governance policies also need intervention
costs and financial consequences, which forecast scores alone cannot establish.
The companion local-currency adaptive-governance repository concerns policy responses to delayed
observations. It is a separate modelling project, not independent empirical evidence for these forecasts.
Neither predictive differences nor directed aggregate exposures alone justify an assertion of causal contagion
or a welfare-improving parameter intervention.

7.3 Selection and measurement
Transfer is a real procedure with saved weights, but deleting a crisis day is particularly damaging to a tail
estimand. The 196-day cohort is explicit about eligibility yet remains selected by publisher filtering. It must
not be advertised as a fully validated cross-protocol warning system. Matching published Aave series can
establish compatibility while leaving common upstream dependencies unresolved. Independent verification
requires event identities and a declared valuation map, not high correlation alone.
HF reconstruction has an analogous boundary: an equation is insuﬀicient when balances accrue interest,
collateral eligibility changes and protocol implementations evolve. Unsupported components must remain
missing rather than become reassuring zeros. Selected-account checks can validate mechanics but cannot
supply a representative risk distribution without an enumerated borrower universe.

7.4 Statistical and submission limits
Effective information is closer to independent stress episodes than total version-days. Moving blocks preserve
local clustering but cannot guarantee coverage under future regimes. The later window has only 40 positives
and an increasingly obsolete graph. AP depends on prevalence; thresholds differ across cohorts. All source-
quality decisions and model fits are retained, but no independent preregistration is claimed.
Independent Compound reconciliation and a representative validated HF comparison remain material
evidence gaps. A claim of network value beyond loan health cannot be made without the latter. This



                                                                                                             13
<PARSED TEXT FOR PAGE: 14 / 16>
Aave Liquidation Stress                                                                            Research revision



is a revised research manuscript for scientific review, with completed and blocked tasks separated below.
Journal quartile and acceptance are not inferred from architecture complexity or document formatting.


8 Conclusion
The selected temporal graph and reliability gate do not demonstrate stable improvement over local/market
alternatives across the original Aave study and a later chronological window. Prior liquidation is
a strong ranking comparator; calibration affects probability error; missing-link ranking changes can
diverge from probability quality. Executed source-weight transfer is weak and conditional on important
calendar/measurement assumptions. The package preserves negative results, distinct runs and unfinished
validation. Additional network value relative to historical borrower health remains an empirical question.


9 Reproducibility and evidence status

                Table 13: Completed analyses and unresolved scientific requirements at this revision.

Analysis                                Status                                 Interpretive boundary
Original metric audit                   Executed                               47 rows recomputed; no
                                                                               independent chain claim
Primary model refit                     Executed                               Software-sensitive outputs kept
                                                                               separate
100-mask analysis                       Executed                               Conditional on fitted ensembles
Later fusion test                       Executed                               New calendar, same source, stale
                                                                               graph
Aave-to-Compound transfer               Executed conditionally                 Filtered daily source;
                                                                               UTC/valuation assumptions
Compound raw-log reconciliation         Blocked                                Historical log access denied
Representative historical HF            Not completed                          Selected old sample is insuﬀicient
Network beyond HF comparison            Not executed                           Requires validated
                                                                               borrower-health panel


The package contains forecast ledgers, original sensitivity outputs, source hashes, transfer/later-window
weights, scaling/calibration metadata, specifications, code and tests. Large upstream archives are
downloaded from cited sources; small derived panels/graphs accompany the review package. Credentials
are read from environment variables and excluded from the repository. Original and refitted primary
ledgers stay separate. Tables are generated directly from score files.
The authors must confirm final authorship, aﬀiliations, funding/competing-interest statements and the
selected journal’s disclosure requirements before submission. No external journal submission is performed
by this revision.




                                                                                                                 14
<PARSED TEXT FOR PAGE: 15 / 16>
Aave Liquidation Stress                                                                     Research revision




10 References

References
Aave. 2025. ‘Aave V3 Core: GenericLogic.sol’. https://github.com/aave/aave-v3-core/blob/master/contr
    acts/protocol/libraries/logic/GenericLogic.sol.
———. 2026. ‘Aave V3 Pool Contract: getUserAccountData’. https://aave.com/docs/aave-v3/smart-
    contracts/pool.
Chaffard, Owen. 2026. ‘Stablecoin DeFi Hourly Dataset, 2026-11-15’. Zenodo, version v192. https:
    //doi.org/10.5281/zenodo.24245638.
Chiu, Jonathan, and Furkan Danisman. 2026. ‘DeFi Lending: Returns, Leverage, and Liquidation Risk’.
    Staff Analytical Paper 2026-13. Bank of Canada. https://doi.org/10.34989/sap-2026-13.
Cho, Kyunghyun, Bart van Merriënboer, Caglar Gulcehre, Dzmitry Bahdanau, Fethi Bougares, Holger
    Schwenk, and Yoshua Bengio. 2014. ‘Learning Phrase Representations Using RNN Encoder–Decoder
    for Statistical Machine Translation’. In Proceedings of the 2014 Conference on Empirical Methods in
    Natural Language Processing, 1724–34. https://doi.org/10.3115/v1/D14-1179.
Compound. 2026a. ‘Compound III Documentation: Liquidation’. https://docs.compound.finance/liquidat
    ion/.
———. 2026b. ‘Compound V2 Documentation: cTokens and Liquidation Events’. https://docs.compound.
    finance/v2/ctokens/.
Compound Finance. 2026. ‘Comet: Main Interface, Absorption Logic and Ethereum USDC Deployment’.
    https://github.com/compound-finance/comet/tree/f766f51583c23acc33b2a7824654ef2029a96804.
Cred Protocol. n.d. ‘Aave V2 Health Factor Dataset’. Accessed 17 November 2026. https://github.com/c
    redprotocol/Aave-V2-Health-Factor-Dataset.
Geifman, Yonatan, and Ran El-Yaniv. 2017. ‘Selective Classification for Deep Neural Networks’. In
    Advances in Neural Information Processing Systems. Vol. 30. https://proceedings.neurips.cc/paper_fil
    es/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html.
Gneiting, Tilmann, and Adrian E. Raftery. 2007. ‘Strictly Proper Scoring Rules, Prediction, and Estimation’.
    Journal of the American Statistical Association 102 (477): 359–78. https://doi.org/10.1198/0162145060
    00001437.
Guo, Chuan, Geoff Pleiss, Yu Sun, and Kilian Q. Weinberger. 2017. ‘On Calibration of Modern Neural
    Networks’. In Proceedings of the 34th International Conference on Machine Learning, 70:1321–30. PMLR.
    https://proceedings.mlr.press/v70/guo17a.html.
Hamilton, William L., Rex Ying, and Jure Leskovec. 2017. ‘Inductive Representation Learning on Large
    Graphs’. In Advances in Neural Information Processing Systems. Vol. 30. https://arxiv.org/abs/1706
    .02216.
Iftikhar, Erum, Wei Wei, and John Cartlidge. 2025. ‘Automated Risk Management Mechanisms in
    DeFi Lending Protocols: A Crosschain Comparative Analysis of Aave and Compound’. arXiv preprint
    2506.12855. https://doi.org/10.48550/arXiv.2506.12855.
Ke, Guolin, Qi Meng, Thomas Finley, Taifeng Wang, Wei Chen, Weidong Ma, Qiwei Ye, and Tie-Yan
    Liu. 2017. ‘LightGBM: A Highly Eﬀicient Gradient Boosting Decision Tree’. In Advances in Neural
    Information Processing Systems. Vol. 30. https://proceedings.neurips.cc/paper_files/paper/2017/hash
    /6449f44a102fde848669bdd9eb6b76fa-Abstract.html.
Künsch, Hans R. 1989. ‘The Jackknife and the Bootstrap for General Stationary Observations’. The Annals
    of Statistics 17 (3): 1217–41. https://doi.org/10.1214/aos/1176347265.
Lakshminarayanan, Balaji, Alexander Pritzel, and Charles Blundell. 2017. ‘Simple and Scalable Predictive
    Uncertainty Estimation Using Deep Ensembles’. In Advances in Neural Information Processing Systems.
    Vol. 30. https://proceedings.neurips.cc/paper/2017/hash/9ef2ed4b7fd2c810847ffa5fa85bce38-
    Abstract.html.
Lehar, Alfred, and Christine A. Parlour. 2022. ‘Systemic Fragility in Decentralised Markets’. BIS Working
    Papers 1062. Bank for International Settlements. https://www.bis.org/publications/working-paper-
    1062-systemic-fragility-decentralised-markets.
Ovadia, Yaniv, Emily Fertig, Jie Ren, Zachary Nado, D. Sculley, Sebastian Nowozin, Joshua V. Dillon, Balaji


                                                                                                          15
<PARSED TEXT FOR PAGE: 16 / 16>
Aave Liquidation Stress                                                                 Research revision



   Lakshminarayanan, and Jasper Snoek. 2019. ‘Can You Trust Your Model’s Uncertainty? Evaluating
   Predictive Uncertainty Under Dataset Shift’. In Advances in Neural Information Processing Systems.
   Vol. 32. https://proceedings.neurips.cc/paper/2019/hash/8558cb408c1d76621371888657d2eb1d-
   Abstract.html.
Qin, Kaihua, Liyi Zhou, Pablo Gamito, Philipp Jovanovic, and Arthur Gervais. 2021. ‘An Empirical Study
   of DeFi Liquidations: Incentives, Risks, and Instabilities’. In Proceedings of the 21st ACM Internet
   Measurement Conference, 336–50. https://doi.org/10.1145/3487552.3487811.
Saito, Takaya, and Marc Rehmsmeier. 2015. ‘The Precision-Recall Plot Is More Informative Than the
   ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets’. PLOS ONE 10 (3): e0118432.
   https://doi.org/10.1371/journal.pone.0118432.
Schuler, Katrin. 2026. ‘Frictions in DeFi Liquidations: Evidence from the Aave V2 Main Market’. SSRN
   working paper, revised 6 June 2026. https://ssrn.com/abstract=6522500.
Shu, Aijie, Wenbin Wu, Gbenga Ibikunle, and Fengxiang He. 2026. ‘DeXposure-FM: A Time-Series, Graph
   Foundation Model for Credit Exposures and Stability on Decentralized Financial Networks’. arXiv
   preprint 2602.03981, version 2. https://doi.org/10.48550/arXiv.2602.03981.
Wu, Wenbin, Kejiang Qian, Alexis Lui, Christopher Jack, Yue Wu, Peter McBurney, Fengxiang He, and
   Bryan Zhang. 2025. ‘DeXposure: A Dataset and Benchmarks for Inter-Protocol Credit Exposure in
   Decentralized Financial Networks’. arXiv preprint 2511.22314. https://doi.org/10.48550/arXiv.2511.22
   314.




                                                                                                      16