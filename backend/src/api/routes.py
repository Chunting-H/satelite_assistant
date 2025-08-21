# backend/src/api/routes.py

import os
import sys
import json
import uuid
import logging
import asyncio
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import time
import torch

# 确保项目根目录在sys.path中
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent  # 上溯四级目录到项目根目录
sys.path.append(str(project_root))

# FastAPI相关导入
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect, \
    Query, Path as PathParam, Body
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.src.tools.knowledge_tools import retrieve_knowledge_for_workflow
from backend.src.graph.nodes import buffered_streaming_planning_nodes
# 项目内部导入
from backend.config.config import settings
from backend.src.graph.state import WorkflowState, ConstellationPlan, Message
from backend.src.graph.workflow_streaming import process_user_input_streaming, save_state, load_state
from backend.src.graph.nodes.enhanced_visualization_nodes import enhance_plan_with_visualization, \
    add_visualization_to_response
from backend.config.ai_config import ai_settings
from backend.src.llm.jiuzhou_model_manager import get_jiuzhou_manager

# 导入多模型管理器
from backend.src.llm.multi_model_manager import get_multi_model_manager

# 导入爬虫智能体
from backend.src.tools.crawler_agent.crawler_workflow import crawler_workflow



# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.log_file) if settings.log_file else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)


# 🆕 导入数据处理工具
# 🆕 数据处理工具可选导入（避免直接运行时模块路径问题）
try:
    from backend.src.tools.data_processor import data_processor
    DATA_PROCESSOR_AVAILABLE = True
    logger.info("✅ 数据处理工具加载成功，启用完整数据处理功能")
except Exception as _e:
    data_processor = None
    DATA_PROCESSOR_AVAILABLE = False
    logger.warning(f"⚠️ 数据处理工具不可用，启用最小接口模式: {_e}")
    logger.warning("💡 要启用完整功能，请安装依赖：pip install -r requirements.txt")



# 使用lifespan事件处理器替代已弃用的on_event
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("虚拟星座助手服务启动")

    # 预加载九州模型
    if ai_settings.jiuzhou_enabled:
        try:
            logger.info("开始预加载九州模型...")
            manager = get_jiuzhou_manager()

            # 使用线程池执行器在后台初始化，避免阻塞启动
            loop = asyncio.get_event_loop()

            # 创建一个任务来初始化模型
            async def init_model():
                await loop.run_in_executor(None, manager.initialize)
                logger.info("✅ 九州模型预加载完成")

            # 创建后台任务
            asyncio.create_task(init_model())

        except Exception as e:
            logger.error(f"❌ 九州模型预加载失败: {e}")
            logger.warning("将在首次使用时加载模型")
    else:
        logger.info("九州模型已禁用，跳过预加载")

    yield  # 应用运行期间

    # 关闭时执行
    logger.info("虚拟星座助手服务关闭")

    # 清理九州模型资源
    try:
        manager = get_jiuzhou_manager()
        if manager._initialized:
            manager.close()
            logger.info("九州模型资源已释放")
    except Exception as e:
        logger.error(f"释放九州模型资源时出错: {e}")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="智慧虚拟星座助手API",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 活跃的WebSocket连接
active_connections: Dict[str, WebSocket] = {}

# 后台任务管理
background_tasks: Dict[str, asyncio.Task] = {}

# 对话状态缓存
conversation_cache: Dict[str, WorkflowState] = {}

# 全局WebSocket连接管理
active_websockets: Dict[str, WebSocket] = {}

# 🆕 新增：数据处理任务存储
processing_tasks: Dict[str, Dict[str, Any]] = {}


# 辅助函数：确保对话文件路径有效
def ensure_conversation_file_path(conversation_id: str) -> str:
    """确保对话文件路径有效，创建必要的目录"""
    path = os.path.join(settings.data_dir, "conversations", f"{conversation_id}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


# 添加根路径处理函数
@app.get("/")
async def root():
    """根路径处理函数"""
    return {
        "message": "欢迎使用智慧虚拟星座助手API",
        "version": settings.app_version,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_check": "/api/health",
        "status": "operational"
    }


# 数据模型定义
class ConversationRequest(BaseModel):
    """对话请求模型"""
    message: str
    conversation_id: Optional[str] = None
    extracted_satellites: Optional[List[str]] = None
    location: Optional[str] = None  # 🆕 新增位置字段


class ConversationRenameRequest(BaseModel):
    """对话重命名请求模型"""
    title: str


class ThinkingStep(BaseModel):
    """思考步骤模型"""
    step: str
    details: Any
    timestamp: float


class ConversationResponse(BaseModel):
    """对话响应模型"""
    conversation_id: str
    message: str
    thinking_steps: Optional[List[ThinkingStep]] = None
    plan: Optional[Any] = None
    extracted_satellites: Optional[List[str]] = None
    location: Optional[str] = None
    visualization_data: Optional[Dict[str, Any]] = None  # 新增
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationListItem(BaseModel):
    """对话列表项"""
    conversation_id: str
    title: str
    created_at: float
    updated_at: float
    message_count: int


class ConversationListResponse(BaseModel):
    """对话列表响应"""
    conversations: List[ConversationListItem]
    total: int


class FileInfoResponse(BaseModel):
    """文件信息响应"""
    file_id: str
    filename: str
    content_type: str
    size: int
    upload_time: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlanSummaryResponse(BaseModel):
    """方案概要响应"""
    plan_id: str
    name: str
    created_at: float
    satellite_count: int
    description: str


class PlanDetailResponse(BaseModel):
    """方案详情响应"""
    plan_id: str
    name: str
    description: str
    satellites: List[Dict[str, Any]]
    advantages: Optional[List[str]] = None
    limitations: Optional[List[str]] = None
    created_at: float
    additional_info: Dict[str, Any] = Field(default_factory=dict)


class SystemInfoResponse(BaseModel):
    """系统信息响应"""
    app_name: str
    version: str
    environment: str
    uptime: float
    status: str = "operational"

class SatelliteQueryRequest(BaseModel):
    """卫星查询请求模型"""
    query: str
    model: str = Field(default="chatgpt", description="使用的AI模型: chatgpt, qwen, deepseek")
    satellites_context: Optional[str] = Field(default="", description="当前卫星数据上下文")

class SatelliteQueryResponse(BaseModel):
    """卫星查询响应模型"""
    answer: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    search_query: str = ""
    model_used: str
    success: bool = True
    error_message: Optional[str] = None


class CrawlJobRequest(BaseModel):
    """爬取任务请求模型"""
    target_sites: List[str] = Field(default=["Gunter's Space Page"], description="目标网站列表")
    keywords: List[str] = Field(default=[], description="搜索关键词")
    max_satellites: int = Field(default=10, ge=1, le=50, description="最大爬取卫星数量")


class CrawlJobResponse(BaseModel):
    """爬取任务响应模型"""
    job_id: str
    status: str
    message: str
    estimated_time: Optional[int] = None


class CrawlJobStatusResponse(BaseModel):
    """爬取任务状态响应模型"""
    job_id: str
    status: str
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class CrawlLogsResponse(BaseModel):
    """爬取日志响应模型"""
    logs: List[Dict[str, Any]]
    total: int


class CrawlStatisticsResponse(BaseModel):
    """爬取统计响应模型"""
    total_crawls: int
    total_new_satellites: int
    total_failed: int
    daily_stats: List[Dict[str, Any]]
    site_stats: List[Dict[str, Any]]
    recent_logs: List[Dict[str, Any]]


# 工具函数
def get_conversation_state_path(conversation_id: str) -> str:
    """获取对话状态文件路径"""
    return os.path.join(settings.data_dir, "conversations", f"{conversation_id}.json")


def get_or_create_conversation(conversation_id: Optional[str] = None) -> WorkflowState:
    """获取或创建对话状态"""
    if conversation_id and conversation_id in conversation_cache:
        return conversation_cache[conversation_id]

    if conversation_id:
        # 尝试从文件加载
        state_path = get_conversation_state_path(conversation_id)
        if os.path.exists(state_path):
            state = load_state(state_path)
            if state:
                conversation_cache[conversation_id] = state
                return state

    # 创建新对话
    new_state = WorkflowState()
    new_id = conversation_id or new_state.conversation_id
    new_state.conversation_id = new_id
    conversation_cache[new_id] = new_state
    return new_state


async def save_conversation_state(state: WorkflowState):
    """保存对话状态"""
    # 确保目录存在
    os.makedirs(os.path.dirname(get_conversation_state_path(state.conversation_id)), exist_ok=True)

    # 保存到缓存
    conversation_cache[state.conversation_id] = state

    # 保存到文件
    save_state(state, get_conversation_state_path(state.conversation_id))


# API路由
@app.post("/api/conversation", response_model=ConversationResponse)
async def handle_conversation(
        request: ConversationRequest,
        background_tasks: BackgroundTasks
):
    """处理对话请求"""
    try:
        # 获取或创建对话状态
        state = get_or_create_conversation(request.conversation_id)

        # 🆕 如果请求中包含卫星信息，保存到状态
        if request.extracted_satellites:
            state.set_extracted_satellites(request.extracted_satellites)

        # 🆕 如果请求中包含位置信息，保存到状态
        if request.location:
            state.metadata["location"] = request.location

        # 处理用户输入
        updated_state, assistant_response = await process_user_input_streaming(request.message, state)

        # 保存状态
        background_tasks.add_task(save_conversation_state, updated_state)

        # 🔧 移除可视化数据生成逻辑

        # 构建响应
        response = ConversationResponse(
            conversation_id=updated_state.conversation_id,
            message=assistant_response,
            thinking_steps=[ThinkingStep(**step) for step in
                            updated_state.thinking_steps] if updated_state.thinking_steps else None,
            plan=updated_state.main_plan,
            extracted_satellites=updated_state.extracted_satellites,
            location=updated_state.metadata.get("location"),
            visualization_data=None  # 🔧 修改：始终返回 None
        )

        return response

    except Exception as e:
        logger.error(f"处理对话请求时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理对话请求时出错: {str(e)}")


@app.get("/api/conversation/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str = PathParam(...)):
    """获取对话详情"""
    try:
        logger.info(f"正在获取对话详情: {conversation_id}")

        # 获取或创建对话状态
        state = get_or_create_conversation(conversation_id)

        # 提取所有消息
        messages_data = []
        for msg in state.messages:
            messages_data.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            })

        # 获取最后一条助手消息
        last_message = ""
        for msg in reversed(state.messages):
            if msg.role == "assistant":
                last_message = msg.content
                break

        # 构建响应对象
        response = ConversationResponse(
            conversation_id=state.conversation_id,
            message=last_message,
            thinking_steps=[ThinkingStep(**step) for step in state.thinking_steps] if state.thinking_steps else None,
            plan=state.main_plan,
            extracted_satellites=state.extracted_satellites,
            location=state.metadata.get("location"),  # 🆕 返回位置信息
            metadata={
                "message_count": len(state.messages),
                "current_stage": state.current_stage,
                "messages": messages_data
            }
        )

        logger.info(f"成功获取对话详情: {conversation_id}, 消息数量: {len(messages_data)}")
        return response

    except Exception as e:
        logger.error(f"获取对话详情时出错: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"获取对话详情时出错: {str(e)}")


@app.get("/api/conversations", response_model=ConversationListResponse)
async def list_conversations(
        limit: int = Query(10, ge=1, le=100),
        offset: int = Query(0, ge=0)
):
    """获取对话列表"""
    try:
        # 获取对话文件列表
        conversations_dir = os.path.join(settings.data_dir, "conversations")
        os.makedirs(conversations_dir, exist_ok=True)

        logger.info(f"正在获取对话列表，目录: {conversations_dir}")

        # 检查目录是否存在
        conversation_files = []
        if os.path.exists(conversations_dir):
            conversation_files = [f for f in os.listdir(conversations_dir) if f.endswith('.json')]
            logger.info(f"找到 {len(conversation_files)} 个对话文件")
        else:
            logger.warning(f"对话目录不存在: {conversations_dir}")
            return ConversationListResponse(conversations=[], total=0)

        # 加载对话数据
        conversations = []
        total = len(conversation_files)

        for filename in conversation_files[offset:offset + limit]:
            try:
                conversation_id = filename.replace('.json', '')
                state_path = os.path.join(conversations_dir, filename)

                # 检查文件存在性和大小
                if not os.path.exists(state_path):
                    logger.warning(f"对话文件不存在: {state_path}")
                    continue

                file_size = os.path.getsize(state_path)
                logger.info(f"加载对话文件: {state_path}, 大小: {file_size} 字节")

                # 读取并验证文件内容是否有效
                try:
                    with open(state_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # 尝试解析为JSON
                    json.loads(content)
                except Exception as e:
                    logger.error(f"对话文件 {filename} 内容无效: {str(e)}")
                    continue

                # 加载状态
                state = load_state(state_path)

                if state:
                    # 优先使用自定义标题
                    if state.metadata and state.metadata.get("custom_title"):
                        title = state.metadata["custom_title"]
                    else:
                        # 使用第一条用户消息作为标题
                        title = "新对话"
                        for msg in state.messages:
                            if msg.role == "user":
                                title = msg.content[:50] + ("..." if len(msg.content) > 50 else "")
                                break

                    # 提取时间戳
                    created_at = 0
                    updated_at = 0
                    if state.messages:
                        created_at = state.messages[0].timestamp
                        updated_at = state.messages[-1].timestamp

                    conversations.append(ConversationListItem(
                        conversation_id=conversation_id,
                        title=title,
                        created_at=created_at,
                        updated_at=updated_at,
                        message_count=len(state.messages)
                    ))
                    logger.info(f"成功加载对话: {conversation_id}, 标题: {title}, 消息数量: {len(state.messages)}")
                else:
                    logger.warning(f"无法加载对话状态: {state_path}")
            except Exception as e:
                logger.error(f"加载对话 {filename} 时出错: {str(e)}")
                logger.error(traceback.format_exc())  # 添加完整堆栈跟踪

        # 按更新时间排序
        conversations.sort(key=lambda x: x.updated_at, reverse=True)

        logger.info(f"成功加载 {len(conversations)} 个对话，返回给前端")
        return ConversationListResponse(
            conversations=conversations,
            total=total
        )

    except Exception as e:
        logger.error(f"获取对话列表时出错: {str(e)}")
        logger.error(traceback.format_exc())  # 添加完整堆栈跟踪
        raise HTTPException(status_code=500, detail=f"获取对话列表时出错: {str(e)}")


@app.patch("/api/conversation/{conversation_id}/rename")
async def rename_conversation(
        request: ConversationRenameRequest,
        conversation_id: str = PathParam(...)
):
    """重命名对话"""
    try:
        if not request or not request.title or not request.title.strip():
            raise HTTPException(status_code=400, detail="标题不能为空")

        new_title = request.title.strip()

        # 从缓存或文件中获取对话
        state = get_or_create_conversation(conversation_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"对话 {conversation_id} 不存在")

        # 更新元数据中的标题
        if not state.metadata:
            state.metadata = {}
        state.metadata["custom_title"] = new_title
        state.metadata["title_updated_at"] = datetime.now().timestamp()

        # 保存更新后的状态
        await save_conversation_state(state)

        # 更新缓存中的对话
        if conversation_id in conversation_cache:
            conversation_cache[conversation_id] = state

        logger.info(f"对话 {conversation_id} 重命名为: {new_title}")

        return {
            "status": "success",
            "conversation_id": conversation_id,
            "new_title": new_title,
            "message": "对话重命名成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重命名对话时出错: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"重命名对话时出错: {str(e)}")


@app.post("/api/conversation/create", response_model=ConversationResponse)
async def create_empty_conversation(
        conversation_id: str = Body(..., embed=True)
):
    """创建空对话 - 不处理任何消息"""
    try:
        logger.info(f"创建空对话: {conversation_id}")

        # 创建新的对话状态
        state = WorkflowState()
        state.conversation_id = conversation_id

        # 保存空对话状态
        await save_conversation_state(state)

        # 构建响应
        response = ConversationResponse(
            conversation_id=state.conversation_id,
            message="",
            thinking_steps=None,
            plan=None,
            extracted_satellites=[],
            location=None,
            visualization_data=None,
            metadata={
                "message_count": 0,
                "current_stage": "initialized",
                "messages": []
            }
        )

        logger.info(f"成功创建空对话: {conversation_id}")
        return response

    except Exception as e:
        logger.error(f"创建空对话时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建空对话时出错: {str(e)}")


@app.delete("/api/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str = PathParam(...)):
    """删除对话"""
    try:
        # 从缓存中删除
        if conversation_id in conversation_cache:
            del conversation_cache[conversation_id]

        # 从文件中删除
        state_path = get_conversation_state_path(conversation_id)
        if os.path.exists(state_path):
            os.remove(state_path)
            return {"status": "success", "message": f"对话 {conversation_id} 已删除"}
        else:
            raise HTTPException(status_code=404, detail=f"对话 {conversation_id} 不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除对话时出错: {str(e)}")
        logger.error(traceback.format_exc())  # 添加完整堆栈跟踪
        raise HTTPException(status_code=500, detail=f"删除对话时出错: {str(e)}")


@app.post("/api/files/upload", response_model=FileInfoResponse)
async def upload_file(
        file: UploadFile = File(...),
        conversation_id: Optional[str] = None
):
    """上传文件"""
    try:
        # 生成唯一文件ID
        file_id = str(uuid.uuid4())

        # 确保上传目录存在
        upload_dir = settings.file_processor.upload_dir
        os.makedirs(upload_dir, exist_ok=True)

        # 检查文件大小
        file_size = 0
        content = await file.read()
        file_size = len(content)

        if file_size > settings.file_processor.max_file_size:
            raise HTTPException(status_code=413,
                                detail=f"文件大小超过限制 ({file_size} > {settings.file_processor.max_file_size} 字节)")

        # 获取文件扩展名
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower() if filename else ""

        # 检查文件类型
        if ext not in settings.file_processor.allowed_extensions:
            raise HTTPException(status_code=415, detail=f"不支持的文件类型: {ext}")

        # 保存文件
        file_path = os.path.join(upload_dir, f"{file_id}{ext}")
        with open(file_path, "wb") as f:
            f.write(content)

        # 如果提供了对话ID，将文件与对话关联
        if conversation_id:
            state = get_or_create_conversation(conversation_id)

            # 在元数据中记录上传的文件
            if "uploaded_files" not in state.metadata:
                state.metadata["uploaded_files"] = []

            state.metadata["uploaded_files"].append({
                "file_id": file_id,
                "filename": filename,
                "upload_time": datetime.now().timestamp()
            })

            # 保存更新后的状态
            await save_conversation_state(state)

        # 构建响应
        response = FileInfoResponse(
            file_id=file_id,
            filename=filename or "unknown",
            content_type=file.content_type or "application/octet-stream",
            size=file_size,
            upload_time=datetime.now().timestamp(),
            metadata={
                "conversation_id": conversation_id,
                "extension": ext
            }
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文件时出错: {str(e)}")
        logger.error(traceback.format_exc())  # 添加完整堆栈跟踪
        raise HTTPException(status_code=500, detail=f"上传文件时出错: {str(e)}")


@app.get("/api/files/{file_id}")
async def get_file(file_id: str = PathParam(...)):
    """获取上传的文件"""
    try:
        # 在上传目录中查找文件
        upload_dir = settings.file_processor.upload_dir

        # 查找所有可能的文件扩展名
        for ext in settings.file_processor.allowed_extensions:
            file_path = os.path.join(upload_dir, f"{file_id}{ext}")
            if os.path.exists(file_path):
                return FileResponse(
                    path=file_path,
                    filename=os.path.basename(file_path),
                    media_type="application/octet-stream"
                )

        # 如果没有找到文件
        raise HTTPException(status_code=404, detail=f"文件 {file_id} 不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件时出错: {str(e)}")
        logger.error(traceback.format_exc())  # 添加完整堆栈跟踪
        raise HTTPException(status_code=500, detail=f"获取文件时出错: {str(e)}")


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str = PathParam(...)):
    """删除上传的文件"""
    try:
        # 在上传目录中查找文件
        upload_dir = settings.file_processor.upload_dir
        deleted = False

        # 查找所有可能的文件扩展名
        for ext in settings.file_processor.allowed_extensions:
            file_path = os.path.join(upload_dir, f"{file_id}{ext}")
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted = True
                break

        if deleted:
            return {"status": "success", "message": f"文件 {file_id} 已删除"}
        else:
            raise HTTPException(status_code=404, detail=f"文件 {file_id} 不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件时出错: {str(e)}")
        logger.error(traceback.format_exc())  # 添加完整堆栈跟踪
        raise HTTPException(status_code=500, detail=f"删除文件时出错: {str(e)}")


@app.get("/api/ai/status")
async def get_ai_status():
    """获取AI模型状态"""
    try:
        from backend.src.llm.jiuzhou_model_manager import get_jiuzhou_manager
        from backend.config.ai_config import ai_settings

        manager = get_jiuzhou_manager()

        return {
            "jiuzhou_enabled": ai_settings.jiuzhou_enabled,
            "jiuzhou_initialized": manager._initialized,
            "model_path": ai_settings.jiuzhou_model_path,
            "device": str(manager.device) if manager._initialized else "not_loaded"
        }
    except Exception as e:
        logger.error(f"获取AI状态失败: {e}")
        return {
            "error": str(e),
            "jiuzhou_enabled": False,
            "jiuzhou_initialized": False
        }


@app.get("/api/ai/model-status")
async def get_model_status():
    """获取AI模型详细状态"""
    try:
        from backend.src.llm.jiuzhou_model_manager import get_jiuzhou_manager
        from backend.config.ai_config import ai_settings

        manager = get_jiuzhou_manager()

        status = {
            "jiuzhou_enabled": ai_settings.jiuzhou_enabled,
            "jiuzhou_initialized": manager._initialized,
            "model_path": ai_settings.jiuzhou_model_path,
            "model_exists": os.path.exists(ai_settings.jiuzhou_model_path),
            "device": str(manager.device) if manager._initialized else "not_loaded",
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
        }

        if manager._initialized and manager.model:
            try:
                # 获取模型大小信息
                model_size = sum(p.numel() for p in manager.model.parameters())
                status["model_parameters"] = f"{model_size:,}"
                status["model_memory_mb"] = f"{model_size * 4 / 1024 / 1024:.2f}"  # 假设float32
            except:
                pass

        return status

    except Exception as e:
        logger.error(f"获取模型状态失败: {e}")
        return {
            "error": str(e),
            "jiuzhou_enabled": False,
            "jiuzhou_initialized": False
        }


@app.get("/api/plans/{plan_id}", response_model=PlanDetailResponse)
async def get_plan(plan_id: str = PathParam(...)):
    """获取星座方案详情"""
    try:
        # 遍历所有对话找到该方案
        for state in conversation_cache.values():
            if state.main_plan and isinstance(state.main_plan, dict) and state.main_plan.get("plan_id") == plan_id:
                plan = state.main_plan
                return PlanDetailResponse(
                    plan_id=plan.get("plan_id", plan_id),
                    name=plan.get("name", "未命名方案"),
                    description=plan.get("description", ""),
                    satellites=plan.get("satellites", []),
                    advantages=plan.get("advantages", []),
                    limitations=plan.get("limitations", []),
                    created_at=plan.get("created_at", datetime.now().timestamp()),
                    additional_info=plan.get("additional_info", {})
                )

            # 检查备选方案
            for alt_plan in state.alternative_plans:
                if isinstance(alt_plan, dict) and alt_plan.get("plan_id") == plan_id:
                    return PlanDetailResponse(
                        plan_id=alt_plan.get("plan_id", plan_id),
                        name=alt_plan.get("name", "未命名方案"),
                        description=alt_plan.get("description", ""),
                        satellites=alt_plan.get("satellites", []),
                        advantages=alt_plan.get("advantages", []),
                        limitations=alt_plan.get("limitations", []),
                        created_at=alt_plan.get("created_at", datetime.now().timestamp()),
                        additional_info=alt_plan.get("additional_info", {})
                    )

        # 如果方案不在缓存中，尝试从文件加载
        conversations_dir = os.path.join(settings.data_dir, "conversations")
        if os.path.exists(conversations_dir):
            for filename in os.listdir(conversations_dir):
                if filename.endswith('.json'):
                    state_path = os.path.join(conversations_dir, filename)
                    state = load_state(state_path)

                    if state and state.main_plan and isinstance(state.main_plan, dict) and state.main_plan.get(
                            "plan_id") == plan_id:
                        plan = state.main_plan
                        return PlanDetailResponse(
                            plan_id=plan.get("plan_id", plan_id),
                            name=plan.get("name", "未命名方案"),
                            description=plan.get("description", ""),
                            satellites=plan.get("satellites", []),
                            advantages=plan.get("advantages", []),
                            limitations=plan.get("limitations", []),
                            created_at=plan.get("created_at", datetime.now().timestamp()),
                            additional_info=plan.get("additional_info", {})
                        )

        # 如果未找到方案
        raise HTTPException(status_code=404, detail=f"方案 {plan_id} 不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取方案详情时出错: {str(e)}")
        logger.error(traceback.format_exc())  # 添加完整堆栈跟踪
        raise HTTPException(status_code=500, detail=f"获取方案详情时出错: {str(e)}")

@app.post("/api/satellite/query", response_model=SatelliteQueryResponse)
async def query_satellites(request: SatelliteQueryRequest):
    """智能卫星查询接口"""
    try:
        logger.info(f"收到卫星查询请求: {request.query[:100]}... 使用模型: {request.model}")
        
        # 获取多模型管理器
        manager = get_multi_model_manager()
        
        # 查询卫星信息
        result = await manager.query_satellite_info(
            user_query=request.query,
            model_name=request.model,
            satellites_context=request.satellites_context
        )
        
        # 构建响应
        response = SatelliteQueryResponse(
            answer=result.get("answer", "处理完成"),
            filters=result.get("filters", {}),
            search_query=result.get("search_query", ""),
            model_used=request.model,
            success=True
        )
        
        logger.info(f"卫星查询成功: {request.model}")
        return response
        
    except Exception as e:
        logger.error(f"卫星查询失败: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 返回错误响应但不抛出异常
        return SatelliteQueryResponse(
            answer=f"抱歉，处理您的查询时出现错误: {str(e)}",
            filters={},
            search_query="",
            model_used=request.model,
            success=False,
            error_message=str(e)
        )


@app.get("/api/health")
async def health_check():
    """健康检查"""
    try:
        start_time = datetime.now().timestamp()

        # 检查知识库
        try:
            from backend.src.rag.knowledge_base import get_knowledge_base
            kb = get_knowledge_base()
            kb_status = "operational" if hasattr(kb, "vector_store") and kb.vector_store is not None else "degraded"
        except Exception as e:
            logger.error(f"检查知识库状态时出错: {str(e)}")
            kb_status = "error"

        # 检查API密钥
        llm_status = "operational" if settings.llm.api_key else "degraded"

        return {
            "status": "operational",
            "services": {
                "api": "operational",
                "knowledge_base": kb_status,
                "llm": llm_status
            },
            "uptime": start_time - startup_time,
            "version": settings.app_version
        }

    except Exception as e:
        logger.error(f"健康检查时出错: {str(e)}")
        logger.error(traceback.format_exc())  # 添加完整堆栈跟踪
        return {
            "status": "degraded",
            "error": str(e),
            "version": settings.app_version
        }


# 调试端点
@app.get("/api/debug/conversations")
async def debug_conversations():
    """调试用：获取对话目录信息"""
    try:
        conversations_dir = os.path.join(settings.data_dir, "conversations")
        exists = os.path.exists(conversations_dir)
        files = []
        file_details = []

        if exists:
            files = [f for f in os.listdir(conversations_dir) if f.endswith('.json')]
            for f in files[:5]:  # 只获取前5个文件的详情
                path = os.path.join(conversations_dir, f)
                size = os.path.getsize(path) if os.path.exists(path) else 0
                file_details.append({"name": f, "size": size})

        return {
            "directory": conversations_dir,
            "exists": exists,
            "file_count": len(files),
            "file_samples": file_details if exists else [],
            "data_dir": settings.data_dir,
            "cache_size": len(conversation_cache)
        }
    except Exception as e:
        logger.error(f"获取调试信息时出错: {str(e)}")
        logger.error(traceback.format_exc())  # 添加完整堆栈跟踪
        return {"error": str(e)}


@app.get("/api/debug/conversation/{conversation_id}")
async def debug_conversation(conversation_id: str = PathParam(...)):
    """调试用：获取对话文件信息"""
    try:
        file_path = get_conversation_state_path(conversation_id)
        exists = os.path.exists(file_path)
        in_cache = conversation_id in conversation_cache

        response_data = {
            "file_path": file_path,
            "exists": exists,
            "in_cache": in_cache
        }

        if exists:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                file_size = len(content)
                response_data["file_size"] = file_size

                # 尝试解析JSON
                try:
                    json_content = json.loads(content)
                    response_data["json_valid"] = True
                    response_data["message_count"] = len(json_content.get("messages", []))

                    if json_content.get("messages") and len(json_content.get("messages")) > 0:
                        response_data["sample_message"] = json_content.get("messages")[0]
                except json.JSONDecodeError as e:
                    response_data["json_valid"] = False
                    response_data["error"] = "无法解析JSON内容"
                    response_data["json_error"] = str(e)
                    response_data["content_preview"] = content[:100] + "..." if len(content) > 100 else content

        if in_cache:
            state = conversation_cache[conversation_id]
            response_data["cache_message_count"] = len(state.messages)
            response_data["cache_first_user_message"] = next(
                (msg.content for msg in state.messages if msg.role == "user"), None)

        return response_data
    except Exception as e:
        logger.error(f"调试对话时出错: {str(e)}")
        logger.error(traceback.format_exc())  # 添加完整堆栈跟踪
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }


# 在 routes.py 中简化WebSocket处理

@app.websocket("/api/ws/{conversation_id}")
async def websocket_endpoint(websocket: WebSocket, conversation_id: str):
    """实时流式WebSocket端点"""
    await websocket.accept()

    # 存储连接
    active_websockets[conversation_id] = websocket

    # 发送连接确认
    await websocket.send_json({
        "type": "connected",
        "conversation_id": conversation_id,
        "message": "WebSocket连接已建立"
    })

    try:
        while True:
            # 接收用户消息
            data = await websocket.receive_text()
            message_data = json.loads(data)
            message_type = message_data.get("type", "message")
            
            # 🆕 新增：处理不同类型的消息
            if message_type == "data_processing_complete":
                # 处理数据处理完成消息（来自前端的通知，谨慎合并，避免覆盖后端真实结果路径）
                processing_id = message_data.get("processing_id")
                client_results = message_data.get("results", {})

                if processing_id and processing_id in processing_tasks:
                    task_ref = processing_tasks[processing_id]

                    # 仅合并非空字段，保留后端写入的 original_data/processed_data/result_package
                    existing_results = task_ref.get("results", {}) or {}
                    merged_results = dict(existing_results)
                    for k, v in (client_results or {}).items():
                        if v is not None:
                            merged_results[k] = v

                    task_ref["results"] = merged_results

                    # 状态以后台任务为准，这里不强制覆盖
                    await websocket.send_json({
                        "type": "data_processing_complete",
                        "message": "数据处理状态已合并",
                        "processing_id": processing_id
                    })
                continue
            
            user_message = message_data.get("message", "")
            extracted_satellites = message_data.get("extracted_satellites", [])
            location = message_data.get("location")

            if not user_message:
                await websocket.send_json({
                    "type": "error",
                    "message": "消息不能为空"
                })
                continue
            print('hhhhhhhh',user_message)
            # 获取或创建对话状态
            state = get_or_create_conversation(conversation_id)

            # 🆕 检测是否是新方案请求
            # is_new_plan_request = any(keyword in user_message.lower() for keyword in [
            #     "监测", "方案", "规划", "设计", "观测", "分析", "查看"
            # ])

            # 🔧 关键修复：如果是新方案请求且已有方案，重置澄清状态
            # if is_new_plan_request and state.main_plan:
            #     logger.info("🔄 检测到新方案请求，重置参数澄清状态")
            #     state.metadata["clarification_completed"] = False
            #     state.metadata["clarification_skipped"] = False
            #     state.metadata["extracted_parameters"] = {}
            #     state.metadata["awaiting_clarification"] = False
            #     state.set_extracted_satellites([])
            #
            #     # 重置参数收集阶段
            #     state.parameter_collection_stage = "not_started"
            #     state.parameter_collection_history = []
            #     state.stage_retry_count = {}
            #
            #     # 🆕 关键：标记新方案请求的起始位置
            #     state.mark_new_plan_request()

            # 🆕 保存位置信息
            if location:
                state.metadata["location"] = location

            # 发送开始处理信号
            await websocket.send_json({
                "type": "processing_start",
                "message": "开始处理您的消息..."
            })

            # 初始化变量
            updated_state = state
            assistant_response = ""

            try:
                # 定义WebSocket回调函数
                async def websocket_callback(data):
                    """WebSocket消息发送回调"""
                    try:
                        await websocket.send_json(data)
                    except Exception as e:
                        logger.error(f"发送WebSocket消息失败: {str(e)}")

                # 使用流式处理
                updated_state, assistant_response = await process_user_input_streaming(
                    user_message,
                    state,
                    websocket_callback
                )

                # 保存状态
                await save_conversation_state(updated_state)

                # 🆕 确保返回最新的卫星信息
                final_satellites = updated_state.extracted_satellites

                # 如果状态中没有卫星但响应中有方案，尝试提取
                if not final_satellites and assistant_response and (
                        "卫星组成" in assistant_response or
                        "虚拟星座方案" in assistant_response
                ):
                    # 导入提取函数
                    from backend.src.graph.workflow_streaming import extract_satellites_from_plan
                    final_satellites = await extract_satellites_from_plan(assistant_response)
                    if final_satellites:
                        updated_state.set_extracted_satellites(final_satellites)
                        await save_conversation_state(updated_state)

                # 🔧 关键修改：获取意图信息
                current_intent = updated_state.metadata.get("intent", "unknown")
                has_streamed_response = current_intent in ["provide_info", "greeting", "thanks", "chat",]
                # 🔧 关键修改：只在特定意图时传递卫星和位置信息
                should_show_map = current_intent in ["generate_plan", "optimize_plan"]

                completion_data = {
                    "type": "processing_complete",
                    "conversation_id": updated_state.conversation_id,
                    "response": assistant_response if not has_streamed_response else None,
                    "intent": current_intent,  # 🔧 新增：传递意图信息
                    "message": "处理完成"
                }

                # 🔧 关键修改：只在应该显示地图时才传递卫星和位置信息
                if should_show_map:
                    completion_data.update({
                        "extracted_satellites": [],
                        "location": updated_state.metadata.get("location"),
                        "show_map": True  # 🔧 新增：明确指示是否显示地图
                    })
                else:
                    completion_data.update({
                        "extracted_satellites": [],  # 🔧 不显示地图时传递空列表
                        "location": None,
                        "show_map": False  # 🔧 明确指示不显示地图
                    })

                # 发送最终完成信号
                await websocket.send_json(completion_data)

            except Exception as e:
                logger.error(f"处理消息时出错: {str(e)}")
                logger.error(traceback.format_exc())

                error_message = f"处理消息时出错: {str(e)}"
                updated_state.add_message("assistant", f"抱歉，{error_message}")

                try:
                    await save_conversation_state(updated_state)
                except:
                    pass

                await websocket.send_json({
                    "type": "error",
                    "message": error_message,
                    "response": f"抱歉，{error_message}",
                    "conversation_id": conversation_id
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket断开连接: {conversation_id}")
        if conversation_id in active_websockets:
            del active_websockets[conversation_id]
    except Exception as e:
        logger.error(f"WebSocket错误: {str(e)}")
        logger.error(traceback.format_exc())
        if conversation_id in active_websockets:
            del active_websockets[conversation_id]


async def process_message_streaming(websocket: WebSocket, state: WorkflowState, user_message: str):
    """流式处理消息 - 简化版本"""
    try:
        # 1. 发送开始信号
        await websocket.send_json({
            "type": "processing_start",
            "message": "开始处理您的消息..."
        })

        # 2. 添加用户消息
        state.add_message("user", user_message)

        # 3. 发送思考步骤
        await websocket.send_json({
            "type": "thinking_step",
            "step": "意图分析",
            "message": "正在分析您的请求意图..."
        })

        await asyncio.sleep(0.5)  # 模拟处理时间

        # 4. 意图分析（简化）
        intent = analyze_intent_simple(user_message, state)

        await websocket.send_json({
            "type": "thinking_step",
            "step": "意图识别",
            "message": f"识别到意图: {intent}"
        })

        # 5. 根据意图处理
        if intent == "generate_plan":
            await websocket.send_json({
                "type": "thinking_step",
                "step": "知识检索",
                "message": "正在检索相关卫星知识..."
            })

            await asyncio.sleep(1)  # 模拟检索时间

            # 知识检索
            state = retrieve_knowledge_for_workflow(state)

            await websocket.send_json({
                "type": "thinking_step",
                "step": "方案生成",
                "message": "正在生成虚拟星座方案..."
            })

            await asyncio.sleep(1)  # 模拟生成时间

            # 生成方案
            state = await buffered_streaming_planning_nodes.generate_constellation_plan_streaming(state)

        if intent == "generate_plan" and state.main_plan:
            # 生成可视化数据

            # 将可视化数据添加到状态中

            # 在响应中添加可视化提示
            visualization_prompt = add_visualization_to_response(state)
            if visualization_prompt and state.messages:
                # 更新最后一条助手消息
                for msg in reversed(state.messages):
                    if msg.role == "assistant":
                        msg.content += visualization_prompt
                        break

        # 6. 流式发送响应
        await stream_response(websocket, state)

        # 7. 保存状态
        await save_conversation_state(state)

        # 发送完成信号时包含可视化数据
        await websocket.send_json({
            "type": "processing_complete",
            "message": "处理完成",
            "visualization_data": state.metadata.get("visualization_data"),
            "extracted_satellites": state.extracted_satellites
        })

    except Exception as e:
        logger.error(f"流式处理出错: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": f"处理出错: {str(e)}"
        })


async def stream_response(websocket: WebSocket, state: WorkflowState):
    """流式发送响应内容"""
    # 获取最新的助手消息
    assistant_message = ""
    for msg in reversed(state.messages):
        if msg.role == "assistant":
            assistant_message = msg.content
            break

    if not assistant_message:
        assistant_message = "抱歉，未能生成有效回复。"

    # 按段落分割内容进行流式发送
    paragraphs = assistant_message.split('\n\n')

    for i, paragraph in enumerate(paragraphs):
        if paragraph.strip():
            await websocket.send_json({
                "type": "response_chunk",
                "content": paragraph.strip(),
                "chunk_index": i,
                "is_final": i == len(paragraphs) - 1
            })

            # 添加延迟使流式效果更明显
            await asyncio.sleep(0.3)


def analyze_intent_simple(user_message: str, state: WorkflowState) -> str:
    """简化的意图分析"""
    lower_msg = user_message.lower()

    if any(word in lower_msg for word in ["监测", "方案", "设计", "观测", "卫星"]):
        return "generate_plan"
    elif any(word in lower_msg for word in ["优化", "改进", "调整"]):
        return "optimize_plan"
    elif any(word in lower_msg for word in ["什么是", "介绍", "说明"]):
        return "provide_info"
    else:
        return "continue_conversation"


async def process_message_async(state: WorkflowState, message: str, websocket: WebSocket):
    """异步处理消息并通过WebSocket发送更新 - 支持流式输出"""
    try:
        # 发送开始消息
        await websocket.send_json({"type": "processing_start"})

        # 向状态添加用户消息
        state.add_message("user", message)

        # 定义WebSocket回调函数
        async def websocket_callback(data):
            """WebSocket消息发送回调"""
            try:
                await websocket.send_json(data)
            except Exception as e:
                logger.error(f"发送WebSocket消息失败: {str(e)}")

        # 使用流式工作流处理消息
        updated_state, assistant_response = await process_user_input_streaming(
            message,
            state,
            websocket_callback
        )

        # 保存对话状态
        await save_conversation_state(updated_state)

        # 发送最终完成消息
        await websocket.send_json({
            "type": "processing_complete",
            "conversation_id": updated_state.conversation_id,
            "message": assistant_response,
            "plan": updated_state.main_plan
        })

    except asyncio.CancelledError:
        # 任务被取消
        await websocket.send_json({"type": "processing_cancelled"})
        raise

    except Exception as e:
        logger.error(f"异步处理消息时出错: {str(e)}")
        logger.error(traceback.format_exc())

        # 发送错误消息
        await websocket.send_json({
            "type": "error",
            "error": f"处理消息时出错: {str(e)}"
        })

        # 添加错误响应到对话
        error_response = f"处理您的请求时出错，请稍后重试。错误: {str(e)}"
        state.add_message("assistant", error_response)

        # 保存对话状态
        await save_conversation_state(state        )


# ===== 爬虫智能体API端点 =====

@app.post("/api/crawl/start", response_model=CrawlJobResponse)
async def start_crawl_job(request: CrawlJobRequest, background_tasks: BackgroundTasks):
    """启动爬取任务"""
    try:
        logger.info(f"收到爬取请求: 站点{request.target_sites}, 关键词{request.keywords}, 最大数量{request.max_satellites}")
        
        # 创建爬取任务
        job_id = await crawler_workflow.create_crawl_job(
            target_sites=request.target_sites,
            keywords=request.keywords,
            max_satellites=request.max_satellites
        )
        
        # 在后台执行任务
        background_tasks.add_task(crawler_workflow.execute_crawl_job, job_id)
        
        return CrawlJobResponse(
            job_id=job_id,
            status="pending",
            message="爬取任务已创建，正在后台执行",
            estimated_time=request.max_satellites * 2  # 估算时间（秒）
        )
        
    except Exception as e:
        logger.error(f"启动爬取任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启动爬取任务失败: {str(e)}")


@app.get("/api/crawl/status/{job_id}", response_model=CrawlJobStatusResponse)
async def get_crawl_job_status(job_id: str = PathParam(...)):
    """获取爬取任务状态"""
    try:
        job_status = crawler_workflow.get_job_status(job_id)
        
        if not job_status:
            raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")
        
        return CrawlJobStatusResponse(
            job_id=job_status["job_id"],
            status=job_status["status"],
            created_at=job_status["created_at"],
            started_at=job_status.get("started_at"),
            completed_at=job_status.get("completed_at"),
            results=job_status.get("results"),
            error_message=job_status.get("error_message")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取爬取任务状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@app.get("/api/crawl/jobs")
async def list_crawl_jobs(
    status: Optional[str] = Query(None, description="按状态筛选: pending, running, completed, failed"),
    limit: int = Query(20, ge=1, le=100)
):
    """获取爬取任务列表"""
    try:
        jobs = crawler_workflow.list_jobs(status=status)
        
        # 限制返回数量
        jobs = jobs[:limit]
        
        return {
            "jobs": jobs,
            "total": len(jobs)
        }
        
    except Exception as e:
        logger.error(f"获取爬取任务列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取任务列表失败: {str(e)}")


@app.get("/api/crawl/logs", response_model=CrawlLogsResponse)
async def get_crawl_logs(
    limit: int = Query(50, ge=1, le=200, description="返回日志条数")
):
    """获取爬取日志"""
    try:
        logs = await crawler_workflow.get_crawl_logs(limit=limit)
        
        return CrawlLogsResponse(
            logs=logs,
            total=len(logs)
        )
        
    except Exception as e:
        logger.error(f"获取爬取日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取爬取日志失败: {str(e)}")


@app.get("/api/crawl/statistics", response_model=CrawlStatisticsResponse)
async def get_crawl_statistics(
    days: int = Query(30, ge=1, le=365, description="统计天数")
):
    """获取爬取统计信息"""
    try:
        stats = await crawler_workflow.get_crawl_statistics(days=days)
        
        return CrawlStatisticsResponse(
            total_crawls=stats["total_crawls"],
            total_new_satellites=stats["total_new_satellites"],
            total_failed=stats["total_failed"],
            daily_stats=stats["daily_stats"],
            site_stats=stats["site_stats"],
            recent_logs=stats["recent_logs"]
        )
        
    except Exception as e:
        logger.error(f"获取爬取统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取爬取统计失败: {str(e)}")


@app.post("/api/crawl/manual")
async def manual_crawl(
    request: CrawlJobRequest,
    background_tasks: BackgroundTasks
):
    """手动触发爬取（立即执行）"""
    try:
        logger.info(f"手动爬取请求: 站点{request.target_sites}")
        
        # 创建并立即执行任务
        job_id = await crawler_workflow.create_crawl_job(
            target_sites=request.target_sites,
            keywords=request.keywords,
            max_satellites=request.max_satellites
        )
        
        # 异步执行任务
        async def execute_and_log():
            try:
                result = await crawler_workflow.execute_crawl_job(job_id)
                logger.info(f"手动爬取完成: {job_id}, 结果: {result}")
            except Exception as e:
                logger.error(f"手动爬取失败: {job_id}, 错误: {str(e)}")
        
        background_tasks.add_task(execute_and_log)
        
        return {
            "job_id": job_id,
            "message": "手动爬取任务已启动",
            "status": "running"
        }
        
    except Exception as e:
        logger.error(f"手动爬取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"手动爬取失败: {str(e)}")


# 🆕 新增：数据处理相关的数据模型
class DataProcessingRequest(BaseModel):
    """数据处理请求模型"""
    conversation_id: str
    selected_satellites: List[str]
    processing_options: Optional[Dict[str, Any]] = None

class DataProcessingResponse(BaseModel):
    """数据处理响应模型"""
    success: bool
    message: str
    processing_id: Optional[str] = None
    progress_url: Optional[str] = None

class ProcessingProgressResponse(BaseModel):
    """处理进度响应模型"""
    processing_id: str
    status: str  # "preparing", "downloading", "processing", "completed", "failed"
    progress: int  # 0-100
    current_stage: str
    message: str
    download_urls: Optional[Dict[str, str]] = None

# 🆕 新增：数据处理API端点

@app.post("/api/process-data", response_model=DataProcessingResponse)
async def process_satellite_data(request: DataProcessingRequest, background_tasks: BackgroundTasks):
    """启动卫星数据处理（若处理器不可用则返回最小响应）"""
    try:
        # 最小模式：直接返回固定 processing_id
        if not DATA_PROCESSOR_AVAILABLE:
            return DataProcessingResponse(
                success=True,
                message="数据处理任务已启动(最小模式)",
                processing_id="test123",
                progress_url=None
            )

        # 标准模式：创建后台处理任务
        processing_id = str(uuid.uuid4())

        processing_tasks[processing_id] = {
            "conversation_id": request.conversation_id,
            "selected_satellites": request.selected_satellites,
            "processing_options": request.processing_options or {},
            "status": "preparing",
            "progress": 0,
            "current_stage": "准备中",
            "message": "正在准备数据处理...",
            "start_time": datetime.now().isoformat(),
            "results": None
        }

        background_tasks.add_task(
            execute_data_processing,
            processing_id,
            request.selected_satellites,
            request.processing_options or {}
        )

        return DataProcessingResponse(
            success=True,
            message="数据处理任务已启动",
            processing_id=processing_id,
            progress_url=f"/api/processing-progress/{processing_id}"
        )

    except Exception as e:
        logger.error(f"启动数据处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动数据处理失败: {str(e)}")

@app.get("/api/processing-progress/{processing_id}", response_model=ProcessingProgressResponse)
async def get_processing_progress(processing_id: str):
    """获取数据处理进度"""
    # 处理最小模式下的固定processing_id
    if processing_id == "test123":
        # 返回模拟进度数据，避免前端崩溃
        return ProcessingProgressResponse(
            processing_id=processing_id,
            status="completed",
            progress=100,
            current_stage="处理完成",
            message="数据处理已完成！(最小模式)",
            download_urls={
                "original": "/api/download/original/test123",
                "processed": "/api/download/processed/test123",
                "package": "/api/download/package/test123"
            }
        )
    
    if processing_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="找不到处理任务")
    
    task = processing_tasks[processing_id]
    
    return ProcessingProgressResponse(
        processing_id=processing_id,
        status=task["status"],
        progress=task["progress"],
        current_stage=task["current_stage"],
        message=task["message"],
        download_urls=task.get("results", {}).get("download_urls") if task.get("results") else None
    )

@app.get("/api/download/{file_type}/{processing_id}")
async def download_processed_data(file_type: str, processing_id: str, preview: bool = Query(False)):
    """下载处理结果文件"""
    # 处理最小模式下的固定processing_id
    if processing_id == "test123":
        # 返回提示信息，告知用户这是最小模式
        raise HTTPException(
            status_code=400, 
            detail="当前运行在最小模式，请先安装OpenCV依赖以启用真实数据处理功能。"
            " 安装命令：cd backend && pip install -r requirements.txt"
        )
    
    if processing_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="找不到处理任务")
    
    task = processing_tasks[processing_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="数据处理尚未完成")
    
    results = task.get("results", {})
    
    if file_type == "original":
        file_path = results.get("original_data")
    elif file_type == "processed":
        file_path = results.get("processed_data")
    elif file_type == "package":
        file_path = results.get("result_package")
    else:
        raise HTTPException(status_code=400, detail="无效的文件类型")
    
    if not file_path:
        raise HTTPException(status_code=404, detail="文件路径缺失")
    # 兼容相对路径：转为绝对路径后检查
    abs_path = file_path
    if not os.path.isabs(abs_path):
        # 以 settings.data_dir 为基准
        try:
            from backend.config.config import settings as _settings
            base_dir = _settings.data_dir
        except Exception:
            base_dir = os.getcwd()
        abs_path = os.path.abspath(os.path.join(base_dir, os.path.relpath(file_path)))

    if not os.path.exists(abs_path):
        # 回退：直接检查原始路径
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")
        abs_path = file_path
    
    # 预览模式：将任意格式（如tif）转为PNG内联返回，便于前端<img>展示
    if preview:
        try:
            png_bytes: bytes = b""
            try:
                import cv2
                import numpy as np
                img = cv2.imread(abs_path, cv2.IMREAD_UNCHANGED)
                if img is None:
                    raise ValueError("无法读取图像用于预览")
                # 若是灰度或带Alpha，尽量转换为BGR
                if len(img.shape) == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                ok, buf = cv2.imencode('.png', img)
                if not ok:
                    raise ValueError("PNG编码失败")
                png_bytes = buf.tobytes()
            except Exception:
                # 回退到PIL
                from PIL import Image
                from io import BytesIO
                pil_img = Image.open(abs_path)
                if pil_img.mode not in ('RGB', 'RGBA'):
                    pil_img = pil_img.convert('RGB')
                bio = BytesIO()
                pil_img.save(bio, format='PNG')
                png_bytes = bio.getvalue()
            return Response(content=png_bytes, media_type='image/png')
        except Exception as e:
            logger.error(f"生成预览失败: {e}")
            raise HTTPException(status_code=500, detail=f"生成预览失败: {str(e)}")

    filename = Path(abs_path).name
    return FileResponse(abs_path, filename=filename)

async def execute_data_processing(processing_id: str, selected_satellites: List[str], processing_options: Dict[str, Any]):
    """执行数据处理的后台任务"""
    try:
        task = processing_tasks[processing_id]
        # 延迟导入，避免在应用启动时因依赖问题导致导入失败
        try:
            from backend.src.graph.state import SatelliteDataSource, DataProcessingOptions
        except Exception:
            # 兜底：定义轻量占位模型，保证最小可运行
            from pydantic import BaseModel
            class SatelliteDataSource(BaseModel):
                satellite_name: str
                data_type: str
                download_url: Optional[str] = None
                local_path: Optional[str] = None
            class DataProcessingOptions(BaseModel):
                normalize_illumination: bool = True
                radiometric_correction: bool = True
                atmospheric_correction: bool = False
                geometric_correction: bool = False
                output_format: str = "geotiff"
        
        # 固定样例图像路径：由调用方预先放置样例图像
        # 要求：请在以下路径放置样例图像文件：data/samples/sample_optical.tif（项目根目录下）
        # 这里仅确保目录存在，不会自动创建样例图像文件
        sample_path = os.path.join(settings.data_dir, "samples", "sample_optical.tif")
        os.makedirs(os.path.dirname(sample_path), exist_ok=True)

        # 更新状态为下载中
        task.update({
            "status": "downloading",
            "progress": 10,
            "current_stage": "数据获取中",
            "message": "正在获取卫星数据..."
        })
        
        # 模拟数据源（实际应用中应该从星座方案中获取）
        data_sources = []
        for satellite in selected_satellites:
            data_source = SatelliteDataSource(
                satellite_name=satellite,
                data_type="optical",
                download_url=None,  # 实际应用中应该有真实的下载地址
                # 使用固定样例图像进行后续处理
                local_path=sample_path
            )
            data_sources.append(data_source)
        
        # 数据获取阶段 (10-50%)
        downloaded_files = []
        for i, data_source in enumerate(data_sources):
            try:
                file_path = await data_processor.download_satellite_data(data_source)
                downloaded_files.append(file_path)
                
                # 更新进度
                progress = 10 + int((i + 1) / len(data_sources) * 40)
                task.update({
                    "progress": progress,
                    "message": f"已获取 {i + 1}/{len(data_sources)} 个卫星数据"
                })
                
            except Exception as e:
                logger.error(f"获取数据失败 {data_source.satellite_name}: {e}")
                continue
        
        if not downloaded_files:
            raise Exception("没有成功获取任何数据")
        
        # 更新状态为处理中
        task.update({
            "status": "processing",
            "progress": 50,
            "current_stage": "数据处理中",
            "message": "正在处理卫星数据..."
        })
        
        # 数据处理阶段 (50-90%)
        processing_options_obj = DataProcessingOptions(**processing_options)
        processed_results = []
        
        for i, file_path in enumerate(downloaded_files):
            try:
                result = await data_processor.process_satellite_data(file_path, processing_options_obj)
                processed_results.append(result)
                
                # 更新进度
                progress = 50 + int((i + 1) / len(downloaded_files) * 40)
                task.update({
                    "progress": progress,
                    "message": f"已处理 {i + 1}/{len(downloaded_files)} 个数据文件"
                })
                
            except Exception as e:
                logger.error(f"处理数据失败 {file_path}: {e}")
                continue
        
        if not processed_results:
            raise Exception("没有成功处理任何数据")
        
        # 完成阶段 (90-100%)
        task.update({
            "status": "completed",
            "progress": 100,
            "current_stage": "处理完成",
            "message": "数据处理完成！",
            "results": {
                "original_data": processed_results[0]["original_data"],
                "processed_data": processed_results[0]["processed_data"],
                "result_package": processed_results[0]["result_package"],
                "download_urls": {
                    "original": f"/api/download/original/{processing_id}",
                    "processed": f"/api/download/processed/{processing_id}",
                    "package": f"/api/download/package/{processing_id}"
                }
            }
        })
        
        logger.info(f"数据处理任务 {processing_id} 完成")
        
    except Exception as e:
        logger.error(f"数据处理任务 {processing_id} 失败: {e}")
        if processing_id in processing_tasks:
            processing_tasks[processing_id].update({
                "status": "failed",
                "progress": 0,
                "current_stage": "处理失败",
                "message": f"数据处理失败: {str(e)}"
            })

# 服务器启动时间
startup_time = datetime.now().timestamp()

# 当直接运行此文件时执行测试
if __name__ == "__main__":
    import uvicorn

    print("=" * 50)
    print("测试智慧虚拟星座助手API")
    print("=" * 50)

    # 确保目录存在
    os.makedirs(os.path.join(settings.data_dir, "conversations"), exist_ok=True)

    # 使用uvicorn运行API
    uvicorn.run(
        app,  # 直接使用app实例
        host="127.0.0.1",  # 使用本地回环地址
        port=2025,
        
        log_level="info"
    )