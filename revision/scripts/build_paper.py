"""Generate every manuscript table from scored files, then compile LaTeX/PDF."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import os
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
R = ROOT/"revision/results"
P = ROOT/"paper"


def table(headers, rows, caption):
    s = "| " + " | ".join(headers) + " |\n|"+"|".join(":---" for _ in headers)+"|\n"
    for row in rows:
        s += "| "+" | ".join(str(x) for x in row)+" |\n"
    return s+"\n: "+caption+"\n"


def interval(r, digits=4):
    return f"{r.difference:.{digits}f} [{r.low:.{digits}f}, {r.high:.{digits}f}]"


def build():
    clean=pd.read_csv(R/"recomputed_metrics.csv").query("scenario == 'clean'").set_index("model")
    aliases={"prior":"Training prior","persistence":"Prior-day liquidation","logistic_local":"Local logit",
             "lightgbm":"LightGBM","lightgbm_graph":"LightGBM + graph summaries","gru":"Market + local GRU",
             "static_graph":"Static graph","graph_no_sequence":"One-step graph","graph_local":"Graph without market",
             "graph_raw":"Graph raw","graph_platt":"Temporal graph + Platt","robust_graph":"Augmented graph"}
    replacements={}
    replacements["PRIMARY_RESULTS"]=table(["Model","AP","Brier","Log loss"],
        [[label,f"{clean.loc[m].ap:.4f}",f"{clean.loc[m].brier:.4f}",f"{clean.loc[m].logloss:.4f}"] for m,label in aliases.items()],
        "Primary clean scores recomputed from the supplied ledger; AP higher and losses lower are preferable.")
    replacements["FOLDS"]=table(["Fold","Test origins","Train n","Test + / n","V2/V3 q95 (USD thousands)"],
        [["A","Apr-Jul 2024",610,"33 / 244","493 / 106"],["B","Aug-Dec 2024",852,"24 / 306","617 / 416"],
         ["C","Jan-Aug 2025",1158,"53 / 472","670 / 815"]],"Original folds; exact inclusive dates and unrounded thresholds are in run.json.")
    ci=pd.read_csv(R/"paired_block_intervals.csv")
    z=ci[(ci.left=="graph_platt")&(ci.right=="gru")&(ci.block_days==14)]
    replacements["PRIMARY_INTERVALS"]=table(["Graph minus GRU","Estimate and 95% interval"],
        [[r.metric.upper() if r.metric=="ap" else r.metric,interval(r)] for r in z.itertuples()],
        "Conditional paired 14-day block intervals, 2,000 replications. Positive loss differences favour GRU.")
    f=pd.read_csv(R/"recomputed_by_fold.csv")
    rows=[]
    for fold in "ABC":
        g=f[(f.fold==fold)&(f.model=="graph_platt")].iloc[0];l=f[(f.fold==fold)&(f.model=="gru")].iloc[0]
        rows.append([fold,f"{g.ap:.4f}",f"{l.ap:.4f}",f"{g.brier:.4f}",f"{l.brier:.4f}"])
    replacements["FOLD_SCORES"]=table(["Fold","Graph AP","GRU AP","Graph Brier","GRU Brier"],rows,"Same source ledger, separated by original test fold.")
    replacements["CALIBRATION"]=table(["Graph probability","AP","Brier","Log loss"],
        [[n,f"{clean.loc[m].ap:.4f}",f"{clean.loc[m].brier:.4f}",f"{clean.loc[m].logloss:.4f}"] for m,n in [("graph_raw","Raw ensemble"),("graph_platt","Platt calibrated"),("graph_isotonic","Isotonic")]],
        "Calibration uses earlier calibration blocks; it is frozen during testing.")
    d=pd.read_csv(R/"mask_paired_changes.csv")
    replacements["MASK_RESULTS"]=table(["Removal","Mean AP change","AP worse / 100","Mean Brier change","Brier worse / 100"],
        [[r.scenario.replace("thin_","")+"%",f"{r.mean_ap_delta:+.5f}",round(r.fraction_ap_worse*100),f"{r.mean_brier_delta:+.6f}",round(r.fraction_brier_worse*100)] for r in d.itertuples()],
        "100 mask draws per rate. All changes are paired with the same fitted clean graph.")
    alerts=pd.read_csv(ROOT/"revision/inputs/Aave_Results_For_Review/results/alerts.csv")
    rows=[]
    for m,policy,label in [("graph_platt","alert","Graph"),("graph_platt","alert_with_review","Graph + review"),("gru","alert","GRU")]:
        q=alerts[(alerts.model==m)&(alerts.scenario=="clean")&(alerts.policy==policy)].iloc[0]
        rows.append([label,int(q.alerts),int(q.false_alerts),f"{int(q.onsets_alerted)}/{int(q.onsets)}",int(q.review_flags)])
    replacements["ALERTS"]=table(["Rule","Automated alerts","False alerts","Onsets hit","Reviews"],rows,"Operational counts from the same supplied primary ledger. Reviews are not successful detections.")
    gc=pd.read_csv(R/"chronological_gate_scores.csv")
    cn={"graph":"Graph","gru":"GRU","half_fixed":"Fixed half","reliability_heuristic":"Disagreement heuristic","learned_gate_penalty10":"Original gate (penalty 10)","nested_selected_gate":"Nested selected gate"}
    replacements["GATE_C"]=table(["C-only predictor","AP","Brier","Log loss"],
        [[cn[r.model],f"{r.ap:.4f}",f"{r.brier:.6f}",f"{r.logloss:.6f}"] for r in gc.itertuples()],"Exploratory original C results, 472 forecasts and 53 positives.")
    late=pd.read_csv(R/"later_holdout/scores.csv")
    ln={"graph":"Graph","gru":"GRU","fixed_half":"Fixed half","reliability_heuristic":"Disagreement heuristic","learned_gate":"Learned gate","freshness_capped_heuristic":"Expiry + heuristic"}
    replacements["LATER_RESULTS"]=table(["Later predictor","AP","Brier","Log loss"],
        [[ln[r.model],f"{r.ap:.6f}",f"{r.brier:.6f}",f"{r.logloss:.6f}"] for r in late.itertuples()],"Previously unscored later calendar, 744 forecasts and 40 positives; no independent-source claim.")
    lci=pd.read_csv(R/"later_holdout/paired_intervals.csv")
    rows=[]
    for m in ln:
        if m=="gru":continue
        zz=lci[lci.model.eq(m)].set_index("metric")
        rows.append([ln[m],interval(zz.loc["ap"],4),interval(zz.loc["brier"],6)])
    replacements["LATER_INTERVALS"]=table(["Minus GRU","AP difference [95%]","Brier difference [95%]"],rows,
        "Paired 14-day intervals conditional on the later fitted forecasts. Small magnitudes are retained.")
    tr=pd.read_csv(R/"transfer/scores.csv")
    rows=[]
    for v in ["c2","c3"]:
        for m,label in [("shared_gru","GRU"),("shared_graph","Graph")]:
            s=tr[(tr.version==v)&(tr.model==m)&(tr.training_domain=="aave_source_only")].iloc[0]
            t=tr[(tr.version==v)&(tr.model==m)&(tr.training_domain=="compound_supervised_reference")].iloc[0]
            rows.append(["V"+v[1]+" "+label,f"{s.ap:.4f}",f"{t.ap:.4f}",f"{s.brier:.4f}",f"{t.brier:.4f}"])
    replacements["TRANSFER_RESULTS"]=table(["Target / model","Frozen-source AP","Target-fit AP","Source Brier","Target Brier"],rows,
        "Conditional publisher-cohort transfer, 196 days per version. Target-history q95 scaling is declared.")
    replacements["EVIDENCE_STATUS"]=table(["Analysis","Status","Interpretive boundary"],
        [["Original metric audit","Executed","47 rows recomputed; no independent chain claim"],
         ["Primary model refit","Executed","Software-sensitive outputs kept separate"],
         ["100-mask analysis","Executed","Conditional on fitted ensembles"],
         ["Later fusion test","Executed","New calendar, same source, stale graph"],
         ["Aave-to-Compound transfer","Executed conditionally","Filtered daily source; UTC/valuation assumptions"],
         ["Compound raw-log reconciliation","Blocked","Historical log access denied"],
         ["Representative historical HF","Not completed","Selected old sample is insufficient"],
         ["Network beyond HF comparison","Not executed","Requires validated borrower-health panel"]],
        "Completed analyses and unresolved scientific requirements at this revision.")
    text=(ROOT/"revision/paper/manuscript.template.md").read_text()
    for key,value in replacements.items():
        text=text.replace("{{"+key+"}}",value)
    if re.search(r"\{\{[A-Z_]+\}\}",text):raise ValueError("Unfilled manuscript marker")
    used=set(re.findall(r"@([a-zA-Z][a-zA-Z0-9_-]*)",text))
    bibkeys=set(re.findall(r"@\w+\{([^,]+),",(P/"references.bib").read_text()))
    if used-bibkeys:raise ValueError("Missing citations: "+repr(used-bibkeys))
    (P/"manuscript.md").write_text(text)
    shutil.copyfile(ROOT/"revision/paper/manuscript.template.md",P/"manuscript.template.md")
    subprocess.run(["pandoc","paper/manuscript.md","--standalone","--citeproc","--number-sections",
        "--bibliography=paper/references.bib","--resource-path=.:paper:revision",
        "--include-in-header=paper/preamble.tex","-o","paper/main.tex"],cwd=ROOT,check=True)
    # Keep charts at their discussing paragraphs and cap their height. Longtable
    # output routines can otherwise stack deferred floats beyond a page boundary.
    tex=(P/"main.tex").read_text()
    tex=tex.replace("\\begin{figure}","\\begin{figure}[H]")
    tex=tex.replace("height=\\textheight]","height=0.33\\textheight,keepaspectratio]")
    tex=tex.replace("\\begin{longtable}","\\Needspace{10\\baselineskip}\n\\begin{longtable}")
    (P/"main.tex").write_text(tex)
    build=ROOT/"build/revised_paper";build.mkdir(parents=True,exist_ok=True)
    texenv=os.environ.copy()
    fmt=subprocess.run(["kpsewhich","xelatex.fmt"],capture_output=True,text=True).stdout.strip()
    local_formats=ROOT.parent/"tex_tools"
    if not fmt and (local_formats/"xelatex.fmt").exists():
        # This host has a complete source tree but a missing search database.
        # A locally built format repairs that environment without system edits.
        texenv["TEXMF"]="{/usr/share/texlive/texmf-dist,/usr/share/texmf}"
        texenv["TEXFORMATS"]=str(local_formats)+":"
        fmt=str(local_formats/"xelatex.fmt")
    tectonic=shutil.which("tectonic")
    if not tectonic:
        candidate=ROOT.parent/"tex_tools/tectonic"
        tectonic=str(candidate) if candidate.exists() else None
    with (build/"compile_output.txt").open("w") as log:
        if fmt:
            for _ in range(2):
                subprocess.run(["xelatex","-interaction=nonstopmode","-halt-on-error",f"-output-directory={build}","main.tex"],cwd=P,env=texenv,stdout=log,stderr=subprocess.STDOUT,check=True)
        elif tectonic:
            subprocess.run([tectonic,"main.tex","--outdir",str(build),"--keep-logs"],cwd=P,stdout=log,stderr=subprocess.STDOUT,check=True)
        else:
            raise RuntimeError("Install complete TeX Live/XeLaTeX or Tectonic to compile the delivered LaTeX")
    shutil.copyfile(build/"main.pdf",P/"manuscript.pdf")
    print("Built",P/"manuscript.pdf","from",len(replacements),"generated tables and",len(used),"cited sources",flush=True)


if __name__=="__main__":build()