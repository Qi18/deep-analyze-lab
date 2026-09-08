# Phase 3 学习笔记：官方评测方法

## 1. 固定上游版本实际提供了什么

`DeepAnalyze/playground/` 中有四组评测入口：

| 基准 | 评测对象 | 评分方式 | 当前可复现性 |
|---|---|---|---|
| DS-1000 | 数据科学代码生成 | 执行生成代码，通过/失败 | 数据与评分器随仓，最完整 |
| TableQA | 表格问答 | exact match / 部分 LLM judge | 脚本齐全，但需要外部数据目录 |
| DSBench | 数据分析与建模 | 任务答案或竞赛指标 | 需要外部下载数据 |
| DABStep-Research | 多文件研究报告 | LLM judge 的 Content/Format 1–5 分 | 100 个问题随仓，context 数据与 judge endpoint 未固定 |

因此“官方评测”不是一个统一命令。Phase 3 先选可严格固定的 DS-1000，不为缺失数据或评审模型自行造替代品。

## 2. DS-1000 的数据流

```text
ds1000.jsonl.gz
  → 官方 prompt 变换
  → vLLM 批量生成
  → 提取最后一个 python fenced block
  → code_context + generated code
  → 独立进程执行 test_execution / test_string
  → overall、library、perturbation pass rate
```

每个样本的 `code_context` 同时包含测试生成逻辑和参考行为。评分器将生成代码注入测试程序并在独立进程中执行，单题超时 120 秒。最终通过率比字符串相似度更贴近代码是否真的解决问题。

## 3. 本 Lab 的封装边界

`scripts/ds1000.py` 只做四件事：

1. 校验官方数据、推理器、评分器和执行 harness 的 SHA256；
2. 把整个官方目录复制到 Git 忽略的 artifact 工作区，避免污染 `DeepAnalyze/`；
3. 选择固定模型路径与 GPU 后调用官方命令；
4. 统计结果条数、静态审计生成代码并调用官方 evaluator。

它不改 prompt、batch、max token、代码提取或评分逻辑。外层 namespace 只用于执行安全，不参与得分。任何为兼容模型而修改上述评分行为的实验必须另起实验 ID，不能继续叫官方结果。

## 4. 为什么还需要 CoDA-Bench

DS-1000 直接把目标问题上下文交给模型，主要衡量代码生成能力，不能测量在大量文件中发现正确数据的 Agent 能力。

CoDA-Bench 的核心是 Data Intelligence + Code Intelligence：Agent 在平均约 980 个文件的社区目录中自行发现目标文件，再写代码回答。官方指标为：

- EA：最终答案与 gold answer 匹配的任务比例；
- DA：发现全部目标文件的任务比例，读取额外文件不扣分。

正式协议还要求每题独立 Docker、数据只读、禁用普通网络、限制 CPU/内存/超时，并禁止把答案、reference code、data path 或目标文件名提供给 Agent。当前 L20 Pod 没有 Docker，所以只能记录环境阻塞，不能用 host direct mode 冒充正式结果。

## 5. 对后续训练实验的约束

- Base、SFT、Cold Start、RL、Official 都使用相同的官方数据、prompt、后处理和评分器。
- DS-1000 报告代码执行通过率；CoDA-Bench 报告 EA/DA，二者不能合并为一个“准确率”。
- 训练数据必须与官方测试题、答案和 reference code 隔离。
- Phase 3 先做单次基线；最终简历数字还需要固定 seed 的重复运行与方差。
- 自建 50 题只保留用于动作状态、恢复、图表和安全回归，不进入官方 benchmark 对比表。

## 6. 实测结果与观察

- Base：300/1000，execution pass rate 30.0%。
- DeepAnalyze-8B：587/1000，execution pass rate 58.7%。
- 绝对提升：28.7 个百分点；这是单次 temperature=0 结果。
- DeepAnalyze-8B 有 954 条输出包含可抽取 Python block，Base 为 736 条；缺失 block 由官方后处理变为空代码。
- DeepAnalyze-8B 生成明显快于 Base，Base 更常持续生成到 16K 上限；速度现象与正确率分别记录，不互相代替。

## 7. 执行边界

官方 harness 在临时目录中逐题执行并设置 120 秒超时，但没有启用 `reliability_guard()`。Lab 先对 2000 条答案做静态审计，未发现敏感路径、网络、进程或删除操作；随后在禁网的 user/mount namespace 中遮蔽 `/data`、HOME、SSH 和 service-account 路径并清空环境变量。

完全遮蔽 `/proc` 会使 TensorFlow 题崩溃，L20 Pod 又不允许挂载新的 procfs。经用户明确批准，本次评分保留宿主 `/proc` 可见。这个限制必须保留在报告中，不能把它描述成 Docker 等级隔离。
