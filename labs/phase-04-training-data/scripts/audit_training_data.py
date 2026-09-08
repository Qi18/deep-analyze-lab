#!/usr/bin/env python3
"""Stream-audit the official DeepAnalyze curriculum datasets.

The input files are multi-gigabyte JSON arrays.  This script intentionally uses
the standard library and never loads a complete dataset into memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterator


ACTIONS = ("Analyze", "Understand", "Code", "Execute", "Answer")
TAG_RE = re.compile(r"^[ \t]*<(/?)(Analyze|Understand|Code|Execute|Answer)>", re.MULTILINE)
MAX_ERROR_EXAMPLES = 20


def iter_json_array(path: Path, chunk_size: int = 4 * 1024 * 1024) -> Iterator[dict[str, Any]]:
    """Yield objects from a top-level JSON array without loading the full file."""
    decoder = json.JSONDecoder()
    buffer = ""
    position = 0
    started = False
    eof = False

    with path.open("r", encoding="utf-8") as handle:
        while True:
            if position:
                buffer = buffer[position:]
                position = 0
            if not eof:
                chunk = handle.read(chunk_size)
                if chunk:
                    buffer += chunk
                else:
                    eof = True

            while position < len(buffer) and buffer[position].isspace():
                position += 1
            if not started:
                if position >= len(buffer):
                    if eof:
                        raise ValueError(f"{path}: empty JSON document")
                    continue
                if buffer[position] != "[":
                    raise ValueError(f"{path}: expected a top-level JSON array")
                started = True
                position += 1

            while True:
                while position < len(buffer) and (buffer[position].isspace() or buffer[position] == ","):
                    position += 1
                if position < len(buffer) and buffer[position] == "]":
                    return
                if position >= len(buffer):
                    if eof:
                        raise ValueError(f"{path}: unterminated JSON array")
                    break
                try:
                    item, end = decoder.raw_decode(buffer, position)
                except json.JSONDecodeError:
                    if eof:
                        raise
                    break
                if not isinstance(item, dict):
                    raise ValueError(f"{path}: expected object, got {type(item).__name__}")
                yield item
                position = end


def percentile(values: list[int], quantile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * quantile)
    return ordered[index]


def distribution(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "p50": None, "p90": None, "p95": None, "p99": None, "max": None, "mean": None}
    return {
        "count": len(values),
        "min": min(values),
        "p50": percentile(values, 0.50),
        "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": max(values),
        "mean": round(sum(values) / len(values), 2),
    }


def hash_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def add_example(errors: dict[str, list[int | str]], kind: str, record_id: int | str) -> None:
    examples = errors.setdefault(kind, [])
    if len(examples) < MAX_ERROR_EXAMPLES:
        examples.append(record_id)


def validate_tags(content: str) -> tuple[list[str], bool]:
    sequence: list[str] = []
    stack: list[str] = []
    valid = True
    for match in TAG_RE.finditer(content):
        closing, action = match.groups()
        if closing:
            if not stack or stack[-1] != action:
                valid = False
            else:
                stack.pop()
        else:
            sequence.append(action)
            if stack:
                valid = False
            stack.append(action)
    return sequence, valid and not stack


def audit(path: Path, name: str, expected_records: int, max_length: int) -> dict[str, Any]:
    ids: set[int | str] = set()
    hashes: set[bytes] = set()
    duplicate_records = 0
    duplicate_id_rows = 0
    non_sequential_id_rows = 0
    id_diagnostic_examples: list[dict[str, int | str]] = []
    previous_id: int | None = None
    input_tokens: list[int] = []
    output_tokens: list[int] = []
    total_tokens: list[int] = []
    user_chars: list[int] = []
    assistant_chars: list[int] = []
    key_sets: Counter[str] = Counter()
    role_sequences: Counter[str] = Counter()
    action_sequences: Counter[str] = Counter()
    action_record_counts: Counter[str] = Counter()
    errors: dict[str, list[int | str]] = {}
    error_counts: Counter[str] = Counter()
    records = 0
    tagged_records = 0
    python_fence_records = 0
    evaluation_present = 0
    over_limit = 0

    for record in iter_json_array(path):
        records += 1
        record_id = record.get("id", f"missing-{records}")
        record_ref = f"row={records - 1},id={record_id}"
        if record_id in ids:
            duplicate_id_rows += 1
        ids.add(record_id)
        if isinstance(record_id, int) and record_id != records - 1:
            non_sequential_id_rows += 1
        if isinstance(record_id, int):
            if previous_id is not None and record_id <= previous_id and len(id_diagnostic_examples) < MAX_ERROR_EXAMPLES:
                id_diagnostic_examples.append({"row": records - 1, "previous_id": previous_id, "id": record_id})
            previous_id = record_id

        key_sets[",".join(sorted(record))] += 1
        messages = record.get("messages")
        if not isinstance(messages, list):
            error_counts["messages_not_list"] += 1
            add_example(errors, "messages_not_list", record_ref)
            continue
        roles = tuple(message.get("role") for message in messages if isinstance(message, dict))
        role_sequences["->".join(str(role) for role in roles)] += 1
        if roles != ("user", "assistant"):
            error_counts["unexpected_role_sequence"] += 1
            add_example(errors, "unexpected_role_sequence", record_ref)
        if len(messages) != 2 or any(not isinstance(message, dict) for message in messages):
            error_counts["unexpected_message_shape"] += 1
            add_example(errors, "unexpected_message_shape", record_ref)
            continue

        user = messages[0].get("content")
        assistant = messages[1].get("content")
        if not isinstance(user, str) or not isinstance(assistant, str) or not user or not assistant:
            error_counts["empty_or_non_string_content"] += 1
            add_example(errors, "empty_or_non_string_content", record_ref)
            continue
        user_chars.append(len(user))
        assistant_chars.append(len(assistant))
        digest = hashlib.sha256((user + "\0" + assistant).encode("utf-8")).digest()
        if digest in hashes:
            duplicate_records += 1
            add_example(errors, "duplicate_conversation", record_ref)
        hashes.add(digest)

        sequence, tags_valid = validate_tags(assistant)
        if sequence:
            tagged_records += 1
        if not tags_valid:
            error_counts["malformed_action_tags"] += 1
            add_example(errors, "malformed_action_tags", record_ref)
        action_sequences["->".join(sequence) if sequence else "<none>"] += 1
        for action in set(sequence):
            action_record_counts[action] += 1
        if "```python" in assistant.lower():
            python_fence_records += 1

        values: dict[str, int] = {}
        for field, destination in (("input_tokens", input_tokens), ("output_tokens", output_tokens), ("total_tokens", total_tokens)):
            value = record.get(field)
            if isinstance(value, int) and value >= 0:
                destination.append(value)
                values[field] = value
            else:
                error_counts[f"invalid_{field}"] += 1
                add_example(errors, f"invalid_{field}", record_ref)
        if len(values) == 3 and values["input_tokens"] + values["output_tokens"] != values["total_tokens"]:
            error_counts["token_sum_mismatch"] += 1
            add_example(errors, "token_sum_mismatch", record_ref)
        if values.get("total_tokens", 0) > max_length:
            over_limit += 1
        if "evaluation" in record:
            evaluation_present += 1

    if records != expected_records:
        error_counts["record_count_mismatch"] += 1
        add_example(errors, "record_count_mismatch", f"expected={expected_records},actual={records}")

    return {
        "name": name,
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": hash_file(path),
        "records": records,
        "expected_records": expected_records,
        "id_diagnostics": {
            "unique_values": len(ids),
            "duplicate_rows": duplicate_id_rows,
            "rows_not_equal_to_global_index": non_sequential_id_rows,
            "reset_or_decrease_examples": id_diagnostic_examples,
            "interpretation": "IDs are source-local metadata in aggregate files; row order is the training index.",
        },
        "duplicate_conversations": duplicate_records,
        "key_sets": dict(key_sets.most_common()),
        "role_sequences": dict(role_sequences.most_common()),
        "evaluation_present": evaluation_present,
        "token_lengths": {
            "input": distribution(input_tokens),
            "output": distribution(output_tokens),
            "total": distribution(total_tokens),
            "configured_max_length": max_length,
            "over_configured_max_length": over_limit,
            "over_configured_max_length_rate": round(over_limit / records, 6) if records else None,
        },
        "character_lengths": {"user": distribution(user_chars), "assistant": distribution(assistant_chars)},
        "action_tags": {
            "tagged_records": tagged_records,
            "untagged_records": records - tagged_records,
            "python_fence_records": python_fence_records,
            "records_by_action": {action: action_record_counts[action] for action in ACTIONS},
            "top_sequences": dict(action_sequences.most_common(20)),
        },
        "error_counts": dict(error_counts),
        "error_examples": errors,
        "passed_structural_checks": not error_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", type=Path, required=True)
    parser.add_argument("--multi", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = {
        "schema_version": 1,
        "datasets": {
            "single_ability": audit(args.single, "single_ability", 437398, 8192),
            "multi_ability": audit(args.multi, "multi_ability", 26202, 32768),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: {"records": data["records"], "errors": data["error_counts"]} for name, data in result["datasets"].items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
