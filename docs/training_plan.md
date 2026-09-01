# DeepAnalyze 六周训练与源码学习计划

更新时间：2026-09-01

## 0. 文档定位与当前事实

这份计划是 DeepAnalyze Lab 的执行主线，不是功能清单。学习顺序固定为：先运行推理闭环，再理解执行环境，然后进入数据、SFT 和 Agentic RL，最后完成自己的数据分析 Agent。

当前可确认的事实：

- 实验仓库：`Qi18/deepanalyze-lab`。
- L20 权威工作区：`/data/projects/deepanalyze-lab`。
- 官方源码位于普通目录 `DeepAnalyze/`，初始上游 commit 为 `d14468b9ef91372359ddcd70da57e0e0f4eb0d1b`。
- 官方模型为 DeepAnalyze-8B，基础模型路线为 `DeepSeek-R1-0528-Qwen3-8B`。
- 推理核心是模型自主生成五类 Action，并根据代码执行反馈继续决策。
- 官方完整单能力 SFT 和 Agentic RL 脚本都以 8 GPU 为基线；学习阶段不默认等同于完整训练复现。
- DeepAnalyze 根目录的简化执行器使用 Python `exec`，只能用于受控学习环境，不能作为生产安全沙箱。

所有结果必须区分：

1. **官方声明**：README 或论文报告的能力与指标。
2. **源码事实**：固定 commit 中实际实现的行为。
3. **L20 实测**：本 Lab 运行后可以回读的命令、日志和产物。

不得把官方结果或历史记录写成当前 L20 已验证结果。

## 1. 学习目标与范围

### 1.1 核心目标

- 能从用户指令追踪到多轮生成、代码执行、环境反馈和最终答案。
- 能解释 DeepAnalyze 与固定 Workflow Agent 的差异。
- 能独立修改推理循环、执行环境或奖励函数中的至少一个部分。
- 能解释特殊 Token、课程式训练、轨迹冷启动和 GRPO 的职责边界。
- 能用自己的数据完成有评测、有证据、有安全边界的数据分析 Agent。

### 1.2 暂不作为前置目标

- 不在推理闭环跑通前下载完整训练数据。
- 不在最小评测建立前启动完整 8B SFT 或 GRPO。
- 不从头通读 `ms-swift` 和 `SkyRL`；只沿 DeepAnalyze 调用链进入框架。
- 不把长报告、loss 下降或单个成功案例当作能力完成证明。
- 不让模型生成的 Python 直接访问生产数据库、凭据或无边界文件系统。

## 2. 六周总览

建议每周投入 6–8 小时；只有每周 4 小时时，将路线拉长到 9 周，但不改变阶段顺序。

| 周次 | 学习重点 | 核心产出 | 阶段门 |
|---|---|---|---|
| 第 1 周 | 跑通项目与整体架构 | 一次分析结果、系统架构图 | 能解释数据如何变成报告 |
| 第 2 周 | 推理循环与 Action 协议 | Action 状态图、故障恢复记录 | 能逐段解释 `generate()` |
| 第 3 周 | API、文件环境与沙箱 | API/WebUI 样例、安全边界清单 | 代码在受控环境运行 |
| 第 4 周 | 训练数据与课程式 SFT | 数据到能力映射、轨迹样本审计 | 能解释 cold start 的必要性 |
| 第 5 周 | Agentic RL、GRPO 与奖励 | RL 数据流图、配置追踪记录 | 能追踪一个配置到实际调用 |
| 第 6 周 | LLM 训练实验分析 Agent | 可演示项目、10 项评测、总结 | 结论可由数据和执行结果复核 |

每周时间建议：

- 2 小时：论文、README 和架构。
- 3 小时：源码阅读与运行。
- 1–2 小时：修改或观察实验。
- 1 小时：沉淀数据流图、结论和问题。

## 3. 第 1 周：运行项目并建立整体认识

阅读顺序：

1. `DeepAnalyze/README.md`
2. `DeepAnalyze/run.py`
3. `DeepAnalyze/deepanalyze.py`
4. 论文 Introduction、Architecture 和案例图

准备一个小型公开或自建数据集，优先选择 LLM 训练实验数据：多个训练 run 的配置、loss、learning rate、tokens/s、GPU 使用率和评测指标。要求模型比较不同 run、定位异常、生成图表，并明确结论的数据依据和局限性。

阶段产出：

- `docs/source_reading/00-system-overview.md`；
- 一张 `instruction → action → environment → report` 架构图；
- 一个最小运行记录，包含命令、模型版本、输入文件和输出位置；
- 能脱离 README 解释完整端到端流程。

## 4. 第 2 周：吃透推理循环与 Action 协议

重点阅读 `DeepAnalyze/deepanalyze.py`：

- `generate()` 如何组织消息和最多 30 轮迭代；
- `stop=[\"</Code>\"]` 如何把生成和执行切开；
- `<Code>` 如何提取并交给 `execute_code()`；
- `<Execute>` 结果如何作为环境反馈送回模型；
- `<Answer>` 如何终止循环；
- 请求失败、无 Code 中间步骤和 Python 异常分别如何处理。

观察改造：

1. 记录每轮 Action、耗时、生成长度和代码执行状态。
2. 增加执行超时与输出长度限制的实验性实现。
3. 故意制造文件不存在、包缺失和代码异常，观察模型能否恢复。
4. 比较“环境错误可见”和“只返回通用失败”时的修复能力。

阶段产出 `docs/source_reading/01-inference-loop.md`、Action 状态图和至少三种错误的恢复记录。阶段门是能逐段解释 `DeepAnalyzeVLLM.generate()`，并指出当前实现的安全与可靠性缺口。

## 5. 第 3 周：API、文件 Workspace 与代码沙箱

阅读顺序：

```text
DeepAnalyze/API/config.py
→ DeepAnalyze/API/start_server.py
→ DeepAnalyze/demo/chat_v2/backend.py
→ 文件上传与 workspace
→ Docker 执行环境
→ 前端流式展示
```

必须理解：

- 模型负责决定下一步动作，不直接提供文件隔离。
- Workspace 负责确定可见数据和生成产物的位置。
- 执行器负责 Python 进程、超时、资源和网络限制。
- API/WebUI 负责文件、会话、流式结果和用户边界。

完成一次 OpenAI 风格 API 文件分析，验证文件名冲突、超大输出、执行超时和会话隔离，并记录容器可见目录、网络、CPU、内存和进程权限。

阶段产出为 `docs/source_reading/02-api-sandbox.md`、可重复演示和 threat model。未经沙箱的 `exec` 不进入共享或公网服务。

## 6. 第 4 周：训练数据、特殊 Token 与课程式 SFT

阅读顺序：

```text
DeepAnalyze/deepanalyze/add_vocab.py
→ DataScience-Instruct-500K 抽样
→ DeepAnalyze/scripts/single.sh
→ DeepAnalyze/scripts/multi_coldstart.sh
```

只抽样下载和审计数据，不把完整训练集作为本阶段前置条件。重点回答：

- 五类 Action Token 如何加入 tokenizer 和模型 vocabulary？
- Reasoning、structured data understanding、code 三类单能力如何映射到 Action？
- 为什么先做单能力 SFT，再做多能力轨迹 cold start？
- 训练轨迹中哪些 token 来自模型，哪些内容来自环境反馈？
- 长轨迹的截断、失败执行和错误答案如何处理？

阶段产出 `docs/source_reading/03-data-curriculum.md`、三类数据样本标注，以及“数据集 → 能力 → Action → 训练阶段”映射表。

## 7. 第 5 周：Agentic RL、GRPO 与奖励

阅读主线：

```text
DeepAnalyze/scripts/multi_rl.sh
→ examples.deepanalyze.main_deepanalyze
→ DeepAnalyze environment
→ rollout generation
→ code execution feedback
→ reward
→ GRPO advantage
→ policy update
```

使用 `rg` 从脚本配置反向查找实现，不从 SkyRL 根目录顺序阅读。重点追踪每个 prompt 的采样数、最大交互轮次、QA/Data Task/Research 三类数据、格式奖励、执行成功奖励、报告质量奖励，以及 vLLM、FSDP2、NCCL 的职责。

```text
Prompt → Policy 生成 Action → Environment 执行代码 → 长轨迹
       → Reward 评价答案与过程 → 组内相对优势 → Policy 更新
```

阶段产出 `docs/source_reading/04-agentic-rl.md`、完整 RL 数据流图，并从 `multi_rl.sh` 选择至少三个配置追踪到实际消费位置。

## 8. 第 6 周：LLM 训练实验自动分析师

输入包括多次训练的配置、loss、learning rate、吞吐量、GPU 指标、checkpoint 和 evaluation 结果。

项目能力：

- 自动发现并对齐不同训练 run；
- 检测 NaN、过拟合、吞吐下降和配置差异；
- 生成对比图，并把每项结论绑定到实际数据；
- 输出结论、证据、局限性和下一步实验建议；
- 代码失败后能够基于环境反馈修复。

至少准备 10 个固定任务，覆盖数值正确性、图表有效性、数据证据、多文件关联、执行成功率、错误恢复、重复运行稳定性、无依据结论、文件与网络越权、报告可读性。

完成 `experiments/06-domain-project/` 下的正式实验和 `docs/final_report.md`，才能将该项目标记为完成。

## 9. 最终完成标准

1. 能解释 DeepAnalyze 与固定 Workflow Agent 的区别。
2. 能从一次用户请求追踪到模型、执行环境和最终报告。
3. 能独立修改并验证推理循环、执行环境或奖励函数之一。
4. 能解释 single-ability SFT、cold start 和 GRPO 的依赖关系。
5. 自建项目至少有 10 项固定评测，并保留命令、配置、数据 manifest 和结果。
6. 所有安全与能力结论都明确区分官方声明、源码事实和 L20 实测。
