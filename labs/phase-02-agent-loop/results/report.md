# Phase 2 实验报告：Agent Loop 与执行反馈

## 状态与范围

Phase 2 已完成。实验覆盖宿主循环契约、执行器边界、提示驱动故障尝试，以及真实执行反馈回放。没有修改上游源码或模型权重。

这些是受控机制实验，每项只运行一次，不是恢复率基准。

## 环境与固定版本

- Lab 起始 commit：`45be5531361096d34faf36ecae7f299354601c97`。
- DeepAnalyze 源码：`d14468b9ef91372359ddcd70da57e0e0f4eb0d1b`。
- 模型：`RUC-DataLab/DeepAnalyze-8B` revision `214c302cebc61ed92f9c856a3dd47a7fdc588d5f`。
- 推理：L20 GPU 0 上既有 vLLM 服务，temperature=0。
- 提示驱动实验：max_tokens=4096、max_rounds=8。
- 反馈回放：单轮 max_tokens=2048、最多 8 轮；后续执行超时 5 秒。
- 超时探针：真实子进程执行 `sleep(5)`，timeout=1 秒。

## 结果分层

| 实验层 | 结果 | 解释 |
|---|---:|---|
| 宿主循环与执行器契约 | 4/4 suites passed | 停止边界、execute 角色、轮数上限、Answer 优先级和执行器行为符合源码 |
| 提示驱动故障 | 0/2 passed | 模型未生成 Code/Execute，却直接声称得到预期错误或恢复 |
| 真实反馈回放 | 3/3 passed | 模型分别正确处理缺失文件、NameError 和 Timeout |

三组实验目的不同，不合并成一个“模型成功率”。

## 关键发现

### Code 停止和 Execute 反馈是宿主行为

模型服务遇到 `</Code>` 停止生成，CLI 宿主补回闭合标签、提取代码并执行。执行输出既进入完整 reasoning 的 `<Execute>` 块，也以 `role=execute` 加入下一次模型请求。确定性测试捕获了实际请求消息并验证这一过程。

### 终止条件存在可观测边界

CLI 达到 `max_rounds` 时会直接返回已有文本，即使没有 Answer，也没有显式 incomplete 标志。如果同一模型响应同时包含 Code 和 Answer，Answer 检查先发生，Code 不会执行。

这些行为以后需要进入统一 Trace 和评分状态，避免把“函数正常返回”等同于“任务完成”。

### API 执行器不是持久会话

API 每次把代码写入临时文件，并启动新的 Python 子进程。变量和 import 不跨轮保留。普通 Python 异常通过 stderr 返回，通常没有 CLI 使用的 `[Error]` 前缀；Timeout 才有稳定的 `[Timeout]` 标志。

Timeout 回放实际经历：

```text
Timeout
→ 新代码未打印，Execute 为空
→ 下一轮使用 time 但未 import，NameError
→ 再次生成并显式 import time，执行得到 10
→ Answer
```

模型最终恢复，但用了三次新代码和四轮生成。

### 提示词中的错误描述不能充当执行证据

两条提示驱动任务要求模型先制造 FileNotFoundError 或 NameError。模型均没有产生任何 Code/Execute，而是在长分析后直接给出目标答案。初版关键词检查曾把其中一条误判为通过；严格核验要求错误必须出现在 Execute 块后，两条都被改判 failed。

这说明 Phase 3 的评分器不能只搜索答案和错误关键词，必须验证动作顺序和证据来源。

## 产物

Git 内：

- [固定配置](../configs/fault-injection.json)
- [运行时契约结果](runtime-contracts.json)
- [提示驱动严格结果](prompt-forced-results.json)
- [真实反馈回放结果](feedback-replay-results.json)
- [综合核验结果](results.json)
- [源码与调用链笔记](../notes/agent-loop.md)

L20 `artifacts/phase2/` 保存逐轮 reasoning、请求后执行输出和运行日志。初版假阳性脚本也作为 `fault_injection-v0.py` 保留在原始产物中，不进入 Git。

## 下一步

Phase 3 应把本轮规则实现为通用 Trace 评分器，至少区分 no_action、execution_error、recovered、answer_without_evidence、round_limit 和 completed，并在开发集与独立测试集上统一运行。
