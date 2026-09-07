import os, json
from huggingface_hub import HfApi, snapshot_download
api=HfApi(endpoint="https://hf-mirror.com")
info=api.model_info("RUC-DataLab/DeepAnalyze-8B")
print("REVISION", info.sha, flush=True)
path=snapshot_download("RUC-DataLab/DeepAnalyze-8B", revision=info.sha, local_dir="/data/models/DeepAnalyze-8B", max_workers=4, ignore_patterns=["*.png","*.jpg"])
print("MODEL_READY", path, flush=True)
