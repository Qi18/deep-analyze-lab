# Phase 4：数据与训练准备

状态：completed

## 学习目标

理解 Action Token、assistant 标签掩码、训练数据格式与上游 SFT 入口，并在 L20 上完成最小训练验证。

## 已完成

- 固定并审计 DataScience-Instruct-500K 数据 revision，共 463,600 条聚合记录。
- 对照上游单能力与多能力训练脚本，记录数据清单和参数。
- 验证 10 个 Action 标签扩展为独立 token。
- 构造 seed 42 的 32 条 smoke subset，人工抽查 8 条结构。
- 使用 Qwen3-0.6B 完成 2-step 全参数 SFT、checkpoint 保存和推理。
- 保留训练前失败和错误推理，不把链路验证写成能力提升。

## 关键结果

| 项目 | 结果 |
|---|---|
| 单能力数据 | 437,398 条；1,838 条精确重复；7,370 条 Action 语法异常；5.139% 超过 8,192 tokens |
| 多能力数据 | 26,202 条；0 条精确重复；64 条 Action 语法异常；1.153% 超过 32,768 tokens |
| 官方单能力口径 | `single.sh` 的 13 个文件共 421,060 条，比聚合文件少 16,338 条 |
| Token 扩展 | 10 个 Action 标签从 3–4 tokens 变为各 1 token |
| Smoke SFT | 32 条打包为 18 个序列；loss 1.41397 → 1.31802；峰值记录 7.02 GiB |
| Smoke 推理 | checkpoint 可加载；参考答案 2，模型输出 1，正确性失败 |

## 复现入口

```bash
python labs/phase-04-training-data/scripts/audit_training_data.py --help
python labs/phase-04-training-data/scripts/build_smoke_subset.py --help
SMOKE_GPU=2 labs/phase-04-training-data/scripts/run_smoke_sft.sh
python labs/phase-04-training-data/scripts/smoke_infer.py --help
```

## 阶段成果

- [源码阅读笔记](notes/source-reading.md)
- [数据 manifest](configs/data-manifest.json)
- [短跑配置](configs/smoke-sft.json)
- [实测指标](results/metrics.json)
- [人工复核](results/manual-review.csv)
- [完整报告](results/report.md)

大体积数据、checkpoint 和原始日志只保存在 L20 的 `/data/` 与 Git 忽略的 `artifacts/phase4/`。
