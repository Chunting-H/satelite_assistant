# backend/main.py

import os
import logging
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import uuid
import json
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="智慧虚拟星座助手",
    description="多智能体协同的虚拟星座规划与遥感数据获取系统",
    version="0.1.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 定义数据模型
class ChatMessage(BaseModel):
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: Optional[float] = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    use_web_search: bool = False


class ChatResponse(BaseModel):
    conversation_id: str
    message: ChatMessage
    thinking_process: Optional[List[Dict[str, Any]]] = None


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    size: int
    type: str
    analysis: Optional[Dict[str, Any]] = None


# 存储活跃的WebSocket连接
active_connections: Dict[str, WebSocket] = {}

# 存储上传的文件信息
uploaded_files: Dict[str, Dict[str, Any]] = {}

# 存储对话历史
conversations: Dict[str, List[ChatMessage]] = {}

# 处理文件上传的目录
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# API路由

@app.get("/")
async def read_root():
    """健康检查端点"""
    return {"status": "ok", "service": "虚拟星座助手API"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求的REST API端点"""
    conversation_id = request.conversation_id or str(uuid.uuid4())

    # 创建新对话或获取现有对话
    if conversation_id not in conversations:
        conversations[conversation_id] = []

    # 添加用户消息到对话历史
    user_message = ChatMessage(
        role="user",
        content=request.message,
        timestamp=time.time()
    )
    conversations[conversation_id].append(user_message)

    # TODO: 调用对话管理智能体处理消息
    # 这里是一个简单的回显响应，实际实现中会调用智能体
    assistant_message = ChatMessage(
        role="assistant",
        content=f"收到你的消息: {request.message}",
        timestamp=time.time()
    )
    conversations[conversation_id].append(assistant_message)

    return ChatResponse(
        conversation_id=conversation_id,
        message=assistant_message,
        thinking_process=[{"step": "初始化", "details": "回显用户消息"}]
    )


@app.post("/api/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """处理文件上传"""
    # 生成唯一文件ID
    file_id = str(uuid.uuid4())

    # 准备文件路径
    filename = file.filename
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{filename}")

    # 保存文件
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)

        # 存储文件信息
        file_info = {
            "file_id": file_id,
            "filename": filename,
            "path": file_path,
            "size": len(contents),
            "type": file.content_type,
            "upload_time": time.time()
        }
        uploaded_files[file_id] = file_info

        # TODO: 调用文件处理智能体解析文件
        # 现在返回一个简单的分析结果
        analysis = {"status": "上传成功，等待处理"}

        return FileUploadResponse(
            file_id=file_id,
            filename=filename or "unknown_file",
            size=len(contents),
            type=file.content_type or "application/octet-stream",
            analysis=analysis
        )
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@app.get("/api/files")
async def list_files():
    """列出上传的文件"""
    return {
        "files": [
            {
                "file_id": file_id,
                "filename": info["filename"],
                "size": info["size"],
                "type": info["type"],
                "upload_time": info["upload_time"]
            }
            for file_id, info in uploaded_files.items()
        ]
    }


@app.get("/api/files/{file_id}")
async def get_file_info(file_id: str):
    """获取特定文件的信息"""
    if file_id not in uploaded_files:
        raise HTTPException(status_code=404, detail="找不到文件")

    return uploaded_files[file_id]


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """删除上传的文件"""
    if file_id not in uploaded_files:
        raise HTTPException(status_code=404, detail="找不到文件")

    file_info = uploaded_files[file_id]
    try:
        os.remove(file_info["path"])
        del uploaded_files[file_id]
        return {"status": "success", "message": "文件已删除"}
    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """处理WebSocket连接"""
    await websocket.accept()

    # 分配连接ID
    connection_id = str(uuid.uuid4())
    active_connections[connection_id] = websocket

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            try:
                # 解析JSON消息
                message_data = json.loads(data)
                message_type = message_data.get("type", "message")

                # 获取或创建会话ID
                conversation_id = message_data.get("conversation_id")
                if not conversation_id:
                    conversation_id = str(uuid.uuid4())
                    message_data["conversation_id"] = conversation_id

                # 根据消息类型处理
                if message_type == "message":
                    # 处理聊天消息
                    user_message = message_data.get("message", "")

                    # 创建或获取对话历史
                    if conversation_id not in conversations:
                        conversations[conversation_id] = []

                    # 添加用户消息到历史
                    conversations[conversation_id].append(
                        ChatMessage(
                            role="user",
                            content=user_message,
                            timestamp=time.time()
                        )
                    )

                    # TODO: 调用对话管理智能体处理消息
                    # 暂时返回简单回显
                    response = {
                        "type": "message",
                        "conversation_id": conversation_id,
                        "message": {
                            "role": "assistant",
                            "content": f"[WebSocket] 收到你的消息: {user_message}",
                            "timestamp": time.time()
                        }
                    }

                    # 将助手消息添加到对话历史
                    conversations[conversation_id].append(
                        ChatMessage(**response["message"])
                    )

                    # 发送响应
                    await websocket.send_text(json.dumps(response))

                elif message_type == "thinking":
                    # 处理思考过程更新请求
                    # 这将用于向客户端流式传输智能体的思考过程
                    await websocket.send_text(json.dumps({
                        "type": "thinking",
                        "conversation_id": conversation_id,
                        "thinking": [{"step": "初始化", "details": "准备处理请求"}]
                    }))

                else:
                    # 未知消息类型
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "error": f"未知的消息类型: {message_type}"
                    }))

            except json.JSONDecodeError:
                # 非JSON消息处理
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": "无效的JSON格式"
                }))

            except Exception as e:
                # 其他错误处理
                logger.error(f"处理WebSocket消息时出错: {str(e)}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": f"处理消息时出错: {str(e)}"
                }))

    except WebSocketDisconnect:
        # 处理断开连接
        logger.info(f"客户端断开连接: {connection_id}")
        if connection_id in active_connections:
            del active_connections[connection_id]

    except Exception as e:
        # 处理其他异常
        logger.error(f"WebSocket连接错误: {str(e)}")
        if connection_id in active_connections:
            del active_connections[connection_id]


@app.on_event("startup")
async def startup_event():
    """服务启动时执行的操作"""
    logger.info("虚拟星座助手服务启动")
    # TODO: 初始化FAISS知识库
    # TODO: 加载智能体模型


@app.on_event("shutdown")
async def shutdown_event():
    """服务关闭时执行的操作"""
    logger.info("虚拟星座助手服务关闭")
    # 清理临时文件
    # 关闭连接等

# 注释掉重复的startup_event函数和未定义的ai_settings
# from backend.src.llm.jiuzhou_model_manager import get_jiuzhou_manager

# async def startup_event():
#     """应用启动事件"""
#     # 预加载九州模型（可选，也可以延迟加载）
#     if ai_settings.jiuzhou_enabled:
#         logger.info("预加载九州模型...")
#         manager = get_jiuzhou_manager()
#         manager.initialize()
#         logger.info("九州模型加载完成")

# app.add_event_handler("startup", startup_event)

# ================== 最小可行的数据处理接口 ==================

@app.post("/api/process-data")
async def process_data(payload: Dict[str, Any]):
    """最小可行的数据处理接口

    输入：用户选择的卫星组合（数组即可），字段名不做强约束，兼容如下几种：
    - selected_satellites
    - selectedCombinations
    - selected
    - combinations

    输出：固定返回 processing_id = "test123"
    """
    try:
        selections = (
            payload.get("selected_satellites")
            or payload.get("selectedCombinations")
            or payload.get("selected")
            or payload.get("combinations")
            or []
        )
        logger.info(f"收到数据处理请求，选择项数量: {len(selections)}")
        return {"success": True, "processing_id": "test123"}
    except Exception as e:
        logger.error(f"处理数据处理请求失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=2025)