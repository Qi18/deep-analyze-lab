# 实验目录规范

```text
experiments/
├── 00-preparation/          # 环境、源码和数据盘点
├── 01-inference-loop/       # 推理闭环与错误恢复
├── 02-api-sandbox/          # API、Workspace 与沙箱
├── 03-training-data/        # Token、数据和轨迹审计
├── 04-curriculum-sft/       # 单能力 SFT 与 cold start
├── 05-agentic-rl/           # rollout、reward 与 GRPO
├── 06-domain-project/       # LLM 训练实验分析 Agent
└── _template/
```

每个正式实验目录包含 `config.json`、`command.sh`、`run.json`、`metrics.csv`、`eval.json`、`report.md`、`checkpoint-manifest.txt` 和 `tracking-url.txt`。

`registry.csv` 是全局索引。实验开始时登记为 `planned/running`，完成目标评测、安全回归和报告后才能改为 `completed`。

模板中的 `command.sh` 默认拒绝执行；只有填写并 review 最终命令后才能移除占位退出逻辑。权重、训练数据和完整日志不进入 Git，只在 manifest 中记录来源、路径、SHA-256、大小和用途。
