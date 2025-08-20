### 背景概览

- **整体架构**：FastAPI 暴露 REST 与 WebSocket 两条入口，所有对话逻辑统一由 `workflow_streaming.py` 的流式工作流管理器编排，期间按需调用：
  - `nodes/` 中的“方案生成/优化、参数澄清”等节点
  - `tools/knowledge_tools.py` 做知识库检索
  - `rag/knowledge_base.py` 用 FAISS 向量索引做本地知识库搜索与持久化
  - `graph/state.py` 定义统一的 `WorkflowState`/消息/元数据等状态模型

---

### 关键模块与职责

- **`src/api/routes.py`：HTTP 与 WebSocket 的 API 入口**
  - REST：`POST /api/conversation`、`GET /api/conversation/{id}` 等
  - WS：`/api/ws/{conversation_id}`，接收消息后把回调传给工作流进行“流式推送”
  - 统一调用 `process_user_input_streaming(...)` 并在后台保存状态

```1:20:src/api/routes.py
# ... existing code ...
from backend.src.graph.workflow_streaming import process_user_input_streaming, save_state, load_state
# ... existing code ...
```

```277:317:src/api/routes.py
@app.post("/api/conversation", response_model=ConversationResponse)
async def handle_conversation(...):
    state = get_or_create_conversation(request.conversation_id)
    if request.extracted_satellites:
        state.set_extracted_satellites(request.extracted_satellites)
    if request.location:
        state.metadata["location"] = request.location
    updated_state, assistant_response = await process_user_input_streaming(request.message, state)
    background_tasks.add_task(save_conversation_state, updated_state)
    return ConversationResponse(..., message=assistant_response, plan=updated_state.main_plan, ...)
```

```966:1100:src/api/routes.py
@app.websocket("/api/ws/{conversation_id}")
async def websocket_endpoint(...):
    # 接收用户消息 → 取/建会话 → 定义 websocket_callback → 调用工作流
    updated_state, assistant_response = await process_user_input_streaming(
        user_message, state, websocket_callback
    )
    await save_conversation_state(updated_state)
    # 发送最终完成信号（intent/是否展示地图等，精简可视化）
```

- **`src/graph/workflow_streaming.py`：对话编排/状态机（流式）**
  - 核心入口：`process_user_input_streaming(user_input, state, websocket_callback)`
  - 主要阶段：
    - 初始化与思考步推送
    - 意图识别（DeepSeek 或回退）
    - 若为方案生成：参数澄清（分阶段）→ 知识检索（本地+可选网络）→ 方案生成/优化 → 生成响应
    - 其他意图：问候/感谢/闲聊/信息提供 → 统一流式输出
  - 与节点/检索的集成点都在这里（是后续扩展“搜索智能体”的最佳挂载位）

```1374:1380:src/graph/workflow_streaming.py
async def process_user_input_streaming(user_input: str, state: Optional[WorkflowState] = None,
                                       websocket_callback=None) -> Tuple[WorkflowState, str]:
    manager = StreamingWorkflowManager(websocket_callback)
    return await manager.process_user_input_streaming(user_input, state)
```

```406:456:src/graph/workflow_streaming.py
# 开始处理 → 初始化 →（若在澄清中则直接处理）→ 否则做意图确认/识别
state = await self.initialize_state_streaming(state, user_input)
# ... awaiting_clarification / awaiting_intent_confirmation ...
# DeepSeek 智能意图分析 & 确认提示的生成/流式发送
```

```1167:1256:src/graph/workflow_streaming.py
async def retrieve_knowledge_streaming(self, state: WorkflowState) -> WorkflowState:
    # 1) 本地知识库检索（knowledge_tools）→ 计数回传
    state = retrieve_knowledge_for_workflow(state)
    # 2) 可选网络增强（web_search_tools）→ 整合回写
    # 3) 阶段收尾、状态推进
```

```1258:1286:src/graph/workflow_streaming.py
async def generate_plan_streaming(...):
    # 回调转发思考步/内容块
    state = await generate_constellation_plan_streaming(state, plan_callback)
```

```1328:1371:src/graph/workflow_streaming.py
async def handle_parameter_clarification(...):
    # 分阶段收集参数节点（staged_parameter_clarification_node）
    # 通过 websocket_callback 实时推送澄清问题/进度
```

- **`src/graph/nodes/*`：智能节点**
  - `direct_streaming_planning_nodes.py`：方案“生成/优化”的流式实现（被工作流调用）
  - `staged_parameter_clarification_node.py`：分阶段参数澄清（被工作流调用）
  - `enhanced_*`/`uncertainty_*`：增强版澄清/可视化/不确定度等（当前多数关闭或按需）

- **`src/tools/knowledge_tools.py`：知识库接入（编排层上的工具）**
  - 生成查询 → 调用知识库 → 过滤 → 回写 `state.retrieved_knowledge` 与思考步
  - 对“补充卫星/按条件找卫星/详情”的轻量封装

```151:204:src/tools/knowledge_tools.py
def retrieve_knowledge_for_workflow(state: WorkflowState, override_query: Optional[str] = None, top_k: int = 7) -> WorkflowState:
    state.add_thinking_step("知识检索", "准备从知识库中检索相关卫星信息")
    query = override_query or generate_query_from_requirement(state.requirement)
    knowledge_items = retrieve_satellite_knowledge(query, top_k=top_k)
    satellite_info = extract_satellite_info(knowledge_items)
    state.retrieved_knowledge = satellite_info
    state.add_thinking_step("知识检索结果", f"检索到 {len(satellite_info)} 条相关卫星信息")
    return state
```

- **`src/rag/knowledge_base.py`：本地知识库（FAISS 向量索引）**
  - 初始化嵌入/索引，搜索、增量写入（持久化）
  - 充当“本地数据库”的最佳现成载体（你的搜索智能体可直接复用它）

```178:209:src/rag/knowledge_base.py
def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    results = self.vector_store.similarity_search_with_score(query, k=top_k)
    # 转为相似度（1/(1+distance)）
    return [{"document": doc.page_content, "score": 1.0/(1.0+score)} for doc, score in results]
```

```215:241:src/rag/knowledge_base.py
def add_texts(self, texts: List[str]) -> bool:
    self.vector_store.add_texts(texts)
    self.vector_store.save_local(self.index_dir)  # 持久化索引
    return True
```

- **`src/graph/state.py`：对话/方案/元数据模型**
  - 统一状态容器，贯穿 REST/WS、编排与节点调用

```46:82:src/graph/state.py
class WorkflowState(BaseModel):
    conversation_id: str = ...
    messages: List[Message] = []
    requirement: Requirement = ...
    retrieved_knowledge: List[Dict[str, Any]] = []
    main_plan: Optional[Any] = None
    alternative_plans: List[Any] = []
    current_stage: str = "requirement_analysis"
    thinking_steps: List[Dict[str, Any]] = []
    extracted_satellites: List[str] = []
    metadata: Dict[str, Any] = {}
    # 参数收集与意图确认的标志
```

---

### 一次完整对话的调用链（REST 与 WS）

- **REST 模式（一次性返回）**
  1) 前端调用 `POST /api/conversation`，带 `message/conversation_id/...`
  2) `routes.py` 获取/创建 `WorkflowState`，设置位置/卫星等元数据
  3) 调用 `process_user_input_streaming` 进入工作流
  4) 工作流内部：意图识别 →（如方案生成）参数澄清→检索→节点生成→组装响应
  5) 状态持久化到 `data/conversations/{id}.json`，返回 `message/plan/thinking_steps/...`

- **WebSocket 模式（全程流式）**
  1) 前端连 `/api/ws/{conversation_id}` → 服务端回“connected”
  2) 前端发送 `{"message": "...", "location": "...", ...}`
  3) `routes.py` 定义 `websocket_callback`，把回调传入工作流
  4) 工作流每步通过回调推送：
     - `processing_start / thinking_step / response_chunk / processing_complete`
  5) 处理完成，后端保存最新状态，前端收到整段流式内容与元信息

---

### 你的“搜索智能体”应接入的位置与实现建议

你的流程（本地数据库命中→本地回答；否则网络搜索→LLM格式化→返回信息+链接→询问是否保存→保存标准化结果）可以无缝挂到“检索/信息提供”路径，且完全复用现有回调与持久化能力。

- **最佳挂载点 A（推荐）**：在 `retrieve_knowledge_streaming` 中，当本地知识库命中不足时走“搜索智能体”分支
  - 触发条件：`len(state.retrieved_knowledge) == 0` 或低于阈值
  - 行为：
    - 调用 `tools/web_search_tools`（已有集成点）或你新建的 `tools/satellite_search_agent.py` 去抓取网页信息
    - 用 LLM 进行“摘要与结构化格式化”（可以走 `generate_info_response_streaming` 的流式管道，把格式化文本按 chunk 推送）
    - 构造“返回信息+链接+是否保存”的一条助手消息，并设置 `state.metadata["awaiting_save_confirmation"]=True`
  - 优点：对方案/信息两个意图通用；复用现有“知识检索”的时序与思考步推送

- **备选挂载点 B**：在 `generate_info_response_streaming` 内做“卫星查询特例”
  - 若用户问的是“某颗卫星 X 是什么/参数/轨道/传感器？”
    - 先本地检索（`knowledge_base.search`）
    - 不足时调用“搜索智能体”
  - 优点：对“信息类”问答定制化程度更高

- **保存逻辑（用户确认后）**
  - 在 WS 模式中，你可在“询问是否保存”的助手消息后，等待下一条用户消息
  - 若用户确认：
    - 把标准化文本（或结构化 JSON → 转文本）写入 `KnowledgeBase.add_texts([text])`，即可持久化到 FAISS（即“本地数据库”）
    - 记录来源链接到 `state.metadata`，便于后续追踪

- **文件建议**
  - 新建：`src/tools/satellite_search_agent.py`
    - `run_agent(query: str, state: WorkflowState, cb) -> AgentResult`
      - 本地命中检测（调用 `get_knowledge_base().search`）
      - 不足则调用 `web_search_tools`（或你自行实现的网络抓取）
      - LLM 组织“摘要+引用链接+保存询问”，通过 `cb` 以 `response_chunk` 流式推送
      - 返回标准化结构（标题、要点、链接清单、原文摘要）
    - `save_to_knowledge_base(standard_text_or_json) -> bool`
  - 在 `workflow_streaming.retrieve_knowledge_streaming` 或 `generate_info_response_streaming` 中按条件调用

---

### 最小改动接入步骤（建议）

- 在 `src/tools/` 新增 `satellite_search_agent.py`，提供：
  - `run_agent(query, state, websocket_callback)`
  - `save_to_knowledge_base(items: List[str])`
- 在 `workflow_streaming.py`：
  - A 线：`retrieve_knowledge_streaming` 中，当 `knowledge_count < N` 时调用 `run_agent(...)`；将格式化结果以 `response_chunk` 流式推送，并落地一个“是否保存”的助手消息（设置 `awaiting_save_confirmation` 标志）
  - B 线（可选）：在 `generate_info_response_streaming` 中，对“卫星名”模式触发 `run_agent(...)`
  - 在主循环中，若检测到 `awaiting_save_confirmation` 且用户回复“是/保存”，调用 `save_to_knowledge_base(...)`，追加“保存成功/失败”的助手消息
- 复用现有回调与状态：
  - 推送用 `self.send_status(...)` 或 `self.content_sender.send_content_streaming(...)`
  - 状态存取照旧由 `routes.py` 的保存逻辑与 `save_state/load_state` 完成

---

### 关键代码位置（用于快速定位）

- API 入口（REST/WS 调度工作流）
```270:317:src/api/routes.py
# handle_conversation → process_user_input_streaming → save_conversation_state
```

```966:1100:src/api/routes.py
# websocket_endpoint → websocket_callback → process_user_input_streaming(…, websocket_callback)
```

- 工作流入口与阶段编排
```1374:1380:src/graph/workflow_streaming.py
# process_user_input_streaming 导出
```

```1089:1166:src/graph/workflow_streaming.py
# analyze_user_input_streaming：DeepSeek 意图识别、触发澄清/生成
```

```1167:1256:src/graph/workflow_streaming.py
# retrieve_knowledge_streaming：本地知识库检索 + 可选网络增强（你的搜索智能体最佳挂点）
```

```1258:1286:src/graph/workflow_streaming.py
# generate_plan_streaming：调用 nodes 的流式生成节点
```

- 知识库工具与本地 DB
```151:204:src/tools/knowledge_tools.py
# retrieve_knowledge_for_workflow：从 state.requirement 生成 query→search→回写
```

```178:241:src/rag/knowledge_base.py
# search / add_texts：本地数据库（FAISS）搜索与持久化
```

- 状态模型（对话/方案/元数据/标志位）
```46:82:src/graph/state.py
# WorkflowState：messages / retrieved_knowledge / main_plan / metadata / awaiting_* 等
```

---

### 小结

- 后端以 `routes.py` 为入口，所有对话统一流入 `workflow_streaming.py` 编排，期间按需调用 `nodes/`（生成/优化/澄清）、`knowledge_tools.py`（查询）、`knowledge_base.py`（本地向量库），`state.py` 贯穿全程。
- 你的“搜索智能体”最合适加在“检索链路”里（推荐 `retrieve_knowledge_streaming` 作为不足命中时的 fallback），或在“信息类回复”里做卫星搜索特例；保存则直接写 `KnowledgeBase.add_texts` 实现“本地数据库”持久化。
- 这样能无缝复用现有的流式回调、思考步骤推送、状态持久化与会话管理，改动小、集成清晰。

- 我已梳理各文件职责与调用链，并给出“搜索智能体”的最佳挂载点与最小改动方案，关键行号已标注，便于你快速跳转定位。