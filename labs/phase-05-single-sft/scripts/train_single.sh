#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="${REPO_ROOT:-/data/projects/deep-analyze-lab}"
PYTHON_BIN="${PYTHON_BIN:-/data/venvs/deepanalyze-train/bin/python}"
PHASE5_GPUS="${PHASE5_GPUS:-2,3,4,5,6,7}"
MAX_LENGTH="${MAX_LENGTH:-2048}"
MAX_STEPS="${MAX_STEPS:-3}"
GRAD_ACCUM="${GRAD_ACCUM:-1}"
DATASET_PATH="${DATASET_PATH:-$REPO_ROOT/artifacts/phase5/data/smoke-96.jsonl}"
OUTPUT_DIR="${OUTPUT_DIR:-$REPO_ROOT/artifacts/phase5/smoke-2048}"
MODEL_PATH="${MODEL_PATH:-/data/models/DeepSeek-R1-0528-Qwen3-8B-phase5-addvocab}"
MASTER_PORT="${MASTER_PORT:-29615}"
export CUDA_HOME=/usr/local/cuda
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export HF_DATASETS_CACHE="$REPO_ROOT/artifacts/phase5/cache/hf-datasets"
export MODELSCOPE_CACHE="$REPO_ROOT/artifacts/phase5/cache/modelscope"
export TMPDIR="$REPO_ROOT/artifacts/phase5/cache/tmp"
export TRITON_CACHE_DIR="$REPO_ROOT/artifacts/phase5/cache/triton"
export TORCH_EXTENSIONS_DIR="$REPO_ROOT/artifacts/phase5/cache/torch-extensions"
export CUDA_CACHE_PATH="$REPO_ROOT/artifacts/phase5/cache/cuda"
mkdir -p "$HF_DATASETS_CACHE" "$MODELSCOPE_CACHE" "$TMPDIR" "$TRITON_CACHE_DIR" "$TORCH_EXTENSIONS_DIR" "$CUDA_CACHE_PATH"
export CUDA_VISIBLE_DEVICES="$PHASE5_GPUS" OMP_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
export PYTHONPATH="$REPO_ROOT/DeepAnalyze/deepanalyze/ms-swift"
IFS=, read -ra PHASE5_DEVICE_ARRAY <<< "$PHASE5_GPUS"
for gpu in "${PHASE5_DEVICE_ARRAY[@]}"; do
  used=$(nvidia-smi -i "$gpu" --query-gpu=memory.used --format=csv,noheader,nounits)
  if (( used > 1000 )); then
    echo "GPU $gpu already uses $used MiB; refusing to overlap another workload" >&2
    exit 2
  fi
done
test -f "$DATASET_PATH"
test -f "$MODEL_PATH/config.json"
cd "$REPO_ROOT/DeepAnalyze/deepanalyze/ms-swift"
exec "$PYTHON_BIN" -m torch.distributed.run --nproc_per_node="${#PHASE5_DEVICE_ARRAY[@]}" \
  --master_port="$MASTER_PORT" -m swift.cli.sft \
  --model "$MODEL_PATH" --model_type deepseek_r1_distill --train_type full \
  --dataset "$DATASET_PATH" --torch_dtype bfloat16 \
  --max_steps "$MAX_STEPS" --num_train_epochs 3 --per_device_train_batch_size 1 \
  --gradient_accumulation_steps "$GRAD_ACCUM" --learning_rate 5e-5 \
  --packing true --max_length "$MAX_LENGTH" --truncation_strategy delete \
  --gradient_checkpointing true --warmup_ratio 0.05 --seed 42 --data_seed 42 \
  --dataloader_num_workers 0 --dataset_num_proc "${DATASET_NUM_PROC:-1}" --split_dataset_ratio 0 \
  --save_strategy steps --save_steps "${SAVE_STEPS:-200}" --save_total_limit 2 --save_only_model "${SAVE_ONLY_MODEL:-true}" \
  --eval_strategy no --logging_steps 1 --response_prefix "" \
  --output_dir "$OUTPUT_DIR" --deepspeed zero3 \
  --use_liger_kernel "${USE_LIGER:-false}" --attn_impl flash_attn --report_to none
