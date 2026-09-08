#!/usr/bin/env python3
"""Budgeted training, checkpointed dev gates, and conditional official evaluation."""
import argparse, fcntl, hashlib, importlib.util, json, os, signal, subprocess, sys, time, traceback
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
LAB=ROOT/"labs/phase-05-single-sft"
RUN=ROOT/"artifacts/phase5/repair-v1"
BASE="/data/models/DeepSeek-R1-0528-Qwen3-8B-phase5-addvocab"
TRAIN_PY="/data/venvs/deepanalyze-train/bin/python"
INFER_PY="/data/venvs/tesla-vllm-085/bin/python"
GPUS=[int(g) for g in os.environ.get("PHASE5_GPUS","2,3,4,5,6,7").split(",")]
if not GPUS or len(set(GPUS))!=len(GPUS) or 252%len(GPUS):
    raise ValueError("Unique GPUs must divide effective batch 252")
ACCUM=252//len(GPUS)
DS_CONFIG=os.environ.get("DEEPSPEED_CONFIG","zero3")
GATE_STEPS=int(os.environ.get("REPAIR_GATE_STEPS","10"))
BUDGET=12*3600
def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".tmp")
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n");temp.replace(path)
def state(stage,**kwargs):
    value={"stage":stage,"time":datetime.now(timezone.utc).isoformat(),"pid":os.getpid(),**kwargs}
    write_json(RUN/"state.json",value);print(json.dumps(value),flush=True)
def check_gpus():
    for gpu in GPUS:
        used=int(subprocess.check_output(["nvidia-smi","-i",str(gpu),"--query-gpu=memory.used",
                                         "--format=csv,noheader,nounits"],text=True).strip())
        if used>1000:raise RuntimeError(f"GPU {gpu} occupied: {used} MiB")
def command(args,log,timeout,env=None):
    started=time.monotonic()
    with log.open("a") as out:
        proc=subprocess.Popen(args,stdout=out,stderr=subprocess.STDOUT,cwd=ROOT,
                              env=env or os.environ.copy(),start_new_session=True)
        try:
            code=proc.wait(timeout=timeout)
        except BaseException:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            raise
    if code:raise RuntimeError(f"Command failed ({code}), inspect {log}")
    return time.monotonic()-started
def development(model,name):
    output=RUN/"dev"/f"{name}.json"
    if not output.exists():
        check_gpus()
        command([INFER_PY,str(LAB/"scripts/repair_dev.py"),"--model",str(model),"--output",str(output)],
                RUN/"logs"/f"dev-{name}.log",1800,
                env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(GPUS[0]),OMP_NUM_THREADS="4",TOKENIZERS_PARALLELISM="false"))
    result=json.loads(output.read_text())
    if result["model"]!=str(model) or result["max_tokens"]!=2048 or result["summary"]["count"]!=32:
        raise RuntimeError("Development cache protocol/model mismatch")
    return result["summary"]
def regression(base,current):
    """Predeclared: catastrophic drop immediately; moderate drop on two gates."""
    severe=(current["passed"]<=base["passed"]-8 or current["has_code"]<=base["has_code"]-8
            or current["repetitive"]>=max(8,base["repetitive"]+6))
    moderate=(current["passed"]<=base["passed"]-4 or current["ended"]<=base["ended"]-4
              or current["repetitive"]>=base["repetitive"]+4)
    return severe,moderate
def qualifies(base,current):
    return (current["passed"]>=base["passed"] and current["has_code"]>=base["has_code"]
            and current["ended"]>=base["ended"] and current["repetitive"]<=base["repetitive"]+1)
def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def pipeline():
    if (RUN/"train").exists():raise RuntimeError("Training exists; explicit recovery required, not an automatic restart")
    preflight=json.loads((RUN/"preflight.json").read_text())
    if preflight.get("deepspeed","zero3")!=DS_CONFIG:
        raise RuntimeError("DeepSpeed mode differs from resume preflight")
    if not preflight["passed"]:raise RuntimeError("Segment resume preflight did not pass")
    for name,digest in preflight["script_hashes"].items():
        if hashlib.sha256((LAB/"scripts"/name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError("Training control changed after preflight")
    manifest=json.loads((RUN/"data/manifest.json").read_text())
    if not 80_000_000<=manifest["actual_tokens"]<=120_000_000:raise RuntimeError("Token budget out of range")
    sha=hashlib.sha256()
    with (RUN/"data/train.jsonl").open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):sha.update(chunk)
    if sha.hexdigest()!=manifest["sha256"]:raise RuntimeError("Training data changed")
    config={"data_sha256":sha.hexdigest(),"actual_tokens":manifest["actual_tokens"],
            "base":BASE,"gpus":GPUS,"micro_batch":1,"gradient_accumulation":ACCUM,"effective_batch":252,
            "deepspeed":DS_CONFIG,
            "learning_rate":1e-5,"max_length":8192,"epochs":1,"warmup_ratio":0.1,
            "training_budget_seconds":BUDGET,"dev_every_optimizer_steps":GATE_STEPS,
            "first_dev_step":1,
            "script_hashes":{name:hashlib.sha256((LAB/"scripts"/name).read_bytes()).hexdigest()
                for name in ["repair_dev.py","repair_callback.py","train_repair.sh","prepare_repair.py","run_repair.py"]},
            "dev_gate":"severe >=8/32 correct/code drop or >=8 repeats; stop immediately. Moderate >=4/32 correct/ending drop or +4 repeats at two consecutive gates. Official eval requires final selected dev result no worse than baseline.",
            "scope":"Audited 15-source ~100M-token repair variant, not complete paper reproduction."}
    write_json(RUN/"config.json",config)
    state("development_baseline")
    base=development(BASE,"base")
    if base["passed"]<24:raise RuntimeError("Baseline below 24/32; review development protocol before training")
    previous=0;training_seconds=0;history=[];moderate_streak=0;resume=None
    while True:
        check_gpus()
        limit=1 if previous==0 else previous+GATE_STEPS
        state("training",next_stop_step=limit,training_seconds=training_seconds,budget_seconds=BUDGET)
        env=dict(os.environ,REPAIR_STOP_STEP=str(limit),PHASE5_GPUS=",".join(map(str,GPUS)),
                 GRAD_ACCUM=str(ACCUM),DEEPSPEED_CONFIG=DS_CONFIG,MICRO_BATCH="1",MAX_LENGTH="8192",
                 MAX_STEPS="-1",SAVE_STEPS=str(GATE_STEPS))
        if resume:env["RESUME_FROM"]=str(resume)
        remaining=BUDGET-training_seconds
        if remaining<60:
            state("stopped_at_budget",checkpoint=str(resume),training_seconds=training_seconds)
            if history:break
            return
        try:
            used=command(["bash",str(LAB/"scripts/train_repair.sh")],RUN/"logs"/f"train-to-{limit}.log",
                         remaining,env=env)
        except subprocess.TimeoutExpired:
            training_seconds=BUDGET
            state("stopped_at_budget",checkpoint=str(resume),training_seconds=BUDGET)
            if history:break
            return
        training_seconds+=used
        checkpoints=list((RUN/"train").glob("checkpoint-*/trainer_state.json"))
        if not checkpoints:raise RuntimeError("No recoverable checkpoint saved")
        latest=max(checkpoints,key=lambda p:int(p.parent.name.split("-")[-1]))
        saved=json.loads(latest.read_text());step=saved["global_step"];resume=latest.parent
        if step<=previous or step>limit:raise RuntimeError("Checkpoint step did not follow segment boundary")
        if saved["max_steps"]<=0:raise RuntimeError("Missing full-run scheduler horizon")
        state("development",step=step,checkpoint=str(resume),training_seconds=training_seconds)
        current=development(resume,f"step-{step}")
        severe,moderate=regression(base,current);moderate_streak=moderate_streak+1 if moderate else 0
        entry={"step":step,"checkpoint":str(resume),"metrics":current,
               "training_seconds":training_seconds,"qualified":qualifies(base,current),
               "max_steps":saved["max_steps"],"severe":severe,"moderate":moderate}
        history.append(entry)
        write_json(RUN/"progress.json",{"baseline":base,"history":history})
        if severe or moderate_streak>=2:
            state("stopped_for_regression",**entry);return
        previous=step
        if step>=saved["max_steps"]:break
    candidates=[r for r in history if r["qualified"]]
    if not candidates:
        state("training_complete_dev_gate_failed",training_seconds=training_seconds,history=history);return
    best=max(candidates,key=lambda r:(r["metrics"]["passed"],r["metrics"]["ended"],-r["metrics"]["repetitive"],r["step"]))
    write_json(RUN/"selected.json",best)
    state("official_evaluation",selected=best,training_seconds=training_seconds)
    runner=load_module("official_repair",LAB/"scripts/run_pilot.py")
    runner.GPUS=GPUS
    runner.NAME="phase5-repair-v1";runner.EVAL=ROOT/"artifacts/phase5/repair-v1-official"
    runner.STATE=RUN/"official-state.json"
    runner.evaluate(Path(best["checkpoint"]))
    summary=json.loads((runner.EVAL/"summary.json").read_text())
    summary["scope"]="Repair-v1 ~100M-token dataset, at most one epoch under 12h training cap; may stop before epoch completion. Checkpoint selected on fresh development tasks; not complete Phase 5 curriculum."
    write_json(runner.EVAL/"summary.json",summary)
    state("completed",training_seconds=training_seconds,selected=best,official=summary["overall"])
def main():
    RUN.mkdir(parents=True,exist_ok=True)
    for name in ["logs","dev","cache"]: (RUN/name).mkdir(exist_ok=True)
    os.environ["TMPDIR"]="/dev/shm";os.environ["DS1000_SCRATCH_ROOT"]="/dev/shm"
    for name,sub in {"HF_DATASETS_CACHE":"hf-datasets","MODELSCOPE_CACHE":"modelscope",
                     "TRITON_CACHE_DIR":"triton","TORCH_EXTENSIONS_DIR":"torch-extensions",
                     "CUDA_CACHE_PATH":"cuda","VLLM_CACHE_ROOT":"vllm"}.items():
        path=RUN/"cache"/sub;path.mkdir(exist_ok=True);os.environ[name]=str(path)
    with (RUN/"pipeline.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:pipeline()
        except Exception as e:
            state("failed",error=str(e));traceback.print_exc();raise
if __name__=="__main__":main()
