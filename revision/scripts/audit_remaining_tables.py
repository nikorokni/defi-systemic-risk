"""Recompute stratified scores, sensitivity arms and operational accounting."""
from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from defi_risk.metrics import probability_scores,reliability_table,risk_coverage,alert_scores
from defi_risk.report import metrics_table,event_windows,CORE,GRAPH
R=ROOT/"revision/inputs/Aave_Results_For_Review/results"
OUT=ROOT/"revision/results/all_table_checks"


def compare(name, actual, keys):
    expected=pd.read_csv(R/name)
    # CSV decimal round-tripping must not make a display coverage fraction a
    # different observation key. Fractions are far more separated than 1e-12.
    if "coverage" in keys:
        actual=actual.copy(); expected=expected.copy()
        actual["coverage"]=actual.coverage.round(12)
        expected["coverage"]=expected.coverage.round(12)
    joined=actual.merge(expected,on=keys,validate="one_to_one",suffixes=("_new","_old"))
    if len(joined)!=len(actual) or len(joined)!=len(expected):
        raise ValueError("Unmatched rows in "+name)
    errors={}
    for c in actual:
        if c in keys or not pd.api.types.is_numeric_dtype(actual[c]):continue
        a,b=joined[c+"_new"],joined[c+"_old"]
        if not a.isna().equals(b.isna()):raise ValueError("Missingness mismatch: "+name+":"+c)
        errors[c]=float((a-b).abs().max()) if a.notna().any() else 0.
    actual.to_csv(OUT/name,index=False)
    return dict(table=name,rows=len(actual),max_abs_error=max(errors.values(),default=0),errors=errors)


def main():
    OUT.mkdir(exist_ok=True)
    p=pd.read_csv(R/"primary/predictions.csv.gz")
    clean=p[p.scenario.eq("clean")]
    reports=[]
    reports.append(compare("metrics_by_fold.csv",metrics_table(p,["fold","model","scenario"]),["fold","model","scenario"]))
    reports.append(compare("metrics_by_version.csv",metrics_table(clean,["version","model"]),["version","model"]))
    cal=pd.concat([reliability_table(g.actual.to_numpy(),g.probability.to_numpy()).assign(model=m) for m,g in clean.groupby("model")])
    reports.append(compare("reliability_bins.csv",cal,["model","bin"]))
    reports.append(compare("risk_coverage.csv",pd.DataFrame(risk_coverage(clean[clean.model.eq(GRAPH)])),["uncertainty_score","coverage"]))
    queues=[]
    for (m,s),g in p[p.model.isin(CORE)].groupby(["model","scenario"]):
        for policy in (["alert","alert_with_review"] if g.uncertainty.notna().all() else ["alert"]):
            queues.append(dict(model=m,scenario=s,**alert_scores(g,policy)))
    reports.append(compare("alerts.csv",pd.DataFrame(queues),["model","scenario","policy"]))
    cfg=json.loads((ROOT/"configs/study.json").read_text())
    reports.append(compare("historical_windows.csv",event_windows(clean[clean.model.isin(CORE)],cfg),["window","version","model"]))
    arms=[metrics_table(clean,["model","scenario"]).assign(target="usd_24h")]
    for folder in ["six_hour","seven_day","borrowing_scaled"]:
        x=pd.read_csv(R/folder/"predictions.csv.gz")
        if x.duplicated(["origin","version","fold","model","scenario"]).any():raise ValueError("Duplicate sensitivity cases")
        arms.append(metrics_table(x,["model","scenario"]).assign(target=folder))
    reports.append(compare("label_sensitivity.csv",pd.concat(arms,ignore_index=True),["target","model","scenario"]))
    (OUT/"parity_summary.json").write_text(json.dumps(reports,indent=2))
    print(json.dumps([{k:v for k,v in r.items() if k!="errors"} for r in reports],indent=2))


if __name__=="__main__":main()