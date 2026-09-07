"""Replay genuine executor feedback to the real model and observe its next actions."""
import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/phase-02-agent-loop"
OUT = ROOT / "artifacts/phase2"
CONFIG = json.loads((LAB / "configs/fault-injection.json").read_text())
sys.path.insert(0, str(ROOT / "DeepAnalyze/API"))

from utils import execute_code_safe, extract_code_from_segment


def run_case(name, user_prompt, failed_code, failed_timeout, followup_timeout=5):
    target = OUT / "feedback-replay" / name
    workspace = target / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    feedback = execute_code_safe(failed_code, str(workspace), timeout_sec=failed_timeout)
    messages = [
        {"role": "user", "content": user_prompt},
        {"role": "assistant", "content": f"<Code>{failed_code}</Code>"},
        {"role": "execute", "content": feedback},
    ]
    trace = [f"<Code>{failed_code}</Code>", f"<Execute>\n{feedback}\n</Execute>"]
    records = []
    for round_index in range(CONFIG["max_rounds"]):
        payload = {
            "model": CONFIG["model"],
            "messages": messages,
            "temperature": CONFIG["temperature"],
            "max_tokens": 2048,
            "add_generation_prompt": False,
            "stop": ["</Code>"],
        }
        response = requests.post(
            CONFIG["api_url"], json=payload, timeout=CONFIG["request_timeout_seconds"]
        )
        response.raise_for_status()
        body = response.json()
        answer = body["choices"][0]["message"]["content"]
        if body["choices"][0].get("stop_reason") == "</Code>":
            answer += "</Code>"
        trace.append(answer)
        record = {"round": round_index + 1, "assistant": answer}
        records.append(record)
        if "<Answer>" in answer:
            break
        messages.append({"role": "assistant", "content": answer})
        code = extract_code_from_segment(answer)
        if code:
            output = execute_code_safe(code, str(workspace), timeout_sec=followup_timeout)
            messages.append({"role": "execute", "content": output})
            trace.append(f"<Execute>\n{output}\n</Execute>")
            record["execute"] = output
    reasoning = "\n".join(trace)
    (target / "reasoning.txt").write_text(reasoning)
    (target / "rounds.json").write_text(json.dumps(records, indent=2, ensure_ascii=False))
    return {"feedback": feedback, "reasoning": reasoning, "records": records}


def contains_execute_value(records, value):
    return any(re.search(rf"(^|\D){value}(\D|$)", str(r.get("execute", ""))) for r in records)


def main():
    missing = run_case(
        "missing-file",
        "The previous file read failed. Use the execution feedback as evidence. Do not invent rows "
        "or values. Return <Answer> with JSON status insufficient_data and "
        "missing_file definitely_missing_phase2.csv.",
        "import pandas as pd\npd.read_csv('definitely_missing_phase2.csv')",
        5,
    )
    name_error = run_case(
        "name-error",
        "The previous code failed. Read the execution feedback, then run new bounded Python code "
        "that prints sum([2, 3]). After successful execution return "
        '<Answer>{"recovered": true, "result": 5}</Answer>.',
        "print(phase2_undefined_name)",
        5,
    )
    timeout = run_case(
        "timeout",
        "The previous computation timed out. Read the execution feedback, then run new bounded "
        "Python code using sum(range(5)). After successful execution return "
        '<Answer>{"recovered": true, "result": 10}</Answer>.',
        "import time\ntime.sleep(5)\nprint('late')",
        CONFIG["executor_timeout_probe_seconds"],
    )

    tasks = [
        {
            "task": "missing-file-feedback",
            "checks": {
                "genuine_file_not_found": "FileNotFoundError" in missing["feedback"],
                "feedback_sent_as_execute_role": True,
                "reports_insufficient_data": "insufficient_data" in missing["reasoning"],
                "preserves_filename": "definitely_missing_phase2.csv" in missing["reasoning"],
                "has_final_answer": "<Answer>" in missing["reasoning"],
            },
            "generated_rounds": len(missing["records"]),
        },
        {
            "task": "name-error-feedback",
            "checks": {
                "genuine_name_error": "NameError" in name_error["feedback"],
                "feedback_sent_as_execute_role": True,
                "successful_followup_value": contains_execute_value(name_error["records"], 5),
                "reports_recovered": '"recovered": true' in name_error["reasoning"],
                "has_final_answer": "<Answer>" in name_error["reasoning"],
            },
            "generated_rounds": len(name_error["records"]),
        },
        {
            "task": "timeout-feedback",
            "checks": {
                "genuine_timeout": timeout["feedback"] == "[Timeout]: execution exceeded 1 seconds",
                "feedback_sent_as_execute_role": True,
                "successful_followup_value": contains_execute_value(timeout["records"], 10),
                "reports_recovered": '"recovered": true' in timeout["reasoning"],
                "has_final_answer": "<Answer>" in timeout["reasoning"],
            },
            "generated_rounds": len(timeout["records"]),
        },
    ]
    for task in tasks:
        task["status"] = "passed" if all(task["checks"].values()) else "failed"
    result = {
        "scope": "genuine executor feedback replayed once per task to the real model; not a benchmark",
        "model_revision": "214c302cebc61ed92f9c856a3dd47a7fdc588d5f",
        "tasks": tasks,
        "passed": sum(t["status"] == "passed" for t in tasks),
        "failed": sum(t["status"] == "failed" for t in tasks),
    }
    (OUT / "feedback-replay-results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
