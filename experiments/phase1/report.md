# Phase 1 实验报告：官方模型部署与五类样例

## 状态与范围

**本阶段运行及结果核验已完成；任务结果为 3 passed / 1 partial / 1 failed。**

官方模型部署、CLI 多轮代码执行、API 上传/追问及报告下载已验证。五类任务均为小型合成数据，每类仅运行一次；这不是正式基准准确率，也不代表训练效果。本阶段未训练、未修复模型失败、未修改上游源码。

## 环境

- 实验代码起点：`d9002cc89e7d72ec1101e1e68f9684f783d74315`；服务脚本之后补充按服务启动和端口检查，最终代码随本报告提交。
- 上游源码：`d14468b9ef91372359ddcd70da57e0e0f4eb0d1b`。
- 模型：`RUC-DataLab/DeepAnalyze-8B`，revision `214c302cebc61ed92f9c856a3dd47a7fdc588d5f`。
- 下载经 HF 镜像，12 个选定文件约 668 秒完成；四个权重分片的索引总 tensor bytes 为 16,381,470,720。
- 8×L20 可见；推理只使用 GPU 0。驱动 535.161.08。
- 执行环境：Python 3.10.12、PyTorch 2.6.0+cu124、pandas 2.2.3、numpy 1.26.4。
- 推理环境：vLLM 0.8.5.post1、torch 2.6.0、transformers 4.51.3。
- 真实 CUDA 矩阵乘法结果：32768.0，符合预期。
- BF16、max_model_len=32768、TP=1、gpu_memory_utilization=0.85、max_num_seqs=2、eager、服务 seed=42。
- 运行结束时 GPU 0 占用 36,108 MiB；这是结束时快照，不是峰值指标。
- 启动出现 YaRN 配置字段 `attn_factor` 未识别警告。服务实际成功加载并推理；本报告不声明与论文推理配置完全等价。

依赖 freeze、安装日志、服务命令及 PID 保存在 L20 `artifacts/phase1/`。模型/分词器 SHA-256 见 [model-sha256.txt](model-sha256.txt)，环境摘要见 [environment.json](environment.json)。

## 任务结果

| 任务 | 路径 | 核验结果 | 代码轮次/错误 | 调用耗时 | 结论 |
|---|---|---|---|---:|---|
| 单表统计 | CLI | 6 笔，总额 1000，均值 166.67 | 2 / 0 | 19.67 s | passed |
| 多文件关联 | CLI | CSV 与 Excel 关联，East/West 各 500 | 3 / 1 | 29.03 s | passed，自动恢复 |
| 数据清洗 | CLI | 删除 null 和 >100，实际 CSV 剩余 id 1/2/4，均值 20 | 3 / 1 | 36.04 s | passed，自动恢复 |
| 月度绘图 | CLI | 三个月数值正确，CSV/PNG 已生成，但月份顺序错误 | 2 / 0 | 26.92 s | failed |
| API 多轮追问 | API 两次请求 | 同一 thread，首问 1000，追问 Mar 占比 50%；首问解释有错误 | 独立 API 路径 | 19.62 + 11.48 s | partial |

CLI 耗时来自 generate 调用；API 耗时来自请求。它们使用不同执行路径和输出预算，不能作为性能对照。结果 JSON 见 [results.json](results.json)。

## 关键发现

### 执行错误能够触发恢复

关联任务第二次代码执行引用上一轮的 `pd` 等变量，引发 `NameError`。上游执行器每轮使用新命名空间。模型接收错误后重新导入 pandas、读取文件并计算，最终得到正确地区汇总。

清洗任务也记录一次执行错误并最终恢复。CLI 共 10 次代码执行，其中 2 次带错误反馈；仅作为这四个样例的观察，不能泛化为恢复率指标。

### 正确数字不能证明图表正确

模型使用 `sort_values('month')` 按字母排序，将曲线画成：

```text
Feb 200 → Jan 300 → Mar 500
```

用户要求 Jan、Feb、Mar 顺序，正确时间趋势应为 300 → 200 → 500。实际查看 PNG 确认顺序错误，图表造成了错误的持续上升印象。原始趋势 CSV 与 PNG 已保留，未替换成修正版本。

### API 答案和解释出现不一致

首问的 total_amount=1000 正确，但 explanation 写：

```text
100+200+150+50+300+100=1000
```

左侧实际为 900；最后一笔订单本应是 200。后续追问正确返回 50%。因此“API 多轮链路可用”和“解释完全准确”分别记录，任务整体为 partial。

### 报告下载已验证

两次 API 响应均返回 Markdown 报告链接。实际 HTTP 下载成功，文件分别为 4694 和 7122 bytes，SHA-256 已写入 results.json。

## 原始产物

L20 仓库中的 `artifacts/phase1/`：

- `download.log`、`model-sha256.txt`：模型准备与校验。
- `environment.json`、`execution-freeze.txt`、`inference-freeze.txt`：环境。
- `services.json`、`api.log`、`vllm.log`：服务状态、请求与采样记录。
- `inputs/`、`input-manifest.json`：可重建合成数据及校验。
- `cli/*/request.json`、`response.json`、`code-manifest.json`：请求、完整 Action 轨迹和代码。
- `cli/*/workspace/`：模型输入及实际生成文件。
- `api/request-*.json`、`response-*.json`、`downloads/`：上传、同线程追问和报告。
- `cli-summary.json`、`smoke.log`、`verification.json`：运行时间和核验结果。

全部数据是实验脚本生成的合成样例。原始完整日志不进 Git，仓库保存摘要和复现入口。

## 学习产物与下一步

已补充 [Phase 1 调用链笔记](../../docs/source_reading/phase1-inference.md)，解释 stop token、execute 消息、CLI/API 执行差异、thread 文件复用和报告生成。

Phase 2 可沿两条真实轨迹学习：变量丢失后如何自我修复、为什么执行成功仍产生错误时间顺序。绘图顺序和解释错误应进入之后的评测断言，本阶段不根据这些样例修改模型或上游代码。
