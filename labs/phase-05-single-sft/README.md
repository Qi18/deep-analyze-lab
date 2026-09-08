# Phase 5：单能力 SFT

状态：in_progress；100-step 试验已完成，DS-1000 为 3.7%。repair-v1 的约 100M-token 数据和分段续训预检完成；8B 正式训练等待 GPU 2–7 可用。

本阶段学习数据清洗、全参数 SFT、packing、标签掩码、ZeRO-3 和训练前后受控评测。
从 DeepSeek-R1-0528-Qwen3-8B 基础权重训练，保留数据、checkpoint、原始日志和失败结果。

## 当前证据

- 官方 13 文件共 421,060 条，生成显式 clean-v1 数据 392,869 条。
- 6 张 L20 已通过 2,048 和 8,192 长度的 8B 全参数短跑。
- 8,192 + Liger 短跑显存峰值记录 37.92 GiB，checkpoint 独立加载和生成通过。
- 用户选择 100-step、约 1–2 小时试验；全量三轮约 5–7 天，未启动。
- 100-step 官方 DS-1000 已完成：37/1,000（3.7%），保留失败结果。
- repair-v1：62,327 条、99,956,985 tokens；开发集 Base 31/32、旧 pilot 6/32。
- 分段停训与恢复已用 0.6B、2 卡实测通过；不作为新一轮 8B 性能证明。

## 入口与成果

- [Repair v1 配置、门槛与资源阻塞](results/repair-v1.md)
- [Repair v1 预检记录](results/repair-preflight.json)
- [Repair v1 数据审计](configs/repair-data-manifest.json)
- [Repair v1 训练流水线](scripts/run_repair.py)

- [源码与实验学习笔记](notes/source-reading.md)
- [数据 manifest](configs/data-manifest.json)
- [训练预算与配置](configs/training-profiles.json)
- [预检报告与运行说明](results/report.md)
- [预检指标](results/metrics.json)
- [Token 成本估算](results/token-estimate.json)
- [数据准备](scripts/prepare_data.py)
- [训练入口](scripts/train_single.sh)
- [试验与官方评测流水线](scripts/run_pilot.py)

原始状态在 L20 `artifacts/phase5/pipeline-state.json`，日志在 `artifacts/phase5/logs/`。
完成标准是训练产物、官方独立评测和分能力对比齐备；loss 变化仅是训练诊断信息。
