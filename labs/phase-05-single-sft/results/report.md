# Phase 5：8B 单能力 SFT 试验

状态：本轮 100-step 试验与官方评测已完成，DS-1000 为 37/1,000（3.7%）。Phase 5 整体仍在进行，全量三轮未启动；后续见 [repair-v1](repair-v1.md)。

## 已完成的预检

| 配置 | steps | loss（按 step） | 框架记录峰值显存 |
|---|---:|---|---:|
| 6×L20，长度 2048，无 Liger | 3 | 1.15292 / 1.13011 / 0.81979 | 36.81 GiB |
| 6×L20，长度 8192，无 Liger | 3 | 1.13832 / 1.20146 / 0.82415 | 42.71 GiB |
| 6×L20，长度 8192，Liger 0.6.2 | 3 | 1.13784 / 1.20198 / 0.82402 | 37.92 GiB |

三次短跑均保存 checkpoint。Liger 在相同短跑输入下减少显存记录 4.79 GiB；三步结果仅用于训练可运行性和资源预检。
8192+Liger checkpoint 已独立加载，在相同 DeepSeek 训练模板下生成 64 tokens，词表和输入/输出 embedding 均为 151,681 行，10 个 Action Token 均为单 token。

## 数据版本

基础数据是固定 revision `f2dd0a62927f49f0a1d2465e32dc4072910e7c89` 下、官方 `single.sh` 明确列出的 13 个文件，共 421,060 条。
下载目录还含两个额外 reasoning 文件，但准备脚本从官方 shell 清单读取输入，额外文件不参与训练。

`clean-v1` 顺序执行 schema/行首 Action 语法检查、DS-1000 完整 user prompt 精确匹配排除、metadata 长度过滤和精确对话去重，生成 392,869 条：

| 处理结果 | 条数 |
|---|---:|
| 原始输入 | 421,060 |
| 角色/内容/行首 Action 结构异常 | 4,987 |
| 超过 metadata 8,192 tokens（前一筛选之后） | 21,373 |
| 精确重复对话（前面筛选之后） | 1,831 |
| DS-1000 完整 user prompt 归一化精确匹配 | 0 |
| 保留 | 392,869 |

去重保留官方文件顺序中的首次出现；仅输出 messages，不把 evaluation 字段写入训练文件。
精确 prompt 无命中不能证明没有 benchmark 污染；未进行语义近重复、来源溯源或完整去污染证明。
真实模板编码后超过 8,192 的记录由 ms-swift 再按 `truncation_strategy=delete` 排除。

过滤改变了能力配比，例如 math 保留 11,526/20,000、code 保留 9,733/20,000。本试验是明确记录的 clean-v1 变体，不作为逐项等同官方原始配方的复现。
数据 SHA-256：`6833b4beaa6c8114d14d88cd3ad594ddea6ca5af2bc9e14ca4deaf02f7d91a42`。
逐文件 checksum 和互斥过滤计数见 `../configs/data-manifest.json`。

## 已完成的 100-step 试验

- 基础模型：DeepSeek-R1-0528-Qwen3-8B，revision `6e8885a6ff5c1dc5201574c8fd700323f23c25fa`。
- 词表：使用固定上游 `add_vocab.py` 扩展 10 个 Action Token；基础模型的额外 padded embedding 行缩到实际词表 151,681，未采用 docstring 中未实现的 think embedding 复制。
- 框架：上游 ms-swift 3.7.0.dev0；PyTorch 2.6.0+cu124；Transformers 4.51.1；Datasets 3.3.2；DeepSpeed 0.16.9；Liger 0.6.2。
- 参数：full SFT、bf16、ZeRO-3、FlashAttention、Liger、packing、max_length 8192、batch 1/GPU、gradient accumulation 4、seed 42、LR 5e-5。
- 上限：100 个优化步骤；有效每步 24 个 packed sequences。使用完整 clean-v1 数据池打乱抽取，本轮不遍历全量三次。
- 每 20 steps 保存模型与优化器状态，保留最近两个 checkpoint；不从三步短跑模型续训。
- 预计训练约 1–2 小时，预处理、保存及随后的官方评测另计；该估计不是实测完成时间。

源模型和数据均保存在 L20 CPFS。开始于 Lab commit `10432b789d828a07ac8e1278fa2aa0e0e519a628`，本次脚本改动由提交 diff 追溯。

## 启动故障与缓存边界

首次启动在 Datasets 预处理阶段因根盘仅余约 244 MiB 而报 `OSError: [Errno 28] No space left on device`，未产生训练 step。
已将本试验的 Datasets、ModelScope、Triton、Torch Extensions、CUDA 与临时缓存定向到 `artifacts/phase5/cache/`（CPFS），保留根盘上其他任务的缓存。
失败目录与日志保留为 `pilot-100-root-cache-failed` / `pipeline-root-cache-failed.log`，没有删除 checkpoint 或原始数据。
重启后完整数据已读入，进入 tokenization/packing。CPFS 临时目录清理曾出现非致命 `.nfs... Device or resource busy`，流水线继续运行。
DS-1000 的隔离评分临时目录通过 `DS1000_SCRATCH_ROOT=/dev/shm` 指定，避免评分副本再次占满根盘；该路径的禁网、敏感目录遮蔽和 TensorFlow 探针通过。
训练日志中的真实优化步骤与最终 `summary.json` 才是训练和评测完成的依据，后台进程启动不代表完成。

## 全量成本估算

固定 seed 均匀抽样 2,048 条，按同一个 `deepseek_r1` 训练模板重新编码，估计每轮 654,579,797 tokens，近似 95% 抽样区间 631,580,515–677,579,079。
结合 6 卡、8192 短跑约 11–13 秒一个 microstep，三轮约需 5–7 天（720–1,008 GPU 小时）。正式吞吐、packing 利用率、梯度累积和 checkpoint I/O 会改变耗时。
用户据此选择了预算受限试验。估算脚本及原始结果见 `scripts/estimate_tokens.py` 和 `token-estimate.json`。

## 官方评测流水线

`scripts/run_pilot.py` 负责训练、checkpoint 校验、6 卡分片推理、严格合并 0–999 problem_id、生成代码静态审计和官方执行评分。
复用 Phase 3 固定 SHA-256 的官方 prompt、推理、抽取与评分实现；既有沙箱包装器增加 `DS1000_WORKDIR` 与 `DS1000_SCRATCH_ROOT` 参数，默认目录保持 Phase 3 的路径。
执行沙箱延续 Phase 3 已批准的 /proc 可见限制；禁网与敏感目录遮蔽探针已通过。命中敏感访问或动态求值的生成代码会停止流程，等待审查。

成功后写入：
- `artifacts/phase5/pilot-100-eval/summary.json`：overall、library、perturbation 和基线对比。
- `artifacts/phase5/pipeline-state.json`：当前阶段、进程、时间及失败原因。
- `artifacts/phase5/logs/pilot-100.log`：训练原始日志。
- `artifacts/phase5/pilot-100/v*/checkpoint-100/`：试验权重与可恢复训练状态。

本次对照是 Base 30.0%、Official 58.7%、100-step SFT 3.7%。三者均是单次 temperature=0 的 DS-1000 代码执行指标。100-step 训练耗时约 88 分钟，平均 loss 0.542，checkpoint-100 保存及重载通过；低 loss 不代表能力提升。
Phase 5 只有在训练产物和训练后独立评测齐备时才能登记本轮试验完成；100-step 试验不等同于完成官方三轮课程。

## 复现与续跑

在 L20 仓库根目录执行：

```bash
python3 labs/phase-05-single-sft/scripts/prepare_data.py \
  --data-root /data/datasets/DataScience-Instruct-500K/f2dd0a62927f49f0a1d2465e32dc4072910e7c89 \
  --output artifacts/phase5/data-new
# 数据脚本保护既有版本；重复运行使用新目录并比较 manifest。

/data/venvs/deepanalyze-train/bin/python labs/phase-05-single-sft/scripts/run_pilot.py
# 正在运行时不要重复启动。流水线保护既有 pilot 目录。
# 训练已完成、仅续跑评测时：
/data/venvs/deepanalyze-train/bin/python labs/phase-05-single-sft/scripts/run_pilot.py \
  --evaluate-only artifacts/phase5/pilot-100/实际运行目录/checkpoint-100

python3 labs/phase-05-single-sft/scripts/collect_results.py
```
