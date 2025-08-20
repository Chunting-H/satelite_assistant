# backend/src/graph/nodes/buffered_streaming_planning_nodes.py

import os
import sys
import logging
import requests
import json
from typing import List, Dict, Any, Optional, Callable, AsyncIterator
from pathlib import Path
import time
import asyncio
import aiohttp
from dotenv import load_dotenv, find_dotenv

# 设置项目根目录
current_file = Path(__file__).resolve()
dotenv_path = find_dotenv()
if dotenv_path:
    project_root = Path(dotenv_path).parent
    print(f"通过find_dotenv确定项目根目录: {project_root}")
else:
    project_root = current_file.parent.parent.parent
    print(f"通过路径推导确定项目根目录: {project_root}")

sys.path.append(str(project_root))

if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path, override=True)
    print(f"加载了.env文件: {dotenv_path}")

from backend.src.graph.state import WorkflowState

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# DeepSeek API配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY环境变量未设置。请确保.env文件包含此密钥或手动设置环境变量。")


class StreamingContentBuffer:
    """流式内容缓冲器 - 聚合小块内容"""

    def __init__(self,
                 min_chunk_size: int = 20,
                 max_buffer_time: float = 0.3,
                 streaming_callback: Optional[Callable] = None):
        self.min_chunk_size = min_chunk_size
        self.max_buffer_time = max_buffer_time
        self.streaming_callback = streaming_callback

        self.buffer = ""
        self.full_content = ""
        self.last_send_time = time.time()
        self.chunk_count = 0
        self.in_table = False
        self.table_buffer = ""  # 新增：专门的表格缓冲区
        self.table_line_count = 0  # 新增：表格行计数

    async def add_content(self, content_chunk: str):
        """添加内容块"""
        content_chunk = content_chunk.replace('\r\n', '\n').replace('\r', '\n')
        self.full_content += content_chunk

        # 检测表格开始（通过检测表格分隔符行）
        if '| ---' in content_chunk and not self.in_table:
            self.in_table = True
            # 如果缓冲区有内容，先发送
            if self.buffer:
                await self._send_buffer()
            self.table_buffer = self.buffer + content_chunk
            self.buffer = ""
            self.table_line_count = content_chunk.count('\n')
            return

        # 如果在表格中，累积到表格缓冲区
        if self.in_table:
            self.table_buffer += content_chunk
            self.table_line_count += content_chunk.count('\n')

            # 检测表格结束（连续两个换行或遇到非表格内容）
            if '\n\n' in self.table_buffer or (
                    '\n' in content_chunk and
                    not content_chunk.strip().startswith('|') and
                    self.table_line_count >= 3  # 至少有表头、分隔符和一行数据
            ):
                self.in_table = False
                # 发送完整的表格
                await self._send_table()
                # 处理表格后的内容
                remaining = content_chunk.split('\n\n', 1)
                if len(remaining) > 1:
                    self.buffer = '\n\n' + remaining[1]
            return

        # 普通内容处理
        self.buffer += content_chunk
        self.chunk_count += 1

        current_time = time.time()
        time_since_last_send = current_time - self.last_send_time

        # 普通内容的发送条件
        should_send = (
                len(self.buffer) >= self.min_chunk_size or
                time_since_last_send >= self.max_buffer_time or
                '\n\n' in self.buffer or  # 段落结束
                self.chunk_count >= 10
        )

        if should_send:
            await self._send_buffer()

    async def _send_table(self):
        """发送完整的表格内容"""
        if self.table_buffer and self.streaming_callback:
            logger.info(f"📊 发送完整表格: {self.table_line_count} 行")
            await self.streaming_callback({
                "type": "plan_content_chunk",
                "content": self.table_buffer,
                "accumulated_content": self.full_content,
                "is_table": True  # 标记这是表格内容
            })
            self.table_buffer = ""
            self.table_line_count = 0

    async def _send_buffer(self):
        """发送缓冲区内容"""
        if self.buffer and self.streaming_callback:
            logger.info(f"📦 发送缓冲内容: {len(self.buffer)} 字符")
            await self.streaming_callback({
                "type": "plan_content_chunk",
                "content": self.buffer,
                "accumulated_content": self.full_content,
                "is_table": False
            })
            self.buffer = ""
            self.last_send_time = time.time()
            self.chunk_count = 0

    async def flush(self):
        """强制发送剩余内容"""
        if self.table_buffer:
            await self._send_table()
        if self.buffer:
            await self._send_buffer()


async def call_deepseek_streaming_api_buffered(
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        streaming_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    带缓冲的DeepSeek流式API调用
    """
    if not DEEPSEEK_API_KEY:
        logger.error("未设置DeepSeek API密钥")
        return {"success": False, "error": "未设置DeepSeek API密钥"}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 2000,
        "stream": True
    }

    try:
        # 创建内容缓冲器
        content_buffer = StreamingContentBuffer(
            min_chunk_size=10,  # 最小15字符发送一次
            max_buffer_time=0.3,  # 最多0.2秒缓冲
            streaming_callback=streaming_callback
        )

        timeout = aiohttp.ClientTimeout(total=120, connect=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(DEEPSEEK_API_URL, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"API请求失败: {response.status}, {error_text}")
                    return {"success": False, "error": f"API请求失败: {response.status}"}

                full_content = ""

                # 使用aiohttp的流式读取
                async for chunk in response.content.iter_chunked(1024):
                    try:
                        # 解码数据块
                        chunk_text = chunk.decode('utf-8', errors='ignore')

                        # 按行分割
                        lines = chunk_text.strip().split('\n')

                        for line in lines:
                            line = line.strip()
                            if line.startswith('data: '):
                                data_content = line[6:]  # 移除 'data: ' 前缀

                                if data_content == '[DONE]':
                                    logger.info("接收到流式结束信号")
                                    break

                                if not data_content.strip():
                                    continue

                                try:
                                    json_data = json.loads(data_content)
                                    if 'choices' in json_data and len(json_data['choices']) > 0:
                                        delta = json_data['choices'][0].get('delta', {})
                                        if 'content' in delta:
                                            content_chunk = delta['content']
                                            full_content += content_chunk

                                            # 添加到缓冲器
                                            await content_buffer.add_content(content_chunk)

                                except json.JSONDecodeError as e:
                                    logger.debug(f"JSON解析错误: {e}")
                                    continue

                    except Exception as e:
                        logger.warning(f"处理数据块时出错: {str(e)}")
                        continue

                # 发送剩余的缓冲内容
                await content_buffer.flush()

                if full_content:
                    logger.info(f"🎉 流式API调用完成，总内容长度: {len(full_content)}")
                    return {"success": True, "content": full_content}
                else:
                    logger.warning("流式API调用完成，但未接收到内容")
                    return {"success": False, "error": "未接收到有效内容"}

    except asyncio.TimeoutError:
        logger.error("DeepSeek API调用超时")
        return {"success": False, "error": "API调用超时"}
    except Exception as e:
        logger.error(f"调用DeepSeek流式API时出错: {str(e)}")
        return {"success": False, "error": str(e)}

async def generate_constellation_plan_streaming(
        state: WorkflowState,
        streaming_callback: Optional[Callable] = None
) -> WorkflowState:
    """
    流式生成虚拟星座方案（带缓冲版本）
    """
    # 发送开始信号
    if streaming_callback:
        await streaming_callback({
            "type": "thinking_step",
            "step": "方案生成",
            "message": "开始基于用户需求和知识库生成虚拟星座方案"
        })

    # 获取对话历史作为用户需求上下文
    conversation_history = state.get_conversation_history()

    # 如果对话历史为空，生成默认方案
    if not conversation_history or conversation_history.strip() == "":
        default_plan = """
# 基础虚拟星座方案

## 方案概述
基于通用需求的虚拟星座方案，适用于基础遥感观测任务。

## 卫星组成

推荐卫星：高分一号、哨兵-2号、环境一号

| 卫星名称 | 所属国家/机构 | 发射时间 | 轨道类型 | 空间分辨率 | 时间分辨率 | 光谱分辨率 | 覆盖范围 | 数据质量 | 实时性 | 主要特点 | 独特价值 |
|---------|--------------|----------|----------|------------|------------|------------|----------|----------|--------|----------|----------|
| 高分一号 | 中国 | 2013年 | 太阳同步轨道 | 2米/8米 | 4天 | 4个波段 | 60公里 | 10位 | 24小时内 | 高分辨率光学影像 | 提供精细地物识别能力 |
| 哨兵-2号 | 欧洲 | 2015年 | 太阳同步轨道 | 10米 | 5天 | 13个波段 | 290公里 | 12位 | 准实时 | 多光谱数据 | 丰富的光谱信息 |
| 环境一号 | 中国 | 2008年 | 太阳同步轨道 | 30米 | 2天 | 4个波段 | 720公里 | 8位 | 准实时 | 环境监测数据 | 大范围环境监测 |

## 主要优势
- 覆盖范围广
- 数据类型丰富
- 时间分辨率较高

## 数据产品
- 高分辨率光学影像
- 多光谱遥感数据
- 环境监测报告

请提供更具体的需求以获得定制化方案。
"""
        state.main_plan = default_plan
        state.add_thinking_step("默认方案", "生成了基础虚拟星座方案")
        return state

    # 从知识库检索相关信息
    knowledge_results = state.retrieved_knowledge
    knowledge_text = ""
    if knowledge_results:
        knowledge_text = "\n\n".join([item.get("content", "") for item in knowledge_results])
        if streaming_callback:
            await streaming_callback({
                "type": "thinking_step",
                "step": "知识库检索",
                "message": f"使用检索到的 {len(knowledge_results)} 条相关卫星知识作为参考"
            })
    else:
        knowledge_text = "基于已有的专业知识进行方案设计。"

    # 1. 专家级生成主提示词
    system_prompt = """
你是一位虚拟星座规划专家，精通卫星遥感、多源数据融合与智能组网。你的任务是基于用户需求，输出**结构化、专业、具有创新性和落地性的虚拟星座组网方案**。

虚拟星座是指通过软件和网络手段，将分属不同组织的多颗卫星资源集中管理、联合调度，实现资源共享、任务协同和数据融合的创新遥感数据获取与服务模式。广泛应用于农业监测、灾害应急、城市管理、生态环境等场景。

请严格按照如下专家级标准输出完整方案：
1. 内容紧扣实际任务场景和行业痛点，输出具备落地性的方案；
2. 每部分均需有案例、推理、创新点，充分体现专业性和创造性；
3. 主动对比传统单星/单系统方案，突出本方案的创新突破与改进空间；
4. 每一结构化部分字数不少于200字，内容详实，条理清晰，避免遗漏关键环节。

输出格式要求：
1. 使用Markdown格式，确保所有的粗体标记（**文字**）都是完整的
2. 避免在数字编号后直接使用粗体，应该在数字和粗体之间加空格
3. 正确格式示例：
   - ✅ 1. **标题**：内容
   - ❌ 1.**标题**：内容
4. 确保所有的Markdown标记都正确配对

你可以参考如下**专家高质量范文片段**的风格和深度：

> 例如：在东亚农业区旱情监测场景下，单颗遥感卫星的重访周期通常为5-16天，极易错失关键农时窗口。虚拟星座方案将欧盟Sentinel-2（5天）、中国高分一号（4天）、美国Landsat 9（16天）等多颗卫星组网，通过智能调度和多源数据融合，将覆盖周期缩短至2天以内。2023年黑龙江玉米长势监测实践显示，多星组网方案相比传统单星方案，监测时效提升80%，数据完整性提升50%，为精准农业决策提供坚实支撑。
"""

    # 2. 结构化专家方案prompt
    prompt = f'''
    基于以下用户需求，设计高质量的虚拟星座组网方案：

    ### 用户需求
    {conversation_history}

    ### 参考知识
    {knowledge_text}

    ### 重要提示：表格格式要求
    **所有表格必须严格遵循以下格式规范：**
    1. 每个表格行必须独占一行，使用换行符分隔
    2. 表头行、分隔符行、数据行必须各占一行
    3. 分隔符行格式：`| --- | --- | --- |`（根据列数调整）
    4. 不要将多行内容挤在一行

    **正确的表格格式示例：**
    ```
    | 列1 | 列2 | 列3 |
    | --- | --- | --- |
    | 数据1 | 数据2 | 数据3 |
    | 数据4 | 数据5 | 数据6 |
    ```

    **错误的表格格式（避免）：**
    ```
    | 列1 | 列2 | 列3 | | --- | --- | --- | | 数据1 | 数据2 | 数据3 |
    ```

    ### 请严格按照以下标题和结构输出：

    1. **方案名称与概述**
       - 用一句话概括方案目标与优势。
       - 一段详细描述，说明本方案解决的核心问题、典型场景与创新突破。

    2. **用户需求解读与场景假设**
       - 提炼用户需求，合理补充任务场景假设。
       - 明确关键数据类型、时空覆盖、精度等技术指标。

    3. **卫星组成**
       先写出推荐卫星，例如：推荐卫星：Landsat-8、Sentinel-2、高分一号

       然后使用表格展示详细信息（注意：表格必须格式正确，每行独占一行）：

       | 卫星名称 | 所属国家/机构 | 发射时间 | 轨道类型 | 空间分辨率 | 时间分辨率 | 光谱分辨率 | 覆盖范围 | 数据质量 | 实时性 | 主要特点 | 独特价值 |
       | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
       | Landsat-8 | 美国 | 2013年 | 太阳同步轨道 | 30米 | 16天 | 11个波段 | 185公里 | 高 | 准实时 | 多光谱成像 | 长时序监测 |
       | Sentinel-2 | 欧洲 | 2015年 | 太阳同步轨道 | 10米 | 5天 | 13个波段 | 290公里 | 高 | 准实时 | 高频观测 | 植被监测 |

       每个表格下方，用一段话分析各卫星协同优势和组合价值。

    4. **卫星协同关系与创新机制**
       使用表格展示协同关系（注意格式）：

       | 卫星1 | 卫星2 | 协同类型 | 协同频率 | 协同效果 |
       | --- | --- | --- | --- | --- |
       | Sentinel-2A | Sentinel-2B | 轨道相位协同 | 每5天 | 重访周期缩短至2.5天 |
       | 高分一号 | Sentinel-2 | 分辨率互补 | 每周2次 | 空间分辨率融合 |

       表格下方详细分析协同调度创新点。

    5. **数据获取与融合策略**
       - 详细说明多星协同如何提升时空分辨率
       - 描述数据融合方法和协同效益

    6. **技术创新与方案亮点**
       - 指出本方案的创新与特色

    7. **预期数据产品与应用成效**
       列出数据产品表格：

       | 产品类型 | 规格参数 | 核心技术 | 应用场景 |
       | --- | --- | --- | --- |
       | 水质参数专题图 | 10m/周 | 多源融合 | 水质监测 |
       | 时序变化分析 | 30m/月 | 变化检测 | 趋势分析 |

    8. **风险与对策**
       使用表格展示：

       | 风险类型 | 具体描述 | 应对措施 |
       | --- | --- | --- |
       | 数据延迟 | 卫星数据获取可能延迟 | 多星备份机制 |
       | 云遮挡 | 光学影像受云影响 | 雷达数据补充 |

    #### 特别强调
    - **所有表格必须格式正确，每行独占一行**
    - **不要将表格内容挤在一行**
    - **分隔符行必须单独一行**
    - **表格前后要有空行**
    - 所有表格参数必须为真实数值
    - 内容必须Markdown格式、结构清晰
    '''

    plan_content = ""

    async def plan_streaming_callback(data):
        nonlocal plan_content
        if data["type"] == "plan_content_chunk":
            content_chunk = data["content"]
            plan_content = data["accumulated_content"]
            if streaming_callback:
                await streaming_callback({
                    "type": "plan_content_chunk",
                    "content": content_chunk,
                    "accumulated_content": plan_content
                })

    try:
        if streaming_callback:
            await streaming_callback({
                "type": "thinking_step",
                "step": "AI生成",
                "message": "正在调用DeepSeek API流式生成方案..."
            })

        api_response = await call_deepseek_streaming_api_buffered(
            prompt,
            system_prompt,
            temperature=0.7,
            streaming_callback=plan_streaming_callback
        )

        if api_response["success"] and plan_content:
            # 修复表格格式
            # 检查内容是否有效
            if len(plan_content) > 50:
                state.main_plan = plan_content
                state.add_thinking_step("方案生成完成", f"成功生成{len(plan_content)}字符的虚拟星座方案")
                # 🔧 新增：立即提取卫星信息并设置到状态中
                # try:
                #     from backend.src.tools.satellite_extractor import extract_satellite_names_with_cache
                #     extracted_satellites = await extract_satellite_names_with_cache(plan_content)
                #     if extracted_satellites:
                #         state.set_extracted_satellites(extracted_satellites)
                #         logger.info(f"✅ 方案生成后立即提取到卫星: {extracted_satellites}")
                #     else:
                #         logger.warning("⚠️ 方案生成后未能提取到卫星信息")
                # except Exception as e:
                #     logger.error(f"❌ 提取卫星信息失败: {e}")

                if streaming_callback:
                    await streaming_callback({
                        "type": "thinking_step",
                        "step": "方案生成完成",
                        "message": f"成功生成 {len(plan_content)} 字符的虚拟星座方案"
                    })
            else:
                raise Exception("API返回内容过短，可能无效")
        else:
            raise Exception(f"API调用失败: {api_response.get('error', '未知错误')}")

    except Exception as e:
        logger.error(f"流式生成方案时出错: {str(e)}")
        state.add_thinking_step("方案生成错误", f"API调用失败: {str(e)}")

        if streaming_callback:
            await streaming_callback({
                "type": "thinking_step",
                "step": "方案生成错误",
                "message": f"API调用失败，使用应急方案: {str(e)}"
            })

        # 生成应急方案
        fallback_plan = f"""
# 应急虚拟星座方案

**说明**：由于当前网络或AI服务异常，暂未能生成专属定制方案。以下为基础虚拟星座组网方案，供临时参考。

## 用户需求概览
{conversation_history[:200]}...

## 推荐卫星组合
| 卫星名称   | 主要用途       | 空间分辨率 | 时间分辨率 | 开放性     | 主要优势                |
|------------|----------------|------------|------------|------------|-------------------------|
| Landsat-8  | 多光谱观测     | 30米       | 16天       | 免费开放   | 国际主流开源卫星         |
| Sentinel-2 | 高频多光谱监测 | 10-60米    | 5天        | 免费开放   | 时空分辨率高，频次高     |
| 高分系列   | 高分辨率成像   | 2-8米      | 4天        | 商业/部分开放 | 细粒度地物识别能力强 |

## 技术建议
- 建议结合多源数据进行趋势分析，关注时空补齐
- 注意数据预处理与质量控制
- 可根据需求细化具体数据产品

如需更优定制化方案，请稍后重试获取详细AI生成结果。
错误信息：{str(e)}
"""
        state.main_plan = fallback_plan

    return state


async def optimize_constellation_plan_streaming(
        state: WorkflowState,
        user_feedback: str,
        streaming_callback: Optional[Callable] = None
) -> WorkflowState:
    """
    流式优化虚拟星座方案（带缓冲版本）
    """
    # 发送开始信号
    if streaming_callback:
        await streaming_callback({
            "type": "thinking_step",
            "step": "方案优化",
            "message": "基于用户反馈开始优化方案"
        })

    # 检查是否有方案可以优化
    if not state.main_plan:
        state.add_thinking_step("方案优化", "没有可优化的方案")
        return state

    # 记录用户反馈
    state.add_thinking_step("用户反馈", user_feedback)

    # 获取原方案
    original_plan = state.main_plan

    # 🔧 关键修改：增强系统提示词，强调具体优化要求
    system_prompt = """你是一位虚拟星座规划专家，需要根据用户的反馈优化现有的虚拟星座方案。

**重要提示**：
1. 必须仔细理解用户的具体优化需求
2. 如果用户要求"更经济"的方案，必须：
   - 选择成本更低的卫星（如使用免费或低成本的卫星数据）
   - 减少卫星数量但保证基本功能
   - 优先选择开放数据源（如Landsat、Sentinel等）
   - 明确说明成本降低的具体措施
3. 如果用户要求其他特定优化（如更高精度、更快响应等），也要针对性地调整
4. 在优化后的方案中明确说明：
   - 如何满足了用户的优化需求
   - 相比原方案的具体改进
   - 可能的权衡和限制

请保持专业性和创造性，确保优化的方案真正满足用户的需求。"""

    # 🔧 关键修改：在主提示词中更加强调用户的具体需求
    prompt = f"""根据用户的反馈，优化现有的虚拟星座方案。

    ### 原始方案
    {original_plan}

    ### 用户反馈
    {user_feedback}

    ### 用户优化需求分析
    请首先分析用户的具体需求：
    - 如果用户提到"更经济"、"成本更低"、"便宜"等词汇，这是成本优化需求
    - 如果用户提到"更精确"、"分辨率更高"等词汇，这是精度优化需求
    - 如果用户提到"更快"、"实时"等词汇，这是时效性优化需求

    ### 优化指导原则
    基于用户反馈"{user_feedback}"，请特别注意：

    **如果是成本优化需求**：
    1. 优先选择免费或低成本的卫星数据源：
       - Landsat系列（免费）
       - Sentinel系列（免费）
       - MODIS（免费）
       - 减少使用商业卫星（如WorldView、Pleiades等）
    2. 优化卫星组合，用更少的卫星实现基本功能
    3. 调整观测频率和分辨率要求，在满足基本需求的前提下降低成本
    4. 明确说明成本节省措施

    **如果是其他优化需求**：
    - 根据具体需求调整卫星选择和参数配置

    ### 请优化上述虚拟星座方案，必须保持以下结构：
    1. **方案名称和概述**（可以更新内容，但保持这个标题）
    2. **卫星组成**（注意：必须使用"卫星组成"作为标题，不要使用"调整后的卫星组成"或其他变体）

    **关键要求**：在"卫星组成"部分，必须：
    - 首先用一行文字列出所有推荐的卫星，格式为："推荐卫星：卫星A、卫星B、卫星C、卫星D"
    - 然后再展示详细的表格
    - **确保文字列表中的卫星与表格中的卫星完全一致，不能有遗漏或多余**
    - 如果优化后减少了卫星数量，推荐列表也要相应减少
    - 如果优化后增加了卫星，推荐列表也要相应增加

    3. **卫星协同关系分析**
    4. **数据获取策略**
    5. **技术优势**
    6. **预期数据产品**
    7. **简要实施建议**

    特别强调：
    - 第2部分的标题必须是"**卫星组成**"，不要添加"调整后的"、"优化后的"等修饰词
    - 保持与原方案相同的章节结构和标题格式
    - 在内容中说明优化的具体改变，但标题保持一致
    - 推荐卫星列表必须与表格中的卫星完全一致

    请给出完整的优化后方案，确保真正满足用户的需求。"""

    # 定义流式回调处理器
    optimized_content = ""

    async def optimize_streaming_callback(data):
        nonlocal optimized_content
        if data["type"] == "plan_content_chunk":
            content_chunk = data["content"]
            optimized_content = data["accumulated_content"]

            # 发送内容块到前端
            if streaming_callback:
                await streaming_callback({
                    "type": "plan_content_chunk",
                    "content": content_chunk,
                    "accumulated_content": optimized_content
                })

    try:
        if streaming_callback:
            await streaming_callback({
                "type": "thinking_step",
                "step": "AI优化",
                "message": f"正在根据您的需求'{user_feedback}'优化方案..."
            })

        # 调用带缓冲的流式API进行优化
        api_response = await call_deepseek_streaming_api_buffered(
            prompt,
            system_prompt,
            temperature=0.7,
            streaming_callback=optimize_streaming_callback
        )

        if api_response["success"] and optimized_content:
            # 将原方案移至备选方案
            if not state.alternative_plans:
                state.alternative_plans = []
            state.alternative_plans.append(original_plan)

            # 更新方案
            state.main_plan = optimized_content
            state.metadata["optimization_prompt"] = prompt
            state.metadata["optimization_system_prompt"] = system_prompt
            state.metadata["optimization_feedback"] = user_feedback  # 🔧 新增：保存用户反馈

            # 记录完成优化方案
            state.add_thinking_step("方案优化完成", f"已根据'{user_feedback}'生成优化方案")

            if streaming_callback:
                await streaming_callback({
                    "type": "thinking_step",
                    "step": "方案优化完成",
                    "message": f"成功根据您的需求生成优化方案"
                })
        else:
            raise Exception(f"API调用失败: {api_response.get('error', '未知错误')}")

    except Exception as e:
        logger.error(f"流式优化方案时出错: {str(e)}")
        state.add_thinking_step("方案优化错误", f"优化方案时出错: {str(e)}")

        if streaming_callback:
            await streaming_callback({
                "type": "thinking_step",
                "step": "方案优化错误",
                "message": f"优化方案时出错: {str(e)}"
            })

        # 保留原方案并添加错误信息
        error_message = f"优化方案时发生错误: {str(e)}。请检查网络连接后重试。"
        state.main_plan = original_plan + "\n\n[优化失败] " + error_message

    return state


if __name__ == "__main__":
    print("=" * 50)
    print("测试带缓冲的流式虚拟星座规划节点")
    print("=" * 50)

    if not DEEPSEEK_API_KEY:
        print("警告: 未设置DEEPSEEK_API_KEY环境变量")
        exit(1)


    async def test_buffered_streaming():
        try:
            from backend.src.graph.state import WorkflowState

            # 创建测试工作流状态
            state = WorkflowState()
            state.add_message("user", "我需要监测青海湖的水质变化情况")

            # 模拟检索知识
            state.retrieved_knowledge = [
                {
                    "content": "高分一号是中国自主研发的高分辨率对地观测卫星，具有全色2米、多光谱8米的分辨率，主要用于土地资源调查、矿产资源勘查、农业研究等领域。",
                    "score": 0.85
                }
            ]

            # 定义测试回调函数
            chunk_count = 0

            async def test_callback(data):
                nonlocal chunk_count
                if data["type"] == "plan_content_chunk":
                    chunk_count += 1
                    content = data.get("content", "")
                    print(f"📦 块 {chunk_count}: {len(content)} 字符 - '{content[:50]}...'")

            print("\n测试带缓冲的流式方案生成:")
            print("-" * 40)
            state = await generate_constellation_plan_streaming(state, test_callback)

            print(f"\n总共收到 {chunk_count} 个内容块")
            print(f"生成的方案长度: {len(state.main_plan) if state.main_plan else 0}")
            print("生成完成!")

        except Exception as e:
            print(f"测试时出错: {str(e)}")
            import traceback
            traceback.print_exc()


    # 运行测试
    asyncio.run(test_buffered_streaming())