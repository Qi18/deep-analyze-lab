# Phase 1 源码学习：从文件到报告

源码基线：`d14468b9ef91372359ddcd70da57e0e0f4eb0d1b`。以下是源码事实；运行表现另见 Phase 1 报告。

## 入口在哪里

- CLI：`DeepAnalyze/deepanalyze.py::DeepAnalyzeVLLM.generate`
- API：`DeepAnalyze/API/main.py::create_app` → `chat_api.py::chat_completions`
- 文件：`file_api.py` 上传 → `storage.py` 元数据 → thread workspace
- 报告：`utils.py::generate_report_from_messages`

## 数据如何流动

CLI 把用户问题发送到 vLLM，使用 `stop=["</Code>"]` 切分生成和执行。得到代码后调用 `execute_code`，把执行结果作为 `role="execute"` 加入消息列表，模型再生成下一轮内容。出现 `<Answer>` 或达到轮数上限时结束。

API 把上传文件复制到 thread workspace；`prepare_vllm_messages` 自动补充 Instruction 和 Data 文件列表。代码交给独立 Python 子进程；执行输出进入下一轮消息。最终把对话中的 Action 和输出整理为 Markdown 报告并返回文件 URL。

## 为什么这样设计

模型根据真实执行输出继续分析，可以纠正文件读取、列名或计算问题。Workspace 使多轮请求复用文件；同一 thread 的后续请求仍需传入完整对话历史。

CLI 每次 `exec(code_str, {})` 使用新的全局字典，Python 变量不会跨代码轮次保留；文件可以保留。API 每次运行一个新 Python 子进程，也不会保留内存变量。

## 本阶段观察重点

- CLI 请求没有显式 HTTP timeout，且宽泛异常捕获仅返回已有 reasoning；外层实验子进程设置 600 秒上限。
- CLI 默认最多 30 轮，本次样例设置 12 轮；API 非流式请求内部仍使用流式模型调用，循环中没有对应的最大轮数变量。
- API 代码执行有超时；“safe”函数名不意味着文件系统或网络已隔离。
- 生成回答需要与执行输出和产物核对；仅看到自然语言声称成功不算完成。
- 四个 CLI 样例和一个 API 两轮样例使用不同调用路径，耗时只能作为各自观测值。

## 如何从实验中学习

运行后逐一回读 `artifacts/phase1/cli/*/response.json` 与 `api/response-*.json`，找到首次 Code、Execute 和 Answer，解释每次继续生成的原因。用输入参考断言检查最终答案，再核对 cleaned.csv、trend.csv、trend.png 和 API 报告链接。未通过的任务保留原始结果，作为 Phase 2 分析材料。
