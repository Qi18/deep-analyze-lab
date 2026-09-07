# DeepAnalyze 源码阅读方法

源码阅读必须与一次可观察运行或最小实验配对，不只摘录代码。

| 阶段 | 笔记位置 | 源码入口 | 目标 |
|---:|---|---|---|
| 1 | `labs/phase-01-deployment/notes/` | README、`run.py`、`deepanalyze.py`、`API/` | 理解部署、Action 和 API 调用链 |
| 2 | `labs/phase-02-agent-loop/notes/` | `deepanalyze.py`、API 执行器 | 理解反馈、状态和终止条件 |
| 4–6 | 对应 Lab 的 `notes/` | `add_vocab.py`、`single.sh`、`multi_coldstart.sh` | 理解 Token、数据和课程式 SFT |
| 7 | `labs/phase-07-agentic-rl/notes/` | `multi_rl.sh`、SkyRL environment | 理解 rollout、reward 和 GRPO |

每篇笔记至少回答输入输出、核心状态、环境反馈、失败与终止、源码事实与待验证边界、对应最小实验。先画数据流，再按调用链分块阅读；不要从 `ms-swift` 或 `SkyRL` 根目录开始顺序通读。
