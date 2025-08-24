# backend/src/graph/nodes/direct_streaming_planning_nodes.py

import os
import sys
import logging
import json
from typing import Optional, Callable
from pathlib import Path
import asyncio
import aiohttp
from dotenv import load_dotenv, find_dotenv
import datetime

# 设置项目根目录
current_file = Path(__file__).resolve()
dotenv_path = find_dotenv()
if dotenv_path:
    project_root = Path(dotenv_path).parent
else:
    project_root = current_file.parent.parent.parent

sys.path.append(str(project_root))

if dotenv_path:
    load_dotenv(dotenv_path=dotenv_path, override=True)

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

if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY环境变量未设置。")


async def call_deepseek_streaming_api_direct(
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        streaming_callback: Optional[Callable] = None
) -> dict:
    """
    直接流式DeepSeek API调用 - 修复版本
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
        timeout = aiohttp.ClientTimeout(total=120, connect=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post("https://api.deepseek.com/v1/chat/completions", headers=headers,
                                    json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"API请求失败: {response.status}, {error_text}")
                    return {"success": False, "error": f"API请求失败: {response.status}"}

                full_content = ""
                buffer = ""  # 添加缓冲区处理不完整的行
                chunk_count = 0

                # 修改：使用更大的块大小并改进解析逻辑
                async for chunk in response.content.iter_chunked(1024):
                    chunk_count += 1
                    try:
                        # 解码并添加到缓冲区
                        chunk_text = chunk.decode('utf-8', errors='ignore')
                        buffer += chunk_text

                        # 处理完整的行
                        lines = buffer.split('\n')
                        # 保留最后一行（可能不完整）
                        buffer = lines[-1]

                        for line in lines[:-1]:
                            line = line.strip()
                            if not line:
                                continue

                            if line.startswith('data: '):
                                data_content = line[6:].strip()

                                if data_content == '[DONE]':
                                    logger.info("接收到流式结束信号")
                                    break

                                if not data_content:
                                    continue

                                try:
                                    json_data = json.loads(data_content)
                                    if 'choices' in json_data and len(json_data['choices']) > 0:
                                        choice = json_data['choices'][0]
                                        delta = choice.get('delta', {})

                                        if 'content' in delta and delta['content']:
                                            content_chunk = delta['content']
                                            full_content += content_chunk

                                            # 立即发送内容
                                            if streaming_callback:
                                                await streaming_callback({
                                                    "type": "plan_content_chunk",
                                                    "content": content_chunk,
                                                    "accumulated_content": full_content
                                                })
                                                # 减少延迟
                                                await asyncio.sleep(0.005)

                                        # 检查是否有结束原因
                                        if choice.get('finish_reason') == 'stop':
                                            logger.info("流式生成正常结束")
                                            break

                                except json.JSONDecodeError as e:
                                    logger.debug(f"JSON解析错误（行 {chunk_count}）: {e}, 数据: {data_content[:100]}")
                                    continue

                    except Exception as e:
                        logger.warning(f"处理数据块 {chunk_count} 时出错: {str(e)}")
                        continue

                # 处理缓冲区中剩余的内容
                if buffer.strip() and buffer.strip().startswith('data: '):
                    try:
                        data_content = buffer[6:].strip()
                        if data_content and data_content != '[DONE]':
                            json_data = json.loads(data_content)
                            if 'choices' in json_data and len(json_data['choices']) > 0:
                                delta = json_data['choices'][0].get('delta', {})
                                if 'content' in delta and delta['content']:
                                    content_chunk = delta['content']
                                    full_content += content_chunk

                                    if streaming_callback:
                                        await streaming_callback({
                                            "type": "plan_content_chunk",
                                            "content": content_chunk,
                                            "accumulated_content": full_content
                                        })
                    except:
                        pass

                if full_content:
                    logger.info(f"🎉 流式API调用完成，总内容长度: {len(full_content)}，处理了 {chunk_count} 个数据块")
                    return {"success": True, "content": full_content}
                else:
                    logger.warning(f"流式API调用完成，但未接收到内容。处理了 {chunk_count} 个数据块")
                    # 返回默认内容而不是错误
                    return {"success": True, "content": "抱歉，生成内容时遇到问题，请重试。"}

    except asyncio.TimeoutError:
        logger.error("DeepSeek API调用超时")
        return {"success": False, "error": "API调用超时"}
    except aiohttp.ClientError as e:
        logger.error(f"网络请求错误: {str(e)}")
        return {"success": False, "error": f"网络错误: {str(e)}"}
    except Exception as e:
        logger.error(f"调用DeepSeek流式API时出错: {str(e)}")
        return {"success": False, "error": str(e)}


async def generate_constellation_plan_streaming(
        state: WorkflowState,
        streaming_callback: Optional[Callable] = None
) -> WorkflowState:
    """
    直接流式生成虚拟星座方案 - 增强错误处理
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

        # 流式发送默认方案
        if streaming_callback:
            lines = default_plan.split('\n')
            accumulated = ""
            for line in lines:
                accumulated += line + '\n'
                await streaming_callback({
                    "type": "plan_content_chunk",
                    "content": line + '\n',
                    "accumulated_content": accumulated
                })
                await asyncio.sleep(0.01)

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

    # 获取当前时间上下文
    current_time = datetime.datetime.now()
    current_year = current_time.year
    current_date = current_time.strftime('%Y年%m月%d日')

    # 构建提示词
    system_prompt = """你是一位虚拟星座规划专家，精通卫星遥感、多源数据融合与智能组网。你的任务是基于用户需求，输出**结构化、专业、具有创新性和落地性的虚拟星座组网方案**。

    **核心约束（必须严格遵守）**：
    - 任务时间窗口内已退役的卫星绝对禁止推荐
    - Sentinel-1B已于2022年8月退役，禁止在2022年8月后的任务中推荐
    - 其他已退役卫星：EGYPTSAT 2(2015)、RISAT-1(2017)、Jason-2(2019)等

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

    当前时间：{current_date}

    ### 关键约束条件
    1. **时间有效性**：只能推荐在用户指定时间窗口内正常运行的卫星（例如问题“我需要监测2023年到2025年6月鄱阳湖的水位变化，请规划虚拟星座方案”中2023年到2025年6月即为用户指定时间窗口）
    - 必须检查卫星发射时间是否早于任务开始时间
    - 必须确认卫星在任务期间未退役（例如问题“我需要监测2023年到2025年6月鄱阳湖的水位变化，请规划虚拟星座方案”中2023年到2025年6月即为任务期间）
    - 禁止推荐计划中但未发射的卫星
    2. **已知退役卫星的和其终止日期**（若某卫星的终止日期在任务期间，生成方案中禁止出现该卫星！）：
    - Sentinel-1B（2022年8月3日退役）
    - EGYPTSAT 2（2015年6月9日退役）
    - DMSP 5D-3 F19（2016年2月11日退役）
    - RBSP A/B（2012年11月9日退役）
    - RISAT-1（2017年3月31日退役）
    - SICH-2（2012年12月12日退役）
    - SAC-D（2015年6月7日退役）
    - PICARD（2014年4月4日退役）
    - METEOR-M 1（2014年9月23日退役）
    - KORONAS-FOTON（2009年12月1日退役）
    - FENGYUN 2E（2018年12月31日退役）
    - Jason-2（2019年10月1日退役）
    - IMS-1（2012年9月20日退役）
    - CBERS 2B（2010年5月16日退役） 
    - MisrSat 1（2010年7月19日退役） 
    - Measat 3（2007年12月21日退役） 
    - STEREO B（2014年10月1日退役） 
    - METOP-A（2021年11月15日退役） 
    - Cloudsat（2023年8月1日退役） 
    - Himawari-7（2016年5月10日退役） 
    - ALOS (DAICHI)（2011年4月22日退役） 
    - Topsat（2008年8月17日退役） 
    - Himawari-6（2015年12月4日退役） 
    - PARASOL（2013年12月18日退役） 
    - FENGYUN 2C（2009年11月23日退役） 
    - FORMOSAT-2 (ROCSAT 2)（2016年8月19日退役） 
    - CBERS 2 (ZY 1B)（2007年11月15日退役） 
    - STSAT-1（2005年10月15日退役） 
    - NigeriaSat-1（2011年11月15日退役） 
    - UK-DMC（2011年11月15日退役） 
    - Midori-2（2003年10月25日退役） 
    - METEOSAT-8 (MSG-1)（2016年7月4日退役） 
    - NOAA 17（2013年4月10日退役） 
    - FENGYUN 1D（2012年4月1日退役） 
    - SPOT 5（2015年3月27日退役） 
    - Envisat（2012年4月8日退役） 
    - JASON-1（2013年7月1日退役） 
    - GOES 12（2010年5月10日退役） 
    - Earth Orbiter 1（2017年3月30日退役） 
    - SAC-C（2013年8月15日退役） 
    - NOAA 16（2014年6月9日退役） 
    - GOES 11（2011年12月5日退役） 
    - INSAT-3B（2010年11月2日退役） 
    - ARIRANG-1 (KOMPSAT-1)（2008年1月31日退役） 
    - ACRIMSat（2013年12月14日退役） 
    - IKONOS 2（2015年3月31日退役） 
    - QuikScat（2009年11月23日退役） 
    - IRS-P4 (OCEANSAT-1)（2010年8月8日退役） 
    - FENGYUN 1C（2004年4月26日退役） 
    - INSAT-2E (APR-1)（2012年4月15日退役）


    ### 请严格按照以下标题和结构输出：

    1. **方案名称与概述**
       - 用一句话概括方案目标、解决的核心问题以及优势。

    2. **用户需求解读与补充**
       - 提炼用户的关键维度，包括研究目标、时间（时间范围、频率）、空间（分辨率、观测区域）、重访周期、波段范围等其他维度。
       - 针对用户的研究目标补充用户提到的维度之外的维度。

    3. **卫星组成**
       先写出推荐卫星，例如：推荐卫星：Landsat-8、Sentinel-2、高分一号

       然后使用表格展示详细信息（注意：表格必须格式正确，每行独占一行。）：

       | 卫星名称 | 所属国家/机构 | 发射时间 | 轨道类型 | 空间分辨率 | 时间分辨率 | 光谱分辨率 | 覆盖范围 | 主要特点 | 独特价值 |
       | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
       | Landsat-8 | 美国 | 2013年 | 太阳同步轨道 | 30米 | 16天 | 11个波段 | 全球区域 | 多光谱成像 | 长时序监测 |
       | Sentinel-2 | 欧洲 | 2015年 | 太阳同步轨道 | 10米 | 5天 | 13个波段 | 全球区域 | 高频观测 | 植被监测 |

    4. **卫星协同方案**
       使用表格展示协同关系（注意格式，特别是“推荐数据类型”字段给出空间分辨率以及产品等级等，“数据下载”字段提供可跳转的网址，注意是真实网址，其中哨兵卫星数据的网址为https://dataspace.copernicus.eu/data-collections）：

       | 卫星1 | 卫星2 | 协同类型 | 协同频率 | 协同效果 | 推荐数据类型 | 数据下载 |
       | --- | --- | --- | --- | --- |
       | Sentinel-2A | Sentinel-2B | 轨道相位协同 | 每5天 | 重访周期缩短至2.5天 | Sentinel-2A：10m分辨率、L1C级；Sentinel-2B：10m分辨率、L2A级 | 提供Sentinel-2A与Sentinel-2B的下载网址（注意是方案中的两颗卫星） |
       | 高分一号 | Sentinel-2 | 分辨率互补 | 每周2次 | 空间分辨率融合 | GF-1：2m分辨率、正射影像；Sentinel-2：10m分辨率、多光谱 | 提供高分一号与Sentinel-2的下载网址（注意是方案中的两颗卫星） |

       表格下方分析各卫星协同优势和组合价值。

    5. **数据处理策略**
       - 描述多星数据处理思路（如配准、融合、时序分析等）。
       - 指明调用工具的接口位置（由OGE算子封装的工具，暂用“[工具调用接口预留]”标注）。

    6. **方案总结与结果分析**
       - 优势：列出本方案的优势。
       - 不足：说明存在的限制。
       - 用户目标完成情况分析：分维度（用户需求中的维度，包括时空范围和时空分辨率、分析结果等）评估本方案对用户任务的完成情况。


    #### 特别强调
    - **所有表格必须格式正确，每行独占一行**
    - **不要将表格内容挤在一行**
    - **分隔符行必须单独一行**
    - **表格前后要有空行**
    - 所有表格参数必须为真实数值
    - 内容必须Markdown格式、结构清晰
    '''

    plan_content = ""

    # 定义流式回调
    async def direct_streaming_callback(data):
        nonlocal plan_content
        if data["type"] == "plan_content_chunk":
            plan_content = data["accumulated_content"]
            # 直接传递给外部回调
            if streaming_callback:
                await streaming_callback(data)

    try:
        if streaming_callback:
            await streaming_callback({
                "type": "thinking_step",
                "step": "AI生成",
                "message": "正在调用DeepSeek API直接流式生成方案..."
            })

        # 使用直接流式API调用
        api_response = await call_deepseek_streaming_api_direct(
            prompt,
            system_prompt,
            temperature=0.7,
            streaming_callback=direct_streaming_callback
        )

        if api_response["success"] and api_response.get("content"):
            plan_content = api_response["content"]

            # 检查内容是否有效
            if len(plan_content) > 50:
                state.main_plan = plan_content
                state.add_thinking_step("方案生成完成", f"成功生成{len(plan_content)}字符的虚拟星座方案")

                if streaming_callback:
                    await streaming_callback({
                        "type": "thinking_step",
                        "step": "方案生成完成",
                        "message": f"成功生成 {len(plan_content)} 字符的虚拟星座方案"
                    })
            else:
                logger.warning(f"生成的方案内容过短: {len(plan_content)} 字符")
                raise Exception("生成的方案内容不完整")
        else:
            error_msg = api_response.get('error', '未知错误')
            logger.error(f"API调用失败: {error_msg}")
            raise Exception(f"API调用失败: {error_msg}")

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

        # 流式发送应急方案
        if streaming_callback:
            lines = fallback_plan.split('\n')
            accumulated = ""
            for line in lines:
                accumulated += line + '\n'
                await streaming_callback({
                    "type": "plan_content_chunk",
                    "content": line + '\n',
                    "accumulated_content": accumulated
                })
                await asyncio.sleep(0.01)

    return state


async def optimize_constellation_plan_streaming(
        state: WorkflowState,
        user_feedback: str,
        streaming_callback: Optional[Callable] = None
) -> WorkflowState:
    """
    直接流式优化虚拟星座方案
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

    # 系统提示词
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

    # 主提示词
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

    # 定义直接流式回调处理器
    optimized_content = ""

    async def direct_optimize_callback(data):
        nonlocal optimized_content
        if data["type"] == "plan_content_chunk":
            optimized_content = data["accumulated_content"]
            # 直接传递给外部回调
            if streaming_callback:
                await streaming_callback(data)

    try:
        if streaming_callback:
            await streaming_callback({
                "type": "thinking_step",
                "step": "AI优化",
                "message": f"正在根据您的需求'{user_feedback}'优化方案..."
            })

        # 调用直接流式API进行优化
        api_response = await call_deepseek_streaming_api_direct(
            prompt,
            system_prompt,
            temperature=0.7,
            streaming_callback=direct_optimize_callback
        )

        if api_response["success"] and api_response.get("content"):
            optimized_content = api_response["content"]

            # 将原方案移至备选方案
            if not state.alternative_plans:
                state.alternative_plans = []
            state.alternative_plans.append(original_plan)

            # 更新方案
            state.main_plan = optimized_content
            state.metadata["optimization_prompt"] = prompt
            state.metadata["optimization_system_prompt"] = system_prompt
            state.metadata["optimization_feedback"] = user_feedback

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
    print("测试直接流式虚拟星座规划节点")
    print("=" * 50)

    if not DEEPSEEK_API_KEY:
        print("警告: 未设置DEEPSEEK_API_KEY环境变量")
        exit(1)


    async def test_direct_streaming():
        try:
            from backend.src.graph.state import WorkflowState

            # 创建测试工作流状态
            state = WorkflowState()
            state.add_message("user", "我需要监测青海湖的水质变化情况")

            # 模拟检索知识
            state.retrieved_knowledge = [
                {
                    "content": "高分一号是中国自主研发的高分辨率对地观测卫星，具有全色2米、多光谱8米的分辨率。",
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
                    print(f"📦 块 {chunk_count}: {content}", end='', flush=True)
                elif data["type"] == "thinking_step":
                    print(f"\n🤔 {data.get('step')}: {data.get('message')}")

            print("\n测试直接流式方案生成:")
            print("-" * 40)
            state = await generate_constellation_plan_streaming(state, test_callback)

            print(f"\n\n总共收到 {chunk_count} 个内容块")
            print(f"生成的方案长度: {len(state.main_plan) if state.main_plan else 0}")
            print("生成完成!")

        except Exception as e:
            print(f"测试时出错: {str(e)}")
            import traceback
            traceback.print_exc()


    # 运行测试
    asyncio.run(test_direct_streaming())
