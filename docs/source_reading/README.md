# DeepAnalyze 源码阅读索引

源码阅读必须与一次可观察运行或最小实验配对，不只摘录代码。

| 顺序 | 文档 | 源码入口 | 目标 |
|---:|---|---|---|
| 0 | `00-system-overview.md` | README、论文、`run.py` | 建立端到端架构 |
| 1 | `01-inference-loop.md` | `deepanalyze.py` | 理解 Action 与环境反馈循环 |
| 2 | `02-api-sandbox.md` | `API/`、`demo/chat_v2/` | 理解文件、API 和代码隔离 |
| 3 | `03-data-curriculum.md` | `add_vocab.py`、`single.sh`、`multi_coldstart.sh` | 理解 Token、数据和课程式 SFT |
| 4 | `04-agentic-rl.md` | `multi_rl.sh`、SkyRL environment | 理解 rollout、reward 和 GRPO |

每篇笔记至少回答输入输出、核心状态、环境反馈、失败与终止、源码事实与待验证边界、对应最小实验。先画数据流，再按调用链分块阅读；不要从 `ms-swift` 或 `SkyRL` 根目录开始顺序通读。
