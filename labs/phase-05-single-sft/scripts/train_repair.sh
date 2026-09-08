#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${REPO_ROOT:-/data/projects/deep-analyze-lab}"
REPAIR_ROOT="${REPAIR_ROOT:-$REPO_ROOT/artifacts/phase5/repair-v1}"
PYTHON_BIN="${PYTHON_BIN:-/data/venvs/deepanalyze-train/bin/python}"
PHASE5_GPUS="${PHASE5_GPUS:-2,3,4,5,6,7}"
MODEL_PATH="${MODEL_PATH:-/data/models/DeepSeek-R1-0528-Qwen3-8B-phase5-addvocab}"
DATASET_PATH="${DATASET_PATH:-$REPAIR_ROOT/data/train.jsonl}"
OUTPUT_DIR="${OUTPUT_DIR:-$REPAIR_ROOT/train}"
export CUDA_HOME=/usr/local/cuda
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export CUDA_VISIBLE_DEVICES="$PHASE5_GPUS" OMP_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
export PYTHONPATH="$REPO_ROOT/DeepAnalyze/deepanalyze/ms-swift"
export HF_DATASETS_CACHE="$REPAIR_ROOT/cache/hf-datasets" MODELSCOPE_CACHE="$REPAIR_ROOT/cache/modelscope"
export TMPDIR=/dev/shm
export TRITON_CACHE_DIR="$REPAIR_ROOT/cache/triton" TORCH_EXTENSIONS_DIR="$REPAIR_ROOT/cache/torch-extensions"
export CUDA_CACHE_PATH="$REPAIR_ROOT/cache/cuda"
mkdir -p "$HF_DATASETS_CACHE" "$MODELSCOPE_CACHE" "$TRITON_CACHE_DIR" "$TORCH_EXTENSIONS_DIR" "$CUDA_CACHE_PATH"
IFS=, read -ra DEVICES <<< "$PHASE5_GPUS"
for gpu in "${DEVICES[@]}"; do
  used=$(nvidia-smi -i "$gpu" --query-gpu=memory.used --format=csv,noheader,nounits)
  if (( used > 1000 )); then echo "GPU $gpu occupied: $used MiB" >&2; exit 2; fi
done
test -f "$DATASET_PATH"
EXTRA=()
if [[ -n "${RESUME_FROM:-}" ]]; then EXTRA+=(--resume_from_checkpoint "$RESUME_FROM"); fi
cd "$REPO_ROOT/DeepAnalyze/deepanalyze/ms-swift"
exec "$PYTHON_BIN" -m torch.distributed.run --nproc_per_node="${#DEVICES[@]}" --master_port="${MASTER_PORT:-29625}" -m swift.cli.sft \
  --model "$MODEL_PATH" --model_type deepseek_r1_distill --train_type full --torch_dtype bfloat16 \
  --dataset "$DATASET_PATH" --max_steps "${MAX_STEPS:--1}" --num_train_epochs 1 \
  --per_device_train_batch_size "${MICRO_BATCH:-1}" --gradient_accumulation_steps "${GRAD_ACCUM:-42}" \
  --learning_rate "${LEARNING_RATE:-1e-5}" --warmup_ratio 0.1 --lr_scheduler_type cosine \
  --packing true --max_length "${MAX_LENGTH:-8192}" --truncation_strategy delete \
  --gradient_checkpointing true --seed 42 --data_seed 42 --split_dataset_ratio 0 \
  --dataset_num_proc 8 --dataloader_num_workers 0 --eval_strategy no --logging_steps 1 \
  --save_strategy steps --save_steps "${SAVE_STEPS:-10}" --save_total_limit 8 --save_only_model false \
  --response_prefix "" --output_dir "$OUTPUT_DIR" --add_version false --deepspeed "${DEEPSPEED_CONFIG:-zero3}" \
  --use_liger_kernel true --attn_impl flash_attn --report_to none \
  --external_plugins "$REPO_ROOT/labs/phase-05-single-sft/scripts/repair_callback.py" "${EXTRA[@]}"
