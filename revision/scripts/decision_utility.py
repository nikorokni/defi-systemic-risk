"""Decision-loss sensitivity on saved, frozen Aave forecasts.

Loss units are hypothetical; neither market interventions nor USD savings
are inferred. Test labels never choose alert thresholds: for FP cost 1 and
FN cost r, cutoff = 1/(1+r). Requires pandas, numpy and scikit-learn.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss

RATIOS = (2,5,10,20,50,100)


def load_ledgers(root):
    original = pd.read_csv(root/"results/primary/predictions.csv.gz")
    original = original[(original.scenario=="clean") &
        (original.model.isin(["prior","persistence","lightgbm","gru","graph_platt"]))].copy()
    original["cohort"]="original_2024_2025"
    original=original[["cohort","origin","version","actual","model","probability"]]
    later=pd.read_csv(root/"revision/results/later_holdout/predictions.csv")
    models=["gru","graph","fixed_half","reliability_heuristic",
            "learned_gate","freshness_capped_heuristic"]
    later=later.melt(id_vars=["origin","version","actual"],value_vars=models,
                     var_name="model",value_name="probability")
    later["cohort"]="later_2025_2026"
    df=pd.concat([original,later[original.columns]],ignore_index=True)
    df["origin"]=pd.to_datetime(df.origin,utc=True,format="mixed")
    if df.duplicated(["cohort","origin","version","model"]).any():
        raise ValueError("Repeated forecast identifiers")
    if df.probability.isna().any() or (~df.probability.between(0,1)).any():
        raise ValueError("Invalid probability")
    for _,g in df.groupby("cohort"):
        labels=g.pivot(index=["origin","version"],columns="model",values="actual")
        if labels.isna().any().any() or labels.nunique(axis=1).max()!=1:
            raise ValueError("Cohort models differ in target keys or outcomes")
    return df


def calculate(df):
    rows=[]
    for (cohort,model),g in df.groupby(["cohort","model"]):
        y=g.actual.to_numpy(dtype=int)
        p=g.probability.to_numpy(dtype=float)
        for r in RATIOS:
            alerts=p>=1/(1+r)
            tp=int((alerts & (y==1)).sum())
            fp=int((alerts & (y==0)).sum())
            fn=int((~alerts & (y==1)).sum())
            cost=fp+r*fn
            rows.append(dict(cohort=cohort,model=model,c_fn_over_c_fp=r,
                p_threshold=1/(1+r),n=len(g),positives=int(y.sum()),
                alerts=int(alerts.sum()),true_alerts=tp,false_alerts=fp,
                missed_positives=fn,cost_units=cost,cost_per_1000=1000*cost/len(g),
                no_alert_cost_units=r*int(y.sum()),
                always_alert_cost_units=int((y==0).sum()),
                ap=float(average_precision_score(y,p)),brier=float(brier_score_loss(y,p)),
                logloss=float(log_loss(y,np.clip(p,1e-6,1-1e-6),labels=[0,1]))))
    return pd.DataFrame(rows)


def paired_interval(df,cohort,a,b,ratio,replicates=2000,seed=24031):
    subset=df[(df.cohort==cohort)&df.model.isin([a,b])]
    pivot=subset.pivot(index=["origin","version"],columns="model",values="probability")
    y=subset.drop_duplicates(["origin","version"]).set_index(
        ["origin","version"]).actual.reindex(pivot.index).to_numpy(int)
    if pivot[[a,b]].isna().any().any():
        raise ValueError("Missing matched forecast")
    cutoff=1/(1+ratio)
    pa=pivot[a].to_numpy()>=cutoff
    pb=pivot[b].to_numpy()>=cutoff
    costs_a=(pa & (y==0)).astype(float)+ratio*(~pa & (y==1))
    costs_b=(pb & (y==0)).astype(float)+ratio*(~pb & (y==1))
    difference=costs_a-costs_b
    dates=pd.Index(sorted(pivot.index.get_level_values("origin").unique()))
    day_rows=[np.flatnonzero(pivot.index.get_level_values("origin")==d) for d in dates]
    span=min(14,len(dates))
    rng=np.random.default_rng(seed)
    samples=np.empty(replicates)
    for i in range(replicates):
        starts=rng.integers(0,len(dates)-span+1,
                            size=(len(dates)+span-1)//span)
        day_idx=np.concatenate([np.arange(j,j+span) for j in starts])[:len(dates)]
        row_idx=np.concatenate([day_rows[j] for j in day_idx])
        samples[i]=1000*difference[row_idx].mean()
    return dict(cohort=cohort,model_a=a,model_b=b,c_fn_over_c_fp=ratio,
        difference_cost_per_1000=1000*difference.mean(),
        block_q025=float(np.quantile(samples,.025)),
        block_q975=float(np.quantile(samples,.975)),
        n=len(difference),bootstrap_draws=replicates,
        caveat="Conditional date-block percentiles, not actual financial welfare")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--project",type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument("--reps",type=int,default=2000)
    args=p.parse_args()
    data=load_ledgers(args.project)
    out=args.project/"revision/results/decision_utility"
    out.mkdir(parents=True,exist_ok=True)
    calculate(data).to_csv(out/"cost_sensitivity.csv",index=False)
    rows=[]
    for cohort,a,b in [
        ("original_2024_2025","graph_platt","gru"),
        ("original_2024_2025","persistence","gru"),
        ("later_2025_2026","learned_gate","gru"),
        ("later_2025_2026","fixed_half","gru"),
        ("later_2025_2026","freshness_capped_heuristic","gru")]:
        for ratio in RATIOS:
            rows.append(paired_interval(data,cohort,a,b,ratio,args.reps))
    pd.DataFrame(rows).to_csv(out/"paired_cost_intervals.csv",index=False)
    print("Computed frozen-score decision sensitivity:",out)


if __name__=="__main__":
    main()
