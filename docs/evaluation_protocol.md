# DeepAnalyze 统一评测协议

评测必须同时覆盖最终答案、分析过程、代码执行、证据质量和安全边界。报告长度、主观流畅度、训练 reward 或单次成功不能单独证明能力提升。

## 固定评测集

第一版至少包含 10 个任务：单表问答、多文件关联、缺失与异常处理、时间趋势、建模、图表一致性、训练 loss 诊断、执行错误恢复、无答案问题和越权测试。固定输入文件、问题、允许工具和参考断言；变更时产生新版本和 manifest。

## 核心指标

| 维度 | 指标 | 说明 |
|---|---|---|
| 正确性 | answer accuracy / numeric error | 最终答案与参考断言 |
| 证据 | grounded claim rate | 结论能否追溯到文件、列和计算 |
| 执行 | code success rate | 代码轮次中成功执行比例 |
| 恢复 | recovery rate | 首次失败后能否正确修复 |
| 图表 | plot validity | 文件存在、可打开且数据一致 |
| 效率 | turns / tokens / latency | 完成任务的交互成本 |
| 稳定性 | repeated-run consistency | 固定配置重复运行差异 |
| 克制 | unsupported claim rate | 无数据支撑或虚构结论比例 |
| 安全 | policy violation count | 文件、网络、进程和凭据越权 |
| 报告 | usefulness / readability | 有用性、结构、局限性表达 |

每次评测保存 prompt、input manifest、model revision、生成参数、Action、执行代码 hash、受限输出、最终答案、参考断言和指标。敏感路径、凭据和完整私有数据不进入 Git。

只有版本已记录、manifest 与断言已固定、全部任务有结果、指标由脚本生成、失败与安全结果进入报告并可复现时，评测状态才是 `completed`。
