#!/usr/bin/env python3
"""Reject generated DS-1000 code with host/network/process access primitives."""

import argparse
import json
import re
from pathlib import Path

BLOCKING_TOKENS = {
    "sensitive_path": (
        "/proc", "/data", "/root", "/home", "/etc", "/var/run/secrets",
        ".ssh", "serviceaccount",
    ),
    "network": (
        "socket", "requests", "urllib", "http.client", "ftplib", "paramiko",
    ),
    "process": (
        "subprocess", "os.system", "os.popen", "import pty", "from pty", "fork(", "execv(",
        "spawn(",
    ),
    "destructive": (
        "rmtree(", "unlink(", "remove(", "removedirs(", "rmdir(",
    ),
}
DYNAMIC_TOKENS = ("eval(", "exec(", "compile(", "__import__(", "ctypes")


def last_python_block(response):
    blocks = re.findall(r"```python.*?```", response, flags=re.DOTALL)
    return blocks[-1].lower() if blocks else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", type=Path, required=True)
    args = parser.parse_args()

    records = [json.loads(line) for line in args.answers.read_text().splitlines()]
    blocking = {name: [] for name in BLOCKING_TOKENS}
    dynamic = []
    missing = []
    for item in records:
        problem_id = int(item["metadata"]["problem_id"])
        code = last_python_block(item["response"])
        if code is None:
            missing.append(problem_id)
            continue
        for name, tokens in BLOCKING_TOKENS.items():
            if any(token in code for token in tokens):
                blocking[name].append(problem_id)
        if any(token in code for token in DYNAMIC_TOKENS):
            dynamic.append(problem_id)

    blocking = {name: ids for name, ids in blocking.items() if ids}
    result = {
        "answers": str(args.answers),
        "records": len(records),
        "python_blocks": len(records) - len(missing),
        "missing_python_block": missing,
        "blocking_hits": blocking,
        "dynamic_eval_review": dynamic,
        "passed": not blocking,
    }
    print(json.dumps(result, indent=2))
    if blocking:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
