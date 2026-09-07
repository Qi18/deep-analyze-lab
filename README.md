# DeepAnalyze Lab

DeepAnalyze Lab 是围绕自主数据科学 Agent 展开的可复现实验项目，目标是完成一个可作为应用算法岗/Agent 算法岗核心简历项目的 LLM 训练实验自动分析 Agent。项目覆盖推理闭环、文件与代码执行环境、API/WebUI、课程式 SFT、Agentic RL、统一评测和领域改造。

本仓库保存实验配置、结果、源码阅读笔记和报告；DeepAnalyze 官方源码通过 Git Subtree 导入 [`DeepAnalyze/`](DeepAnalyze/)，初始基线固定到上游 commit `d14468b9ef91372359ddcd70da57e0e0f4eb0d1b`。

## 项目目标

- 在 NVIDIA L20 环境跑通 DeepAnalyze-8B 的推理和多轮代码执行闭环。
- 解释 `<Analyze>`、`<Understand>`、`<Code>`、`<Execute>`、`<Answer>` 五类动作如何形成自主编排。
- 理解单能力 SFT、多能力 cold start、GRPO 和环境奖励之间的训练关系。
- 建立带沙箱、安全边界和证据引用的数据分析评测协议。
- 完成一个面向 LLM 训练实验的自动分析 Agent，而不只复现官方演示。
- 通过上游基线、工程增强版和训练增强版的受控对照，量化正确性、可靠性、安全性、服务效率和离线人工效率。

## 仓库导航

- [项目说明](docs/project-overview.md)
- [系统架构](docs/architecture.md)
- [八阶段实验与学习方案](docs/learning-plan.md)
- [Phase 1 部署与五类任务实测报告](labs/phase-01-deployment/results/report.md)
- [Labs 阶段索引](labs/README.md)
- [仓库管理方式](docs/repository-management.md)
- [统一评测协议](docs/evaluation-protocol.md)
- [复现规范](docs/reproducibility.md)
- [简历证据与最终报告模板](docs/resume-guide.md)
- [源码阅读方法](docs/source-reading-guide.md)
- [DeepAnalyze 上游来源与同步](docs/upstream.md)

## 学习与实验主线

按八阶段推进：部署与推理 → 源码与执行反馈 → 评测基线 → 数据与训练准备 → 单能力 SFT → 多能力 Cold Start → Agentic RL → 综合评测与展示。

复用上游代码和训练框架，小模型调通流程、8B 开展正式实验；使用 Base-direct、Base-agent、SFT、Cold-start、RL、Official 的同协议对照。配置须经 L20 预检和短跑确认，未完成的训练不得写成简历成果。

Phase 1 已完成五类合成样例的运行与核验：3 项通过、1 项部分通过、1 项失败。失败结果如实保留，不将部署验证当作正式基准评测。

## 当前进度

| 阶段 | 状态 | 当前证据 |
|---|---|---|
| Phase 01：部署与推理 | completed | 五类样例 3 passed / 1 partial / 1 failed |
| Phase 02：Agent Loop | completed | 契约 4/4；提示驱动 0/2；真实反馈回放 3/3 |
| Phase 03：评测基线 | planned | 等待开发集、测试集与评分器 |
| Phase 04：训练数据 | planned | 等待数据审计和训练短跑 |
| Phase 05：单能力 SFT | planned | 等待训练前后对照 |
| Phase 06：Cold Start | planned | 等待多轮轨迹训练 |
| Phase 07：Agentic RL | planned | 等待 GRPO 和奖励消融 |
| Phase 08：综合评测 | planned | 等待最终冻结版本 |

## 目录职责

```text
DeepAnalyze/     固定的上游源码
docs/            项目级方案、协议和简历证据规范
labs/            八个阶段各自完整的学习与实验闭环
src/             被多个 Lab 复用的本项目正式代码
tests/           src 的自动化测试
scripts/         跨阶段的启动、评测、同步和清理入口
data/            可提交的小型 fixture 与数据 manifest
artifacts/       L20 原始日志和大体积产物，Git 忽略
experiments.csv  正式运行的全局索引
```

## 克隆

```bash
git clone git@github.com:Qi18/deep-analyze-lab.git
cd deep-analyze-lab
```

`DeepAnalyze/` 已作为普通源码目录进入仓库，不需要初始化 Submodule。

## L20 权威工作区

```text
/data/projects/deep-analyze-lab
```

代码修改、验证、commit 和 push 均在 L20 完成。模型、训练数据和完整日志不进入 Git。

## 产物边界

- GitHub：配置、命令、指标摘要、评测结果、源码笔记和报告。
- SwanLab：训练曲线、系统指标、样本输出与实验对比。
- Hugging Face：最终选中的少量模型权重与 Model Card。
- L20：数据集、活动 checkpoint、优化器状态、缓存和完整原始日志。

未经评测、无法追溯到数据与执行结果，或仅由模型主观生成的数字，不进入 README 和简历。
