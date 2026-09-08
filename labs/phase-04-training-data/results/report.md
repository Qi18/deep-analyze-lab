# Phase 4：数据与训练准备实测报告

## 结论

Phase 4 已完成。L20 上审计了 DataScience-Instruct-500K 两个聚合文件共 463,600 条记录，并用 Qwen3-0.6B 完成 Action 词表扩展、32 条数据构造、两步全参数 SFT、checkpoint 保存和确定性推理。

验收结论限定为“数据与训练链路已打通”，不代表模型能力得到提升。短跑推理的参考答案是 2，模型输出 1，正确性未通过。

## 固定输入

| 项目 | 固定值 |
|---|---|
| Lab 起始 commit | `b997e76e7c6cf30d627bd239db493ac05322ff56` |
| DeepAnalyze 上游 commit | `d14468b9ef91372359ddcd70da57e0e0f4eb0d1b` |
| 数据 revision | `f2dd0a62927f49f0a1d2465e32dc4072910e7c89` |
| 小模型 revision | `c1899de289a04d12100db370d81485cdf75e47ca` |
| 硬件 | NVIDIA L20 46,068 MiB，Driver 535.161.08 |
| 训练栈 | Python 3.10.12；PyTorch 2.6.0+cu124；Transformers 4.51.1；Datasets 3.3.2；ms-swift 3.7.0.dev0 |

完整数据、checkpoint 和日志位于 L20 的 `artifacts/phase4/` 或 `/data/`，不提交 Git。校验值见 `configs/data-manifest.json` 和 `results/metrics.json`。

## 数据审计

| 指标 | 单能力聚合数据 | 多能力聚合数据 |
|---|---:|---:|
| 记录数 | 437,398 | 26,202 |
| `user -> assistant` | 437,398 | 26,202 |
| 精确重复对话 | 1,838（0.420%） | 0 |
| 行首 Action 语法异常 | 7,370（1.685%） | 64（0.244%） |
| total tokens P50 / P95 | 1,208 / 8,397 | 11,150 / 23,500 |
| 超过官方 max length | 22,477 / 8,192（5.139%） | 302 / 32,768（1.153%） |

Action 语法统计只解析行首标签，用于发现缺失闭合和错误嵌套，不把正文中对标签的文字引用误算为协议动作。`id` 在多个来源间会重置或复用，因此只作为来源局部元数据，不能当聚合文件的全局主键。

另一个关键差异是：单能力聚合文件有 437,398 条，但上游 `scripts/single.sh` 的 13 个输入文件合计 421,060 条，差出的 16,338 条对应 `dscode_16338.json`。Phase 5 默认复现官方 421,060 条清单，不静默改变训练数据。

## Token 与标签掩码

原始 DeepSeek-R1-0528-Qwen3-8B tokenizer 会把 10 个 Action 标签拆成 3–4 个 token。运行上游 `add_vocab.py --add_tags` 后，小模型 tokenizer 与 embedding 均为 151,679 行，10 个标签均编码为一个 token。

上游脚本的 docstring 声称 `<Analyze>` embedding 从 `<think>` 初始化，但实现中没有 embedding copy，仅执行 `add_tokens` 和 `resize_token_embeddings`。本阶段保留上游代码，只记录差异。

最终训练预处理日志显示，样例前 532 个 user/prompt token 的 label 全部为 `-100`，assistant 轨迹保留监督标签。这证明本次配置没有让模型学习复述用户输入。

## 小模型短跑

从结构有效且 `total_tokens <= 2048` 的 306,243 条样本中，以 seed 42 做 reservoir sampling，得到固定 32 条数据；文件 SHA-256 为 `d1b89fc755f1b607fe3d771029dd790dc60319ae1ce365dcfd22ebb4843919d0`。人工复核 8 条，角色顺序、Action 结构和 Answer 均通过；没有独立核对答案事实正确性。

`packing=true` 将 32 条记录组成 18 个序列。两步全参数 SFT 的结果为：

| step | loss | token accuracy | grad norm | 显存记录 |
|---:|---:|---:|---:|---:|
| 1 | 1.41397 | 0.72689 | 33.75 | 5.64 GiB |
| 2 | 1.31802 | 0.73580 | 19.75 | 7.02 GiB |

最终 `train_loss=1.36599`，运行 3.4126 秒，checkpoint 保存到 `artifacts/phase4/smoke/run/v2-20260908-041334/checkpoint-2`。这两个 step 只用于接口、显存和产物验收，loss 变化不能解释为能力提升。

## 推理验收

checkpoint 可被 Transformers 加载并完成确定性生成：输入 589 tokens，生成 38 tokens，峰值分配显存 1.198 GiB。因此模型保存与加载链路通过。

但该样例参考答案为 `2`，生成答案为 `1`。所以：

- runtime validation：通过；
- correctness validation：失败；
- model-quality claim：不成立。

## 失败记录

1. `packing=true` 配合 SDPA 在训练前被 ms-swift 拒绝，要求使用 FlashAttention。
2. 改用 FlashAttention 后，未显式指定 `--model_type qwen3` 的运行仍在训练前失败。
3. 环境中的 Datasets 4.x 与固定上游栈不兼容；固定为 3.3.2 后两步训练成功。

最终可运行入口已经将 `flash_attn` 和 `model_type=qwen3` 固化，避免重复踩坑。

## 复现入口

```bash
python labs/phase-04-training-data/scripts/audit_training_data.py \
  --single /data/datasets/DataScience-Instruct-500K/f2dd0a62927f49f0a1d2465e32dc4072910e7c89/single_ability_finetuning.json \
  --multi /data/datasets/DataScience-Instruct-500K/f2dd0a62927f49f0a1d2465e32dc4072910e7c89/multi_ability_agentic_training.json \
  --output artifacts/phase4/data-audit.json

python labs/phase-04-training-data/scripts/build_smoke_subset.py \
  --input /data/datasets/DataScience-Instruct-500K/f2dd0a62927f49f0a1d2465e32dc4072910e7c89/single_ability_finetuning.json \
  --output artifacts/phase4/smoke/single-ability-32.json \
  --manifest artifacts/phase4/smoke/subset-manifest.json

SMOKE_GPU=2 labs/phase-04-training-data/scripts/run_smoke_sft.sh

CUDA_VISIBLE_DEVICES=2 /data/venvs/deepanalyze-train/bin/python \
  labs/phase-04-training-data/scripts/smoke_infer.py \
  --model artifacts/phase4/smoke/run/v2-20260908-041334/checkpoint-2 \
  --dataset artifacts/phase4/smoke/single-ability-32.json \
  --output artifacts/phase4/smoke/inference.json
```

## Phase 5 输入约束

- 正式单能力 SFT 跟随上游 13 文件、421,060 条数据口径。
- 训练前过滤或修复 Action 语法异常，去重策略作为显式数据版本记录。
- 明确统计截断比例，不能只记录 `max_length=8192`。
- 单独验证 `add_vocab.py` 随机初始化新 embedding 的影响；如修改初始化方式，必须做对照实验。
- Phase 5 使用独立评测集比较训练前后，不能用训练 loss 或本次短跑样例替代效果评测。
