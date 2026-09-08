# Phase 5 源码与实验学习笔记

## 入口代码在哪里

- 上游训练配方：`DeepAnalyze/scripts/single.sh`。13 个输入文件、full SFT、8192、packing、ZeRO-3、Liger 和空 response_prefix 均从这里核对。
- 模板：`DeepAnalyze/deepanalyze/ms-swift/swift/llm/template/template/deepseek.py` 的 `DeepseekR1Template`，通用编码与 labels 处理在同层 `base.py`。
- 本 Lab 数据版本：`../scripts/prepare_data.py`；训练参数覆盖：`../scripts/train_single.sh`；训练后官方评测：`../scripts/run_pilot.py`。

## 数据如何流动

官方单能力文件清单 → 格式检查、长度筛选、精确去重 → 只保留 messages 的 clean-v1 → DeepSeek 模板编码 → 超长删除与 packing → SFT → checkpoint 重载 → 官方 DS-1000 生成与执行评分。

manifest 保存输入 checksum、各阶段互斥计数与输出 checksum。训练日志记录实际模板、屏蔽的 prompt labels、打包长度和损失。
metadata token 数只是预筛：最终长度受 tokenizer 和模板影响，不能用 metadata 代替实际编码检查。

本次真实 packing 得到 78,029 个序列，平均长度 8,068.83 tokens，最大 8,192。
100 steps × 6 GPU × batch 1 × accumulation 4 = 2,400 个 packed sequence 的优化预算；这不是遍历 392,869 条原始对话一轮。

## 为什么这样设计

小模型短跑负责排查数据与调用链；8B 预检负责确认真实模型的资源边界，两者不能互相替代。
本次不重写 trainer，沿用上游 ms-swift；新增的是数据版本、L20 参数覆盖、运行校验与评测调度。
ZeRO-3 对训练状态分片；梯度累积改变有效 batch 与更新频率，并不把单次前后向的序列长度降低。
采用 Liger 是实测资源选择：相同三步预检里，框架记录的峰值显存从 42.71 降到 37.92 GiB。
只训练 100 steps 是预算决定，不是完整课程复现；有效 batch 24 也明显小于官方 256，报告中必须保留差异。

## 实验支持了什么结论

已支持：清洗数据可以进入 8B full SFT；8192+Liger 在 6 张 L20 上通过三步短跑；保存后的模型能独立加载和生成。
尚未支持：单能力训练提高 DS-1000 或真实 Agent 成功率。需等待 100-step checkpoint 与官方评测，不用训练 loss 代替效果指标。
DS-1000 主要测给定上下文下的数据科学代码正确性，不能据此声称多文件分析、工具错误恢复或报告可信度已提升。
