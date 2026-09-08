#!/usr/bin/env python3
"""Prepare an explicit Phase 5 data version from the official single.sh list."""
import argparse, gzip, hashlib, json, random, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "labs/phase-04-training-data/scripts"))
from audit_training_data import iter_json_array, hash_file, validate_tags

def normalized(text):
    return " ".join(text.split())

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--output", type=Path, default=ROOT / "artifacts/phase5/data")
    args = p.parse_args()
    paths = re.findall(r'\$\{DATA_DIR\}/(reasoning/[^"]+\.json)', (ROOT / "DeepAnalyze/scripts/single.sh").read_text())
    assert len(paths) == 13, paths
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output / "single-clean-v1.jsonl"
    assert not output.exists(), "Use a fresh output directory to preserve data versions"
    benchmark = ROOT / "DeepAnalyze/playground/DS-1000/data/ds1000.jsonl.gz"
    with gzip.open(benchmark, "rt") as f:
        benchmark_rows = [json.loads(line) for line in f if line.strip()]
    assert len(benchmark_rows) == 1000
    prompts = {normalized(row["prompt"]) for row in benchmark_rows}
    seen = set()
    rng = random.Random(42)
    smoke, summaries, count, eligible = [], [], 0, 0
    with output.open("w") as dest:
        for rel in paths:
            source = args.data_root / rel
            stats = dict(source=rel, sha256=hash_file(source), bytes=source.stat().st_size,
                         raw=0, malformed=0, duplicate=0, exact_benchmark_prompt=0,
                         invalid_tokens=0, over_metadata_8192=0, kept=0)
            for row, record in enumerate(iter_json_array(source)):
                stats["raw"] += 1
                messages = record.get("messages", [])
                if (len(messages) != 2 or any(not isinstance(m, dict) for m in messages)
                    or [m.get("role") for m in messages] != ["user", "assistant"]
                    or any(not isinstance(m.get("content"), str) or not m["content"].strip() for m in messages)
                    or not validate_tags(messages[-1]["content"])[1]):
                    stats["malformed"] += 1
                    continue
                if normalized(messages[0]["content"]) in prompts:
                    stats["exact_benchmark_prompt"] += 1
                    continue
                total = record.get("total_tokens")
                if not isinstance(total, int) or total <= 0:
                    stats["invalid_tokens"] += 1
                    continue
                if total > 8192:
                    stats["over_metadata_8192"] += 1
                    continue
                digest = hashlib.sha256(json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()).digest()
                if digest in seen:
                    stats["duplicate"] += 1
                    continue
                seen.add(digest)
                clean = {"messages": messages}
                dest.write(json.dumps(clean, ensure_ascii=False) + "\n")
                stats["kept"] += 1
                count += 1
                if total <= 2048:
                    eligible += 1
                    item = ({"source": rel, "source_row": row, "source_id": record.get("id")}, clean)
                    if len(smoke) < 96:
                        smoke.append(item)
                    else:
                        index = rng.randrange(eligible)
                        if index < 96:
                            smoke[index] = item
            assert stats["raw"] == int(re.search(r"_(\d+)\.json$", rel).group(1)), stats
            assert stats["raw"] == sum(stats[k] for k in ("malformed", "duplicate", "exact_benchmark_prompt", "invalid_tokens", "over_metadata_8192", "kept"))
            summaries.append(stats)
            print(json.dumps(stats), flush=True)
    assert sum(s["raw"] for s in summaries) == 421060
    smoke_path = args.output / "smoke-96.jsonl"
    smoke_path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for _, item in smoke))
    manifest = dict(
        dataset_revision="f2dd0a62927f49f0a1d2465e32dc4072910e7c89",
        source_script="DeepAnalyze/scripts/single.sh",
        source_script_sha256=hash_file(ROOT / "DeepAnalyze/scripts/single.sh"),
        policy="clean-v1: schema and line-start tags, exact benchmark user prompt exclusion, metadata length <=8192, exact conversation dedup; first occurrence retained",
        benchmark_check="Normalized full user prompt equality only; no semantic/decontamination guarantee. Gold answers and reference code never enter training outputs.",
        benchmark_sha256=hash_file(benchmark),
        tokenizer_limit_note="Metadata tokens are a prefilter; ms-swift must additionally delete samples exceeding actual templated max_length.",
        files=summaries, records=count, output=str(output), sha256=hash_file(output),
        smoke=dict(count=len(smoke), seed=42, max_metadata_tokens=2048, eligible=eligible,
                   output=str(smoke_path), sha256=hash_file(smoke_path), rows=[ref for ref, _ in smoke]))
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"records": count, "output": str(output), "sha256": manifest["sha256"]}), flush=True)

if __name__ == "__main__":
    main()
