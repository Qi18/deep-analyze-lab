from huggingface_hub import snapshot_download

REVISION = "214c302cebc61ed92f9c856a3dd47a7fdc588d5f"
print("REVISION", REVISION, flush=True)
path=snapshot_download("RUC-DataLab/DeepAnalyze-8B", revision=REVISION, local_dir="/data/models/DeepAnalyze-8B", max_workers=4, ignore_patterns=["*.png","*.jpg"])
print("MODEL_READY", path, flush=True)
