# backend/src/graph/workflow_streaming.py - 修复所有意图的流式输出
import os
import sys
import logging
import json
import requests
import uuid
import numpy as np
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Callable, Union
from pathlib import Path
import time
from dotenv import load_dotenv, find_dotenv
import re

# 设置项目根目录
dotenv_path = find_dotenv()
if dotenv_path:
    project_root = Path(dotenv_path).parent
else:
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent

sys.path.append(str(project_root))

if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path, override=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 导入项目组件
from backend.src.graph.state import WorkflowState
from backend.src.tools.knowledge_tools import retrieve_knowledge_for_workflow
# 导入流式方案生成节点 - 优先使用带缓冲的版本
# from backend.src.graph.nodes.buffered_streaming_planning_nodes import (
#     generate_constellation_plan_streaming,
#     optimize_constellation_plan_streaming
# )
from backend.src.graph.nodes.direct_streaming_planning_nodes import (
    generate_constellation_plan_streaming,
    optimize_constellation_plan_streaming
)
from backend.src.tools.satellite_extractor import (
    extract_satellite_names,
    extract_satellite_names_from_messages,
    extract_satellite_names_with_cache,
    extract_satellites_from_composition,
    extract_satellites_from_table,
    extract_satellites_two_phase,
    normalize_satellite_name
)

STREAMING_NODES_AVAILABLE = True
logger.info("成功导入带缓冲的流式方案生成节点")

# DeepSeek API配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

if not DEEPSEEK_API_KEY:
    logger.warning("DEEPSEEK_API_KEY环境变量未设置，意图分析将无法使用LLM")


def convert_to_json_serializable(obj):
    """递归地将对象转换为JSON可序列化的格式"""
    if isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, set):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif hasattr(obj, '__dict__'):
        return convert_to_json_serializable(obj.__dict__)
    else:
        return obj


def safe_json_dumps(obj, **kwargs):
    """安全的JSON序列化函数"""
    try:
        return json.dumps(obj, **kwargs)
    except TypeError as e:
        logger.warning(f"直接序列化失败: {str(e)}, 尝试转换后序列化")
        converted_obj = convert_to_json_serializable(obj)
        return json.dumps(converted_obj, **kwargs)


async def extract_satellites_from_plan(plan_content: str) -> List[str]:
    """从方案内容中提取卫星名称 - 使用统一的提取器"""
    if not plan_content:
        logger.warning("方案内容为空，无法提取卫星")
        return []

    logger.info(f"🔍 开始从方案中提取卫星，内容长度: {len(plan_content)}")

    # 使用统一的提取函数
    satellites = await extract_satellite_names_with_cache(plan_content)

    logger.info(f"✅ 最终提取到的卫星列表: {satellites}")
    return satellites


class StreamingContentSender:
    """流式内容发送器 - 用于模拟和真实的流式输出"""

    def __init__(self, websocket_callback=None):
        self.websocket_callback = websocket_callback

    async def send_content_streaming(self, content: str, chunk_size: int = 15, delay: float = 0.1):
        """以流式方式发送内容"""
        if not content or not self.websocket_callback:
            return

        # 按句子或自然分段点分割内容
        segments = self._split_content_naturally(content)
        accumulated_content = ""

        for segment in segments:
            accumulated_content += segment

            await self.websocket_callback({
                "type": "response_chunk",
                "content": segment,
                "accumulated_content": accumulated_content,
                "chunk_type": "streaming_response"
            })

            # 根据内容长度调整延迟
            segment_delay = min(delay * len(segment) / 10, delay * 3)
            await asyncio.sleep(segment_delay)

    def _split_content_naturally(self, content: str) -> List[str]:
        """自然地分割内容为段落"""
        import re

        # 按段落分割
        paragraphs = content.split('\n\n')
        segments = []

        for paragraph in paragraphs:
            if not paragraph.strip():
                continue

            # 如果段落很长，按句子分割
            if len(paragraph) > 100:
                sentences = re.split(r'([。！？\.!?])', paragraph)
                current_segment = ""

                for i in range(0, len(sentences), 2):
                    sentence = sentences[i]
                    punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""

                    current_segment += sentence + punctuation

                    # 如果段落达到合适长度或是最后一个句子
                    if len(current_segment) >= 30 or i >= len(sentences) - 2:
                        segments.append(current_segment)
                        current_segment = ""
            else:
                segments.append(paragraph)

            # 段落之间添加换行
            if paragraph != paragraphs[-1]:
                segments.append('\n\n')

        return [seg for seg in segments if seg.strip()]


class StreamingWorkflowManager:
    """增强的流式工作流管理器 - 支持所有意图的流式输出"""

    def __init__(self, websocket_callback=None):
        self.websocket_callback = websocket_callback
        self.sent_thinking_steps = set()
        self.current_session_id = str(uuid.uuid4())
        self.content_sender = StreamingContentSender(websocket_callback)

    async def send_status(self, message_type: str, data: Dict[str, Any]):
        """立即发送状态更新"""
        if self.websocket_callback:
            try:
                if message_type == "thinking_step":
                    step_key = f"{data.get('step', '')}__{data.get('message', '')}"
                    if step_key in self.sent_thinking_steps:
                        return
                    self.sent_thinking_steps.add(step_key)

                await self.websocket_callback({
                    "type": message_type,
                    "timestamp": time.time(),
                    **data
                })
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"发送WebSocket消息失败: {str(e)}")

    def reset_session(self):
        """重置会话"""
        self.sent_thinking_steps.clear()
        self.current_session_id = str(uuid.uuid4())
        logger.info(f"重置思考步骤会话: {self.current_session_id}")

    def _smart_truncate_history(self, history_messages: List[Dict], current_message: str, max_messages: int = 20) -> \
            List[Dict]:
        """智能截断对话历史"""
        if len(history_messages) <= max_messages:
            return history_messages

        # 提取当前消息的关键词
        current_keywords = self._extract_keywords(current_message)

        # 计算每条历史消息的相关性分数
        message_scores = []
        for i, msg in enumerate(history_messages):
            if msg["role"] == "user":
                relevance_score = self._calculate_relevance(msg["content"], current_keywords)
                message_scores.append((i, relevance_score))

        # 按相关性排序，保留最相关的消息
        message_scores.sort(key=lambda x: x[1], reverse=True)

        # 选择最相关的消息，但确保包含最近的对话
        selected_indices = set()

        # 首先保留最近的对话（最后5轮）
        recent_count = min(5, len(history_messages) // 2)
        for i in range(len(history_messages) - recent_count, len(history_messages)):
            selected_indices.add(i)

        # 然后添加最相关的消息
        for i, score in message_scores:
            if len(selected_indices) < max_messages and i not in selected_indices:
                selected_indices.add(i)

        # 按原始顺序返回选中的消息
        selected_messages = [history_messages[i] for i in sorted(selected_indices)]

        logger.info(f"智能截断：从{len(history_messages)}条消息中选择{len(selected_messages)}条最相关的消息")
        return selected_messages

    def _extract_keywords(self, text: str) -> List[str]:
        """提取文本关键词（简化版本）"""
        # 简单的关键词提取：去除停用词，保留重要词汇
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很',
                      '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}

        # 简单的分词（按空格和标点分割）
        import re
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text.lower())

        # 过滤停用词和短词
        keywords = [word for word in words if word not in stop_words and len(word) > 1]

        return keywords[:10]  # 最多返回10个关键词

    def _calculate_relevance(self, text: str, keywords: List[str]) -> float:
        """计算文本与关键词的相关性分数"""
        if not keywords:
            return 0.0

        text_lower = text.lower()
        matches = sum(1 for keyword in keywords if keyword in text_lower)
        return matches / len(keywords)

    async def generate_response_streaming(self, state: WorkflowState) -> WorkflowState:
        """流式响应生成 - 移除可视化数据处理"""
        intent = state.metadata.get("intent", "unknown")

        await self.send_status("thinking_step", {
            "step": "响应生成",
            "message": f"正在为 '{intent}' 意图生成响应"
        })

        # 生成响应内容
        response_content = ""

        if intent == "generate_plan" and state.main_plan:
            response_content = str(state.main_plan) if not isinstance(state.main_plan, str) else state.main_plan

            # 🔧 移除可视化数据生成逻辑
            # 仅确保卫星信息已经在状态中
            # if not hasattr(state, 'extracted_satellites') or not state.extracted_satellites:
            #     # 改为同步调用
            #     from backend.src.tools.satellite_extractor import extract_satellites_from_composition
            #     extracted_satellites = extract_satellites_from_composition(response_content)
            #     if extracted_satellites:
            #         state.set_extracted_satellites(extracted_satellites)
            #         state.metadata['extracted_satellites'] = extracted_satellites
            #         logger.info(f"✅ 从新方案中提取到卫星: {extracted_satellites}")
            #     else:
            #         logger.warning("⚠️ 未能从方案中提取到卫星信息")

        elif intent == "optimize_plan" and state.main_plan:
            response_content = str(state.main_plan) if not isinstance(state.main_plan, str) else state.main_plan

            # 从优化后的方案中提取卫星
            # extracted_satellites = extract_satellites_from_plan(response_content)
            # if extracted_satellites:
            #     state.set_extracted_satellites(extracted_satellites)

        elif intent == "provide_info":
            response_content = await self.generate_info_response_streaming(state)
        else:
            response_content = await self.generate_general_response_streaming(state)

        # 确保有有效响应
        if not response_content or response_content.strip() == "":
            response_content = "抱歉，未能生成有效回复。请尝试重新描述您的需求。"

        # 添加到状态
        state.add_message("assistant", response_content)

        await self.send_status("thinking_step", {
            "step": "响应准备完成",
            "message": "响应内容已准备完毕"
        })

        state.current_stage = "complete"
        return state

    async def generate_intent_confirmation_message(self, intent: str, user_message: str) -> str:
        """生成意图确认消息 - 仅用于方案生成和优化"""
        confirmation_messages = {
            "generate_plan": f"""📍 基于您的描述，我准备为您：
    1、 🛰️ 设计定制化的虚拟星座组合
    2、 📊 分析最适合的卫星配置
    3、 📈 生成详细的监测方案
    请再一次确认：是否需要我为您生成虚拟星座方案？(是/否)""",

            "optimize_plan": f"""我注意到您想要优化现有的虚拟星座方案。
    🔧 优化意图：
    根据您的反馈「{user_message}」，我理解您希望：
    1、 调整当前方案的某些参数
    2、 改进卫星组合配置
    3、 优化监测效果
    请确认：是否需要我优化当前方案(是/否)？"""
        }

        # 默认返回generate_plan的确认消息
        return confirmation_messages.get(intent, confirmation_messages["generate_plan"])

    async def handle_intent_confirmation(self, state: WorkflowState, user_response: str) -> Tuple[bool, Optional[str]]:
        """处理用户的意图确认回复

        返回: (是否确认, 新意图)
        """
        response_lower = user_response.lower()

        # 确认关键词
        confirm_keywords = ['是', '对', '确认', '没错', '是的', 'yes', 'ok', '好的', '可以', '开始']
        deny_keywords = ['不是', '不对', '否', '不', 'no', '错了', '不用']

        # 检查是否确认
        if any(keyword in response_lower for keyword in confirm_keywords):
            return True, None

        # 检查是否否认
        if any(keyword in response_lower for keyword in deny_keywords):
            # 尝试从新的描述中识别意图
            if len(user_response) > 10:  # 如果用户提供了较长的描述
                # 重新分析意图
                new_intent = await self.deepseek_intent_analysis(
                    user_response,
                    state.get_conversation_history(),
                    state
                )
                return False, new_intent
            return False, None

        # 如果既不确认也不否认，可能是用户直接说明了新需求
        if len(user_response) > 20:
            new_intent = await self.deepseek_intent_analysis(
                user_response,
                state.get_conversation_history(),
                state
            )
            return False, new_intent

        # 默认视为不确认
        return False, None

    async def process_user_input_streaming(self, user_input: str, state: Optional[WorkflowState] = None) -> Tuple[
        WorkflowState, str]:
        """流式处理用户输入 - 🔧 修复：所有意图都支持流式输出"""
        if state is None:
            state = WorkflowState()

        start_time = time.time()
        elapsed = 0.0
        assistant_response = ""
        visualization_data = None

        try:
            # 发送开始处理信号
            await self.send_status("processing_start", {
                "message": "开始处理您的请求...",
                "conversation_id": state.conversation_id
            })

            # 步骤1: 初始化状态
            state = await self.initialize_state_streaming(state, user_input)

            # 🔧 关键修复：先检查是否在等待参数澄清回复
            if state.metadata.get("awaiting_clarification", False):
                # 如果正在等待参数澄清，直接处理澄清回复，跳过意图分析
                await self.send_status("thinking_step", {
                    "step": "参数收集",
                    "message": "处理您的参数回复..."
                })

                state = await self.handle_parameter_clarification(state)

                if state.metadata.get("awaiting_clarification", False):
                    # 仍在等待更多参数
                    assistant_messages = [msg for msg in state.messages if msg.role == "assistant"]
                    assistant_response = assistant_messages[-1].content if assistant_messages else ""

                    await self.send_status("processing_complete", {
                        "message": "等待参数澄清",
                        "clarification_pending": True
                    })

                    return state, assistant_response

                # 参数收集完成，使用之前保存的意图继续流程
                intent = state.metadata.get("intent", "generate_plan")

            else:
                # 🆕 检查是否在等待意图确认
                if state.awaiting_intent_confirmation and state.pending_intent:
                    # 处理用户的确认回复
                    is_confirmed, new_intent = await self.handle_intent_confirmation(state, user_input)

                    if is_confirmed:
                        # 用户确认了意图
                        state.metadata["intent"] = state.pending_intent
                        state.awaiting_intent_confirmation = False
                        state.intent_confirmed = True
                        intent = state.pending_intent
                        state.pending_intent = None

                        await self.send_status("thinking_step", {
                            "step": "意图确认",
                            "message": f"已确认您的意图：{intent}"
                        })

                        # 继续执行原定流程
                    elif new_intent:
                        # 用户提供了新的意图
                        state.metadata["intent"] = new_intent
                        state.pending_intent = new_intent
                        intent = new_intent

                        # 生成新的确认消息
                        confirmation_msg = await self.generate_intent_confirmation_message(intent, user_input)
                        state.add_message("assistant", confirmation_msg)

                        # 流式发送确认消息
                        await self.content_sender.send_content_streaming(confirmation_msg, delay=0.05)

                        await self.send_status("processing_complete", {
                            "message": "等待意图确认",
                            "awaiting_confirmation": True
                        })

                        return state, confirmation_msg
                    else:
                        # 用户否认但没有提供新信息
                        clarify_msg = """我理解您的需求可能不同。请告诉我：

                您具体想要什么帮助呢？比如：
                - 🛰️ 设计卫星监测方案
                - 📚 了解虚拟星座知识
                - 🔧 优化现有方案
                - 💬 其他问题

                请详细描述您的需求。"""

                        state.add_message("assistant", clarify_msg)
                        state.awaiting_intent_confirmation = False
                        state.pending_intent = None

                        await self.content_sender.send_content_streaming(clarify_msg, delay=0.08)

                        await self.send_status("processing_complete", {
                            "message": "请提供更多信息"
                        })

                        return state, clarify_msg
                else:
                    # 步骤2: 只有在非参数澄清状态下才进行意图分析
                    state = await self.analyze_user_input_streaming(state)
                    intent = state.metadata.get("intent", "unknown")

            if intent == "generate_plan" and not state.intent_confirmed:  # 修改这一行，从 ["generate_plan", "optimize_plan"] 改为只有 "generate_plan"
                # 保存待确认的意图
                state.pending_intent = intent
                state.awaiting_intent_confirmation = True
                state.intent_confirmed = False

                # 生成确认消息
                confirmation_msg = await self.generate_intent_confirmation_message(intent, user_input)
                state.add_message("assistant", confirmation_msg)

                # 流式发送确认消息
                await self.content_sender.send_content_streaming(confirmation_msg, delay=0.05)

                await self.send_status("processing_complete", {
                    "message": "等待意图确认",
                    "awaiting_confirmation": True,
                    "pending_intent": intent
                })

                return state, confirmation_msg

            # 🔧 关键改进：所有意图都使用流式输出
            if intent == "greeting":
                # 🆕 流式问候回复
                response = await self.generate_greeting_response_streaming(state)
                state.add_message("assistant", response)
                assistant_response = response

            elif intent == "thanks":
                # 🆕 流式感谢回复
                response = await self.generate_thanks_response_streaming(state)
                state.add_message("assistant", response)
                assistant_response = response

            elif intent == "chat":
                # 🆕 流式闲聊回复
                response = await self.generate_chat_response_streaming(state)
                state.add_message("assistant", response)
                assistant_response = response

            elif intent == "generate_plan" and not state.metadata.get("clarification_completed", False):
                # 生成方案需要参数澄清
                state = await self.handle_parameter_clarification(state)

                if state.metadata.get("awaiting_clarification", False):
                    assistant_messages = [msg for msg in state.messages if msg.role == "assistant"]
                    assistant_response = assistant_messages[-1].content if assistant_messages else ""

                    await self.send_status("processing_complete", {
                        "message": "参数澄清中",
                        "clarification_pending": True,
                        "response": assistant_response
                    })

                    return state, assistant_response

            # 处理方案生成或优化
            elif intent in ["generate_plan", "optimize_plan"]:
                await self.send_status("thinking_step", {
                    "step": "流程准备",
                    "message": f"准备处理{intent}请求..."
                })

                if intent == "generate_plan":
                    state = await self.retrieve_knowledge_streaming(state)
                    state = await self.generate_plan_streaming(state)

                elif intent == "optimize_plan":
                    if state.main_plan:
                        state = await self.optimize_plan_streaming(state)
                    else:
                        state = await self.retrieve_knowledge_streaming(state)
                        state = await self.generate_plan_streaming(state)

                # 生成响应（包含可视化数据处理）
                state = await self.generate_response_streaming(state)

            elif intent == "provide_info":
                # 🆕 流式信息回复
                info_response = await self.generate_info_response_streaming(state)
                state.add_message("assistant", info_response)
                assistant_response = info_response

            else:
                # 🆕 流式通用回复
                general_response = await self.generate_general_response_streaming(state)
                state.add_message("assistant", general_response)
                assistant_response = general_response

            # 统一提取助手响应和可视化数据
            if not assistant_response:
                for msg in reversed(state.messages):
                    if msg.role == "assistant":
                        assistant_response = msg.content
                        break

            state.intent_confirmed = False
            # 获取可视化数据
            visualization_data = state.metadata.get("visualization_data")

            elapsed = time.time() - start_time

        except Exception as e:
            logger.error(f"流式处理用户输入时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

            elapsed = time.time() - start_time
            # 提供更友好的错误信息，不暴露技术细节
            error_type = type(e).__name__
            if "timeout" in str(e).lower() or "timeout" in error_type.lower():
                assistant_response = "抱歉，处理您的请求时超时了。请稍后重试，或者尝试简化您的需求描述。"
            elif "connection" in str(e).lower() or "network" in str(e).lower():
                assistant_response = "抱歉，网络连接出现问题。请检查网络连接后重试。"
            elif "api" in str(e).lower() or "deepseek" in str(e).lower():
                assistant_response = "抱歉，AI服务暂时不可用。请稍后重试，或者尝试重新描述您的需求。"
            else:
                assistant_response = "抱歉，处理您的请求时遇到了问题。请稍后重试，或者尝试重新描述您的需求。"

            state.add_message("assistant", assistant_response)

            await self.send_status("error", {
                "message": "处理请求时出错",
                "response": assistant_response
            })

            return state, assistant_response

        # 发送完成信号
        try:
            logger.info(f"流式工作流处理用时: {elapsed:.2f}秒")

            await self.send_status("thinking_step", {
                "step": "处理完成",
                "message": f"处理完成，用时 {elapsed:.1f} 秒"
            })

            # 🔧 简化完成数据，不再包含可视化数据
            completion_data = {
                "message": "处理完成",
                "extracted_satellites": getattr(state, 'extracted_satellites', []),
                "location": state.metadata.get("location")
            }

            await self.send_status("processing_complete", completion_data)

            return state, assistant_response

        except Exception as e:
            logger.error(f"发送完成状态时出错: {str(e)}")
            return state, assistant_response

    # 🆕 新增：流式问候回复生成
    async def generate_greeting_response_streaming(self, state: WorkflowState) -> str:
        """生成流式问候回复"""
        await self.send_status("thinking_step", {
            "step": "生成回复",
            "message": "准备友好的问候回复"
        })

        greetings = [
            "你好！我是智慧虚拟星座助手，很高兴为您服务。我可以帮助您设计定制化的虚拟星座方案，进行卫星监测任务规划。有什么可以帮助您的吗？",
            "您好！欢迎使用智慧虚拟星座系统。我可以根据您的需求设计最适合的卫星观测方案，无论是水质监测、农业观测还是城市规划，都能为您提供专业的支持。",
            "你好！我是您的虚拟星座规划专家。请告诉我您的观测需求，我将为您量身定制最优的卫星组合方案。"
        ]

        import random
        response = random.choice(greetings)

        # 🔧 流式发送回复
        await self.content_sender.send_content_streaming(response, delay=0.08)

        return response

    # 🆕 新增：流式感谢回复生成
    async def generate_thanks_response_streaming(self, state: WorkflowState) -> str:
        """生成流式感谢回复"""
        await self.send_status("thinking_step", {
            "step": "生成回复",
            "message": "准备礼貌的回应"
        })

        responses = [
            "不客气！很高兴能帮助到您。如果您还有其他关于虚拟星座的需求，随时告诉我。",
            "您太客气了！为您提供专业的虚拟星座方案是我的职责。期待继续为您服务！",
            "很高兴能够帮助您！如果方案需要调整或有新的监测需求，请随时告诉我。"
        ]

        import random
        response = random.choice(responses)

        # 🔧 流式发送回复
        await self.content_sender.send_content_streaming(response, delay=0.08)

        return response

    # 🆕 修改：流式闲聊回复生成
    async def generate_chat_response_streaming(self, state: WorkflowState) -> str:
        """使用DeepSeek生成流式闲聊回复"""
        await self.send_status("thinking_step", {
            "step": "生成回复",
            "message": "正在思考合适的回复..."
        })

        # 获取最新的用户消息
        last_user_message = None
        for msg in reversed(state.messages):
            if msg.role == "user":
                last_user_message = msg.content
                break

        if not last_user_message:
            default_response = "抱歉，我没有理解您的意思。请问有什么关于虚拟星座的需求吗？"
            await self.content_sender.send_content_streaming(default_response, delay=0.08)
            return default_response

        # 获取对话历史
        conversation_history = state.get_conversation_history(max_messages=10)

        # 🔧 修改：使用流式API调用，传递对话历史
        response = await self._call_deepseek_streaming_for_chat(last_user_message, conversation_history)

        return response

    # 🆕 修改：流式信息回复生成
    async def generate_info_response_streaming(self, state: WorkflowState) -> str:
        """流式生成信息性响应 - 支持流式输出"""
        await self.send_status("thinking_step", {
            "step": "信息查询",
            "message": "正在准备相关信息回复"
        })

        # 获取用户最新的消息
        last_user_message = None
        for msg in reversed(state.messages):
            if msg.role == "user":
                last_user_message = msg.content
                break

        if not last_user_message:
            default_response = "抱歉，我没有理解您想了解什么信息。请告诉我您的具体问题。"
            await self.content_sender.send_content_streaming(default_response, delay=0.08)
            return default_response

        # 获取对话历史
        conversation_history = state.get_conversation_history(max_messages=20)

        # 🔧 修改：使用流式API调用，传递对话历史
        response = await self._call_deepseek_streaming_for_info(last_user_message, conversation_history)

        return response

    # 🆕 修改：流式通用回复生成
    async def generate_general_response_streaming(self, state: WorkflowState) -> str:
        """流式生成一般性响应"""
        await self.send_status("thinking_step", {
            "step": "对话回复",
            "message": "生成引导性回复"
        })

        if state.main_plan:
            response = "您对当前的虚拟星座方案有什么问题或需要进一步调整吗？我可以根据您的反馈对方案进行优化。"
        else:
            response = """我是智慧虚拟星座助手，可以帮助您设计定制化的虚拟星座方案。

## 我能为您做什么？

1. **方案设计**: 根据您的观测需求设计最适合的卫星组合
2. **技术咨询**: 解答虚拟星座相关的技术问题
3. **方案优化**: 根据您的反馈优化现有方案

## 开始使用

请告诉我您的具体需求，比如：
- 监测目标和区域
- 时间范围要求
- 分辨率需求
- 应用场景

我将为您量身定制一个虚拟星座方案！"""

        # 🔧 流式发送回复
        await self.content_sender.send_content_streaming(response, delay=0.06)

        return response

    # 🆕 新增：流式DeepSeek调用（闲聊）
    async def _call_deepseek_streaming_for_chat(self, user_message: str, conversation_history: str = "") -> str:
        """使用DeepSeek API进行流式闲聊回复"""
        if not DEEPSEEK_API_KEY:
            default_response = "我理解您的意思。作为虚拟星座助手，我主要擅长帮助您设计卫星监测方案。如果您有相关需求，请随时告诉我！"
            await self.content_sender.send_content_streaming(default_response, delay=0.08)
            return default_response

        try:
            system_prompt = """你是智慧虚拟星座助手，一个专业友好的AI助手。你的主要职责是帮助用户设计虚拟星座方案，但也可以进行友好的对话。

请注意：
1. 保持专业但友好的语气
2. 如果用户的问题与卫星、遥感、监测相关，可以适当引导到你的专业领域
3. 如果是一般性对话，给出简洁友好的回复
4. 适时提醒用户你可以帮助设计虚拟星座方案
5. 记住之前的对话内容，保持对话的连贯性"""

            # 🔧 使用流式API调用，传递对话历史
            response = await self._stream_deepseek_response_with_history(system_prompt, user_message,
                                                                         conversation_history)
            return response

        except Exception as e:
            logger.error(f"生成闲聊回复时出错: {str(e)}")
            default_response = "我理解您的意思。作为虚拟星座助手，我主要擅长帮助您设计卫星监测方案。如果您有相关需求，请随时告诉我！"
            await self.content_sender.send_content_streaming(default_response, delay=0.08)
            return default_response

    # 🆕 新增：流式DeepSeek调用（信息查询）
    async def _call_deepseek_streaming_for_info(self, user_message: str, conversation_history: str = "") -> str:
        """使用DeepSeek API进行流式信息回复"""
        if not DEEPSEEK_API_KEY:
            default_response = """虚拟星座是指将分属不同组织的多颗卫星资源通过软件和网络技术集中管理和调度，实现资源共享、任务协同和数据融合的创新遥感数据获取模式。

## 核心特点

与传统的物理星座（同一组织运营的卫星群）不同，虚拟星座突破了组织边界，能够更灵活地整合全球卫星资源，优化遥感数据获取效率。

## 主要优势

1. **资源整合**: 统一调度多个组织的卫星资源
2. **成本效益**: 降低单一组织的卫星部署成本
3. **覆盖增强**: 提高全球观测覆盖能力
4. **数据融合**: 实现多源数据的协同处理

## 应用场景

虚拟星座助手可以帮助您设计针对特定需求的最优卫星组合方案，包括环境监测、灾害预警、农业遥感等多个领域。

请告诉我您的具体需求，例如监测目标、时间要求、分辨率需求等，我将为您设计一个定制化的虚拟星座方案。"""
            await self.content_sender.send_content_streaming(default_response, delay=0.05)
            return default_response

        try:
            system_prompt = """你是智慧虚拟星座助手，一个知识渊博的AI助手。你的主要职责是帮助用户设计虚拟星座方案，但你也具备广泛的知识，可以回答各种问题。

回答原则：
1. 准确、专业地回答用户的问题
2. 使用结构化的方式组织信息（如使用标题、列表等）
3. 如果问题与卫星、遥感、地球观测相关，可以适当引入你的专业领域
4. 如果问题完全无关，也要给出准确的回答，但在最后可以温和地提醒用户你的主要功能
5. 回答要详细但不冗长，控制在800字以内"""

            # 🔧 使用流式API调用，传递对话历史
            response = await self._stream_deepseek_response_with_history(system_prompt, user_message,
                                                                         conversation_history)
            return response

        except Exception as e:
            logger.error(f"生成信息回复时出错: {str(e)}")
            default_response = "抱歉，获取信息时出现问题。作为虚拟星座助手，我主要专长于设计卫星监测方案。请问您有相关的观测需求吗？"
            await self.content_sender.send_content_streaming(default_response, delay=0.08)
            return default_response

    # 🆕 新增：通用的流式DeepSeek API调用
    async def _stream_deepseek_response(self, system_prompt: str, user_message: str) -> str:
        """通用的流式DeepSeek API调用方法"""
        return await self._stream_deepseek_response_with_history(system_prompt, user_message, "")

    # 🆕 新增：带对话历史的流式DeepSeek API调用
    async def _stream_deepseek_response_with_history(self, system_prompt: str, user_message: str,
                                                     conversation_history: str = "") -> str:
        """带对话历史的流式DeepSeek API调用方法"""
        import aiohttp

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }

        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]

        # 智能处理对话历史
        if conversation_history and conversation_history.strip():
            # 将对话历史转换为消息格式
            history_lines = conversation_history.strip().split('\n')
            history_messages = []

            for line in history_lines:
                if line.startswith('user: '):
                    history_messages.append({"role": "user", "content": line[6:]})
                elif line.startswith('assistant: '):
                    history_messages.append({"role": "assistant", "content": line[11:]})

            # 智能截断：保留最近的对话，但确保不超过合理长度
            max_history_messages = 20  # 最多保留20轮对话
            if len(history_messages) > max_history_messages:
                # 保留最近的对话
                history_messages = history_messages[-max_history_messages:]
                logger.info(f"对话历史过长，截断为最近{max_history_messages}轮对话")

            messages.extend(history_messages)

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_message})

        data = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800,
            "stream": True  # 🔧 启用流式响应
        }

        full_response = ""

        try:
            timeout = aiohttp.ClientTimeout(total=60, connect=10)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers=headers,
                        json=data
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"DeepSeek API请求失败: {response.status}, {error_text}")
                        raise Exception(f"API请求失败: {response.status}")

                    # 🔧 处理流式响应
                    async for chunk in response.content.iter_chunked(1024):
                        try:
                            chunk_text = chunk.decode('utf-8', errors='ignore')
                            lines = chunk_text.strip().split('\n')

                            for line in lines:
                                line = line.strip()
                                if line.startswith('data: '):
                                    data_content = line[6:]

                                    if data_content == '[DONE]':
                                        break

                                    if not data_content.strip():
                                        continue

                                    try:
                                        json_data = json.loads(data_content)
                                        if 'choices' in json_data and len(json_data['choices']) > 0:
                                            delta = json_data['choices'][0].get('delta', {})
                                            if 'content' in delta:
                                                content_chunk = delta['content']
                                                full_response += content_chunk

                                                # 🔧 实时发送内容块
                                                if self.websocket_callback:
                                                    await self.websocket_callback({
                                                        "type": "response_chunk",
                                                        "content": content_chunk,
                                                        "accumulated_content": full_response,
                                                        "chunk_type": "ai_response"
                                                    })

                                                # 适当延迟以控制发送速度
                                                await asyncio.sleep(0.02)

                                    except json.JSONDecodeError:
                                        continue

                        except Exception as e:
                            logger.debug(f"处理流式数据块时出错: {e}")
                            continue

            return full_response.strip() if full_response else "抱歉，未能生成有效回复。"

        except Exception as e:
            logger.error(f"流式API调用失败: {str(e)}")
            raise

    async def initialize_state_streaming(self, state: WorkflowState, user_input: str) -> WorkflowState:
        """流式初始化状态"""
        self.reset_session()

        message = state.add_message("user", user_input if isinstance(user_input, str) else str(user_input))
        # 检查是否是澄清回复（通过metadata跟踪）
        if state.metadata.get("awaiting_clarification", False):
            state.metadata["is_clarification_response"] = True

        state.add_thinking_step("初始化", "开始处理用户输入")
        state.current_stage = "analyze_input"

        await self.send_status("thinking_step", {
            "step": "初始化",
            "message": "开始处理用户输入",
            "stage": "initialize"
        })

        return state

    async def deepseek_intent_analysis(self, user_message: str, conversation_history: str,
                                       state: WorkflowState) -> str:
        """使用DeepSeek进行智能意图分析 - 增强版本"""
        if not DEEPSEEK_API_KEY:
            logger.warning("DeepSeek API密钥未设置，使用默认意图分析")
            return "chat"  # 默认为闲聊

        system_prompt = """你是一个意图分析专家，需要准确识别用户在虚拟星座助手对话中的意图。

    请分析用户的输入，并返回以下意图之一：
    1. "greeting" - 用户在打招呼或问候（如：你好、您好、hi、hello等）
    2. "thanks" - 用户在表示感谢（如：谢谢、感谢、多谢等）
    3. "generate_plan" - 用户想要生成虚拟星座方案，包含以下情况：
       - 明确提到监测、观测、设计、规划等需求
       - 描述具体的监测目标（如水质、农业、城市等）
       - 提到地理位置和监测需求
       - 询问如何设计卫星方案
    4. "optimize_plan" - 用户想要优化或修改现有方案（如：优化、改进、调整、修改等）
    5. "provide_info" - 用户在询问信息或知识，包括：
       - 询问"什么是"、"介绍一下"、"解释"、"说明"等
       - 询问关于任何事物的基础知识或信息
       - 不涉及具体监测需求的一般性询问
    6. "chat" - 一般闲聊或其他不明确的意图

    重要判断原则：
    - 当用户使用"介绍"、"什么是"、"解释"等词汇时，优先判断为"provide_info"
    - 只有当用户明确表达了监测、观测、设计等需求时才返回"generate_plan"
    - 如果用户只是简单问候或闲聊，返回对应的意图，不要默认为"generate_plan"
    - 仔细区分用户是在询问信息还是要求设计方案

    请只返回意图标签，不要有其他内容。"""

        prompt = f"""用户输入: {user_message}

    对话历史:
    {conversation_history}

    请仔细分析用户意图并返回对应的标签。"""

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }

            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 50
            }

            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                intent = result["choices"][0]["message"]["content"].strip().lower()

                # 验证返回的意图是否有效
                valid_intents = ["greeting", "thanks", "generate_plan", "optimize_plan", "provide_info", "chat"]
                if intent in valid_intents:
                    logger.info(f"✅ DeepSeek意图分析结果: {intent}")
                    return intent
                else:
                    logger.warning(f"❌ DeepSeek返回了无效的意图: {intent}，使用默认意图")
                    return "chat"
            else:
                logger.error(f"❌ DeepSeek API调用失败: {response.status_code}")
                return "chat"

        except Exception as e:
            logger.error(f"❌ DeepSeek意图分析出错: {str(e)}")
            return "chat"

    async def analyze_user_input_streaming(self, state: WorkflowState) -> WorkflowState:
        """流式意图分析 - 修复：检测新方案请求时重置澄清状态"""
        conversation_history = state.get_conversation_history(max_messages=30)

        last_user_message = None
        for msg in reversed(state.messages):
            if msg.role == "user":
                last_user_message = msg.content
                break

        if not last_user_message:
            state.add_thinking_step("意图分析", "未找到用户消息")
            state.metadata["intent"] = "unknown"
            return state

        await self.send_status("thinking_step", {
            "step": "意图分析",
            "message": f"正在分析用户意图: '{last_user_message[:50]}...'",
            "stage": "analyze_intent"
        })

        # 使用DeepSeek进行意图分析
        logger.info("直接使用DeepSeek进行智能意图分析")
        intent = await self.deepseek_intent_analysis(last_user_message, conversation_history, state)

        # 🔧 关键修复：检测是否是新的方案生成请求
        if intent == "generate_plan":
            # 检查是否已经有方案存在
            has_existing_plan = state.main_plan is not None

            # 检查是否是新的监测需求（而不是对现有方案的讨论）
            # new_plan_keywords = ['规划', '设计']
            # is_new_request = any(keyword in last_user_message for keyword in new_plan_keywords)
            print('zzzzzzzzzzzzzzzzzz', last_user_message)
            # 如果已有方案且是新请求，重置澄清状态并标记新方案起始
            if has_existing_plan:
                logger.info("🔄 检测到新的方案生成请求，重置澄清状态")
                state.metadata["clarification_completed"] = False
                state.metadata["clarification_skipped"] = False
                state.metadata["extracted_parameters"] = {}
                state.metadata["awaiting_clarification"] = False
                state.metadata["pending_questions"] = []

                # 重置参数收集阶段
                state.parameter_collection_stage = "not_started"
                state.parameter_collection_history = []
                state.stage_retry_count = {}

                # 🆕 关键：标记新方案请求的起始位置
                state.mark_new_plan_request()

                # 添加思考步骤
                state.add_thinking_step("新方案检测", "检测到新的方案需求，将重新收集参数")

            # 🆕 如果是第一次方案请求，也要标记
            # elif not has_existing_plan:
            #     state.mark_new_plan_request()
            #     logger.info("🔖 标记第一次方案请求")

            # 设置需要澄清标志
            is_clarification_response = state.metadata.get("is_clarification_response", False)
            if not is_clarification_response and not state.metadata.get("clarification_completed", False):
                state.metadata["needs_clarification"] = True
                logger.info("检测到方案生成需求，需要参数澄清")
            else:
                logger.info("已完成参数澄清或正在处理澄清回复，跳过澄清步骤")

        state.metadata["intent"] = intent
        state.add_thinking_step("意图识别", f"识别意图: {intent}")

        await self.send_status("thinking_step", {
            "step": "意图识别",
            "message": f"AI智能识别意图: {intent}",
            "stage": "analyze_intent"
        })

        return state

    async def retrieve_knowledge_streaming(self, state: WorkflowState) -> WorkflowState:
        """流式知识检索 - 增强版：包含网络搜索"""
        await self.send_status("thinking_step", {
            "step": "知识检索",
            "message": "正在分析用户需求..."
        })

        await asyncio.sleep(0.3)

        # 步骤1：知识库检索
        state = retrieve_knowledge_for_workflow(state)
        knowledge_count = len(state.retrieved_knowledge)

        await self.send_status("thinking_step", {
            "step": "知识库检索",
            "message": f"从知识库检索到 {knowledge_count} 条相关信息"
        })

        # 步骤2：网络搜索增强
        try:
            from backend.src.tools.web_search_tools import WebSearchTool, integrate_search_with_knowledge

            search_tool = WebSearchTool()
            if search_tool.default_provider:
                await self.send_status("thinking_step", {
                    "step": "网络搜索",
                    "message": "正在搜索最新卫星信息..."
                })

                # 提取关键信息进行搜索
                user_messages = [msg.content for msg in state.messages if msg.role == "user"]
                search_query = user_messages[-1] if user_messages else ""

                # 执行网络搜索
                search_results = await search_tool.search(
                    search_query,
                    max_results=5,
                    search_type="satellite"
                )

                if search_results:
                    # 如果有卫星信息，搜索具体卫星
                    if hasattr(state, 'extracted_satellites') and state.extracted_satellites:
                        satellite_info = await search_tool.search_satellite_info(
                            state.extracted_satellites[:3]  # 限制搜索前3个卫星
                        )

                        # 将卫星信息添加到搜索结果
                        for satellite, info_list in satellite_info.items():
                            state.metadata[f"satellite_info_{satellite}"] = info_list

                    # 整合知识库和搜索结果
                    integrated_knowledge = integrate_search_with_knowledge(
                        state.retrieved_knowledge,
                        search_results
                    )

                    # 将整合后的知识添加到状态
                    state.retrieved_knowledge.append({
                        "content": integrated_knowledge,
                        "source": "integrated_search",
                        "score": 0.9
                    })

                    await self.send_status("thinking_step", {
                        "step": "网络搜索完成",
                        "message": f"补充了 {len(search_results)} 条网络信息"
                    })
                else:
                    await self.send_status("thinking_step", {
                        "step": "网络搜索",
                        "message": "网络搜索未找到相关信息"
                    })
            else:
                logger.info("网络搜索功能未配置，跳过")

        except Exception as e:
            logger.error(f"网络搜索失败: {str(e)}")
            await self.send_status("thinking_step", {
                "step": "网络搜索",
                "message": "网络搜索遇到问题，使用知识库信息"
            })

        await self.send_status("thinking_step", {
            "step": "知识检索完成",
            "message": f"共获取 {len(state.retrieved_knowledge)} 条参考信息"
        })

        state.current_stage = "generate_plan"
        return state

    async def generate_plan_streaming(self, state: WorkflowState) -> WorkflowState:
        """真正的流式方案生成"""
        await self.send_status("thinking_step", {
            "step": "方案生成",
            "message": "开始调用AI模型流式生成方案..."
        })

        async def plan_callback(data):
            if data["type"] == "thinking_step":
                await self.send_status("thinking_step", {
                    "step": data["step"],
                    "message": data["message"]
                })
            elif data["type"] == "plan_content_chunk":
                await self.send_status("response_chunk", {
                    "content": data["content"],
                    "accumulated_content": data["accumulated_content"],
                    "chunk_type": "plan_generation"
                })

        state = await generate_constellation_plan_streaming(state, plan_callback)

        await self.send_status("thinking_step", {
            "step": "方案生成完成",
            "message": "虚拟星座方案已流式生成完成"
        })

        state.current_stage = "respond"
        return state

    async def optimize_plan_streaming(self, state: WorkflowState) -> WorkflowState:
        """真正的流式方案优化"""
        last_user_message = None
        for msg in reversed(state.messages):
            if msg.role == "user":
                last_user_message = msg.content
                break

        if not last_user_message:
            state.add_thinking_step("优化错误", "未找到用户反馈")
            return state

        await self.send_status("thinking_step", {
            "step": "方案优化",
            "message": f"开始根据反馈优化方案: {last_user_message[:30]}..."
        })

        async def optimize_callback(data):
            if data["type"] == "thinking_step":
                await self.send_status("thinking_step", {
                    "step": data["step"],
                    "message": data["message"]
                })
            elif data["type"] == "plan_content_chunk":
                await self.send_status("response_chunk", {
                    "content": data["content"],
                    "accumulated_content": data["accumulated_content"],
                    "chunk_type": "plan_optimization"
                })

        state = await optimize_constellation_plan_streaming(state, last_user_message, optimize_callback)

        await self.send_status("thinking_step", {
            "step": "方案优化完成",
            "message": "方案已根据您的反馈流式优化完成"
        })

        state.current_stage = "respond"
        return state

    async def handle_parameter_clarification(self, state: WorkflowState) -> WorkflowState:
        """处理参数澄清流程"""

        async def clarification_callback(data: Dict[str, Any]):
            if self.websocket_callback:
                message_type = data.get("type", "clarification_update")
                callback_data = {k: v for k, v in data.items() if k != "type"}
                await self.send_status(message_type, callback_data)

        # 使用分阶段参数收集
        from backend.src.graph.nodes.staged_parameter_clarification_node import (
            process_staged_parameter_clarification,
            process_staged_clarification_response
        )

        if state.metadata.get("awaiting_clarification", False):
            # 处理用户回复
            user_messages = [msg for msg in state.messages if msg.role == "user"]
            if user_messages:
                latest_response = user_messages[-1].content
                state = await process_staged_clarification_response(
                    state,
                    latest_response,
                    clarification_callback
                )

                # 检查是否完成所有阶段
                if state.get_current_collection_stage() == "completed":
                    state.current_stage = "retrieve_knowledge"

                return state

        # 开始或继续分阶段收集
        state = await process_staged_parameter_clarification(
            state,
            clarification_callback
        )

        if state.metadata.get("awaiting_clarification", False):
            state.current_stage = "awaiting_clarification"
        elif state.get_current_collection_stage() == "completed":
            state.current_stage = "retrieve_knowledge"

        return state


# 更新导出函数
async def process_user_input_streaming(user_input: str, state: Optional[WorkflowState] = None,
                                       websocket_callback=None) -> Tuple[WorkflowState, str]:
    """流式处理用户输入的入口函数"""
    manager = StreamingWorkflowManager(websocket_callback)
    return await manager.process_user_input_streaming(user_input, state)


def save_state(state: WorkflowState, filepath: str) -> bool:
    """保存工作流状态到文件，增强错误处理和数据类型转换"""
    try:
        logger.info(f"正在保存状态到: {filepath}")

        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # 将状态转换为字典
        state_dict = {
            "conversation_id": state.conversation_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": float(msg.timestamp)
                }
                for msg in state.messages
            ],
            "thinking_steps": state.thinking_steps,
            "current_stage": state.current_stage,
            "metadata": state.metadata,
            "main_plan": state.main_plan,
            "alternative_plans": state.alternative_plans,
            "retrieved_knowledge": state.retrieved_knowledge
        }

        # 转换为JSON可序列化格式
        logger.debug("转换数据为JSON可序列化格式...")
        serializable_dict = convert_to_json_serializable(state_dict)

        # 保存到文件
        logger.debug("写入文件...")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_dict, f, ensure_ascii=False, indent=2)

        logger.info(f"状态保存成功: {filepath}")
        return True

    except Exception as e:
        logger.error(f"保存状态时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def load_state(filepath: str) -> Optional[WorkflowState]:
    """从文件加载工作流状态"""
    try:
        logger.info(f"正在加载状态从: {filepath}")

        if not os.path.exists(filepath):
            logger.warning(f"状态文件不存在: {filepath}")
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            state_dict = json.load(f)

        state = WorkflowState(
            conversation_id=state_dict.get("conversation_id", str(uuid.uuid4())),
            messages=[],
            thinking_steps=state_dict.get("thinking_steps", []),
            current_stage=state_dict.get("current_stage", ""),
            metadata=state_dict.get("metadata", {}),
            main_plan=state_dict.get("main_plan"),
            alternative_plans=state_dict.get("alternative_plans", []),
            retrieved_knowledge=state_dict.get("retrieved_knowledge", [])
        )

        # 添加消息
        for msg_dict in state_dict.get("messages", []):
            state.add_message(msg_dict["role"], msg_dict["content"])

        logger.info(f"状态加载成功: {filepath}, 消息数量: {len(state.messages)}")
        return state

    except Exception as e:
        logger.error(f"加载状态时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


if __name__ == "__main__":
    print("=" * 50)
    print("测试支持所有意图流式输出的工作流")
    print("=" * 50)


    async def test_streaming_workflow():
        try:
            async def test_callback(data):
                print(f"[{data['type']}] {data.get('step', '')} - {data.get('message', data.get('content', ''))}")

            state = WorkflowState()
            manager = StreamingWorkflowManager(test_callback)

            # 测试不同意图
            test_cases = [
                ("你好", "greeting"),
                ("什么是虚拟星座？", "provide_info"),
                ("我需要监测青海湖的水质变化", "generate_plan"),
                ("谢谢你的帮助", "thanks"),
                ("今天天气不错", "chat")
            ]

            for test_input, expected_intent in test_cases:
                print(f"\n测试输入: {test_input} (期望意图: {expected_intent})")
                print("-" * 50)

                result_state, response = await manager.process_user_input_streaming(test_input, WorkflowState())
                print(f"响应长度: {len(response)}")

                await asyncio.sleep(1)  # 等待流式输出完成

            print("\n所有测试完成!")

        except Exception as e:
            print(f"测试出错: {str(e)}")
            import traceback
            traceback.print_exc()


    # 运行测试
    asyncio.run(test_streaming_workflow())