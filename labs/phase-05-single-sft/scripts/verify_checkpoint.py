#!/usr/bin/env python3
"""Reload an 8B smoke checkpoint and generate one deterministic output."""
import argparse, json
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--dataset", required=True)
    p.add_argument("--output", required=True)
    args=p.parse_args()
    with open(args.dataset) as f: item=json.loads(next(f))
    t=AutoTokenizer.from_pretrained(args.model,local_files_only=True)
    m=AutoModelForCausalLM.from_pretrained(args.model,local_files_only=True,
        torch_dtype=torch.bfloat16,attn_implementation="flash_attention_2").cuda().eval()
    actions=[f"<{slash}{name}>" for name in ["Analyze","Understand","Code","Execute","Answer"] for slash in ["","/"]]
    action_ids={a:t.encode(a,add_special_tokens=False) for a in actions}
    assert all(len(ids)==1 for ids in action_ids.values())
    assert len(t)==m.get_input_embeddings().weight.shape[0]==m.get_output_embeddings().weight.shape[0]
    # Match the vendored deepseek_r1 training template with response_prefix="".
    prompt="<｜begin▁of▁sentence｜><｜User｜>"+item["messages"][0]["content"]+"<｜Assistant｜>"
    inputs=t(prompt,return_tensors="pt",add_special_tokens=False).to("cuda")
    torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode():
        result=m.generate(**inputs,max_new_tokens=64,do_sample=False,pad_token_id=t.eos_token_id)
    generated=result[0,inputs["input_ids"].shape[1]:]
    assert generated.numel()>0
    output=dict(model=args.model,action_token_ids=action_ids,embedding_rows=len(t),
        input_tokens=inputs["input_ids"].shape[1],generated_tokens=generated.numel(),
        output=t.decode(generated,skip_special_tokens=False),
        peak_allocated_gib=round(torch.cuda.max_memory_allocated()/1024**3,3),
        scope="Checkpoint load/generation only; no correctness or model-quality claim.")
    Path(args.output).write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v for k,v in output.items() if k!="output"}))
if __name__=="__main__":main()
