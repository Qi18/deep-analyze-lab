# Phase 3 实验报告：官方 DS-1000 基线

## 结论

两种模型均完成官方 DS-1000 全部 1000 题推理与执行评分。DeepAnalyze-8B 相对基础模型的 execution pass rate 绝对提升 28.7 个百分点（单次运行）。

| 模型 | 通过数 | execution pass rate |
|---|---:|---:|
| Base 8B | 300/1000 | 30.0% |
| DeepAnalyze-8B | 587/1000 | 58.7% |

## 分库结果

| library | Base | DeepAnalyze-8B | 绝对差值 |
|---|---:|---:|---:|
| Matplotlib | 45.8% | 59.4% | +13.5 pp |
| Numpy | 35.5% | 69.1% | +33.6 pp |
| Pandas | 21.3% | 52.9% | +31.6 pp |
| Pytorch | 30.9% | 67.6% | +36.8 pp |
| Scipy | 24.5% | 54.7% | +30.2 pp |
| Sklearn | 24.3% | 49.6% | +25.2 pp |
| Tensorflow | 31.1% | 62.2% | +31.1 pp |

## 扰动类型结果

| perturbation | Base | DeepAnalyze-8B | 绝对差值 |
|---|---:|---:|---:|
| Difficult-Rewrite | 24.7% | 50.6% | +25.9 pp |
| Origin | 38.1% | 63.9% | +25.9 pp |
| Semantic | 27.8% | 58.1% | +30.3 pp |
| Surface | 15.1% | 52.6% | +37.5 pp |

## 协议与边界

- 上游源码 commit：`d14468b9ef91372359ddcd70da57e0e0f4eb0d1b`。
- 数据、推理脚本、评分器及 execution harness 的 SHA256 见 `../configs/official-benchmarks.json`。
- 两组模型使用相同的官方 prompt、代码抽取、生成参数和 `test_ds1000.py`。
- Base 先生成 128 题，余下 872 题按原始 problem_id 分到 4 张 GPU；合并后校验 0–999 各出现一次。分片只改变调度，不改变单题协议。
- 官方评分器未被修改；评分前静态审计最终 Python block，外层使用 user/mount/network namespace 禁网，遮蔽 `/data`、HOME、SSH 和 service-account 路径，并清空环境变量。
- L20 容器无法挂载独立 procfs，完全遮蔽 `/proc` 会使 TensorFlow 题崩溃；经用户明确批准，本次保留宿主 `/proc` 可见。审计确认 2000 条答案没有敏感路径、网络、进程或删除操作。
- DeepAnalyze-8B 有 954/1000 条答案包含 Python block，Base 为 736/1000；缺失 block 按官方后处理转为空代码，不人工修补。
- 这是单次、temperature=0 的基线，不提供跨 seed 方差。

## 能说明什么

DS-1000 衡量给定代码上下文后的数据科学代码执行正确性。它不能证明模型具备多文件发现、长程 Agent 恢复或报告证据引用能力；这些能力应由 CoDA-Bench 和补充工程回归分别验证。

## 可追溯产物

- `metrics.json`：完整 overall、library 与 perturbation 聚合结果。
- `metrics.csv`：便于绘图和阶段对比的长表。
- 原始 1000 条答案与逐题执行日志保存在 L20 的 Git 忽略目录 `artifacts/phase3/official-eval/DS-1000/`，不提交生成内容。
