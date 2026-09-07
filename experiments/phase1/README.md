# Phase 1：官方部署与五类推理验证

本阶段使用官方 DeepAnalyze-8B 与原始推理/API 实现。任务均来自脚本生成的合成数据；用于验证部署和调用链，不是正式测试集。

## 环境与命令

- 权威工作区：`/data/projects/deep-analyze-lab`
- 权重：`/data/models/DeepAnalyze-8B`
- 模型来源：`RUC-DataLab/DeepAnalyze-8B`；下载 revision 见运行报告
- vLLM：复用只读环境 `/data/venvs/tesla-vllm-085`
- 分析执行环境：`/data/venvs/deepanalyze-phase1`，继承基础 Python 系统包，新增分析依赖
- 原始日志与任务产物：`artifacts/phase1/`（Git 忽略）

```bash
# 在 L20 仓库根目录运行
HF_ENDPOINT=https://hf-mirror.com HF_HUB_DISABLE_XET=1 \
  /data/venvs/tesla-vllm-085/bin/python scripts/launch/phase1_download.py

# 默认打印命令；确认端口和 GPU 0 空闲后执行
/data/venvs/deepanalyze-phase1/bin/python scripts/launch/phase1_services.py
/data/venvs/deepanalyze-phase1/bin/python scripts/launch/phase1_services.py --execute

curl -fsS http://127.0.0.1:8000/v1/models
curl -fsS http://127.0.0.1:8200/health

/data/venvs/deepanalyze-phase1/bin/python scripts/eval/phase1_smoke.py --execute
```

服务只监听回环地址。API 启动包装器设置监听地址并提供文件 HTTP 服务，使用上游 create_app、存储和执行逻辑。CLI 调用上游 DeepAnalyzeVLLM.generate；没有新增 Agent Loop。原始执行器并非安全沙箱，仅执行本阶段的受控合成样例。

## 输入与参考断言

| 任务 | 路径 | 输入 | 参考结果 |
|---|---|---|---|
| 单表统计 | CLI | orders.csv | 6 笔，总额 1000，均值 166.6667 |
| 多文件关联 | CLI | orders.csv + customers.xlsx | East=500，West=500 |
| 清洗 | CLI | dirty.json | 删除 null 和 value>100，剩余 3 行，均值 20；输出 cleaned.csv |
| 绘图 | CLI | orders.csv | Jan=300、Feb=200、Mar=500；输出 trend.csv、trend.png |
| 多轮追问 | API 两次请求 | 上传 orders.csv 后复用 thread | 首问总额 1000；追问 Mar 占比 50% |

CLI 配置：temperature=0、max_tokens=4096、max_rounds=12、单任务墙钟上限 600 秒。API 使用官方默认生成上限，客户端请求超时 600 秒；两条路径的性能数字不能当作同配置对照。

脚本的 numeric_screen 只是数值候选检查，最终通过情况需回读答案含义、执行反馈与产物。成功与失败均保留。每个 CLI 子进程独立运行，避免上游全局 cwd 改动互相影响。

## 学习问题

1. stop=</Code> 如何触发执行，role=execute 如何进入下一轮？
2. CLI 的 max_rounds 和 API 的 while 循环终止行为有何差异？
3. CLI exec 与 API 子进程执行在状态持久化、超时方面有何差异？
4. thread_id 如何关联已上传文件，多轮追问为什么仍需完整历史？
5. 最终答案与真实执行结果如何核对？

状态和实测结果见 [report.md](report.md)。
