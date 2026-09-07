"""Deterministic Phase 2 tests for the upstream host loop and API executor."""
import json
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "artifacts/phase2"
sys.path.insert(0, str(ROOT / "DeepAnalyze"))
sys.path.insert(0, str(ROOT / "DeepAnalyze/API"))

from deepanalyze import DeepAnalyzeVLLM
from utils import execute_code_safe


class ScriptedHandler(BaseHTTPRequestHandler):
    responses = []
    requests = []

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(size))
        type(self).requests.append(payload)
        scripted = type(self).responses.pop(0)
        body = json.dumps({"choices": [{"message": {"content": scripted["content"]},
                                        "stop_reason": scripted.get("stop_reason")}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


def run_scripted(responses, max_rounds, workspace):
    handler = type("PerTestHandler", (ScriptedHandler,), {
        "responses": list(responses),
        "requests": [],
    })
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = DeepAnalyzeVLLM(
            "scripted-model",
            api_url=f"http://127.0.0.1:{server.server_port}/v1/chat/completions",
            max_rounds=max_rounds,
        )
        result = client.generate("phase2 contract test", str(workspace), temperature=0, max_tokens=256)
        return result["reasoning"], handler.requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="phase2-contract-", dir=OUT) as tmp:
        workspace = Path(tmp)

        recovery_reasoning, recovery_requests = run_scripted([
            {"content": "<Analyze>Run a controlled failure.</Analyze>"},
            {"content": "<Code>print(phase2_undefined_name)", "stop_reason": "</Code>"},
            {"content": "<Code>print(sum([2, 3]))", "stop_reason": "</Code>"},
            {"content": '<Answer>{"recovered": true, "result": 5}</Answer>'},
        ], 6, workspace)
        recovery_checks = {
            "stop_parameter_sent": all(r["stop"] == ["</Code>"] for r in recovery_requests),
            "stop_reason_reclosed_code": "</Code>" in recovery_requests[2]["messages"][-2]["content"],
            "error_feedback_role_execute": recovery_requests[2]["messages"][-1]["role"] == "execute",
            "error_feedback_contains_name_error": "NameError" in recovery_requests[2]["messages"][-1]["content"],
            "success_feedback_role_execute": recovery_requests[3]["messages"][-1]["role"] == "execute",
            "success_feedback_contains_5": recovery_requests[3]["messages"][-1]["content"].strip() == "5",
            "final_answer_present": "<Answer>" in recovery_reasoning,
        }

        capped_reasoning, capped_requests = run_scripted([
            {"content": "<Analyze>step one</Analyze>"},
            {"content": "<Analyze>step two</Analyze>"},
        ], 2, workspace)
        cap_checks = {
            "exactly_two_requests": len(capped_requests) == 2,
            "no_answer_after_cap": "<Answer>" not in capped_reasoning,
        }

        side_effect = workspace / "answer_precedence_should_not_exist.txt"
        answer_reasoning, answer_requests = run_scripted([{
            "content": f'<Code>open("{side_effect.name}", "w").write("bad")</Code>'
                       '<Answer>{"done": true}</Answer>'
        }], 2, workspace)
        answer_checks = {
            "single_request": len(answer_requests) == 1,
            "answer_terminates_before_code_execution": not side_effect.exists(),
            "answer_preserved": "<Answer>" in answer_reasoning,
        }

        executor_workspace = workspace / "executor"
        executor_workspace.mkdir()
        success = execute_code_safe("print(6 * 7)", str(executor_workspace), timeout_sec=2)
        failure = execute_code_safe("print(phase2_missing_name)", str(executor_workspace), timeout_sec=2)
        execute_code_safe("phase2_state = 7", str(executor_workspace), timeout_sec=2)
        isolated = execute_code_safe("print(phase2_state)", str(executor_workspace), timeout_sec=2)
        started = time.monotonic()
        timeout_output = execute_code_safe(
            "import time\ntime.sleep(5)\nprint('late')",
            str(executor_workspace),
            timeout_sec=1,
        )
        timeout_elapsed = time.monotonic() - started
        executor_checks = {
            "success_stdout": success.strip() == "42",
            "exception_returned_as_stderr": "NameError" in failure,
            "exception_not_prefixed_error": not failure.startswith("[Error]"),
            "fresh_process_loses_state": "NameError" in isolated,
            "timeout_marker": timeout_output == "[Timeout]: execution exceeded 1 seconds",
            "timeout_is_bounded": timeout_elapsed < 3,
            "temporary_scripts_removed": not list(executor_workspace.glob("tmp*.py")),
        }

    sections = {
        "scripted_recovery": {"checks": recovery_checks, "reasoning": recovery_reasoning,
                              "request_count": len(recovery_requests)},
        "max_round_cap": {"checks": cap_checks, "reasoning": capped_reasoning,
                          "request_count": len(capped_requests)},
        "answer_precedence": {"checks": answer_checks, "reasoning": answer_reasoning},
        "api_executor": {"checks": executor_checks, "outputs": {
            "success": success,
            "failure": failure,
            "isolated_second_call": isolated,
            "timeout": timeout_output,
            "timeout_elapsed_seconds": round(timeout_elapsed, 3),
        }},
    }
    checks = [value for section in sections.values() for value in section["checks"].values()]
    result = {"status": "passed" if all(checks) else "failed", "sections": sections}
    (OUT / "runtime-contracts.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if all(checks) else 1)


if __name__ == "__main__":
    main()
