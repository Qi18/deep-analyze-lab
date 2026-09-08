#!/usr/bin/env python3
"""Collect small, shareable Phase 5 run summaries from the retained raw artifacts."""
import argparse, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=ROOT / "labs/phase-05-single-sft/results/metrics.json")
    args = p.parse_args()
    manifest = json.loads((ROOT / "artifacts/phase5/data/manifest.json").read_text())
    result = {
        "stage": "phase-05", "status": "in_progress",
        "base_revision": "6e8885a6ff5c1dc5201574c8fd700323f23c25fa",
        "data_revision": manifest["dataset_revision"],
        "clean_data_sha256": manifest["sha256"],
        "data_totals": {k: sum(s[k] for s in manifest["files"]) for k in
                        ["raw", "malformed", "duplicate", "exact_benchmark_prompt", "over_metadata_8192", "kept"]},
        "scope": "8B training preflight; DS-1000 post-training evaluation remains pending",
        "runs": []
    }
    for name in ["smoke-2048", "smoke-8192", "smoke-8192-liger", "pilot-100"]:
        for run in sorted((ROOT / "artifacts/phase5" / name).glob("v*")):
            item = {"run": str(run.relative_to(ROOT))}
            config = run / "args.json"
            if config.exists():
                a = json.loads(config.read_text())
                item["config"] = {k:a.get(k) for k in ["model", "model_type", "template", "dataset",
                  "train_type", "max_length", "max_steps", "num_train_epochs", "per_device_train_batch_size",
                  "gradient_accumulation_steps", "learning_rate", "use_liger_kernel", "truncation_strategy"]}
            log = run / "logging.jsonl"
            if log.exists():
                logs = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
                item["training_metrics"] = [m for m in logs if "loss" in m or "train_loss" in m]
            checkpoints = list(run.glob("checkpoint-*/trainer_state.json"))
            item["checkpoint_states"] = []
            for cp in sorted(checkpoints):
                state = json.loads(cp.read_text())
                item["checkpoint_states"].append({"path": str(cp.parent.relative_to(ROOT)),
                   "global_step": state["global_step"], "epoch":state.get("epoch")})
            raw = ROOT / "artifacts/phase5/logs" / (name + ".log")
            if raw.exists():
                text = raw.read_text(errors="replace")
                item["oom_observed"] = "CUDA out of memory" in text
                item["completed_in_log"] = "End time of running main:" in text
                item["dataset_token_stats"] = re.findall(r"Dataset Token Length: ([^\n]+)", text)
                item["masked_prompt_example_lengths"] = re.findall(r"\[LABELS\] \[-100 \* (\d+)\]", text)
            result["runs"].append(item)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output":str(args.output), "runs":len(result["runs"]), "data_totals":result["data_totals"]}))
if __name__ == "__main__":
    main()
