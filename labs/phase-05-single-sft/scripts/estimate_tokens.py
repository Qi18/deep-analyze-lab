#!/usr/bin/env python3
"""Estimate token volume with the same upstream training template on a fixed sample."""
import argparse, json, random, statistics, math
from pathlib import Path
from swift.llm import get_model_tokenizer, get_template
ROOT = Path(__file__).resolve().parents[3]
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sample-size", type=int, default=2048)
    args=p.parse_args()
    rng=random.Random(42); sample=[]; count=0
    with (ROOT/"artifacts/phase5/data/single-clean-v1.jsonl").open() as f:
        for line in f:
            count+=1
            if len(sample)<args.sample_size:
                sample.append(line)
            else:
                i=rng.randrange(count)
                if i<args.sample_size: sample[i]=line
    _, tokenizer=get_model_tokenizer("/data/models/DeepSeek-R1-0528-Qwen3-8B-phase5-addvocab",
                                    model_type="deepseek_r1_distill",load_model=False)
    template=get_template("deepseek_r1",tokenizer,response_prefix="",max_length=200000)
    template.mode="train"
    lengths=[len(template.encode(json.loads(line))["input_ids"]) for line in sample]
    kept=[v if v<=8192 else 0 for v in lengths]
    mean=statistics.mean(kept)
    se=statistics.stdev(kept)/math.sqrt(len(kept))
    result=dict(source_records=count,sample_size=len(sample),seed=42,
        template="deepseek_r1",max_length=8192,response_prefix="",
        sample_actual_over_limit=sum(v>8192 for v in lengths),
        estimated_tokens_per_epoch=round(mean*count),
        approximate_95pct_token_interval=[round((mean-1.96*se)*count),round((mean+1.96*se)*count)],
        estimated_packed_sequences_per_epoch=math.ceil(mean*count/8192),
        caveat="Uniform sample estimate; actual packing efficiency, long-example filtering and training duration must be measured separately.")
    out=ROOT/"labs/phase-05-single-sft/results/token-estimate.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result))
if __name__=="__main__": main()
