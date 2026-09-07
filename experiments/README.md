# 实验目录规范

实验目录按简历证据链组织，不再按“读到哪一章”组织：

```text
experiments/
├── 00-env-baseline/            # E00/E01：环境、B0/B1 基线
├── 01-observability-eval/      # E02/E06：trace、评分器、稳定性
├── 02-sandbox-recovery/        # E03/E04：错误反馈、沙箱和安全回归
├── 03-domain-agent/            # E05：LLM 训练实验分析 Agent
├── 04-sft-coldstart/           # E07：领域 SFT 与 cold start
├── 05-agentic-rl/              # E08：rollout、reward 与 GRPO
├── 06-deployment-business/     # E09/E10：服务性能与人工效率对照
└── _template/
```

每个正式实验目录包含 `config.json`、`command.sh`、`run.json`、`metrics.csv`、`eval.json`、`report.md`、`checkpoint-manifest.txt` 和 `tracking-url.txt`。原始结果可以保存在 L20 数据盘，但必须在 `run.json` 中记录路径、checksum、生成时间和对应 Lab commit。

`registry.csv` 是全局索引。实验开始时登记为 `planned/running`；命令完成只代表运行结束，只有目标评测、安全回归、失败样本和报告齐全后才能改为 `completed`。阶段门是否通过应在报告中单独标记为 `passed/partial/failed`。

模板中的 `command.sh` 默认拒绝执行；只有填写并 review 最终命令后才能移除占位退出逻辑。权重、训练数据和完整日志不进入 Git，只在 manifest 中记录来源、路径、SHA-256、大小和用途。

所有简历数字必须来自 `docs/final_report.md` 的“简历可引用结论”表，并且状态为 `verified`。
