#!/usr/bin/env python3
"""Validate official DS-1000 logs and write small, reviewable summaries."""

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LAB = ROOT / "labs/phase-03-evaluation"
RAW = ROOT / "artifacts/phase3/official-eval/DS-1000/results"
OUTPUT = LAB / "results"
CONFIG = json.loads((LAB / "configs/official-benchmarks.json").read_text())
MODELS = ("base8b", "deepanalyze8b")


def aggregate(records, field=None):
    groups = defaultdict(list)
    for item in records:
        groups[item[field] if field else "overall"].append(int(item["score"]))
    return {
        name: {
            "count": len(scores),
            "passed": sum(scores),
            "pass_rate": sum(scores) / len(scores),
        }
        for name, scores in sorted(groups.items())
    }


def load_model(name):
    path = RAW / f"{name}-log.json"
    records = json.loads(path.read_text())
    ids = [int(item["completion_id"]) for item in records]
    expected = list(range(CONFIG["ds1000"]["task_count"]))
    if sorted(ids) != expected or len(set(ids)) != len(ids):
        raise RuntimeError(f"{name}: expected each completion_id 0..999 exactly once")
    if any(int(item["score"]) not in (0, 1) for item in records):
        raise RuntimeError(f"{name}: score outside 0/1")
    return {
        "revision": CONFIG["models"][name]["revision"],
        "overall": aggregate(records)["overall"],
        "by_library": aggregate(records, "library"),
        "by_perturbation": aggregate(records, "perturbation_type"),
    }


def load_audit(name):
    path = RAW / f"{name}-audit.json"
    result = json.loads(path.read_text())
    if not result["passed"] or result["blocking_hits"]:
        raise RuntimeError(f"{name}: generated-code security audit did not pass")
    return {
        "records": result["records"],
        "python_blocks": result["python_blocks"],
        "missing_python_blocks": len(result["missing_python_block"]),
        "blocking_hits": result["blocking_hits"],
        "dynamic_eval_review": result["dynamic_eval_review"],
        "passed": result["passed"],
    }


def write_csv(results):
    with (OUTPUT / "metrics.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["model", "dimension", "category", "count", "passed", "pass_rate"])
        for model, metrics in results.items():
            for dimension in ("overall", "by_library", "by_perturbation"):
                values = metrics[dimension]
                if dimension == "overall":
                    values = {"overall": values}
                for category, item in values.items():
                    writer.writerow([
                        model, dimension, category, item["count"], item["passed"],
                        f'{item["pass_rate"]:.6f}',
                    ])


def comparison_rows(results, dimension):
    rows = []
    for category, base in results["base8b"][dimension].items():
        trained = results["deepanalyze8b"][dimension][category]
        delta = trained["pass_rate"] - base["pass_rate"]
        rows.append(
            f'| {category} | {base["pass_rate"]:.1%} | '
            f'{trained["pass_rate"]:.1%} | {delta * 100:+.1f} pp |'
        )
    return "\n".join(rows)


def write_report(results, audits):
    base = results["base8b"]["overall"]
    trained = results["deepanalyze8b"]["overall"]
    delta = trained["pass_rate"] - base["pass_rate"]
    delta_pp = delta * 100
    rows = []
    for name, label in (("base8b", "Base 8B"), ("deepanalyze8b", "DeepAnalyze-8B")):
        item = results[name]["overall"]
        rows.append(f'| {label} | {item["passed"]}/{item["count"]} | {item["pass_rate"]:.1%} |')
    report = f"""# Phase 3 实验报告：官方 DS-1000 基线

## 结论

两种模型均完成官方 DS-1000 全部 1000 题推理与执行评分。DeepAnalyze-8B 相对基础模型的 execution pass rate 绝对提升 {delta_pp:.1f} 个百分点（单次运行）。

| 模型 | 通过数 | execution pass rate |
|---|---:|---:|
{chr(10).join(rows)}

## 分库结果

| library | Base | DeepAnalyze-8B | 绝对差值 |
|---|---:|---:|---:|
{comparison_rows(results, "by_library")}

## 扰动类型结果

| perturbation | Base | DeepAnalyze-8B | 绝对差值 |
|---|---:|---:|---:|
{comparison_rows(results, "by_perturbation")}

## 协议与边界

- 上游源码 commit：`d14468b9ef91372359ddcd70da57e0e0f4eb0d1b`。
- 数据、推理脚本、评分器及 execution harness 的 SHA256 见 `../configs/official-benchmarks.json`。
- 两组模型使用相同的官方 prompt、代码抽取、生成参数和 `test_ds1000.py`。
- Base 先生成 128 题，余下 872 题按原始 problem_id 分到 4 张 GPU；合并后校验 0–999 各出现一次。分片只改变调度，不改变单题协议。
- 官方评分器未被修改；评分前静态审计最终 Python block，外层使用 user/mount/network namespace 禁网，遮蔽 `/data`、HOME、SSH 和 service-account 路径，并清空环境变量。
- L20 容器无法挂载独立 procfs，完全遮蔽 `/proc` 会使 TensorFlow 题崩溃；经用户明确批准，本次保留宿主 `/proc` 可见。审计确认 2000 条答案没有敏感路径、网络、进程或删除操作。
- DeepAnalyze-8B 有 {audits["deepanalyze8b"]["python_blocks"]}/1000 条答案包含 Python block，Base 为 {audits["base8b"]["python_blocks"]}/1000；缺失 block 按官方后处理转为空代码，不人工修补。
- 这是单次、temperature=0 的基线，不提供跨 seed 方差。

## 能说明什么

DS-1000 衡量给定代码上下文后的数据科学代码执行正确性。它不能证明模型具备多文件发现、长程 Agent 恢复或报告证据引用能力；这些能力应由 CoDA-Bench 和补充工程回归分别验证。

## 可追溯产物

- `metrics.json`：完整 overall、library 与 perturbation 聚合结果。
- `metrics.csv`：便于绘图和阶段对比的长表。
- 原始 1000 条答案与逐题执行日志保存在 L20 的 Git 忽略目录 `artifacts/phase3/official-eval/DS-1000/`，不提交生成内容。
"""
    (OUTPUT / "report.md").write_text(report)


def main():
    results = {name: load_model(name) for name in MODELS}
    audits = {name: load_audit(name) for name in MODELS}
    payload = {
        "phase_status": "completed",
        "benchmark": "DS-1000",
        "task_count": CONFIG["ds1000"]["task_count"],
        "metric": CONFIG["ds1000"]["metric"],
        "run_count": 1,
        "absolute_improvement_percentage_points": round(
            (results["deepanalyze8b"]["overall"]["pass_rate"]
             - results["base8b"]["overall"]["pass_rate"]) * 100,
            1,
        ),
        "models": results,
        "security_audit": audits,
    }
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n")
    write_csv(results)
    write_report(results, audits)
    print(json.dumps({name: value["overall"] for name, value in results.items()}, indent=2))


if __name__ == "__main__":
    main()
