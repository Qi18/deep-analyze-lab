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

- [简历目标导向六周实验方案](docs/training_plan.md)
- [仓库管理方式](docs/repository-management.md)
- [统一评测协议](docs/evaluation_protocol.md)
- [最终报告模板](docs/final_report.md)
- [源码阅读索引](docs/source_reading/README.md)
- [DeepAnalyze 上游来源与同步](docs/upstream-deepanalyze.md)
- [实验登记规范](experiments/README.md)

## 学习与实验主线

```text
Resume Evidence Goal / Frozen Baseline
            ↓
Observability + Resume-Eval-v1
            ↓
Inference Loop + Error Recovery + Docker Sandbox
            ↓
LLM Training Experiment Analyst
            ↓
Baseline / Ablation / Stability Evaluation
            ↓
Optional SFT / Cold Start / Agentic RL
            ↓
API Deployment + Controlled Efficiency Test + Final Report
```

核心项目以 B0 基础模型、B1 上游 DeepAnalyze 和 B2 本 Lab 工程增强版的同协议对照为主。完整 8B SFT/GRPO 只在数据、算力、基线和评测门槛都满足后启动；未完成训练不影响 Agent 工程主线闭环，但不得在简历中声明训练成果。

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
