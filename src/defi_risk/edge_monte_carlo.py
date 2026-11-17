"""Repeat independent edge thinning without selecting a favourable random mask.

Fit once per chronological fold and evaluate 100 disjoint perturbation seeds.
Requires the original prepared parquet files from 'python -m defi_risk prepare'.
Report realised scores, not expected results.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score, brier_score_loss

from .inputs import ForecastInputs
from .models import NeuralSpec, Scaling, TorchInput, stack_inputs, predict_member, train_member, Platt
from .run import create_split


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed",type=Path,default=Path("data/processed"))
    parser.add_argument("--config",type=Path,default=Path("configs/study.json"))
    parser.add_argument("--output",type=Path,default=Path("results/edge_monte_carlo"))
    parser.add_argument("--repetitions",type=int,default=100)
    args=parser.parse_args()
    import json
    with args.config.open() as file: cfg=json.load(file)
    if args.repetitions < 2: raise ValueError("Require at least two independent masks")
    args.output.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    panel=pd.read_parquet(args.processed/"panel.parquet")
    inputs=ForecastInputs(args.processed,panel,cfg)
    spec=NeuralSpec(graph=True)
    all_rows=[]
    for fold in cfg["folds"]:
        split=create_split(args.processed,panel,cfg,fold,24,False)
        clean_views=inputs.arrays()
        scaling=Scaling().fit(stack_inputs(clean_views,graph=True)[split.train])
        clean=TorchInput(inputs,clean_views,spec,scaling,cfg["history_days"])
        members=[train_member(seed,split.train,split.tune,split.labels,clean,None,spec,cfg)[0]
                 for seed in cfg["seeds"]]
        ref=np.stack([predict_member(model,clean,split.calibrate) for model in members]).mean(axis=0)
        calibrator=Platt().fit(ref,split.labels[split.calibrate])
        y=split.labels[split.test]
        for rate,scenario in [(0.0,"clean"),(.1,"thin_10"),(.3,"thin_30"),(.5,"thin_50")]:
            n=1 if rate==0 else args.repetitions
            for iteration in range(n):
                views=clean_views if rate==0 else inputs.arrays(scenario,mask_seed=100000+iteration)
                data=clean if rate==0 else TorchInput(inputs,views,spec,scaling,cfg["history_days"])
                raw=np.stack([predict_member(model,data,split.test) for model in members]).mean(axis=0)
                p=calibrator.predict(raw)
                all_rows.extend(dict(fold=fold["id"],version=panel.version.iat[row],origin=str(panel.origin.iat[row].date()),
                                     scenario=scenario,iteration=iteration,actual=int(truth),probability=float(prob))
                                for row,truth,prob in zip(split.test,y,p))
            print(f"Completed {fold['id']} {scenario}",flush=True)
    ledger=pd.DataFrame(all_rows)
    ledger.to_csv(args.output/"predictions.csv.gz",index=False,compression="gzip")
    # Pooled scoring within replicate preserves joint fold-version event pairing.
    summary=[]
    for (scenario,iteration),data in ledger.groupby(["scenario","iteration"],sort=True):
        y=data.actual.to_numpy();p=data.probability.to_numpy()
        summary.append(dict(scenario=scenario,iteration=iteration,n=len(y),positives=int(y.sum()),
                            ap=average_precision_score(y,p),brier=brier_score_loss(y,p)))
    scores=pd.DataFrame(summary)
    scores.to_csv(args.output/"replicate_scores.csv",index=False)
    aggregate=scores.groupby("scenario").agg(
        seeds=("iteration","nunique"),mean_ap=("ap","mean"),sd_ap=("ap","std"),
        q025_ap=("ap",lambda x:float(np.quantile(x,.025))),
        q975_ap=("ap",lambda x:float(np.quantile(x,.975))),
        mean_brier=("brier","mean"),sd_brier=("brier","std")).reset_index()
    aggregate.to_csv(args.output/"summary.csv",index=False)
    print(aggregate.to_string(index=False))
    print("Mask intervals quantify perturbation variation conditional on the refitted models; NOT population confidence intervals.")

if __name__=="__main__":
    main()
