#!/usr/bin/env python3
"""Audit 15 source files; make a fixed source/actual-length-stratified token budget."""
import argparse, collections, gzip, hashlib, json, random, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"labs/phase-04-training-data/scripts"))
from audit_training_data import iter_json_array,hash_file,validate_tags
from repair_dev import cases
BASE="/data/models/DeepSeek-R1-0528-Qwen3-8B-phase5-addvocab"
def normalized(s):return " ".join(s.split())
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--target-tokens",type=int,default=100_000_000)
    p.add_argument("--output",type=Path,default=ROOT/"artifacts/phase5/repair-v1/data")
    args=p.parse_args()
    if args.output.exists():raise RuntimeError("Use a fresh data directory; never overwrite a version")
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(BASE)
    source_root=Path("/data/datasets/DataScience-Instruct-500K/f2dd0a62927f49f0a1d2465e32dc4072910e7c89")
    official=re.findall(r'\$\{DATA_DIR\}/(reasoning/[^"]+\.json)',(ROOT/"DeepAnalyze/scripts/single.sh").read_text())
    assert len(official)==13
    sources=official+["reasoning/dscode_16338.json","reasoning/TableQA_original_35357.json"]
    benchmark=ROOT/"DeepAnalyze/playground/DS-1000/data/ds1000.jsonl.gz"
    with gzip.open(benchmark,"rt") as f:excluded={normalized(json.loads(l)["prompt"]) for l in f}
    excluded.update(normalized(c["prompt"]) for c in cases())
    pools=collections.defaultdict(list);seen=set();audits=[]
    for source in sources:
        path=source_root/source
        stats=collections.Counter();pending=[]
        def encode_pending():
            if not pending:return
            texts=[tok.bos_token+"<｜User｜>"+r["messages"][0]["content"]+
                   "<｜Assistant｜>"+r["messages"][1]["content"]+tok.eos_token for r,_,_ in pending]
            lengths=tok(texts,add_special_tokens=False,return_length=True)["length"]
            for (record,row,digest),length in zip(pending,lengths):
                if length>8192:stats["sample_actual_over_8192"]+=1;continue
                bucket="0-2048" if length<=2048 else "2049-4096" if length<=4096 else "4097-8192"
                pools[(source,bucket)].append((digest,length,record,row))
                stats["candidate_kept"]+=1;stats["candidate_tokens"]+=length
            pending.clear()
        for row,record in enumerate(iter_json_array(path)):
            stats["raw"]+=1
            messages=record.get("messages",[])
            if (not isinstance(messages,list) or len(messages)!=2 or
                any(not isinstance(m,dict) for m in messages) or
                [m.get("role") for m in messages]!=["user","assistant"] or
                any(not isinstance(m.get("content"),str) or not m["content"].strip() for m in messages)):
                stats["schema_invalid"]+=1;continue
            answer=messages[-1]["content"]
            if not validate_tags(answer)[1]:stats["tag_invalid"]+=1;continue
            if answer.count(chr(96)*3)%2:stats["unclosed_fence"]+=1;continue
            lines=[s.strip() for s in answer.splitlines() if len(s.strip())>30]
            if max(collections.Counter(lines).values(),default=0)>=10:
                stats["repetitive_answer"]+=1;continue
            if normalized(messages[0]["content"]) in excluded:stats["exact_eval_prompt"]+=1;continue
            clean={"messages":messages}
            digest=hashlib.sha256(json.dumps(clean,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            if digest in seen:stats["exact_duplicate"]+=1;continue
            seen.add(digest)
            if int(digest[:8],16)>=2**30:stats["outside_fixed_quarter_sample"]+=1;continue
            stats["sampled_for_actual_encoding"]+=1
            pending.append((clean,row,digest))
            if len(pending)>=128:encode_pending()
        encode_pending()
        assert stats["raw"]==int(re.search(r"_(\d+)\.json$",source).group(1))
        audits.append({"source":source,"sha256":hash_file(path),"stats":dict(stats),
                       "in_official_single_script":source in official})
        print(json.dumps(audits[-1]),flush=True)
    total=sum(item[1] for pool in pools.values() for item in pool)
    assert total>=args.target_tokens*.95,("Insufficient candidates",total)
    ratio=min(1,args.target_tokens/total);chosen=[];strata=[]
    for (source,bucket),pool in sorted(pools.items()):
        pool.sort(key=lambda x:x[0]);available=sum(x[1] for x in pool);quota=int(available*ratio)
        used=0;count=0
        for digest,length,record,row in pool:
            if used+length>quota:continue
            chosen.append((source,bucket,row,digest,length,record));used+=length;count+=1
        strata.append({"source":source,"actual_length_bucket":bucket,"candidate_records":len(pool),
                       "candidate_tokens":available,"selected_records":count,"selected_tokens":used})
    random.Random(42).shuffle(chosen)
    selected_tokens=sum(x[4] for x in chosen)
    assert 80_000_000<=selected_tokens<=120_000_000,selected_tokens
    args.output.mkdir(parents=True)
    data=args.output/"train.jsonl";refs=args.output/"rows.jsonl"
    with data.open("w") as f,refs.open("w") as rf:
        for source,bucket,row,digest,length,record in chosen:
            f.write(json.dumps(record,ensure_ascii=False)+"\n")
            rf.write(json.dumps({"source":source,"row":row,"digest":digest,"tokens":length,"bucket":bucket})+"\n")
    manifest={"version":"repair-v1-100m","dataset_revision":source_root.name,"base_model":BASE,
              "target_tokens":args.target_tokens,"actual_tokens":selected_tokens,"records":len(chosen),
              "candidate_tokens":total,"sha256":hash_file(data),"row_manifest_sha256":hash_file(refs),
              "source_script_sha256":hash_file(ROOT/"DeepAnalyze/scripts/single.sh"),
              "development_source_sha256":hash_file(Path(__file__).with_name("repair_dev.py")),
              "files":audits,"strata":strata,"seed":42,
              "policy":"15-file audited variant; schema/action/fence/repetition checks; exact prompt exclusion and conversation dedup; deterministic hash-quarter candidates; actual template length <=8192; proportional token retention within source x actual-length strata.",
              "limitations":"Not exact paper reproduction. No semantic decontamination guarantee. Strata reflect eligible candidate mix, not the distribution before filtering. Gold evaluation outputs are never training data."}
    (args.output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"records":len(chosen),"actual_tokens":selected_tokens,"sha256":manifest["sha256"]}),flush=True)
if __name__=="__main__":main()
