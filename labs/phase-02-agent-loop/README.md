# Phase 2：Agent Loop 与执行反馈

状态：completed

## 学习目标

推理循环、停止条件、上下文拼接和 Python 执行反馈。

## 实验任务

注入文件缺失、代码异常和超时，观察模型如何接收反馈并恢复。

## 验收条件

- 输入、模型、配置和执行预算已固定。
- 自动断言与人工复核均完成。
- 成功和失败轨迹全部保留。
- 结果已登记到根目录 `experiments.csv`。
- 没有把计划目标写成实测结论。

## 阶段成果

调用链笔记、错误轨迹、终止条件表和必要的运行记录增强。

本轮已补齐 `notes/`、`configs/`、`scripts/` 和 `results/`，完整逐轮轨迹保存在 L20 `artifacts/phase2/`。

## 实测结果

| 实验 | 结果 | 含义 |
|---|---:|---|
| 宿主循环与执行器契约 | 4/4 suites passed | 代码提取、execute 角色、轮数和终止分支符合源码 |
| 提示驱动故障 | 0/2 passed | 无 Code/Execute，却直接声称恢复 |
| 真实执行反馈回放 | 3/3 passed | 正确处理缺失文件、NameError 和 Timeout |

三组结果验证的是不同问题，不能合并成一个模型准确率。完整分析见 [实验报告](results/report.md)。

## 运行命令

```bash
cd /data/projects/deep-analyze-lab

/data/venvs/deepanalyze-phase1/bin/python \
  labs/phase-02-agent-loop/scripts/runtime_contracts.py

# 重新运行两条提示驱动实验；不带 --execute 只核验现有轨迹
/data/venvs/deepanalyze-phase1/bin/python \
  labs/phase-02-agent-loop/scripts/prompt_forced.py --execute

/data/venvs/deepanalyze-phase1/bin/python \
  labs/phase-02-agent-loop/scripts/feedback_replay.py

/data/venvs/deepanalyze-phase1/bin/python \
  labs/phase-02-agent-loop/scripts/phase2_verify.py
```

真实模型实验要求 Phase 1 的 vLLM 服务仍监听 `127.0.0.1:8000`。受控回放使用真实执行器产生的错误文本，不伪造成功输出。
