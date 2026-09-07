"""Record reproducible runtime versions and a real CUDA smoke operation."""
import hashlib, importlib.metadata as md, json, platform, subprocess
from pathlib import Path
import torch
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/"artifacts/phase1"; out.mkdir(parents=True,exist_ok=True)
def cmd(args): return subprocess.check_output(args,text=True).strip()
d={"python":platform.python_version(),"lab_commit":cmd(["git","-C",str(ROOT),"rev-parse","HEAD"]),
"source_commit":"d14468b9ef91372359ddcd70da57e0e0f4eb0d1b",
"gpu":cmd(["nvidia-smi","--query-gpu=name,memory.total,driver_version","--format=csv,noheader"]),
"cuda_available":torch.cuda.is_available(),"cuda_count":torch.cuda.device_count(),
"torch":torch.__version__,"torch_cuda":torch.version.cuda,
"cuda_matmul_sum":float((torch.ones((32,32),device="cuda")@torch.ones((32,32),device="cuda")).sum().item()),
"packages":{p:md.version(p) for p in ["pandas","numpy","openpyxl","matplotlib","requests","fastapi","openai"]}}
(out/"environment.json").write_text(json.dumps(d,indent=2))
print(json.dumps(d,indent=2))
