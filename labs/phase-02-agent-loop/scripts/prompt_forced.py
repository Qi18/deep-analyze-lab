"""Prompt-driven fault induction; strict verification requires real Code/Execute blocks."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/phase-02-agent-loop"
OUT = ROOT / "artifacts/phase2"
CONFIG = json.loads((LAB / "configs/fault-injection.json").read_text())
sys.path.insert(0, str(ROOT / "DeepAnalyze"))

from deepanalyze import DeepAnalyzeVLLM


TASKS = {
    "missing-file": {
        "prompt": "This is a controlled missing-file test. In the first Code action, use pandas to "
                  "read definitely_missing_phase2.csv. After receiving the real execution error, "
                  "do not invent data. Return an Answer JSON with status insufficient_data and "
                  "missing_file definitely_missing_phase2.csv.",
        "required_error": "FileNotFoundError",
        "claimed_text": "insufficient_data",
    },
    "name-error": {
        "prompt": "This is a controlled recovery test. The first Code action must execute "
                  "print(phase2_undefined_name). After receiving the real error, run valid Python "
                  "that prints sum([2, 3]), then return an Answer JSON with recovered true and result 5.",
        "required_error": "NameError",
        "claimed_text": "recovered",
    },
}


def blocks(tag, text):
    return re.findall(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)


def execute_task(name, prompt):
    target = OUT / name
    workspace = target / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    client = DeepAnalyzeVLLM(
        CONFIG["model"], api_url=CONFIG["api_url"], max_rounds=CONFIG["max_rounds"]
    )
    reasoning = client.generate(
        prompt, str(workspace), temperature=CONFIG["temperature"],
        max_tokens=CONFIG["max_tokens"]
    )["reasoning"]
    (target / "reasoning.txt").write_text(reasoning)


def verify_task(name, spec):
    reasoning = (OUT / name / "reasoning.txt").read_text()
    code = blocks("Code", reasoning)
    execute = blocks("Execute", reasoning)
    answer = blocks("Answer", reasoning)
    checks = {
        "has_code_action": bool(code),
        "has_execute_feedback": bool(execute),
        "required_error_in_execute_feedback": any(spec["required_error"] in item for item in execute),
        "has_final_answer": bool(answer),
        "answer_claims_requested_result": spec["claimed_text"] in answer[-1] if answer else False,
    }
    return {
        "task": f"prompt-forced-{name}",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "finding": "Mentions in analysis do not count as execution evidence.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.execute:
        for name, spec in TASKS.items():
            execute_task(name, spec["prompt"])
    results = [verify_task(name, spec) for name, spec in TASKS.items()]
    payload = {
        "scope": "two prompt-forced tasks, one run each; strict action evidence required",
        "tasks": results,
        "passed": sum(item["status"] == "passed" for item in results),
        "failed": sum(item["status"] == "failed" for item in results),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "prompt-forced-results.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False)
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
