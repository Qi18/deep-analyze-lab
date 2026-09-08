# Repair-v1 双卡执行调整

用户选择先使用已有空闲 GPU，不暂停 MiniMind。2026-09-08 检查：GPU 2、3 空闲，4–7 属于 MiniMind Phase 7，0、1 保留推理服务。

## 固定配置

- 8B 全参数训练，GPU 2、3；ZeRO-3 参数和优化器卸载到 CPU。
- micro batch 1，梯度累积 126，有效 batch 252，学习率 1e-5。
- packing 8192，原有 62,327 条 / 99,956,985 tokens 数据不变。
- 最多一轮、累计训练进程时间上限 12 小时；双卡不保证完整跑完一轮，不宣称完成完整 SFT。
- 第 1 步保存并检查开发集，后续每 10 步检查；保留原退化停止门槛。
- 到预算上限后，仅从已完成开发集检查且合格的 checkpoint 中选择官方评测模型。
- 开发集和官方评测均仅使用本次指定卡，不扩展到 MiniMind 的卡；评测时间另计。

## 启动与证据

先以 0.6B、双卡 CPU offload 验证第 1 步保存及恢复至第 2 步，完整优化器和调度器状态必须通过检查，才更新 preflight.json 并启动 8B。

启动环境：PHASE5_GPUS=2,3 DEEPSPEED_CONFIG=zero3_offload MAX_JOBS=4。
入口：labs/phase-05-single-sft/scripts/run_repair.py。实时证据：artifacts/phase5/repair-v1/state.json、config.json、logs/train-to-1.log、progress.json。原六卡说明为先前方案，本文件记录本次资源调整。
