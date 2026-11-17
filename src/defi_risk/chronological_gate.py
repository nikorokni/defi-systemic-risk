"""Chronological reliability gate: learn only from earlier held-out fold predictions.

Fold A and B provide historical out-of-sample meta-training forecasts.
Fold C is the subsequent (later) evaluation period. The gate NEVER sees C labels
during fitting. As this hypothesis was developed after inspecting the original
benchmark, treat this as exploratory and externally revalidate.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.metrics import average_precision_score,brier_score_loss,log_loss

from .fusion import mix_forecasts

EPS=1e-6


def features(paired):
    pg=np.clip(paired.p_graph.to_numpy(float),EPS,1-EPS)
    pl=np.clip(paired.p_local.to_numpy(float),EPS,1-EPS)
    u=paired.uncertainty_rank.to_numpy(float)
    # No outcomes in features; all scores/uncertainty were available at forecast time.
    return np.column_stack([np.ones(len(pg)),u,np.abs(pg-pl),pg])


def fit_gate(development, penalty=10.0):
    z=features(development)
    pg=development.p_graph.to_numpy(float)
    pl=development.p_local.to_numpy(float)
    y=development.actual.to_numpy(float)
    prior=np.array([-1.5,-1.0,0.0,0.0])  # conservative local-model preference
    def objective(theta):
        w=expit(z@theta)
        p=np.clip(w*pg+(1-w)*pl,EPS,1-EPS)
        loss=-(y*np.log(p)+(1-y)*np.log1p(-p)).sum()
        return loss+0.5*penalty*np.square(theta-prior).sum()
    sol=minimize(objective,prior,method="L-BFGS-B")
    if not sol.success:
        raise RuntimeError("Chronological gate fit did not converge: "+sol.message)
    return sol.x


def run(ledger,out):
    x=pd.read_csv(ledger)
    g=x[(x.model=="graph_platt")&(x.scenario=="clean")]
    l=x[(x.model=="gru")&(x.scenario=="clean")]
    paired=mix_forecasts(g,l)
    development=paired[paired.fold.isin(["A","B"])].copy()
    test=paired[paired.fold.eq("C")].copy()
    if development.empty or test.empty or set(paired.fold)!=set(["A","B","C"]):
        raise ValueError("Require exactly chronological A/B/C fold predictions")
    if pd.to_datetime(development.origin).max()>=pd.to_datetime(test.origin).min():
        raise ValueError("Development must finish before later test period starts")
    theta=fit_gate(development)
    test["gate_weight"]=expit(features(test)@theta)
    test["p_learned"]=np.clip(test.gate_weight*test.p_graph+
                              (1-test.gate_weight)*test.p_local,EPS,1-EPS)
    scores=[]
    y=test.actual.to_numpy()
    for name,col in [("graph","p_graph"),("gru","p_local"),
                     ("half_fixed","p_fixed"),("heuristic_uncertainty","p_reliability"),
                     ("learned_chronological_gate","p_learned")]:
        p=test[col].to_numpy()
        scores.append({"model":name,"n":len(y),"positives":int(y.sum()),
                       "ap":float(average_precision_score(y,p)),
                       "brier":float(brier_score_loss(y,p)),
                       "logloss":float(log_loss(y,p,labels=[0,1]))})
    out.mkdir(parents=True,exist_ok=True)
    test.to_csv(out/"fold_C_predictions.csv",index=False)
    pd.DataFrame(scores).to_csv(out/"fold_C_scores.csv",index=False)
    (out/"coefficients.txt").write_text(
        "Intercept, disagreement rank, expert difference, graph probability\n"+
        ",".join(f"{v:.10g}" for v in theta)+"\n"+
        "Exploratory post-hoc study; no independent new source data evaluated.\n")
    print(pd.DataFrame(scores).to_string(index=False))
    print("Exploratory: old OOS forecasts train the gate, new chronological C forecasts evaluate it; hypothesis selected after reviewing the original benchmark.")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ledger",type=Path,default=Path("results/primary/predictions.csv.gz"))
    ap.add_argument("--out",type=Path,default=Path("results/chronological_fusion"))
    a=ap.parse_args()
    run(a.ledger,a.out)


if __name__=="__main__":
    main()
