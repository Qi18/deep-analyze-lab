"""Run the vendored official DS-1000 inference and evaluator without editing upstream."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/phase-03-evaluation"
CONFIG = json.loads((LAB / "configs/official-benchmarks.json").read_text())
SOURCE = ROOT / CONFIG["ds1000"]["upstream_dir"]
WORK = ROOT / "artifacts/phase3/official-eval/DS-1000"
INFER_PYTHON = Path("/data/venvs/tesla-vllm-085/bin/python")
EVAL_PYTHON = Path("/data/venvs/ds1000-eval/bin/python")
SANDBOX = LAB / "scripts/run_ds1000_sandbox.sh"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source():
    expected = {
        "data/ds1000.jsonl.gz": CONFIG["ds1000"]["dataset_sha256"],
        "run_deepanalyze.py": CONFIG["ds1000"]["inference_script_sha256"],
        "test_ds1000.py": CONFIG["ds1000"]["evaluator_sha256"],
        "execution.py": CONFIG["ds1000"]["execution_harness_sha256"],
    }
    for relative, digest in expected.items():
        actual = sha256(SOURCE / relative)
        if actual != digest:
            raise RuntimeError(f"Official file hash changed: {relative}: {actual}")


def prepare():
    verify_source()
    if not WORK.exists():
        shutil.copytree(SOURCE, WORK)
    return WORK


def model_spec(name):
    item = CONFIG["models"][name]
    return Path(item["path"]), name


def answer_path(name):
    return WORK / "data" / f"{name}-answers.jsonl"


def status(name):
    answers = answer_path(name)
    count = 0
    if answers.exists():
        with answers.open() as handle:
            count = sum(1 for line in handle if line.strip())
    result = WORK / "results" / f"{name}-result.txt"
    return {
        "model": name,
        "answers": count,
        "expected": CONFIG["ds1000"]["task_count"],
        "inference_complete": count == CONFIG["ds1000"]["task_count"],
        "evaluation_complete": result.exists(),
        "workdir": str(WORK),
    }


def infer(name, gpu):
    work = prepare()
    model_path, output_name = model_spec(name)
    command = [
        str(INFER_PYTHON), "run_deepanalyze.py",
        "--model", str(model_path), "--model_name", output_name, "--resume",
    ]
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu))
    with (work / f"{name}-infer.log").open("a") as log:
        subprocess.run(command, cwd=work, env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True)


def evaluate(name):
    work = prepare()
    if not EVAL_PYTHON.exists():
        raise RuntimeError(f"Create the official evaluation environment first: {EVAL_PYTHON}")
    if not status(name)["inference_complete"]:
        raise RuntimeError(f"Inference is incomplete for {name}")
    subprocess.run([str(SANDBOX), name], cwd=work, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "infer", "evaluate", "status"])
    parser.add_argument("--model", choices=sorted(CONFIG["models"]))
    parser.add_argument("--gpu", type=int)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.action in {"infer", "evaluate"} and not args.model:
        parser.error("--model is required")
    if args.action == "infer" and args.gpu is None:
        parser.error("--gpu is required for inference")
    if args.action in {"prepare", "infer", "evaluate"} and not args.execute:
        raise SystemExit("Dry run only; add --execute to mutate artifacts or run evaluation")

    if args.action == "prepare":
        print(prepare())
    elif args.action == "infer":
        infer(args.model, args.gpu)
        print(json.dumps(status(args.model), indent=2))
    elif args.action == "evaluate":
        evaluate(args.model)
        print(json.dumps(status(args.model), indent=2))
    elif args.model:
        print(json.dumps(status(args.model), indent=2))
    else:
        print(json.dumps({name: status(name) for name in sorted(CONFIG["models"])}, indent=2))


if __name__ == "__main__":
    main()
