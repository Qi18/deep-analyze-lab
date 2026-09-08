# Phase 3：官方评测基线

状态：completed

## 学习目标

复现 DeepAnalyze 官方公开的推理与评分方法，理解数据科学代码执行评测和数据发现型 Agent 评测的差异。

## 评测选择

| 优先级 | 基准 | 规模 | 官方指标 | 状态 |
|---|---|---:|---|---|
| P0 | DS-1000 | 1000 | execution pass rate | completed |
| P1 | CoDA-Bench Hard / Full | 119 / 1009 | EA、DA | blocked：当前 L20 Pod 无 Docker |
| P2 | Resume-Eval-v1 | 20 dev + 30 test | Lab 自定义 | 仅作补充回归，不作为主基准 |

固定上游版本还提供 DABStep-Research、DSBench 和 TableQA 入口，但它们需要额外数据或 judge 服务。Phase 3 选择数据和评分器均随仓提供的 DS-1000，避免自行补造缺失依赖后仍声称是官方结果。

## 实测结果

两种模型均完成 1000/1000 题推理和官方 `test_ds1000.py` 执行评分，失败结果未删除或重跑覆盖。

| 模型 | 通过数 | execution pass rate |
|---|---:|---:|
| DeepSeek-R1-0528-Qwen3-8B Base | 300/1000 | 30.0% |
| DeepAnalyze-8B | 587/1000 | 58.7% |

DeepAnalyze-8B 相对 Base 绝对提升 28.7 个百分点。这是单次 temperature=0 基线，不包含跨 seed 方差。完整分库和 perturbation 结果见 [metrics.csv](results/metrics.csv)，实验解释见 [report.md](results/report.md)。

## 固定版本与协议

- DeepAnalyze source commit：`d14468b9ef91372359ddcd70da57e0e0f4eb0d1b`。
- DS-1000 数据 SHA256：`e8c6daa9d7223976bce0296644f3933f78d7f47830669ff05cd61da62c6ba9b3`。
- DeepAnalyze-8B revision：`214c302cebc61ed92f9c856a3dd47a7fdc588d5f`。
- Base revision：`6e8885a6ff5c1dc5201574c8fd700323f23c25fa`。
- 生成参数：max_model_len=16384、max_new_tokens=16384、temperature=0、top_p=0.8、batch_size=128。
- 推理 prompt、代码抽取、测试逻辑和评分器均使用固定上游实现，不修改算法。

Base 先在 GPU 3 生成 128 题，余下 872 题按原始 problem_id 分到 GPU 4–7。合并器校验 0–999 各出现一次；分片只改变调度和 batch 边界，不改变单题输入、参数或评分逻辑。

完整文件哈希见 [official-benchmarks.json](configs/official-benchmarks.json)，实现说明见 [official-evaluation.md](notes/official-evaluation.md)。

## 执行安全边界

上游 `execution.py` 没有启用 reliability guard，因此 Lab 在调用官方评分器前增加执行层保护，但不改变得分算法：

1. 静态审计两组最终 Python block，拦截敏感路径、网络、系统进程和删除操作；本次 blocking hit 为 0。
2. 使用 user/mount/network namespace 禁网，遮蔽 `/data`、HOME、SSH 与 service-account 路径，并清空环境变量。
3. L20 容器不允许创建独立 procfs，而 TensorFlow 依赖 `/proc`；经用户明确批准，本次保留宿主 `/proc` 可见。
4. DeepAnalyze-8B 有 954 条答案包含 Python block，Base 有 736 条；缺失 block 按官方后处理转为空代码，不人工修复。

该 `/proc` 例外只适用于已经静态审计的 DS-1000 代码，不适用于开放式 Agent 生成代码。CoDA-Bench 仍要求官方 Docker 隔离模式。

## 复现入口

原始答案与逐题执行日志保存在 Git 忽略目录 `artifacts/phase3/official-eval/DS-1000/`。

```bash
cd /data/projects/deep-analyze-lab
python3 labs/phase-03-evaluation/scripts/ds1000.py prepare --execute
python3 labs/phase-03-evaluation/scripts/ds1000.py infer --model deepanalyze8b --gpu 2 --execute
python3 labs/phase-03-evaluation/scripts/ds1000.py evaluate --model deepanalyze8b --execute
python3 labs/phase-03-evaluation/scripts/collect_results.py
```

## 阶段成果

- [metrics.json](results/metrics.json)：模型 revision、总体、分库、扰动类型和安全审计摘要。
- [metrics.csv](results/metrics.csv)：可直接用于后续阶段对比与绘图的长表。
- [report.md](results/report.md)：结论、实验边界与可用于简历的证据范围。
- `experiments.csv`：两种模型各一条 completed 实验记录。
