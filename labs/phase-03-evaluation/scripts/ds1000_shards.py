"""Shard DS-1000 inference across GPUs while preserving official prompts and scoring."""
import argparse
import gzip
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/phase-03-evaluation"
CONFIG = json.loads((LAB / "configs/official-benchmarks.json").read_text())
SOURCE = ROOT / CONFIG["ds1000"]["upstream_dir"]
MAIN_WORK = ROOT / "artifacts/phase3/official-eval/DS-1000"
SHARD_ROOT = ROOT / "artifacts/phase3/official-eval/DS-1000-shards"
PYTHON = Path("/data/venvs/tesla-vllm-085/bin/python")


def load_tasks(path):
    with gzip.open(path, "rt") as handle:
        return [json.loads(line) for line in handle]


def count_lines(path):
    if not path.exists():
        return 0
    with path.open() as handle:
        return sum(1 for line in handle if line.strip())


def ranges(start, stop, count):
    size, remainder = divmod(stop - start, count)
    result = []
    cursor = start
    for index in range(count):
        end = cursor + size + (1 if index < remainder else 0)
        result.append((cursor, end))
        cursor = end
    return result


def prepare(model, start, gpus):
    tasks = load_tasks(SOURCE / "data/ds1000.jsonl.gz")
    model_path = Path(CONFIG["models"][model]["path"])
    SHARD_ROOT.mkdir(parents=True, exist_ok=True)
    records = []
    for index, ((begin, end), gpu) in enumerate(zip(ranges(start, len(tasks), len(gpus)), gpus)):
        work = SHARD_ROOT / f"{model}-{index:02d}"
        if not work.exists():
            shutil.copytree(SOURCE, work)
            with gzip.open(work / "data/ds1000.jsonl.gz", "wt") as handle:
                for task in tasks[begin:end]:
                    handle.write(json.dumps(task) + "\n")
        output = work / "data" / f"{model}-answers.jsonl"
        log_path = work / f"{model}-infer.log"
        command = [
            str(PYTHON), "run_deepanalyze.py",
            "--model", str(model_path), "--model_name", model, "--resume",
        ]
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu))
        with log_path.open("a") as log:
            process = subprocess.Popen(
                command, cwd=work, env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
        records.append({
            "index": index, "begin": begin, "end": end, "gpu": gpu,
            "pid": process.pid, "workdir": str(work), "output": str(output),
        })
    manifest = {"model": model, "start": start, "stop": len(tasks), "shards": records}
    (SHARD_ROOT / f"{model}-manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def read_manifest(model):
    return json.loads((SHARD_ROOT / f"{model}-manifest.json").read_text())


def status(model):
    manifest = read_manifest(model)
    for shard in manifest["shards"]:
        shard["completed"] = count_lines(Path(shard["output"]))
        shard["expected"] = shard["end"] - shard["begin"]
    return manifest


def merge(model):
    manifest = status(model)
    records = {}
    prefix = MAIN_WORK / "data" / f"{model}-answers.jsonl"
    if prefix.exists():
        with prefix.open() as handle:
            for line in handle:
                item = json.loads(line)
                problem_id = int(item["metadata"]["problem_id"])
                if problem_id < manifest["start"]:
                    records[problem_id] = item
    for shard in manifest["shards"]:
        if shard["completed"] != shard["expected"]:
            raise RuntimeError(f"Shard incomplete: {shard}")
        with Path(shard["output"]).open() as handle:
            for line in handle:
                item = json.loads(line)
                records[int(item["metadata"]["problem_id"])] = item
    expected_ids = list(range(CONFIG["ds1000"]["task_count"]))
    if sorted(records) != expected_ids:
        missing = sorted(set(expected_ids) - set(records))
        raise RuntimeError(f"Missing problem ids: {missing[:20]}")
    with prefix.open("w") as handle:
        for problem_id in expected_ids:
            item = records[problem_id]
            item["id"] = problem_id
            handle.write(json.dumps(item) + "\n")
    return {"model": model, "merged": len(records), "output": str(prefix)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["launch", "status", "merge"])
    parser.add_argument("--model", default="base8b", choices=sorted(CONFIG["models"]))
    parser.add_argument("--start", type=int, default=128)
    parser.add_argument("--gpus", default="4,5,6,7")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.action in {"launch", "merge"} and not args.execute:
        raise SystemExit("Dry run only; add --execute")
    if args.action == "launch":
        gpus = [int(item) for item in args.gpus.split(",")]
        print(json.dumps(prepare(args.model, args.start, gpus), indent=2))
    elif args.action == "status":
        print(json.dumps(status(args.model), indent=2))
    else:
        print(json.dumps(merge(args.model), indent=2))


if __name__ == "__main__":
    main()
