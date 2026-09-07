"""Start local-only upstream services; no upstream source modifications."""
import argparse, os, subprocess, sys, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/phase1"
parser = argparse.ArgumentParser()
parser.add_argument("--execute", action="store_true")
args = parser.parse_args()
commands = {
"vllm": ["/data/venvs/tesla-vllm-085/bin/python", "-m", "vllm.entrypoints.openai.api_server",
"--model", "/data/models/DeepAnalyze-8B", "--served-model-name", "DeepAnalyze-8B",
"--host", "127.0.0.1", "--port", "8000", "--dtype", "bfloat16",
"--max-model-len", "32768", "--gpu-memory-utilization", "0.85", "--max-num-seqs", "2",
"--enforce-eager", "--seed", "42"],
"api": ["/data/venvs/deepanalyze-phase1/bin/python", str(ROOT / "scripts/launch/phase1_api.py")]
}
print(json.dumps(commands, indent=2))
if args.execute:
    OUT.mkdir(parents=True, exist_ok=True)
    procs = {}
    for name, cmd in commands.items():
        env = dict(os.environ, CUDA_VISIBLE_DEVICES="0", MPLBACKEND="Agg", VLLM_USE_V1="0")
        with (OUT / (name + ".log")).open("a") as log:
            p = subprocess.Popen(cmd, cwd=OUT, env=env, stdout=log, stderr=log,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
        procs[name] = {"pid":p.pid, "command":cmd}
    (OUT/"services.json").write_text(json.dumps(procs, indent=2))
    print(json.dumps(procs))
