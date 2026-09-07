# 跨阶段脚本

- `bootstrap/`：公共环境与依赖预检。
- `launch/`：跨阶段服务和训练启动。
- `sync/`：整理日志、tracking 链接和实验摘要。
- `evaluate/`：统一正确性、证据、执行恢复与安全评测。
- `cleanup/`：按 checkpoint manifest 清理冗余产物。

只服务于单个阶段的脚本放入对应 `labs/phase-*/scripts/`；成熟且被两个以上阶段复用后，才提升到这里或 `src/`。

脚本必须支持 dry-run 或打印最终命令，并禁止把凭据写进参数、日志和仓库。正式训练前检查 GPU 空闲、CUDA、NCCL、CPFS、`/dev/shm`、模型与数据 revision。
