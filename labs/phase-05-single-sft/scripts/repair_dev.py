#!/usr/bin/env python3
"""Fresh 32-case development gate. Generated code is interpreted, never exec'ed."""
import argparse, ast, copy, json, math, operator, re
from pathlib import Path
FENCE=chr(96)*3
def cases():
    result=[]
    for family in range(8):
        for variant in range(4):
            checks=[]
            for shift in [0,9]:
                k=variant+shift+2; vals=[k,-2,k+3,0,k,-5]
                if family==0:
                    inp={"values":vals};expected=sum(vals);ref="result = sum(values)"
                    task="Compute the sum of values."
                elif family==1:
                    inp={"values":vals};expected=sorted(set(vals));ref="result = sorted(set(values))"
                    task="Return the sorted unique values as a list."
                elif family==2:
                    inp={"records":[{"region":"east","sales":k},{"region":"west","sales":k+7},{"region":"east","sales":2*k}],"region":"east"}
                    expected=3*k;ref="result = sum(r['sales'] for r in records if r['region'] == region)"
                    task="Sum sales only for records whose region equals the supplied region variable."
                elif family==3:
                    inp={"values":vals,"threshold":k-1};expected=[v for v in vals if v>k-1]
                    ref="result = [v for v in values if v > threshold]"
                    task="Keep values strictly greater than threshold, preserving order."
                elif family==4:
                    inp={"matrix":[[k,2],[-1,k+1],[3,k]]};expected=3*k+5
                    ref="result = sum(sum(row) for row in matrix)";task="Compute the sum of all numbers in matrix."
                elif family==5:
                    inp={"values":[k,2*k,k+1],"weights":[1,2,3]};expected=(k+4*k+3*(k+1))/6
                    ref="result = sum(v*w for v,w in zip(values,weights)) / sum(weights)"
                    task="Compute the weighted mean of values using weights."
                elif family==6:
                    inp={"values":vals};expected={"positive":sum(v>0 for v in vals),"negative":sum(v<0 for v in vals)}
                    ref="result = {'positive': sum(v > 0 for v in values), 'negative': sum(v < 0 for v in values)}"
                    task="Return a dict with keys positive and negative counting strictly positive and negative values; ignore zeros."
                else:
                    inp={"scores":{"red":k,"blue":k+6,"green":k+1}};expected=k+6
                    ref="result = max(scores.values())";task="Return the largest score value."
                checks.append({"inputs":inp,"expected":expected})
            context="\n".join(f"{name} = {value!r}" for name,value in checks[0]["inputs"].items())
            prompt=(task+"\nThe inputs already exist and will vary in tests. Do not hard-code or redefine them. "
                    "Use pure Python built-ins only, without imports. Assign the answer to result. "
                    "Return only missing statements in a fenced Python code block, with no explanation.\n"
                    "Existing context:\n"+FENCE+"python\n"+context+"\n"+FENCE+"\nMissing statements:\n")
            result.append({"id":f"repair-dev-{family}-{variant}","family":family,
                           "prompt":prompt,"checks":checks,"reference":ref})
    return result

class RestrictedPython:
    """Bounded AST interpreter supporting only the documented development subset."""
    def __init__(self, inputs):self.env=copy.deepcopy(inputs);self.fuel=10000
    def tick(self):
        self.fuel-=1
        if self.fuel<0:raise ValueError("operation_budget")
    def checked(self,v):
        if isinstance(v,(str,list,tuple,dict,set,range)) and len(v)>1000:raise ValueError("value_too_large")
        if isinstance(v,(int,float)) and (not math.isfinite(v) or abs(v)>1e12):raise ValueError("number_too_large")
        return v
    def bind(self,node,v):
        if isinstance(node,ast.Name):
            if node.id.startswith("_"):raise ValueError("private_name")
            self.env[node.id]=self.checked(v)
        elif isinstance(node,(ast.Tuple,ast.List)):
            if len(node.elts)!=len(v):raise ValueError("unpack")
            for n,x in zip(node.elts,v):self.bind(n,x)
        elif isinstance(node,ast.Subscript):
            obj=self.expr(node.value);key=self.expr(node.slice);obj[key]=self.checked(v)
        else:raise ValueError("unsupported_target")
    def expr(self,n):
        self.tick()
        if isinstance(n,ast.Constant):return self.checked(n.value)
        if isinstance(n,ast.Name):return self.env[n.id]
        if isinstance(n,(ast.List,ast.Tuple,ast.Set)):
            v=[self.expr(x) for x in n.elts]
            return v if isinstance(n,ast.List) else tuple(v) if isinstance(n,ast.Tuple) else set(v)
        if isinstance(n,ast.Dict):return {self.expr(k):self.expr(v) for k,v in zip(n.keys,n.values)}
        if isinstance(n,ast.Subscript):return self.expr(n.value)[self.expr(n.slice)]
        if isinstance(n,ast.Slice):return slice(*(self.expr(v) if v is not None else None for v in [n.lower,n.upper,n.step]))
        if isinstance(n,ast.BinOp):
            a,b=self.expr(n.left),self.expr(n.right)
            ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
                 ast.Div:operator.truediv,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod}
            if isinstance(n.op,ast.Mult):
                if isinstance(a,(list,tuple,str)) and isinstance(b,int) and len(a)*abs(b)>1000:raise ValueError("allocation")
                if isinstance(b,(list,tuple,str)) and isinstance(a,int) and len(b)*abs(a)>1000:raise ValueError("allocation")
            if isinstance(a,str) and isinstance(n.op,ast.Mod):raise ValueError("string_format")
            return self.checked(ops[type(n.op)](a,b))
        if isinstance(n,ast.UnaryOp):
            return {ast.USub:operator.neg,ast.UAdd:operator.pos,ast.Not:operator.not_}[type(n.op)](self.expr(n.operand))
        if isinstance(n,ast.Compare):
            left=self.expr(n.left)
            ops={ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Lt:operator.lt,ast.LtE:operator.le,
                 ast.Gt:operator.gt,ast.GtE:operator.ge,ast.In:lambda a,b:a in b,ast.NotIn:lambda a,b:a not in b,
                 ast.Is:operator.is_,ast.IsNot:operator.is_not}
            for op,right_node in zip(n.ops,n.comparators):
                right=self.expr(right_node)
                if not ops[type(op)](left,right):return False
                left=right
            return True
        if isinstance(n,ast.BoolOp):
            val=None
            for item in n.values:
                val=self.expr(item)
                if isinstance(n.op,ast.And) and not val:return val
                if isinstance(n.op,ast.Or) and val:return val
            return val
        if isinstance(n,ast.IfExp):return self.expr(n.body if self.expr(n.test) else n.orelse)
        if isinstance(n,(ast.ListComp,ast.GeneratorExp,ast.SetComp,ast.DictComp)):
            values=[]
            def walk(i):
                if i==len(n.generators):
                    values.append((self.expr(n.key),self.expr(n.value)) if isinstance(n,ast.DictComp) else self.expr(n.elt))
                    self.checked(values);return
                g=n.generators[i]
                if g.is_async:raise ValueError("async")
                for v in self.expr(g.iter):
                    self.tick();self.bind(g.target,v)
                    if all(self.expr(c) for c in g.ifs):walk(i+1)
            walk(0)
            return dict(values) if isinstance(n,ast.DictComp) else set(values) if isinstance(n,ast.SetComp) else values
        if isinstance(n,ast.Call):
            args=[self.expr(a) for a in n.args];kwargs={k.arg:self.expr(k.value) for k in n.keywords}
            if None in kwargs:raise ValueError("kwargs_unpack")
            allowed={"sum":sum,"len":len,"sorted":sorted,"set":set,"list":list,"dict":dict,"min":min,"max":max,
                     "abs":abs,"round":round,"enumerate":lambda a:list(enumerate(a)),
                     "zip":lambda *a:list(zip(*a)),"range":lambda *a:self.checked(range(*a)),
                     "int":int,"float":float}
            if isinstance(n.func,ast.Name):
                v=allowed[n.func.id](*args,**kwargs)
                if isinstance(v,range):v=list(v)
            elif isinstance(n.func,ast.Attribute):
                obj=self.expr(n.func.value);name=n.func.attr
                if isinstance(obj,dict) and name in {"items","keys","values","get"}:
                    v=getattr(obj,name)(*args,**kwargs)
                    if name!="get":v=list(v)
                elif isinstance(obj,list) and name in {"append","count","index","sort"}:
                    v=getattr(obj,name)(*args,**kwargs);self.checked(obj)
                else:raise ValueError("unsupported_method")
            else:raise ValueError("unsupported_call")
            return self.checked(v)
        raise ValueError("unsupported_expression:"+type(n).__name__)
    def statements(self,body):
        for n in body:
            self.tick()
            if isinstance(n,ast.Assign):
                v=self.expr(n.value)
                for target in n.targets:self.bind(target,v)
            elif isinstance(n,ast.AugAssign):
                self.bind(n.target,self.expr(ast.BinOp(left=n.target,op=n.op,right=n.value)))
            elif isinstance(n,ast.For):
                for v in self.expr(n.iter):
                    self.tick();self.bind(n.target,v);self.statements(n.body)
                self.statements(n.orelse)
            elif isinstance(n,ast.If):self.statements(n.body if self.expr(n.test) else n.orelse)
            elif isinstance(n,ast.Expr):self.expr(n.value)
            elif isinstance(n,ast.Pass):pass
            else:raise ValueError("unsupported_statement:"+type(n).__name__)
    def run(self,code):
        if len(code)>20000:raise ValueError("code_too_long")
        tree=ast.parse(code)
        if sum(1 for _ in ast.walk(tree))>2000:raise ValueError("ast_too_large")
        self.statements(tree.body);return self.env["result"]
def equal(a,b):
    if isinstance(b,float):return isinstance(a,(float,int)) and math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-8)
    return a==b
def score(case,text):
    blocks=re.findall(FENCE+r"python\s*\n?(.*?)"+FENCE,text,re.S)
    out={"id":case["id"],"has_code":bool(blocks),"passed":False}
    if not blocks:return dict(out,error="missing_code")
    code=blocks[-1].strip("\n")
    try:
        passed=all(equal(RestrictedPython(c["inputs"]).run(code),c["expected"]) for c in case["checks"])
        return dict(out,passed=passed,error=None if passed else "wrong_result")
    except Exception as e:return dict(out,error=type(e).__name__+":"+str(e)[:160])
def summarize(rows):
    return {"count":len(rows),"passed":sum(r["passed"] for r in rows),
            "has_code":sum(r["has_code"] for r in rows),"ended":sum(r["ended"] for r in rows),
            "length_limited":sum(r["finish_reason"]=="length" for r in rows),
            "repetitive":sum(r["repetitive"] for r in rows)}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--max-tokens",type=int,default=2048);args=p.parse_args()
    if args.output.exists():raise RuntimeError("Refusing to overwrite development results")
    from vllm import LLM,SamplingParams
    from transformers import AutoTokenizer
    data=cases();tok=AutoTokenizer.from_pretrained(args.model)
    prompts=[tok.apply_chat_template([{"role":"user","content":r["prompt"]}],tokenize=False,
             add_generation_prompt=False,enable_thinking=True) for r in data]
    model=LLM(model=args.model,max_model_len=4096,max_num_seqs=8,gpu_memory_utilization=0.85,
              tensor_parallel_size=1,enforce_eager=True,seed=42)
    outputs=model.generate(prompts,SamplingParams(temperature=0,max_tokens=args.max_tokens),use_tqdm=True)
    from collections import Counter
    rows=[]
    for case,output in zip(data,outputs):
        gen=output.outputs[0];text=gen.text
        lines=[s.strip() for s in text.splitlines() if len(s.strip())>30]
        repeated=max(Counter(lines).values(),default=0)>=10
        rows.append(dict(score(case,text),response=text,tokens=len(gen.token_ids),
                         finish_reason=gen.finish_reason,ended=gen.finish_reason=="stop",repetitive=repeated))
    result={"model":args.model,"protocol":"repair-dev-v1: 32 fresh pure-Python tasks, two input checks each",
            "max_tokens":args.max_tokens,"temperature":0,"summary":summarize(rows),"rows":rows,
            "limitations":"Restricted AST scorer rejects unsupported Python. Development regression gate only; not DS-1000."}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result["summary"]),flush=True)
if __name__=="__main__":main()
