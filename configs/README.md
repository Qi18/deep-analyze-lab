# 配置目录

- `inference/`：模型服务、生成参数和上下文长度。
- `single_ability_sft/`：单能力 SFT。
- `multi_ability_coldstart/`：多能力交互轨迹 cold start。
- `agentic_rl/`：GRPO、rollout、environment 和 reward。
- `evaluation/`：固定任务集、评测器和安全回归。

正式配置必须记录模型 revision、数据 manifest、硬件、dtype、seed 和对应实验 ID。
