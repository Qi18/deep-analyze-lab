#!/usr/bin/env python3
"""Run a bounded 8B pilot, then the unchanged official DS-1000 inference and scorer."""
import argparse, concurrent.futures, gzip, hashlib, importlib.util, json, os, shutil, subprocess, sys, traceback
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
LAB=ROOT/"labs/phase-05-single-sft"
RUN=ROOT/"artifacts/phase5/pilot-100"
EVAL=ROOT/"artifacts/phase5/pilot-100-eval"
NAME="phase5-pilot100"
GPUS=[2,3,4,5,6,7]
STATE=ROOT/"artifacts/phase5/pipeline-state.json"
def state(stage, **kwargs):
    value={"stage":stage,"updated_at":datetime.now(timezone.utc).isoformat(),"pid":os.getpid(),**kwargs}
    temp=STATE.with_suffix(".tmp")
    temp.write_text(json.dumps(value,indent=2)+"\n");temp.replace(STATE)
    print(json.dumps(value),flush=True)
def check_gpus():
    for gpu in GPUS:
        used=int(subprocess.check_output(["nvidia-smi","-i",str(gpu),"--query-gpu=memory.used","--format=csv,noheader,nounits"],text=True).strip())
        if used>1000: raise RuntimeError(f"GPU {gpu} is occupied ({used} MiB); waiting for user rather than overlapping")
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def command(args,log,**kwargs):
    with log.open("a") as out:
        subprocess.run(args,stdout=out,stderr=subprocess.STDOUT,check=True,**kwargs)
def evaluate(checkpoint):
    check_gpus()
    phase3=load_module("phase3_runner",ROOT/"labs/phase-03-evaluation/scripts/ds1000.py")
    phase3.verify_source()
    source=phase3.SOURCE
    with gzip.open(source/"data/ds1000.jsonl.gz","rt") as f: tasks=[json.loads(line) for line in f]
    assert len(tasks)==1000
    work=EVAL/"DS-1000"
    if not work.exists():shutil.copytree(source,work)
    checkpoint_file=EVAL/"checkpoint.json"
    if checkpoint_file.exists():
        assert json.loads(checkpoint_file.read_text())["path"]==str(checkpoint),"Refusing mixed checkpoints"
    else:checkpoint_file.write_text(json.dumps({"path":str(checkpoint)},indent=2)+"\n")
    def infer(shard):
        gpu=GPUS[shard]
        selected=tasks[shard::len(GPUS)]
        directory=EVAL/f"shard-{shard}"
        if not directory.exists():
            shutil.copytree(source,directory)
            with gzip.open(directory/"data/ds1000.jsonl.gz","wt") as f:
                for item in selected:f.write(json.dumps(item)+"\n")
        answers=directory/"data"/f"{NAME}-answers.jsonl"
        if answers.exists():
            got=[json.loads(line) for line in answers.read_text().splitlines() if line.strip()]
            if len(got)==len(selected):return answers
        command([str(phase3.INFER_PYTHON),"run_deepanalyze.py","--model",str(checkpoint),
                 "--model_name",NAME,"--resume"],directory/"inference.log",
                cwd=directory,env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(gpu)))
        return answers
    state("official_inference",checkpoint=str(checkpoint),task_count=1000)
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(GPUS)) as pool:
        paths=list(pool.map(infer,range(len(GPUS))))
    records={}
    for path in paths:
        for line in path.read_text().splitlines():
            item=json.loads(line);pid=int(item["metadata"]["problem_id"])
            if pid in records:raise RuntimeError(f"Duplicate problem_id {pid}")
            records[pid]=item
    assert sorted(records)==list(range(1000))
    answers=work/"data"/f"{NAME}-answers.jsonl"
    with answers.open("w") as f:
        for pid,item in sorted(records.items()):item["id"]=pid;f.write(json.dumps(item)+"\n")
    audit=ROOT/"labs/phase-03-evaluation/scripts/audit_ds1000_answers.py"
    audit_result=subprocess.run([sys.executable,str(audit),"--answers",str(answers)],text=True,capture_output=True)
    audit_path=EVAL/"pre-score-audit.json"
    audit_path.write_text(audit_result.stdout)
    audit_result.check_returncode()
    if json.loads(audit_result.stdout)["dynamic_eval_review"]:
        raise RuntimeError("Generated code contains dynamic evaluation; manual review required before scoring")
    state("official_scoring",checkpoint=str(checkpoint),task_count=1000)
    command(["bash",str(phase3.SANDBOX),NAME],EVAL/"scoring.log",
            env=dict(os.environ,DS1000_WORKDIR=str(work)),cwd=work)
    raw=json.loads((work/"results"/f"{NAME}-log.json").read_text())
    assert sorted(int(v["completion_id"]) for v in raw)==list(range(1000))
    assert all(v["score"] in [0,1] for v in raw)
    agg=load_module("phase3_metrics",ROOT/"labs/phase-03-evaluation/scripts/collect_results.py").aggregate
    base=json.loads((ROOT/"labs/phase-03-evaluation/results/metrics.json").read_text())
    result=dict(model=NAME,checkpoint=str(checkpoint),benchmark="DS-1000",task_count=1000,
                overall=agg(raw)["overall"],by_library=agg(raw,"library"),
                by_perturbation=agg(raw,"perturbation_type"),
                reference_baselines={k:v["overall"] for k,v in base["models"].items()},
                scope="100-step clean-v1 pilot, single temperature=0 official evaluation; full Phase 5 remains incomplete")
    (EVAL/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    state("pilot_and_evaluation_completed",result=str(EVAL/"summary.json"),overall=result["overall"])
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--evaluate-only",type=Path)
    args=p.parse_args()
    cache=ROOT/"artifacts/phase5/cache"
    for name,sub in {"HF_DATASETS_CACHE":"hf-datasets","MODELSCOPE_CACHE":"modelscope",
                     "TMPDIR":"tmp","TRITON_CACHE_DIR":"triton","TORCH_EXTENSIONS_DIR":"torch-extensions",
                     "CUDA_CACHE_PATH":"cuda","VLLM_CACHE_ROOT":"vllm"}.items():
        path=cache/sub;path.mkdir(parents=True,exist_ok=True);os.environ[name]=str(path)
    os.environ["DS1000_SCRATCH_ROOT"]="/dev/shm"
    STATE.parent.mkdir(parents=True,exist_ok=True)
    try:
        if args.evaluate_only:evaluate(args.evaluate_only.resolve());return
        if RUN.exists():raise RuntimeError("Pilot directory exists; resume explicitly to preserve existing run")
        check_gpus()
        state("training",steps=100,max_length=8192,gradient_accumulation=4,gpus=GPUS)
        env=dict(os.environ,MAX_STEPS="100",MAX_LENGTH="8192",GRAD_ACCUM="4",USE_LIGER="true",
                 SAVE_ONLY_MODEL="false",SAVE_STEPS="20",DATASET_NUM_PROC="8",
                 DATASET_PATH=str(ROOT/"artifacts/phase5/data/single-clean-v1.jsonl"),OUTPUT_DIR=str(RUN))
        command(["bash",str(LAB/"scripts/train_single.sh")],ROOT/"artifacts/phase5/logs/pilot-100.log",
                env=env,cwd=ROOT)
        checkpoints=list(RUN.glob("v*/checkpoint-100"))
        assert len(checkpoints)==1,checkpoints
        checkpoint=checkpoints[0]
        trainer=json.loads((checkpoint/"trainer_state.json").read_text())
        assert trainer["global_step"]==100
        command([str(Path("/data/venvs/deepanalyze-train/bin/python")),str(LAB/"scripts/verify_checkpoint.py"),
                 "--model",str(checkpoint),"--dataset",str(ROOT/"artifacts/phase5/data/smoke-96.jsonl"),
                 "--output",str(ROOT/"artifacts/phase5/pilot-checkpoint-inference.json")],
                ROOT/"artifacts/phase5/logs/pilot-checkpoint-inference.log",
                env=dict(os.environ,CUDA_VISIBLE_DEVICES="2"))
        evaluate(checkpoint)
    except Exception as exc:
        state("failed",error=str(exc));traceback.print_exc();raise
if __name__=="__main__":main()
