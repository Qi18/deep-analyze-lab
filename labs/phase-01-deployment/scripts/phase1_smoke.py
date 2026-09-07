"""Five deterministic synthetic fixtures; calls unmodified upstream loop and API."""
import argparse, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path
import pandas as pd
import requests
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/"artifacts/phase1"
MODEL = "DeepAnalyze-8B"
def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
def fixtures():
    d = OUT/"inputs"
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"order_id":[1,2,3,4,5,6], "customer_id":[1,2,1,3,2,3],
        "month":["Jan","Jan","Feb","Feb","Mar","Mar"], "amount":[100,200,150,50,300,200]}).to_csv(d/"orders.csv",index=False)
    pd.DataFrame({"customer_id":[1,2,3],"region":["East","West","East"]}).to_excel(d/"customers.xlsx",index=False)
    (d/"dirty.json").write_text(json.dumps([{"id":i+1,"value":v} for i,v in enumerate([10,20,None,30,1000])]))
    save(OUT/"input-manifest.json", [{"name":p.name,"bytes":p.stat().st_size,
        "sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(d.iterdir())])
    return d
TASKS = [
("single",["orders.csv"],"Compute order count, total amount and mean amount from orders.csv.",
 {"count":6,"total":1000,"mean":1000/6}),
("join",["orders.csv","customers.xlsx"],"Join orders.csv to customers.xlsx by customer_id. Compute total amount by region.",
 {"East":500,"West":500}),
("clean",["dirty.json"],"Read dirty.json as records. Drop rows whose value is null or strictly greater than 100. Save cleaned.csv. Report kept row count and mean value.",
 {"count":3,"mean":20}),
("plot",["orders.csv"],"Aggregate amount by month in Jan, Feb, Mar order. Save a line plot to trend.png and the three aggregated rows to trend.csv. Report monthly totals.",
 {"Jan":300,"Feb":200,"Mar":500})
]
SUFFIX = ' Execute Python to verify. Keep analysis brief. End with <Answer> containing a JSON object with the requested numeric results and concise explanation. Use only supplied synthetic files.'
def check_answer(text, expected):
    answer = text.split("<Answer>")[-1] if "<Answer>" in text else ""
    nums = [float(x) for x in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", answer.replace(",",""))]
    return bool(answer) and all(any(abs(n-v)<=max(.02,abs(v)*.001) for n in nums) for v in expected.values())
def cli_one(task_id):
    sys.path.insert(0,str(ROOT/"DeepAnalyze"))
    from deepanalyze import DeepAnalyzeVLLM
    name,names,prompt,expected = next(t for t in TASKS if t[0]==task_id)
    d=OUT/"cli"/name
    d.mkdir(parents=True,exist_ok=True)
    import shutil
    workspace = d/"workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    for n in names: shutil.copy2(OUT/"inputs"/n,workspace/n)
    full="# Instruction\n"+prompt+SUFFIX+"\n\n# Data\n"+"\n".join(names)
    save(d/"request.json",{"prompt":full,"expected":expected,"temperature":0,"max_tokens":4096,"max_rounds":12})
    start=time.monotonic()
    result=DeepAnalyzeVLLM(MODEL,max_rounds=12).generate(full,str(workspace),temperature=0,max_tokens=4096)
    save(d/"response.json",result)
    text=result.get("reasoning","")
    codes=re.findall(r"<Code>(.*?)</Code>",text,re.S)
    save(d/"code-manifest.json",[{"code":c,"sha256":hashlib.sha256(c.encode()).hexdigest()} for c in codes])
    print(json.dumps({"task":name,"seconds":time.monotonic()-start,
        "has_answer":"<Answer>" in text,"has_execution":"<Execute>" in text,
        "numeric_screen":check_answer(text,expected)},ensure_ascii=False))
def api_followup():
    url="http://127.0.0.1:8200"
    d=OUT/"api"; d.mkdir(parents=True,exist_ok=True)
    with (OUT/"inputs/orders.csv").open("rb") as f:
        r=requests.post(url+"/v1/files",files={"file":("orders.csv",f,"text/csv")},timeout=30)
    r.raise_for_status(); save(d/"upload.json",r.json())
    messages=[{"role":"user","content":"Compute total amount from orders.csv."+SUFFIX,"file_ids":[r.json()["id"]]}]
    for i in range(2):
        payload={"model":MODEL,"messages":messages,"temperature":0,"stream":False}
        save(d/f"request-{i+1}.json",payload)
        start=time.monotonic()
        r=requests.post(url+"/v1/chat/completions",json=payload,timeout=600)
        r.raise_for_status(); result=r.json(); save(d/f"response-{i+1}.json",result)
        message=result["choices"][0]["message"]
        print(json.dumps({"task":f"api-{i+1}","seconds":time.monotonic()-start,
                          "thread_id":message.get("thread_id")}),flush=True)
        if i==0:
            messages.append({"role":"assistant","content":message["content"]})
            messages.append({"role":"user","content":"Using the same uploaded orders.csv, what percentage of total amount is from Mar?"+SUFFIX,"thread_id":message["thread_id"]})
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--execute",action="store_true")
    ap.add_argument("--task"); args=ap.parse_args()
    if args.task: return cli_one(args.task)
    if not args.execute:
        print("Will generate synthetic fixtures, run four CLI tasks and one two-turn API task.")
        return
    fixtures()
    records=[]
    for name,*_ in TASKS:
        start=time.monotonic()
        try:
            r=subprocess.run([sys.executable,__file__,"--task",name],capture_output=True,text=True,timeout=600)
            item={"task":name,"returncode":r.returncode,"stdout":r.stdout,"stderr":r.stderr,"seconds":time.monotonic()-start}
        except subprocess.TimeoutExpired as e:
            item={"task":name,"error":"timeout","seconds":time.monotonic()-start}
        records.append(item); save(OUT/"cli-summary.json",records); print(json.dumps(item),flush=True)
    try: api_followup()
    except Exception as e:
        save(OUT/"api-error.json",{"error":repr(e)})
        raise
if __name__=="__main__": main()
