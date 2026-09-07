# DeepAnalyze 上游来源与同步

- 上游仓库：`https://github.com/ruc-datalab/DeepAnalyze`
- 上游分支：`main`
- 初始 commit：`d14468b9ef91372359ddcd70da57e0e0f4eb0d1b`
- 导入方式：Git Subtree，prefix 为 `DeepAnalyze/`
- 固定日期：2026-09-01

`DeepAnalyze/` 在本仓库中是普通源码目录，不是 Submodule。任何源码结论和正式实验都必须同时记录 Lab commit 与上游来源 commit。

## 更新流程

```bash
git switch -c feature/sync-deepanalyze-upstream
git subtree pull \
  --prefix=DeepAnalyze \
  git@github.com:ruc-datalab/DeepAnalyze.git \
  main --squash
```

同步后检查源码 diff，更新上游 commit，运行 import/API/推理 smoke test，检查 Action Token、API schema、训练脚本和环境接口变化，并重新执行固定评测集。
