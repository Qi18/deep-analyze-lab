"""Strict Phase 2 verification: require evidence inside actual Code/Execute blocks."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/phase2"


def load(path):
    return json.loads(path.read_text())


def blocks(tag, text):
    return re.findall(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)


def prompt_forced(name, required_error, claimed_text):
    reasoning = (OUT / name / "reasoning.txt").read_text()
    code = blocks("Code", reasoning)
    execute = blocks("Execute", reasoning)
    answer = blocks("Answer", reasoning)
    checks = {
        "has_code_action": bool(code),
        "has_execute_feedback": bool(execute),
        "required_error_in_execute_feedback": any(required_error in item for item in execute),
        "has_final_answer": bool(answer),
        "answer_claims_requested_result": claimed_text in answer[-1] if answer else False,
    }
    return {
        "task": f"prompt-forced-{name}",
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "finding": "Mentions in analysis do not count as execution evidence.",
    }


def main():
    contracts = load(OUT / "runtime-contracts.json")
    replay = load(OUT / "feedback-replay-results.json")
    prompt_tasks = [
        prompt_forced("missing-file", "FileNotFoundError", "insufficient_data"),
        prompt_forced("name-error", "NameError", '"recovered": true'),
    ]
    result = {
        "phase_status": "completed",
        "scope": "runtime contracts, two prompt-forced attempts, and three genuine-feedback replays",
        "runtime_contracts": {
            "status": contracts["status"],
            "section_count": len(contracts["sections"]),
        },
        "prompt_forced_tasks": prompt_tasks,
        "feedback_replay": replay,
        "key_findings": [
            "CLI stop_reason </Code> is reclosed before extracting and executing code.",
            "Execution output is appended to the next request with role=execute.",
            "CLI max_rounds may finish without an Answer and exposes no explicit incomplete flag.",
            "An Answer substring terminates the CLI loop before a Code block in the same response is executed.",
            "API execution uses a fresh subprocess and timeout; normal Python failures are stderr without an [Error] prefix.",
            "Prompt text that describes an expected error can produce unsupported recovery claims without any Code or Execute action.",
        ],
        "upstream_modified": subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--", "DeepAnalyze"]
        ).returncode != 0,
    }
    (OUT / "phase2-results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    required = (
        contracts["status"] == "passed"
        and replay["passed"] == 3
        and all(task["status"] == "failed" for task in prompt_tasks)
        and not result["upstream_modified"]
    )
    raise SystemExit(0 if required else 1)


if __name__ == "__main__":
    main()
