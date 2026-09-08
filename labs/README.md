# Labs 阶段索引

每个 Lab 同时保存学习目标、源码笔记、实际脚本、配置和结果摘要，形成可以复现和面试讲解的闭环。完整原始日志仍放在 Git 忽略的 `artifacts/`。

| 阶段 | 主题 | 状态 | 完成证据 |
|---|---|---|---|
| [Phase 01](phase-01-deployment/README.md) | 官方部署与五类推理验证 | completed | 3 passed / 1 partial / 1 failed |
| [Phase 02](phase-02-agent-loop/README.md) | Agent Loop 与执行反馈 | completed | 契约 4/4；提示驱动 0/2；反馈回放 3/3 |
| [Phase 03](phase-03-evaluation/README.md) | 官方评测基线 | completed | DS-1000：Base 300/1000，DeepAnalyze-8B 587/1000 |
| [Phase 04](phase-04-training-data/README.md) | 数据与训练准备 | completed | 审计 463,600 条；Qwen3-0.6B 2-step SFT 与推理链路通过 |
| [Phase 05](phase-05-single-sft/README.md) | 单能力 SFT | in_progress | clean-v1 392,869 条；6×L20 8B 预检通过；100-step 试验启动，官方评测待完成 |
| [Phase 06](phase-06-cold-start/README.md) | 多能力 Cold Start | planned | 多轮工具交互对照 |
| [Phase 07](phase-07-agentic-rl/README.md) | Agentic RL | planned | GRPO、奖励分析和消融 |
| [Phase 08](phase-08-final-evaluation/README.md) | 综合评测与展示 | planned | 冻结测试、演示和简历数字 |

## Lab 约定

每个阶段回答六个问题：学什么、为什么有价值、读哪些源码、做哪些实验、如何验收、留下哪些证据。阶段专属内容留在 Lab 内；只有跨阶段复用的实现才进入根目录 `src/` 或 `scripts/`。

## 目录模板

`_template/` 保存一次正式实验所需的配置、命令、运行信息、指标、评测结果和报告模板。执行阶段按需复制到对应 Lab，填写真实内容后再运行；不要为了目录整齐创建没有实际用途的空配置。

全局运行索引是根目录 `experiments.csv`。模型权重、完整训练数据和大体积日志只在索引及报告中记录路径与校验信息，不提交 Git。
