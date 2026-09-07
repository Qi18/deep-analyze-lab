# 复现规范

每次正式运行必须在 `experiments.csv` 登记，并记录 Lab commit、上游 commit、模型 revision、数据 manifest、配置、seed、运行命令、硬件环境和报告路径。

## Git 内保存

- 可执行脚本和配置。
- 小型合成 fixture 与数据 manifest。
- 环境摘要、指标 JSON、校验和、失败分析和报告。
- 不包含凭据的命令和 tracking 链接。

## Git 外保存

- 模型权重、checkpoint 和优化器状态。
- 完整训练数据、缓存和大体积日志。
- 临时工作目录和生成文件。

Git 外产物保存在 L20 `artifacts/` 或专用数据目录；报告必须给出路径、哈希或可重建方法。运行完成不等于实验通过，只有自动断言、人工复核和报告均完成后，状态才可标记为 completed。
