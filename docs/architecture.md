# 系统架构

```text
用户请求与文件
      │
      ▼
API / CLI 入口
      │
      ▼
DeepAnalyze 模型 ── 生成 Analyze / Understand / Code
      ▲                         │
      │                         ▼
执行反馈消息 ◀──────── Python 执行环境与工作目录
      │
      └──────── 多轮循环 ──────┘
                    │
                    ▼
             Answer / 图表 / 报告
                    │
                    ▼
        Lab 评分器与人工证据复核
```

## 代码归属

- 上游推理和 API：`DeepAnalyze/`。
- 单阶段复现包装器：`labs/phase-*/scripts/`。
- 通用运行时、数据和评测实现：成熟后进入 `src/deep_analyze_lab/`。
- 评测协议和简历证据口径：`docs/`。
- 大体积运行证据：L20 的 `artifacts/`。

所有增强都必须在同一输入、生成预算和执行预算下，与上游基线对照。
