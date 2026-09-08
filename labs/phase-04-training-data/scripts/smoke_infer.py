#!/usr/bin/env python3
"""Run one deterministic generation from a Phase 4 smoke checkpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=64)
    args = parser.parse_args()

    records = json.loads(args.dataset.read_text(encoding="utf-8"))
    prompt = records[0]["messages"][0]["content"]
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        local_files_only=True,
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    ).cuda()
    rendered = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    inputs = tokenizer(rendered, return_tensors="pt").to(model.device)
    torch.manual_seed(42)
    torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            do_sample=False,
            max_new_tokens=args.max_new_tokens,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_ids = generated[0, inputs["input_ids"].shape[1] :]
    text = tokenizer.decode(new_ids, skip_special_tokens=False)
    if not new_ids.numel() or not text.strip():
        raise RuntimeError("smoke inference produced no output")

    result = {
        "model": str(args.model),
        "dataset": str(args.dataset),
        "sample_index": 0,
        "input_tokens": inputs["input_ids"].shape[1],
        "generated_tokens": int(new_ids.numel()),
        "max_new_tokens": args.max_new_tokens,
        "deterministic": True,
        "peak_gpu_memory_gib": round(torch.cuda.max_memory_allocated() / 1024**3, 3),
        "output": text,
        "purpose": "runtime validation only; output quality is not evaluated",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
