# 实验脚本

- `launch/`：L20 预检、服务和训练启动。
- `sync/`：整理日志、tracking 链接和实验摘要。
- `eval/`：统一正确性、证据、执行恢复与安全评测。
- `cleanup/`：按 checkpoint manifest 清理冗余产物。

脚本必须支持 dry-run 或打印最终命令，并禁止把凭据写进参数、日志和仓库。正式训练前检查 GPU 空闲、CUDA、NCCL、CPFS、`/dev/shm`、模型与数据 revision。
