#!/usr/bin/env python3
"""Build a deterministic, structurally valid smoke subset from a large JSON array."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from audit_training_data import iter_json_array, validate_tags


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--count", type=int, default=32)
    parser.add_argument("--max-total-tokens", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    reservoir: list[tuple[int, dict]] = []
    eligible = 0
    scanned = 0
    skipped_malformed = 0
    skipped_length = 0

    for row, record in enumerate(iter_json_array(args.input)):
        scanned += 1
        messages = record.get("messages")
        if not isinstance(messages, list) or len(messages) != 2:
            skipped_malformed += 1
            continue
        assistant = messages[1].get("content") if isinstance(messages[1], dict) else None
        if not isinstance(assistant, str) or not validate_tags(assistant)[1]:
            skipped_malformed += 1
            continue
        if not isinstance(record.get("total_tokens"), int) or record["total_tokens"] > args.max_total_tokens:
            skipped_length += 1
            continue

        eligible += 1
        candidate = (row, record)
        if len(reservoir) < args.count:
            reservoir.append(candidate)
        else:
            index = rng.randrange(eligible)
            if index < args.count:
                reservoir[index] = candidate

    if len(reservoir) != args.count:
        raise RuntimeError(f"requested {args.count} records, found {len(reservoir)}")

    reservoir.sort(key=lambda item: item[0])
    records = [record for _, record in reservoir]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    manifest = {
        "source": str(args.input),
        "source_rows_scanned": scanned,
        "eligible_rows": eligible,
        "skipped_malformed_action_tags": skipped_malformed,
        "skipped_over_token_limit": skipped_length,
        "selection": "reservoir sampling over eligible rows",
        "seed": args.seed,
        "count": args.count,
        "max_total_tokens": args.max_total_tokens,
        "selected_source_rows": [row for row, _ in reservoir],
        "selected_ids": [record.get("id") for record in records],
        "output": str(args.output),
        "output_sha256": digest,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
