"""Verify that saved neural weights and transforms reproduce saved predictions."""
from pathlib import Path
import json,sys
import numpy as np
import pandas as pd
import torch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src"))
from defi_risk.inputs import ForecastInputs
from defi_risk.models import NeuralSpec,Scaling,TorchInput,StressNet,predict_member,Platt


def main():
    torch.set_num_threads(1)
    base=ROOT/"revision"
    reports=[]
    for name in ["transfer","later_holdout"]:
        out=base/"results"/name
        cfg=json.loads((out/"run.json").read_text())
        settings=cfg["config"] if name=="transfer" else json.loads((ROOT/"configs/study.json").read_text())
        panel=pd.read_parquet(base/"data"/name/"panel.parquet")
        inputs=ForecastInputs(base/"data"/name,panel,settings)
        views=inputs.arrays()
        predictions=pd.read_csv(out/("predictions.csv.gz" if name=="transfer" else "predictions.csv"))
        predictions.origin=pd.to_datetime(predictions.origin,utc=True)
        meta=json.loads((out/"fitting_metadata.json").read_text()) if name=="transfer" else cfg["fitting"]
        for record in meta:
            model_name=record["model"]
            graph=model_name in ["shared_graph","graph"]
            target=predictions[predictions.model.eq(model_name)&predictions.training_domain.eq(record["training_domain"])] if name=="transfer" else predictions
            unique=target[["origin","version"]].copy()
            lookup=panel.reset_index(names="row")[["origin","version","row"]]
            rows=unique.merge(lookup,on=["origin","version"],validate="one_to_one").row.to_numpy()
            scaling=Scaling()
            scaling.mean=np.array(record["scaling_mean"])
            scaling.scale=np.array(record["scaling_scale"])
            data=TorchInput(inputs,views,NeuralSpec(graph=graph),scaling,14)
            probs=[]
            for seed in [19,43,71,101,137]:
                net=StressNet(data.tabular.shape[-1],24,graph)
                prefix=record["training_domain"]+"_"+model_name if name=="transfer" else model_name
                net.load_state_dict(torch.load(out/f"{prefix}_{seed}.pt",map_location="cpu",weights_only=True))
                probs.append(predict_member(net,data,rows))
            platt=Platt();platt.intercept=record["platt_intercept"];platt.slope=record["platt_slope"]
            got=platt.predict(np.stack(probs).mean(axis=0))
            expected=target.probability.to_numpy() if name=="transfer" else target[model_name].to_numpy()
            err=float(np.max(np.abs(got-expected)))
            # Transfer metadata was exported to 10 decimal places. This explicit
            # tolerance verifies checkpoint identity without asserting bit equality.
            passed=err<1e-6
            reports.append(dict(experiment=name,model=model_name,training_domain=record.get("training_domain","aave"),
                n=len(rows),max_absolute_probability_error=err,tolerance=1e-6,passed=passed))
            if not passed:raise ValueError("Checkpoint replay failed: "+repr(reports[-1]))
    (base/"results/checkpoint_replay.json").write_text(json.dumps(reports,indent=2))
    print(json.dumps(reports,indent=2))


if __name__=="__main__":main()