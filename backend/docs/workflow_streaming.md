# workflow_streaming.py 设计与调用流程说明

本文详细说明 `backend/src/graph/workflow_streaming.py` 中各函数/类的职责、相互关联、以及一次完整对话在该模块内的时序与数据流。阅读本文件后，你可以快速定位扩展点（如插入搜索智能体、修改意图识别策略、变更流式推送格式等）。

## 模块定位

- 该模块是“流式工作流编排器”：接收来自 API 层（`routes.py`，REST 或 WebSocket）的用户输入，驱动意图识别、参数澄清、知识检索、方案生成/优化、信息/闲聊回复，并通过回调将“思考步骤与内容块”以流式方式推送给前端。
- 上游：`src/api/routes.py` 调用导出函数 `process_user_input_streaming(...)`，并传入 `WorkflowState` 与 `websocket_callback`（可选）。
- 下游：
  - `nodes/`：方案生成/优化节点（`direct_streaming_planning_nodes.py`）与分阶段参数澄清节点（`staged_parameter_clarification_node.py`）。
  - `tools/knowledge_tools.py`：本地知识库检索（封装 `rag/knowledge_base.py` 的 FAISS 向量检索）。
  - `tools/satellite_extractor.py`：从文本中提取卫星名称。
  - DeepSeek API：用于意图识别与闲聊/信息类回复的流式生成。

---

## 关键数据结构与依赖

- `WorkflowState`（定义于 `src/graph/state.py`）：贯穿全流程的对话状态容器，包含 `messages`、`metadata`、`thinking_steps`、`main_plan`、`retrieved_knowledge` 等。
- WebSocket 回调：模块内部统一通过 `self.send_status(...)` 和 `StreamingContentSender` 发送如下事件给前端：
  - `processing_start`：开始处理
  - `thinking_step`：思考步骤/阶段进度
  - `response_chunk`：内容分片（流式）
  - `processing_complete`：处理完成
  - `error`：错误提示
- 外部节点/工具：
  - `generate_constellation_plan_streaming` / `optimize_constellation_plan_streaming`（方案生成/优化，流式回调）
  - `process_staged_parameter_clarification` / `process_staged_clarification_response`（分阶段参数收集）
  - `retrieve_knowledge_for_workflow`（从需求生成查询→本地向量库检索→回写 state）

---

## 函数与类总览（按出现顺序）

- 工具函数
  - `convert_to_json_serializable(obj)`：递归将 `numpy`、自定义对象等转换为标准 JSON 可序列化类型。
  - `safe_json_dumps(obj, **kwargs)`：在 `json.dumps` 失败时自动做类型转换后再序列化。
  - `extract_satellites_from_plan(plan_content)`：调用统一提取器从生成的方案文本中异步提取卫星名称。

- 内容流式发送器
  - `class StreamingContentSender`：负责“自然分段”并以 `response_chunk` 事件流式推送文本。
    - `send_content_streaming(content, chunk_size=15, delay=0.1)`：依据段落/句号切分为小片段，逐片发送。
    - `_split_content_naturally(content)`：段落优先、长段落再按句子切分，控制单 chunk 长度。

- 编排器（核心）
  - `class StreamingWorkflowManager`
    - `__init__(websocket_callback)`：注入回调，初始化会话/去重集合/内容发送器。
    - `send_status(message_type, data)`：统一的事件发送入口，带去重逻辑（防止重复思考步）。
    - `reset_session()`：重置“思考步去重集合”和 session id，便于每轮用户输入从干净状态开始。
    - `_smart_truncate_history(history_messages, current_message, max_messages=20)`：基于“最近 + 相关性”选择对话历史子集。（用于控制传给 LLM 的上下文长度）
    - `_extract_keywords(text)`、`_calculate_relevance(text, keywords)`：关键词提取与简易相关性评估（配合历史截断）。
    - `generate_response_streaming(state)`：根据意图生成最终文本回复（方案/优化→直接回显方案文本；信息/闲聊→调用专用生成函数），并写入 `messages`。
    - `generate_intent_confirmation_message(intent, user_message)`：当意图为“生成方案”时生成确认提示（是否执行生成）。
    - `handle_intent_confirmation(state, user_response)`：处理用户对确认提示的回复（确认/否认/提供新意图），必要时再次进行意图分析。
    - `process_user_input_streaming(user_input, state)`：主流程入口（详见“整体流程”章节）。
    - `generate_greeting_response_streaming` / `generate_thanks_response_streaming` / `generate_chat_response_streaming` / `generate_info_response_streaming` / `generate_general_response_streaming`：不同意图的流式回复生成；其中“chat/info”会调用 DeepSeek 流式接口。
    - `_call_deepseek_streaming_for_chat` / `_call_deepseek_streaming_for_info`：准备 system 提示词与上下文后，调用通用流式接口。
    - `_stream_deepseek_response(system_prompt, user_message)` / `_stream_deepseek_response_with_history(system_prompt, user_message, conversation_history)`：DeepSeek 流式 API 的统一封装（SSE/分片解析 → 逐片推送 `response_chunk`）。
    - `initialize_state_streaming(state, user_input)`：添加用户消息、设置阶段、推送“初始化”思考步；若处于澄清流程中，标记为澄清回复。
    - `deepseek_intent_analysis(user_message, conversation_history, state)`：调用 DeepSeek 做“意图识别”，失败则回退为 `chat`。
    - `analyze_user_input_streaming(state)`：综合对话历史与最新用户消息完成意图识别；若判定为生成新方案且已有方案，重置澄清相关标志与阶段，标记“新方案请求起点”。
    - `retrieve_knowledge_streaming(state)`：
      1) 本地知识库检索（`retrieve_knowledge_for_workflow`）并推送思考步；
      2) 若配置了网络搜索工具（`web_search_tools`），则进行网络增强与知识整合；
      3) 设置流程阶段并返回。
    - `generate_plan_streaming(state)`：调用“方案生成”流式节点，把节点回调转发为 `response_chunk`；阶段推进到 `respond`。
    - `optimize_plan_streaming(state)`：按用户最新消息作为优化依据，调用“方案优化”流式节点，回调转发与阶段推进同上。
    - `handle_parameter_clarification(state)`：驱动分阶段参数收集（开始/继续/响应用户回答），并把节点回调转发为 `thinking_step`/`clarification_update` 等；阶段在 `awaiting_clarification` 与 `retrieve_knowledge` 之间切换。

- 模块级导出与持久化
  - `process_user_input_streaming(user_input, state=None, websocket_callback=None)`：对外唯一入口（供 `routes.py` 调用），创建 `StreamingWorkflowManager` 并代理到其同名方法。
  - `save_state(state, filepath)` / `load_state(filepath)`：对 `WorkflowState` 的 JSON 持久化与加载（带类型转换与错误日志）。

---

## 主流程（process_user_input_streaming）

以下描述来自 `StreamingWorkflowManager.process_user_input_streaming(...)` 的控制流，展示一次“用户输入 → 处理 → 流式推送 → 完成”的完整路径。

1) 启动与初始化
   - 发送 `processing_start`
   - `initialize_state_streaming`：把用户输入写入 `state.messages`，推送“初始化”思考步，设置阶段为 `analyze_input`

2) 快速分流：是否处于参数澄清会话中？
   - 若 `state.metadata["awaiting_clarification"] == True`：
     - 直接进入 `handle_parameter_clarification` 处理用户澄清回复，期间通过回调持续推送澄清问题/进度
     - 若仍需更多澄清：返回“等待参数澄清”的完成态，结束本轮
     - 若澄清完成：继续使用之前保存的意图进入后续流程

3) 意图确认分支（仅限 generate_plan）
   - 若正在等待“意图确认”（`awaiting_intent_confirmation` 为真），调用 `handle_intent_confirmation`：
     - 确认：写入 `intent_confirmed=True`，继续流程
     - 否认且给出新需求：调用 `deepseek_intent_analysis` 重新识别意图，生成新的确认提示并流式推送，结束本轮
     - 否认但信息不足：发送引导澄清消息，结束本轮

4) 意图识别（非澄清状态且不在确认交互中）
   - `analyze_user_input_streaming`：
     - 调用 `deepseek_intent_analysis` → 返回 `greeting/thanks/generate_plan/optimize_plan/provide_info/chat`
     - 若判定为“生成新方案”且 `state.main_plan` 已存在：重置澄清状态/阶段并 `mark_new_plan_request()`
     - 写入 `state.metadata["intent"]`

5) 生成方案的“确认门”
   - 若意图为 `generate_plan` 且 `state.intent_confirmed` 为假：
     - 生成确认提示（`generate_intent_confirmation_message`）并流式推送
     - 标记 `awaiting_intent_confirmation=True`，结束本轮（等待用户回复）

6) 各意图处理与流式输出
   - `greeting/thanks/chat/provide_info`：分别调用对应的流式回复生成函数；
   - `generate_plan`：
     - 若未完成参数澄清：`handle_parameter_clarification` 并早退（等待用户继续澄清）
     - 完成澄清后：`retrieve_knowledge_streaming` → `generate_plan_streaming` → `generate_response_streaming`
   - `optimize_plan`：
     - 有现有方案：`optimize_plan_streaming` → `generate_response_streaming`
     - 无现有方案：退化为生成流程（检索→生成→响应）

7) 统一收尾
   - 确定 `assistant_response`（若过程为纯流式，最终从 `state.messages` 取最新助手文本）
   - 推送“处理完成（processing_complete）”，包含：`extracted_satellites` 与 `location`（简化后不再附带可视化数据）
   - 返回 `(state, assistant_response)` 给上游（`routes.py` 会负责持久化和 API 返回）

---

## 事件与前端协作协议（回调数据）

- `processing_start`: `{ message, conversation_id }`
- `thinking_step`: `{ step, message, timestamp, stage? }`（自动去重，避免重复刷屏）
- `response_chunk`: `{ content, accumulated_content, chunk_type }`
  - `chunk_type` 取值：`streaming_response`（一般文本）、`plan_generation`、`plan_optimization`、`ai_response`（DeepSeek）等
- `processing_complete`: `{ message: "处理完成", extracted_satellites, location }`
- `error`: `{ message, response }`
- `clarification_update` / `clarification_question`：由澄清节点回调透传（在 `handle_parameter_clarification` 中转发为“思考步或更新”事件）

---

## 与外部模块的耦合点

- `nodes/direct_streaming_planning_nodes.py`
  - `generate_constellation_plan_streaming(state, callback)`：方案生成，边生成边通过回调推送内容块。
  - `optimize_constellation_plan_streaming(state, user_feedback, callback)`：依据用户反馈优化已有方案。

- `nodes/staged_parameter_clarification_node.py`
  - `process_staged_parameter_clarification(state, callback)`：进入/推进分阶段澄清流程。
  - `process_staged_clarification_response(state, latest_response, callback)`：处理用户对澄清问题的回答。

- `tools/knowledge_tools.py`
  - `retrieve_knowledge_for_workflow(state, override_query=None, top_k=7)`：从 `state.requirement` 生成查询并执行 FAISS 相似度搜索，结果写入 `state.retrieved_knowledge`。

- `tools/satellite_extractor.py`
  - `extract_satellite_names_with_cache(text)` 等：从结果文本/方案中解析卫星名，便于下游展示与检索增强。

---

## 扩展建议（典型用例：接入“搜索智能体”）

- 插入点 A：`retrieve_knowledge_streaming` 中在“本地命中不足”时触发“网络搜索→LLM 格式化→询问是否保存→写入本地库”。
- 插入点 B：`generate_info_response_streaming` 对“[卫星名]是什么/参数/轨道/传感器”等信息类问题走“先本地→否则网络检索”。
- 保存：调用 `KnowledgeBase.add_texts([...])` 持久化为 FAISS 向量条目；将来源链接记录到 `state.metadata`。

---

## 错误处理与健壮性

- DeepSeek/网络异常：统一捕获并返回“用户可理解”的错误文案，仍会通过 `error` 与最终的助手消息提示。
- JSON 持久化：`save_state` 使用 `convert_to_json_serializable` 做降级转换，避免 `numpy`/对象导致写盘失败。
- 意图/澄清的短路：当处于 `awaiting_clarification` 或 `awaiting_intent_confirmation` 时，优先处理这些分支并在必要时早退，保持对话节奏自然。

---

## 序列图（高层）

```mermaid
sequenceDiagram
  participant FE as 前端
  participant API as routes.py (REST/WS)
  participant WF as StreamingWorkflowManager
  participant KB as knowledge_tools / knowledge_base
  participant NODES as nodes (clarify/plan/opt)
  participant DS as DeepSeek API

  FE->>API: 用户输入 (message)
  API->>WF: process_user_input_streaming(state, cb)
  WF-->>FE: processing_start
  WF-->>FE: thinking_step(初始化)
  alt 等待澄清
    WF->>NODES: process_staged_parameter_clarification/response
    NODES-->>WF: 回调(问题/进度)
    WF-->>FE: thinking_step/clarification_update
    WF-->>FE: processing_complete(等待澄清)
  else 新输入 → 意图分析
    WF->>DS: deepseek_intent_analysis
    DS-->>WF: intent
    opt 生成方案需确认
      WF-->>FE: response_chunk(确认提示)
      WF-->>FE: processing_complete(等待确认)
    end
    opt 信息/闲聊
      WF->>DS: 流式生成
      DS-->>WF: 文本分片
      WF-->>FE: response_chunk*
      WF-->>FE: processing_complete
    end
    opt 生成/优化
      WF->>KB: 本地知识检索
      KB-->>WF: 相关知识
      WF->>NODES: 生成/优化(流式)
      NODES-->>WF: 内容分片/思考步
      WF-->>FE: response_chunk*
      WF-->>FE: processing_complete
    end
  end
  API<<--WF: 返回 (state, assistant_response)
  API->>API: save_state()
```

---

## 结语

`workflow_streaming.py` 是后端“对话驱动 + 流式输出”的中枢。理解其“主流程 + 意图/澄清分流 + 节点/工具接口 + 回调协议”，即可在不破坏整体结构的前提下，快速接入例如“搜索智能体”、可视化增强、模型替换（如改 DeepSeek 为本地 LLM）等能力。
