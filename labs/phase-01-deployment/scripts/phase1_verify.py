"""Phase 1 fixture-specific verification, not a general benchmark scorer."""
import json,re,hashlib,math,subprocess
from pathlib import Path
import pandas as pd
import requests
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]; OUT=ROOT/"artifacts/phase1"
def read(p): return json.loads(p.read_text())
def answer(t):
    t=t.split("<Answer>")[-1]
    return json.JSONDecoder().raw_decode(t[t.index("{"):])[0]
summary=[]
for name in ["single","join","clean","plot"]:
    d=OUT/"cli"/name; t=read(d/"response.json")["reasoning"]; a=answer(t)
    if name=="single":
        checks={"count":a["order_count"]==6,"total":a["total_amount"]==1000,"mean":abs(a["mean_amount"]-1000/6)<.02}
    elif name=="join":
        checks={"regions":{x["Region"]:x["Total Amount"] for x in a["result"]}=={"East":500,"West":500}}
    elif name=="clean":
        df=pd.read_csv(d/"workspace/cleaned.csv")
        checks={"answer":a["kept_row_count"]==3 and a["mean_value"]==20,
                "file":df["id"].tolist()==[1,2,4] and df["value"].tolist()==[10,20,30]}
    else:
        df=pd.read_csv(d/"workspace/trend.csv")
        with Image.open(d/"workspace/trend.png") as im: im.verify()
        checks={"totals":dict(zip(df["month"],df["amount"]))=={"Jan":300,"Feb":200,"Mar":500},
                "month_order":df["month"].tolist()==["Jan","Feb","Mar"],"png_decodable":True}
    codes=re.findall(r"<Code>(.*?)</Code>",t,re.S)
    exes=re.findall(r"<Execute>(.*?)</Execute>",t,re.S)
    summary.append({"task":name,"checks":checks,"status":"passed" if all(checks.values()) else "failed",
                    "code_rounds":len(codes),"execution_errors":sum("[Error]" in e for e in exes),"answer":a})
a1=read(OUT/"api/response-1.json")["choices"][0]["message"]
a2=read(OUT/"api/response-2.json")["choices"][0]["message"]
checks={"same_thread":a1["thread_id"]==a2["thread_id"],
"total":answer(a1["content"])["total_amount"]==1000,
"march_percentage":answer(a2["content"])["percentage_march"]==50}
downloads=[]
for message in [a1,a2]:
 for f in message.get("files",[]):
    r=requests.get(f["url"],timeout=20); r.raise_for_status()
    dst=OUT/"api/downloads"/f["name"];dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(r.content)
    downloads.append({"name":f["name"],"bytes":len(r.content),"sha256":hashlib.sha256(r.content).hexdigest()})
checks["reports_downloaded"]=len(downloads)==2 and all(f["bytes"]>0 for f in downloads)
equations = re.findall(r"(\d+(?:\+\d+)+)=(\d+)", answer(a1["content"])["explanation"].replace(" ", ""))
checks["explanation_arithmetic"] = all(sum(map(int,lhs.split("+")))==int(rhs) for lhs,rhs in equations)
summary.append({"task":"followup","checks":checks,"status":"passed" if all(checks.values()) else "partial",
"manual_review":"Both numeric answers are correct. First response explanation writes 100+200+150+50+300+100=1000, whose addends sum to 900; actual last order is 200. Evidence text is inconsistent.",
"reports":downloads})
result={"scope":"five synthetic smoke task types, one run each; not benchmark accuracy",
"tasks":summary,"passed":sum(x["status"]=="passed" for x in summary),
"partial":sum(x["status"]=="partial" for x in summary),
"failed":sum(x["status"]=="failed" for x in summary),
"upstream_modified":subprocess.run(["git","-C",str(ROOT),"diff","--quiet","HEAD","--","DeepAnalyze"]).returncode != 0}
(OUT/"verification.json").write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps(result,indent=2,ensure_ascii=False))
