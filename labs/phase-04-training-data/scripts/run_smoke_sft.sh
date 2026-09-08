#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/data/projects/deep-analyze-lab}"
PYTHON_BIN="${PYTHON_BIN:-/data/venvs/deepanalyze-train/bin/python}"
MODEL_PATH="${MODEL_PATH:-/data/models/Qwen3-0.6B-c1899de-addvocab}"
DATASET_PATH="${DATASET_PATH:-${REPO_ROOT}/artifacts/phase4/smoke/single-ability-32.json}"
OUTPUT_DIR="${OUTPUT_DIR:-${REPO_ROOT}/artifacts/phase4/smoke/run}"
SMOKE_GPU="${SMOKE_GPU:-2}"

test -x "${PYTHON_BIN}"
test -f "${MODEL_PATH}/config.json"
test -f "${DATASET_PATH}"

cd "${REPO_ROOT}/DeepAnalyze/deepanalyze/ms-swift"
env CUDA_VISIBLE_DEVICES="${SMOKE_GPU}" \
  PYTHONPATH=. \
  TOKENIZERS_PARALLELISM=false \
  "${PYTHON_BIN}" -m swift.cli.sft \
    --model "${MODEL_PATH}" \
    --model_type qwen3 \
    --train_type full \
    --dataset "${DATASET_PATH}" \
    --torch_dtype bfloat16 \
    --max_steps 2 \
    --per_device_train_batch_size 1 \
    --gradient_accumulation_steps 1 \
    --packing true \
    --max_length 2048 \
    --learning_rate 1e-5 \
    --warmup_ratio 0 \
    --save_strategy steps \
    --save_steps 2 \
    --save_only_model true \
    --eval_strategy no \
    --logging_steps 1 \
    --dataloader_num_workers 0 \
    --dataset_num_proc 1 \
    --response_prefix "" \
    --output_dir "${OUTPUT_DIR}" \
    --attn_impl flash_attn \
    --report_to none \
    --use_liger_kernel false
