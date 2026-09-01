# 仓库管理方式

`deepanalyze-lab` 保存推理、训练与评测配置，L20 脚本，实验元数据、指标、源码笔记和报告。`DeepAnalyze/` 是通过 Git Subtree 导入的普通源码目录，保存官方源码和本 Lab 的源码修改。

## 权威工作区

L20 的 `/data/projects/deepanalyze-lab` 是权威 checkout。代码修改、验证、commit 和 push 都在 L20 完成，不使用本地仓库中转。

正式实验前记录：Lab commit、DeepAnalyze source commit、源码 dirty 状态、model revision、hardware、dtype、dataset version、seed、command 和 tracking URL。工作区不干净时停止正式实验。

## 分支与实验

- `main`：只保存已验证、可公开复现的实验资产。
- `feature/<name>`：推理循环、沙箱、统一评测、奖励函数等改造。
- 仅参数不同的运行用实验 ID 区分，不创建分支。
- 实验 ID 使用 `<stage>-<subject>-<variant>-<date>`。

每个正式实验目录至少包含 `config.json`、`command.sh`、`run.json`、`metrics.csv`、`eval.json`、`report.md`、`checkpoint-manifest.txt` 和 `tracking-url.txt`。

## 结果边界

| 内容 | GitHub | SwanLab/HF | L20 |
|---|---:|---:|---:|
| 配置、命令和指标摘要 | 是 | 可选 | 是 |
| 完整日志 | 否 | 否 | 是 |
| 数据集 | 仅 manifest | 外部来源 | 是 |
| 中间 checkpoint | 否 | 否 | 是 |
| 最终选中权重 | 链接 | 是 | 是 |

凭据、用户敏感数据、完整模型权重和原始生产日志不得进入 Git。

## 上游源码工作流

```bash
git switch -c feature/sync-deepanalyze-upstream
git subtree pull \
  --prefix=DeepAnalyze \
  git@github.com:ruc-datalab/DeepAnalyze.git \
  main --squash
```

同步后检查源码 diff、运行推理 smoke test，更新 [`upstream-deepanalyze.md`](upstream-deepanalyze.md) 和实验元数据。正式实验开始后不得自动漂移源码版本。

## 发布门槛

配置、命令、commit、数据版本、目标评测和安全回归必须齐全；报告数值必须能追溯到实际数据，并说明收益、代价、失败和适用边界。
