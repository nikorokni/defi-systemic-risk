"""Figures from the exact scored ledgers, without smoothing or fitted trend lines."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/"revision"
OUT = BASE/"figures"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":9, "axes.spines.top":False,
    "axes.spines.right":False,"axes.titleweight":"bold","savefig.dpi":200})
NAVY, TEAL, ORANGE = "#243B53", "#117C83", "#CF7426"


def save(fig, name):
    fig.savefig(OUT/(name+".pdf"), bbox_inches="tight")
    fig.savefig(OUT/(name+".png"), bbox_inches="tight")
    plt.close(fig)


def main():
    d = pd.read_csv(BASE/"results/recomputed_metrics.csv")
    names = {"persistence":"Prior-day liquidation", "lightgbm":"LightGBM", "gru":"Market + local GRU",
             "static_graph":"Static graph", "graph_no_sequence":"One-step graph", "graph_platt":"Temporal graph",
             "robust_graph":"Augmented graph"}
    q = d[d.scenario.eq("clean")].set_index("model").loc[list(names)]
    fig, axes = plt.subplots(1,2,figsize=(10,3.5), layout="constrained")
    for ax, metric, title in zip(axes,["ap","brier"],["Average precision (higher is better)","Brier score (lower is better)"]):
        ax.barh(np.arange(len(q)), q[metric], color=[TEAL if i=="gru" else NAVY for i in q.index], height=.65)
        ax.set_yticks(np.arange(len(q)),[names[n] for n in q.index])
        ax.invert_yaxis();ax.set_xlabel(title);ax.grid(axis="x",alpha=.18);ax.set_axisbelow(True)
    save(fig,"primary_performance")
    ledger = pd.read_csv(BASE/"inputs/Aave_Results_For_Review/results/primary/predictions.csv.gz")
    fig, ax = plt.subplots(figsize=(6.8,4.1),layout="constrained")
    for m,label,c in [("graph_raw","Graph raw",ORANGE),("graph_platt","Graph calibrated",NAVY),("gru","GRU calibrated",TEAL)]:
        g = ledger[ledger.model.eq(m)&ledger.scenario.eq("clean")]
        pp, yy, nn = [], [], []
        bins = np.minimum((g.probability.to_numpy()*10).astype(int),9)
        for i in range(10):
            h = g[bins==i]
            if len(h):
                pp.append(h.probability.mean()); yy.append(h.actual.mean());nn.append(len(h))
        ax.plot(pp,yy,"-",lw=1.2,color=c,label=label)
        ax.scatter(pp,yy,s=np.sqrt(nn)*13,alpha=.6,color=c,edgecolors="white",linewidths=.5)
    ax.plot([0,.7],[0,.7],"--",color="#8A96A3",lw=1);ax.set(xlabel="Mean predicted stress probability",ylabel="Observed stress frequency",xlim=(0,.7),ylim=(0,.7));ax.legend(frameon=False);ax.grid(alpha=.15)
    save(fig,"calibration_recomputed")
    masks = pd.read_csv(BASE/"results/mask_scores_recomputed.csv")
    clean = masks[masks.scenario.eq("clean")].iloc[0]
    fig, axes = plt.subplots(1,2,figsize=(9.4,3.2),layout="constrained")
    for ax, metric, title in zip(axes,["ap","brier"],["AP change from clean","Brier change from clean"]):
        arrays = [masks[masks.scenario.eq(s)][metric]-clean[metric] for s in ["thin_10","thin_30","thin_50"]]
        bx = ax.boxplot(arrays,tick_labels=["10%","30%","50%"],whis=(2.5,97.5),showfliers=True,patch_artist=True)
        for patch in bx["boxes"]:patch.set_facecolor("#B6D7D8")
        ax.axhline(0,linestyle="--",color=NAVY,lw=1);ax.set(xlabel="Expected edge-removal rate",ylabel=title);ax.grid(axis="y",alpha=.15)
    fig.suptitle("100 mask draws per rate; conditional on fitted models",fontsize=10)
    save(fig,"mask_sensitivity")
    tt = pd.read_csv(BASE/"results/transfer/scores.csv")
    fig, axes = plt.subplots(1,2,figsize=(9.4,3.5),layout="constrained")
    for ax,v in zip(axes,["c2","c3"]):
        x=np.arange(2)
        for j,(domain,label,c) in enumerate([("aave_source_only","Aave weights frozen",NAVY),("compound_supervised_reference","Target supervised reference",TEAL)]):
            val=tt[tt.version.eq(v)&tt.training_domain.eq(domain)].set_index("model").loc[["shared_gru","shared_graph"]]
            ax.bar(x+(j-.5)*.32,val.ap,width=.32,label=label,color=c)
        prev=tt[tt.version.eq(v)].prevalence.iloc[0]
        ax.axhline(prev,linestyle="--",color=ORANGE,lw=1,label="Test prevalence")
        ax.set(xticks=x,xticklabels=["Shared GRU","Shared graph"],ylabel="Average precision",title="Compound V"+v[1]+" (196 days)",ylim=(0,.24))
        ax.grid(axis="y",alpha=.15);ax.set_axisbelow(True)
    axes[0].legend(frameon=False,fontsize=8,loc="upper left")
    save(fig,"transfer_performance")
    late = pd.read_csv(BASE/"results/later_holdout/predictions.csv")
    late.origin = pd.to_datetime(late.origin)
    weekly=late.set_index("origin")[["graph","gru","learned_gate","actual","graph_age_days"]].resample("7D").mean()
    fig, axes=plt.subplots(2,1,figsize=(9.4,4.7),sharex=True,layout="constrained",gridspec_kw={"height_ratios":[2.3,1]})
    axes[0].plot(weekly.index,weekly.graph,label="Graph",color=NAVY)
    axes[0].plot(weekly.index,weekly.gru,label="GRU",color=TEAL)
    axes[0].plot(weekly.index,weekly.learned_gate,label="Learned gate",color=ORANGE,lw=1)
    axes[0].plot(weekly.index,weekly.actual,label="Observed (weekly mean)",color="#919AA4",linestyle="--",alpha=.7)
    axes[0].set_ylabel("Probability / frequency");axes[0].legend(ncol=4,frameon=False,fontsize=8);axes[0].grid(alpha=.15)
    axes[1].plot(weekly.index,weekly.graph_age_days,color=NAVY);axes[1].axhline(28,color=ORANGE,linestyle="--",label="28-day expiry")
    axes[1].set_ylabel("Graph age (days)");axes[1].set_xlabel("Later holdout: August 2025 to August 2026");axes[1].grid(alpha=.15)
    save(fig,"later_holdout_history")
    ci=pd.read_csv(BASE/"results/later_holdout/paired_intervals.csv")
    labels={"graph":"Graph", "fixed_half":"50/50 mixture", "reliability_heuristic":"Disagreement heuristic", "learned_gate":"Learned gate", "freshness_capped_heuristic":"Expiry + heuristic"}
    fig,axes=plt.subplots(1,2,figsize=(9.4,3.1),layout="constrained")
    for ax,metric,title in zip(axes,["ap","brier"],["AP difference from GRU","Brier difference from GRU"]):
        z=ci[ci.metric.eq(metric)].set_index("model").loc[list(labels)]
        ax.errorbar(z.difference,np.arange(len(z)),xerr=[z.difference-z.low,z.high-z.difference],fmt="o",color=NAVY,capsize=3)
        ax.axvline(0,color=ORANGE,linestyle="--",lw=1);ax.set_yticks(np.arange(len(z)),[labels[m] for m in z.index]);ax.invert_yaxis();ax.set_xlabel(title);ax.grid(axis="x",alpha=.15)
    save(fig,"later_holdout_differences")


if __name__=="__main__":
    main()