# Phase 4 源码阅读笔记

## 入口代码在哪里

- `DeepAnalyze/deepanalyze/add_vocab.py`：向 tokenizer 加入 10 个 Action 起止标签，并扩展模型词嵌入矩阵。
- `DeepAnalyze/scripts/single.sh`：单能力全参数 SFT，13 个 `reasoning/` 数据文件，共 421,060 条，`max_length=8192`。
- `DeepAnalyze/scripts/multi_coldstart.sh`：多能力 cold start，12 个上游拼写为 `interation/` 的数据文件，共 26,202 条，`max_length=32768`。
- `DeepAnalyze/deepanalyze/ms-swift/`：上游固定的训练框架实现。

## 数据如何流动

1. 原始记录包含一轮 `user -> assistant` 消息及 token 统计。
2. assistant 内容以 `<Analyze>`、`<Understand>`、`<Code>`、`<Execute>`、`<Answer>` 组织完整轨迹。
3. `add_vocab.py` 将 10 个 Action 标签变为独立 token，同时调整输入、输出 embedding 行数。
4. ms-swift 套用 Qwen3 chat template；本次日志观察到样例前 532 个 user/prompt token 标签均为 `-100`，assistant 部分保留监督标签。
5. `packing=true` 把 32 条短样本拼成 18 个训练序列，再执行全参数 SFT。

## 为什么这样设计

- 独立 Action token 避免协议标签被拆成 3–4 个普通 token，让模型更直接地学习阶段边界。
- `response_prefix=""` 配合 assistant-only label mask，只训练回答轨迹，不把 user 内容作为预测目标。
- packing 提高短样本下的有效 token 利用率；长轨迹阶段则依靠更大的 `max_length`。
- 单能力 SFT 先学习分析、表格、代码等局部能力，多能力 cold start 再学习多轮执行轨迹，之后才进入 Agentic RL。

## 源码与材料中的差异

- `add_vocab.py` 的 docstring 写着用 `<think>` / `</think>` 初始化 `<Analyze>` / `</Analyze>` embedding，但当前实现只调用 `add_tokens` 和 `resize_token_embeddings`，没有复制旧 token embedding。这是固定上游 commit 的源码事实，Phase 4 未改写上游。
- `single_ability_finetuning.json` 聚合文件有 437,398 条，而 `single.sh` 明确列出的 13 个文件合计 421,060 条。差值 16,338 对应未进入官方脚本的 `dscode_16338.json`。Phase 5 默认跟随官方文件清单，额外数据只能作为独立消融变量。
- 上游目录名使用 `interation`，虽是拼写问题，但配置与复现命令必须保留实际路径。

## 实验支持了什么结论

- 10 个 Action 标签在原始 DeepSeek 8B tokenizer 中均不是独立 token；在 Qwen3-0.6B 上运行上游脚本后，tokenizer 长度与 embedding 行数一致增加到 151,679，10 个标签均成为单 token。
- 数据结构并非完全干净：单能力聚合数据有 7,370 条行首 Action 语法异常、1,838 条精确重复对话；多能力数据有 64 条 Action 语法异常。
- 小模型可使用上游 ms-swift、扩展后的 tokenizer、packing 和 assistant label mask 完成训练、保存 checkpoint 并推理。
- 两步短跑只证明训练链路可运行。推理样例参考答案为 2，短跑模型输出 1，不能据此声称能力提升。
