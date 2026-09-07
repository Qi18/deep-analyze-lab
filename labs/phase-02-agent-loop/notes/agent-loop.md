# Agent Loop 与执行反馈源码笔记

源码基线：DeepAnalyze commit `d14468b9ef91372359ddcd70da57e0e0f4eb0d1b`。

## CLI 调用链

`DeepAnalyze/deepanalyze.py` 的 `generate()` 在 `max_rounds` 范围内循环：

1. 请求 vLLM 时传入 `stop=["</Code>"]`。
2. 当响应的 `stop_reason` 是 `</Code>`，宿主把被服务端截掉的闭合标签补回。
3. 宿主先检查响应中是否出现 `<Answer>`；出现便立即结束。
4. 没有 Answer 时，用正则提取第一个 `<Code>...</Code>`。
5. `execute_code()` 通过 `exec(code, {})` 执行，并捕获 stdout/stderr。
6. 下一次请求追加 assistant 代码消息和 `{"role": "execute", "content": exe_output}`。

因此，`</Code>` 本身不执行代码。它只是生成停止边界；真正的提取和执行发生在宿主程序收到响应以后。模型看到的 `<Execute>` 是结果展示形式，下一轮请求中的真实消息角色是 `execute`。

## CLI 终止行为

- 响应只包含 Analyze/Understand：追加为 assistant 消息并进入下一轮。
- 响应包含 Answer：立即终止，即使同一响应前面还有 Code，该 Code 也不会执行。
- 达到 `max_rounds`：返回已有 reasoning，没有显式的 incomplete/error 状态。
- 请求或宿主异常：异常被顶层捕获，只返回截至当时的 reasoning。
- CLI 执行没有超时限制，而且 `os.chdir(workspace)` 修改进程级工作目录。

确定性契约测试验证了上述分支，包括闭合 Code、execute 角色、最大轮数和 Answer 优先级。

## CLI 与 API 执行差异

| 行为 | CLI | API |
|---|---|---|
| 生成停止 | 字符串 `</Code>` | `STOP_TOKEN_IDS` |
| Answer 终止 | 出现 `<Answer>` | 流式内容出现 `</Answer>` |
| 执行方式 | 当前进程 `exec(code, {})` | 临时 Python 文件 + 子进程 |
| 状态持久化 | 每个 exec 使用新字典 | 每次启动新进程 |
| 超时 | 无 | 默认 120 秒 |
| Python 异常 | 格式化为 `[Error]` | stderr 原样返回，通常无 `[Error]` 前缀 |
| 临时文件 | 无 | finally 中删除 |
| 安全隔离 | 不是沙箱 | 有进程和时间边界，但仍不是安全沙箱 |

## 本轮真实反馈轨迹

真实执行器产生 FileNotFoundError、NameError 和一秒 Timeout，然后把原始文本作为 `role=execute` 交给官方模型：

- 缺失文件：模型用一轮生成直接返回 insufficient_data，没有编造数据。
- NameError：模型生成新代码，执行得到 5，下一轮返回 recovered=true。
- Timeout：模型第一次新代码没有 print，得到空反馈；第二次代码依赖上一轮未保留的 `time`，触发 NameError；第三次重新 import 后执行成功，第四轮回答。这条轨迹同时证明每轮子进程不保留 Python 状态。

## 评测启示

只在自然语言中搜索 “NameError” 或 “FileNotFoundError” 会产生假阳性。两条提示驱动实验没有任何 Code/Execute 动作，却在分析和最终答案中声称已完成恢复。后续评分器必须分别检查：

1. 是否存在闭合的 Code 动作。
2. 错误是否出现在真实 Execute 块。
3. 错误之后是否出现新的 Code。
4. 新 Code 是否获得成功 Execute 证据。
5. Answer 是否与执行结果一致。
