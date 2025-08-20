import os
import json
import logging
import re
from typing import Dict, List, Any, Optional, Callable, Tuple
from pathlib import Path
import asyncio
import aiohttp
from backend.src.graph.state import WorkflowState
from backend.src.llm.jiuzhou_model_manager import get_jiuzhou_manager
from datetime import datetime
import calendar
import time
from backend.src.graph.nodes.uncertainty_calculator import get_uncertainty_calculator
logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


class EnhancedParameterClarificationNode:
    """增强的参数澄清节点 - 结合九州模型和规则系统"""

    def __init__(self):
        self.parameters_config = self._load_parameters_config()
        self.example_plans = self._load_example_plans()
        self.collected_params = {}
        self.question_history = []

        # 获取九州模型管理器
        self.jiuzhou_manager = get_jiuzhou_manager()

        # 是否启用AI模式
        self.ai_mode_enabled = True

        # 新增：选项生成使用DeepSeek
        self.use_deepseek_for_options = True

        self.use_batch_options_generation = True  # 设为 True 启用批量生成

    # 新增：DeepSeek API调用方法
    async def _call_deepseek_api(self, prompt: str, system_prompt: str = "", max_tokens: int = 800) -> str:
        """调用DeepSeek API"""
        if not DEEPSEEK_API_KEY:
            logger.error("DeepSeek API密钥未设置")
            return ""

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
            "temperature": 0.7,
            "max_tokens": max_tokens
        }

        try:
            timeout = aiohttp.ClientTimeout(total=300, connect=100)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(DEEPSEEK_API_URL, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"DeepSeek API请求失败: {response.status}, {error_text}")
                        return ""

                    result = await response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"].strip()
                    else:
                        logger.error("DeepSeek API返回格式错误")
                        return ""

        except asyncio.TimeoutError:
            logger.error("DeepSeek API调用超时")
            return ""
        except Exception as e:
            logger.error(f"调用DeepSeek API时出错: {str(e)}")
            return ""

    def _load_parameters_config(self) -> Dict:
        """加载参数配置"""
        config_path = Path(__file__).parent.parent.parent.parent / "data" / "constellation_parameters.json"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载参数配置失败: {e}")
            return self._get_default_parameters_config()

    def _load_example_plans(self) -> Dict:
        """加载示例方案"""
        examples_path = Path(__file__).parent.parent.parent.parent / "data" / "example_constellations.json"
        try:
            with open(examples_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载示例方案失败: {e}")
            return {"example_plans": []}

    def _get_default_parameters_config(self) -> Dict:
        """获取默认参数配置 - 完整版包含分析需求参数"""
        return {
            "parameter_categories": {
                "spatial": {
                    "name": "空间参数",
                    "priority": 1,
                    "parameters": {
                        "observation_area": {
                            "name": "观测区域",
                            "description": "需要监测的地理区域或地点",
                            "required": True,
                            "examples": ["青海湖", "长江流域", "北京市", "柬埔寨", "越南"],
                            "clarification_prompt": "您需要监测哪个具体的地理区域？"
                        },
                        "coverage_type": {
                            "name": "覆盖类型",
                            "description": "观测覆盖的范围类型",
                            "required": False,
                            "options": ["全覆盖", "重点区域密集观测", "关键点位监测"],
                            "clarification_prompt": "您需要什么类型的区域覆盖？"
                        }
                    }
                },
                "temporal": {
                    "name": "时间参数",
                    "priority": 2,
                    "parameters": {
                        "observation_frequency": {
                            "name": "观测频率",
                            "description": "多久获取一次数据",
                            "required": True,
                            "examples": ["每天1次", "每周2次", "每月1次", "实时监测"],
                            "clarification_prompt": "您希望多久获取一次新的卫星影像？（例如：每天、每周两次等）"
                        },
                        "monitoring_period": {
                            "name": "监测周期",
                            "description": "总共监测多长时间",
                            "required": True,
                            "examples": ["3个月", "6个月", "1年", "长期监测"],
                            "clarification_prompt": "您的监测项目需要持续多长时间？（例如：3个月、1年、长期等）"
                        },
                        "time_criticality": {
                            "name": "时效性要求",
                            "description": "数据获取的时间紧急程度",
                            "required": False,
                            "options": ["准实时（1小时内）", "快速（6小时内）", "常规（24小时内）", "非紧急（72小时内）"],
                            "clarification_prompt": "您对数据获取的时效性有什么要求？"
                        }
                    }
                },
                "technical": {
                    "name": "技术参数",
                    "priority": 3,
                    "parameters": {
                        "spatial_resolution": {
                            "name": "空间分辨率",
                            "description": "需要的图像分辨率",
                            "required": True,
                            "options": ["超高分辨率(<1米)", "高分辨率(1-5米)", "中分辨率(5-30米)", "低分辨率(>30米)"],
                            "clarification_prompt": "您需要什么级别的空间分辨率？"
                        },
                        "spectral_bands": {
                            "name": "光谱波段",
                            "description": "需要的光谱类型",
                            "required": False,
                            "options": ["可见光", "多光谱", "高光谱", "热红外", "雷达", "多光谱+热红外"],
                            "clarification_prompt": "您需要什么类型的光谱数据？"
                        },
                        "weather_dependency": {
                            "name": "天气依赖性",
                            "description": "对天气条件的依赖程度",
                            "required": False,
                            "options": ["全天候（不受天气影响）", "晴天条件", "云覆盖<30%", "无特殊要求"],
                            "clarification_prompt": "您对天气条件有什么要求？"
                        }
                    }
                },
                "application": {
                    "name": "应用参数",
                    "priority": 1,
                    "parameters": {
                        "monitoring_target": {
                            "name": "监测目标",
                            "description": "具体要监测什么",
                            "required": True,
                            "examples": ["水质变化", "植被覆盖", "城市扩张", "农业监测", "灾害应急"],
                            "clarification_prompt": "您的主要监测目标是什么？"
                        },
                        "analysis_requirements": {
                            "name": "分析需求",
                            "description": "需要进行的数据分析类型",
                            "required": True,
                            "options": [
                                "变化检测", "分类识别", "定量反演", "趋势分析",
                                "异常检测", "目标识别", "参数提取", "多时相对比"
                            ],
                            "clarification_prompt": "您需要进行什么类型的数据分析？",
                            "dynamic_options": True
                        },
                        "accuracy_requirements": {
                            "name": "精度要求",
                            "description": "对分析结果精度的要求",
                            "required": False,
                            "options": [
                                "科研级（>95%）", "业务级（85-95%）", "应用级（70-85%）", "一般级（>70%）"
                            ],
                            "clarification_prompt": "您对分析结果的精度有什么要求？"
                        }
                    }
                },
                "output": {
                    "name": "输出参数",
                    "priority": 4,
                    "parameters": {
                        "output_format": {
                            "name": "输出格式",
                            "description": "期望的数据输出格式",
                            "required": False,
                            "options": [
                                "遥感影像", "专题图", "统计报表", "分析报告",
                                "实时预警", "API接口", "数据库"
                            ],
                            "clarification_prompt": "您希望以什么格式获得分析结果？"
                        },
                        "data_processing_level": {
                            "name": "数据处理级别",
                            "description": "需要的数据处理程度",
                            "required": False,
                            "options": [
                                "原始数据", "几何校正", "辐射校正", "大气校正", "深度处理产品"
                            ],
                            "clarification_prompt": "您需要什么级别的数据处理？"
                        }
                    }
                },
                "constraints": {
                    "name": "约束条件",
                    "priority": 5,
                    "parameters": {
                        "budget_constraint": {
                            "name": "预算约束",
                            "description": "项目预算限制",
                            "required": False,
                            "options": ["无预算限制", "高预算", "中等预算", "低预算", "需要成本优化"],
                            "clarification_prompt": "您的项目预算情况如何？"
                        },
                        "data_security": {
                            "name": "数据安全要求",
                            "description": "对数据安全的要求",
                            "required": False,
                            "options": ["无特殊要求", "商业机密", "政府敏感", "军用级别"],
                            "clarification_prompt": "您对数据安全有什么特殊要求？"
                        }
                    }
                }
            },
            "clarification_rules": {
                "max_questions": 6,  # 增加最大问题数以包含分析需求
                "min_questions": 3,
                "skip_option": True
            }
        }

    async def extract_existing_parameters(self, state: WorkflowState) -> Dict[str, Any]:
        """智能提取已有参数 - 使用DeepSeek替代九州模型"""
        # 🔧 修复：如果正在参数澄清过程中，不应该重新提取参数
        if state.metadata.get("awaiting_clarification", False):
            # 直接返回已收集的参数
            return state.metadata.get("extracted_parameters", {})

        # 🔧 修复：检查是否是新需求
        is_new_requirement = self._is_new_requirement(state)

        # 🔧 修复：如果是新需求，清空之前的参数
        if is_new_requirement:
            logger.info("检测到新需求，清空旧参数")
            self.collected_params = {}
            state.metadata["extracted_parameters"] = {}
            state.metadata["clarification_completed"] = False

        # 🔧 关键修改：只使用最新方案请求后的消息进行参数提取
        rule_based_params = self._extract_parameters_by_rules(state, use_latest_plan_messages=True)

        if self.ai_mode_enabled:
            try:
                # 🔧 关键修改：获取最新方案请求后的用户消息
                messages_since_plan = state.get_messages_since_latest_plan_request()
                user_messages = [msg.content for msg in messages_since_plan if msg.role == "user"]

                if user_messages:
                    context_for_ai = " ".join(user_messages)
                    logger.info(f"🔖 使用最新方案请求后的消息进行AI参数提取，消息数: {len(user_messages)}")
                else:
                    context_for_ai = ""

                # 使用DeepSeek提取参数
                ai_extracted_params = await self._extract_parameters_with_deepseek(
                    context_for_ai,
                    {'existing_params': rule_based_params, 'is_new_requirement': is_new_requirement}
                )

                # 合并两种方法的结果（AI结果优先）
                merged_params = {**rule_based_params, **ai_extracted_params}

                logger.info(f"规则提取参数: {rule_based_params}")
                logger.info(f"DeepSeek提取参数: {ai_extracted_params}")
                logger.info(f"合并后参数: {merged_params}")

                return merged_params

            except Exception as e:
                logger.error(f"DeepSeek参数提取失败，回退到规则方法: {e}")
                return rule_based_params
        else:
            return rule_based_params

    async def _extract_parameters_with_deepseek(self, user_input: str, context: Dict[str, Any] = None) -> Dict[
        str, Any]:
        """使用DeepSeek提取参数"""
        if not DEEPSEEK_API_KEY:
            logger.error("DeepSeek API密钥未设置")
            return {}

        try:
            logger.info(f"开始使用DeepSeek提取参数，用户输入: {user_input[:100]}...")

            # 构建提示词
            prompt = self._build_deepseek_extraction_prompt(user_input, context)

            # 调用DeepSeek API
            response = await self._call_deepseek_api(prompt, self._get_extraction_system_prompt(), max_tokens=800)

            if response:
                # 解析响应
                extracted_params = self._parse_deepseek_extraction(response)
                logger.info(f"DeepSeek成功提取参数: {extracted_params}")
                return extracted_params
            else:
                logger.warning("DeepSeek未返回有效响应")
                return {}

        except Exception as e:
            logger.error(f"DeepSeek参数提取过程出错: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _get_extraction_system_prompt(self) -> str:
        """获取参数提取的系统提示词"""
        return """你是一个虚拟星座参数提取专家。你的任务是从用户的自然语言描述中准确提取出与虚拟星座设计相关的参数。

    重要原则：
    1. 只提取用户明确提到的参数，不要推断或补充
    2. 如果用户没有明确说明某个参数，就不要提取该参数
    3. 提取的参数值要忠实于用户的原始表述
    4. 输出必须是标准的JSON格式"""

    def _build_deepseek_extraction_prompt(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """构建DeepSeek参数提取的提示词"""
        is_new_requirement = context.get('is_new_requirement', False) if context else False

        prompt = """请从用户输入中提取虚拟星座相关参数。

    参数类别说明：
    1. **监测目标 (monitoring_target)**：
       - 提取条件：用户明确说"监测XX"、"观测XX"、"关注XX"
       - 示例："监测水质"→"水质变化"，"监测农业"→"农业监测"

    2. **观测区域 (observation_area)**：
       - 提取条件：用户提到具体地名
       - 示例：青海湖、北京市、长江流域、柬埔寨

    3. **覆盖范围 (coverage_range)**：
       - 提取条件：用户提到具体面积或范围描述
       - 示例：100平方公里、全市范围、局部区域

    4. **观测频率 (observation_frequency)**：
       - 提取条件：用户明确说明观测间隔
       - 示例：每天1次、每周2次、实时监测

    5. **监测周期 (monitoring_period)**：
       - 提取条件：用户明确说明监测时长
       - 示例：3个月、1年、长期监测

    6. **空间分辨率 (spatial_resolution)**：
       - 提取条件：用户明确要求分辨率
       - 示例：高分辨率、10米分辨率、超高清

    7. **光谱波段 (spectral_bands)**：
       - 提取条件：用户提到光谱需求
       - 示例：多光谱、热红外、可见光

    8. **分析需求 (analysis_requirements)**：
       - 提取条件：用户提到数据分析类型
       - 示例：变化检测、分类识别、定量反演
    """

        if is_new_requirement:
            prompt += "\n\n**注意：这是一个新的监测需求，请忽略之前的对话历史，只关注当前用户输入**\n"

        prompt += f"""
    当前用户输入："{user_input}"

    请提取参数，输出格式：
    {{
        "extracted_parameters": {{
            "参数名": "参数值"
        }}
    }}

    示例：
    用户输入："我需要监测柬埔寨的农业信息，每周观测2次，持续6个月"
    输出：
    {{
        "extracted_parameters": {{
            "monitoring_target": "农业监测",
            "observation_area": "柬埔寨",
            "observation_frequency": "每周2次",
            "monitoring_period": "6个月"
        }}
    }}

    请分析用户输入并提取参数："""

        # 如果有已知参数且不是新需求，添加到提示中
        if context and context.get('existing_params') and not is_new_requirement:
            prompt += "\n\n已经识别的参数（请勿重复提取）：\n"
            for key, value in context['existing_params'].items():
                prompt += f"- {key}: {value}\n"

        return prompt

    def _parse_deepseek_extraction(self, response: str) -> Dict[str, Any]:
        """解析DeepSeek的参数提取响应"""
        try:
            # 清理响应
            cleaned_response = response.strip()

            # 尝试直接解析JSON
            import json
            import re

            # 查找JSON部分
            json_match = re.search(r'\{[\s\S]*\}', cleaned_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)

                if "extracted_parameters" in data:
                    return data["extracted_parameters"]
                else:
                    # 如果没有extracted_parameters键，假设整个对象就是参数
                    return data

            # 如果解析失败，尝试手动提取
            logger.warning("无法解析JSON，尝试手动提取参数")
            return self._manual_extract_from_response(cleaned_response)

        except Exception as e:
            logger.error(f"解析DeepSeek响应失败: {e}")
            return {}

    def _manual_extract_from_response(self, response: str) -> Dict[str, Any]:
        """手动从响应中提取参数"""
        params = {}

        # 定义参数模式
        param_patterns = {
            "monitoring_target": [
                r'"monitoring_target"\s*:\s*"([^"]+)"',
                r'监测目标[：:]\s*([^\n,，]+)'
            ],
            "observation_area": [
                r'"observation_area"\s*:\s*"([^"]+)"',
                r'观测区域[：:]\s*([^\n,，]+)'
            ],
            "observation_frequency": [
                r'"observation_frequency"\s*:\s*"([^"]+)"',
                r'观测频率[：:]\s*([^\n,，]+)'
            ],
            "monitoring_period": [
                r'"monitoring_period"\s*:\s*"([^"]+)"',
                r'监测周期[：:]\s*([^\n,，]+)'
            ],
            "coverage_range": [
                r'"coverage_range"\s*:\s*"([^"]+)"',
                r'覆盖范围[：:]\s*([^\n,，]+)'
            ]
        }

        # 尝试匹配每个参数
        import re
        for param_key, patterns in param_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    params[param_key] = match.group(1).strip()
                    break

        return params

    async def calculate_parameters_uncertainty(self, params: Dict[str, Any]) -> Dict[str, Dict]:
        """计算参数的不确定性"""
        calculator = get_uncertainty_calculator()

        uncertainty_results = {}

        # 计算监测目标的不确定性
        if "monitoring_target" in params:
            uncertainty_results["monitoring_target"] = await calculator.calculate_monitoring_target_uncertainty(
                params.get("monitoring_target"),
                enable_web_search=True,  # 可配置
                enable_llm=True  # 可配置
            )

            logger.info(f"监测目标不确定性: {uncertainty_results['monitoring_target']}")

        # 🆕 新增：计算时间参数的不确定性
        time_uncertainty = await calculator.calculate_time_uncertainty(
            params.get("observation_frequency"),
            params.get("monitoring_period"),
            enable_llm=True  # 可配置
        )

        # 将时间参数的不确定性结果添加到总结果中
        if "observation_frequency" in time_uncertainty:
            uncertainty_results["observation_frequency"] = time_uncertainty["observation_frequency"]
            logger.info(f"观测频率不确定性: {uncertainty_results['observation_frequency']}")

        if "monitoring_period" in time_uncertainty:
            uncertainty_results["monitoring_period"] = time_uncertainty["monitoring_period"]
            logger.info(f"监测周期不确定性: {uncertainty_results['monitoring_period']}")

        # 🆕 添加：计算地点参数的不确定性
        location_uncertainty = await calculator.calculate_location_uncertainty(
            params.get("observation_area"),
            params.get("coverage_range"),
            enable_llm=True  # 可配置
        )

        # 将地点参数的不确定性结果添加到总结果中
        if "observation_area" in location_uncertainty:
            uncertainty_results["observation_area"] = location_uncertainty["observation_area"]
            logger.info(f"观测区域不确定性: {uncertainty_results['observation_area']}")

        if "coverage_range" in location_uncertainty:
            uncertainty_results["coverage_range"] = location_uncertainty["coverage_range"]
            logger.info(f"覆盖范围不确定性: {uncertainty_results['coverage_range']}")

        return uncertainty_results


    def _extract_parameters_by_rules(self, state: WorkflowState, use_latest_plan_messages: bool = False) -> Dict[
        str, Any]:
        """基于规则的参数提取（修复版本）"""
        existing_params = {}

        # 🔧 关键修改：根据标志决定使用哪些消息
        if use_latest_plan_messages:
            # 使用最新方案请求后的消息
            messages_since_plan = state.get_messages_since_latest_plan_request()
            user_messages = [msg.content for msg in messages_since_plan if msg.role == "user"]
            logger.info(f"🔖 使用最新方案请求后的 {len(user_messages)} 条用户消息进行规则参数提取")
        else:
            # 使用所有用户消息（保持原有行为）
            user_messages = [msg.content for msg in state.messages if msg.role == "user"]
            logger.info(f"使用所有 {len(user_messages)} 条用户消息进行规则参数提取")

        # 合并用户消息内容
        full_context = " ".join(user_messages) if user_messages else ""

        if not full_context:
            logger.warning("没有用户消息可供参数提取")
            return existing_params

        logger.info(f"参数提取上下文: {full_context[:200]}...")

        # 1. 监测目标提取
        target_patterns = {
            "water": {
                "keywords": ["水质", "水体", "水位", "富营养化", "藻类", "水污染", "水资源"],
                "targets": ["水质变化", "水位监测", "水体面积", "富营养化", "藻类爆发"]
            },
            "vegetation": {
                "keywords": ["植被", "森林", "草地", "作物", "农业", "绿化", "生态"],
                "targets": ["植被覆盖", "作物长势", "森林变化", "草地退化", "物候监测"]
            },
            "agriculture": {  # 🔧 新增：农业相关模式
                "keywords": ["农业", "农作物", "种植", "农田", "耕地", "庄稼", "粮食"],
                "targets": ["作物长势", "农业监测", "作物分类", "产量估算", "农田变化"]
            },
            "urban": {
                "keywords": ["城市", "建筑", "热岛", "交通", "违建", "城镇", "扩张"],
                "targets": ["城市扩张", "建筑变化", "热岛效应", "交通流量", "违建监测"]
            }
        }

        # 🔧 修复：优先匹配更具体的关键词
        for category, config in target_patterns.items():
            for keyword in config["keywords"]:
                if keyword in full_context:
                    # 对于农业，选择更合适的目标
                    if category == "agriculture" and "农业" in full_context:
                        existing_params["monitoring_target"] = "农业监测"
                        break
                    else:
                        for target in config["targets"]:
                            if any(t in full_context for t in target.split()):
                                existing_params["monitoring_target"] = target
                                break
                    if "monitoring_target" in existing_params:
                        break

        # 2. 地理位置提取
        # 🔧 新增：国家名称识别
        countries = ["柬埔寨", "越南", "泰国", "老挝", "缅甸", "马来西亚", "新加坡", "印度尼西亚", "菲律宾"]
        for country in countries:
            if country in full_context:
                existing_params["observation_area"] = country
                break

        # 如果没找到国家，再找省市区县
        if "observation_area" not in existing_params:
            location_pattern = r'([^省]+省|[^市]+市|[^区]+区|[^县]+县)'
            locations = re.findall(location_pattern, full_context)
            if locations:
                existing_params["observation_area"] = locations[0]

        # 特定地名
        if "observation_area" not in existing_params:
            specific_locations = ["青海湖", "长江", "黄河", "太湖", "洞庭湖", "鄱阳湖", "珠江"]
            for loc in specific_locations:
                if loc in full_context:
                    existing_params["observation_area"] = loc
                    break

        # 🆕 新增：覆盖范围提取
        coverage_patterns = {
            # 明确的面积表述
            r'(\d+)\s*平方公里': lambda m: f"{m.group(1)}平方公里",
            r'(\d+)\s*平方千米': lambda m: f"{m.group(1)}平方公里",
            r'(\d+)\s*km²': lambda m: f"{m.group(1)}平方公里",
            r'(\d+)\s*公顷': lambda m: f"{int(m.group(1)) / 100}平方公里",

            # 描述性范围
            r'全市': "city",
            r'全省': "large",
            r'全流域': "large",
            r'整个.*?地区': "large",
            r'局部': "local",
            r'重点区域': "regional",
            r'单点': "point",
            r'小范围': "local",
            r'大范围': "large"
        }

        for pattern, handler in coverage_patterns.items():
            match = re.search(pattern, full_context)
            if match:
                if callable(handler):
                    existing_params["coverage_range"] = handler(match)
                else:
                    existing_params["coverage_range"] = handler
                break

        # 如果提到了特定地点但没有明确范围，智能推断
        if "observation_area" in existing_params and "coverage_range" not in existing_params:
            area = existing_params["observation_area"]
            if "湖" in area or "水库" in area:
                existing_params["coverage_range"] = "regional"  # 湖泊通常是区域范围
            elif "市" in area:
                existing_params["coverage_range"] = "city"  # 城市级别
            elif "县" in area or "区" in area:
                existing_params["coverage_range"] = "regional"  # 县区级别
            elif "省" in area or "流域" in area:
                existing_params["coverage_range"] = "large"  # 大范围

        return existing_params

    async def _adjust_params_by_context(self, params: List[Dict], user_context: str, existing_params: Dict) -> List[
        Dict]:
        """根据用户上下文动态调整参数必要性"""

        # 根据监测目标调整相关参数的必要性
        target = existing_params.get("monitoring_target", "")

        for param in params:
            param_key = param["key"]

            # 水质监测场景
            if "水" in target or "水质" in user_context:
                if param_key in ["spectral_bands", "analysis_requirements"]:
                    param["required"] = True
                    param["priority"] = 2

            # 农业监测场景
            elif "农业" in target or "作物" in user_context:
                if param_key == "spectral_bands":
                    param["required"] = True
                    param["priority"] = 2
                if param_key == "monitoring_period":
                    param["examples"] = ["生长季(4-10月)", "全年监测", "关键生育期"]

            # 灾害应急场景
            elif "灾害" in target or "应急" in user_context:
                if param_key == "time_criticality":
                    param["required"] = True
                    param["priority"] = 1
                if param_key == "weather_dependency":
                    param["required"] = True
                    param["priority"] = 2

        return params

    async def identify_missing_parameters(self, existing_params: Dict[str, Any], state: WorkflowState) -> List[
        Dict[str, Any]]:
        """识别缺失的参数 - 修复版：确保技术参数作为可选项展示"""
        missing_params = []
        param_config = self.parameters_config.get("parameter_categories", {})

        # 🔧 修复：定义参数到类别的映射
        param_to_category = {
            "monitoring_target": "monitoring_target",
            "observation_area": "monitoring_area",
            "coverage_range": "monitoring_area",  # 🆕 新增
            "observation_frequency": "monitoring_time",
            "monitoring_period": "monitoring_time",
            "spatial_resolution": "technical_params",
            "spectral_bands": "technical_params",
            "analysis_requirements": "technical_params",
            "accuracy_requirements": "technical_params",
            "output_format": "technical_params",
            "time_criticality": "technical_params",
            "weather_dependency": "technical_params"
        }

        # 🔧 修复：定义每个简化类别的必需参数
        category_required_params = {
            "monitoring_target": ["monitoring_target"],
            "monitoring_area": ["observation_area", "coverage_range"],  # 🆕 修改
            "monitoring_time": ["observation_frequency", "monitoring_period"],
            "technical_params": []  # 技术参数都是可选的
        }

        # 🔧 修复：从原始配置中查找参数定义
        all_params_info = {}
        for cat_key, cat_info in param_config.items():
            for param_key, param_info in cat_info.get("parameters", {}).items():
                all_params_info[param_key] = {
                    "info": param_info,
                    "original_category": cat_key,
                    "category_info": cat_info
                }

        # 按照新的4个类别顺序检查参数
        categories_order = ["monitoring_target", "monitoring_area", "monitoring_time", "technical_params"]

        # 首先处理必需参数（前3个类别）
        for category_key in categories_order[:3]:  # 只处理前3个类别
            # 获取该类别的必需参数
            required_params = category_required_params.get(category_key, [])

            # 检查必需参数是否缺失
            for param_key in required_params:
                if param_key not in existing_params and param_key in all_params_info:
                    param_data = all_params_info[param_key]
                    param_info = param_data["info"]

                    missing_params.append({
                        "key": param_key,
                        "name": param_info.get("name"),
                        "prompt": param_info.get("clarification_prompt"),
                        "options": param_info.get("options"),
                        "examples": param_info.get("examples"),
                        "category": category_key,  # 使用简化的类别
                        "category_name": self._get_category_display_name(category_key),
                        "priority": self._get_category_priority(category_key),
                        "required": True,  # 前3个类别的参数都是必需的
                        "dynamic_options": param_info.get("dynamic_options"),
                        "description": param_info.get("description")
                    })

        # 🔧 关键修复：总是添加一些技术参数作为可选项（不再依赖 _user_wants_technical_params）
        # 获取相关的技术参数
        relevant_tech_params = self._get_relevant_technical_params_from_config(
            existing_params, all_params_info
        )

        # 🔧 新增：确保至少有一些技术参数被展示
        # 如果没有相关的技术参数，使用默认的技术参数列表
        if not relevant_tech_params:
            relevant_tech_params = ["spatial_resolution", "analysis_requirements", "output_format"]

        # 添加技术参数（最多3个，让用户不会感到负担）
        tech_params_added = 0
        max_tech_params = 3

        for param_key in relevant_tech_params:
            if tech_params_added >= max_tech_params:
                break

            if param_key not in existing_params and param_key in all_params_info:
                param_data = all_params_info[param_key]
                param_info = param_data["info"]

                missing_params.append({
                    "key": param_key,
                    "name": param_info.get("name"),
                    "prompt": param_info.get("clarification_prompt"),
                    "options": param_info.get("options"),
                    "examples": param_info.get("examples"),
                    "category": "technical_params",
                    "category_name": "技术参数（可选）",
                    "priority": 4,
                    "required": False,  # 技术参数是可选的
                    "dynamic_options": param_info.get("dynamic_options"),
                    "description": param_info.get("description"),
                    "is_technical": True  # 标记为技术参数
                })

                tech_params_added += 1

        logger.info(
            f"识别出 {len(missing_params)} 个参数（{len([p for p in missing_params if p.get('required')])} 个必需，{tech_params_added} 个可选技术参数）")
        return missing_params

    def _get_category_display_name(self, category_key: str) -> str:
        """获取类别显示名称"""
        display_names = {
            "monitoring_target": "监测目标",
            "monitoring_area": "监测区域",
            "monitoring_time": "监测时间要求",
            "technical_params": "技术参数"
        }
        return display_names.get(category_key, category_key)

    def _get_category_priority(self, category_key: str) -> int:
        """获取类别优先级"""
        priorities = {
            "monitoring_target": 1,
            "monitoring_area": 2,
            "monitoring_time": 3,
            "technical_params": 4
        }
        return priorities.get(category_key, 5)

    def _get_relevant_technical_params_from_config(
            self, existing_params: Dict, all_params_info: Dict
    ) -> List[str]:
        """从配置中获取相关的技术参数 - 修复版：确保总是返回技术参数"""
        monitoring_target = existing_params.get("monitoring_target", "")

        # 技术参数列表
        tech_params = [
            "spatial_resolution", "spectral_bands", "analysis_requirements",
            "accuracy_requirements", "time_criticality", "weather_dependency",
            "output_format", "data_processing_level"
        ]

        # 根据监测目标确定最相关的技术参数
        target_tech_mapping = {
            "水质": ["spectral_bands", "analysis_requirements", "accuracy_requirements"],
            "农业": ["spatial_resolution", "spectral_bands", "output_format"],
            "城市": ["spatial_resolution", "analysis_requirements", "output_format"],
            "灾害": ["time_criticality", "weather_dependency", "spatial_resolution"],
            "植被": ["spectral_bands", "spatial_resolution", "analysis_requirements"],
            "环境": ["spectral_bands", "analysis_requirements", "accuracy_requirements"]
        }

        relevant_keys = []

        # 根据监测目标选择相关参数
        matched = False
        for target_keyword, tech_keys in target_tech_mapping.items():
            if target_keyword in monitoring_target:
                relevant_keys.extend(tech_keys)
                matched = True
                break

        # 🔧 关键修复：如果没有匹配或列表为空，使用默认的通用技术参数
        if not matched or not relevant_keys:
            # 默认技术参数组合，适用于大多数场景
            relevant_keys = ["spatial_resolution", "analysis_requirements", "output_format"]
            logger.info(f"未找到特定监测目标的技术参数映射，使用默认技术参数: {relevant_keys}")

        # 确保参数不重复
        relevant_keys = list(dict.fromkeys(relevant_keys))

        # 只返回配置中实际存在的参数
        available_keys = [key for key in relevant_keys if key in all_params_info]

        # 🔧 新增：如果过滤后没有参数，尝试添加其他可用的技术参数
        if not available_keys:
            for param in tech_params:
                if param in all_params_info:
                    available_keys.append(param)
                    if len(available_keys) >= 3:  # 最多3个
                        break

        logger.info(f"返回的技术参数: {available_keys}")
        return available_keys

    def _get_most_relevant_technical_params(self, tech_params: List[Dict], existing_params: Dict) -> List[Dict]:
        """根据监测目标获取最相关的技术参数"""
        monitoring_target = existing_params.get("monitoring_target", "")

        # 定义不同监测目标的技术参数优先级
        priority_mapping = {
            "水质": ["spectral_bands", "analysis_requirements", "accuracy_requirements", "output_format"],
            "农业": ["spatial_resolution", "spectral_bands", "analysis_requirements", "output_format"],
            "城市": ["spatial_resolution", "analysis_requirements", "output_format"],
            "灾害": ["time_criticality", "weather_dependency", "spatial_resolution", "output_format"],
            "植被": ["spectral_bands", "spatial_resolution", "analysis_requirements"],
            "环境": ["spectral_bands", "analysis_requirements", "accuracy_requirements"]
        }

        # 默认优先级
        default_priority = ["spatial_resolution", "analysis_requirements", "output_format"]

        # 获取相关的参数键列表
        relevant_keys = default_priority
        for target_keyword, param_keys in priority_mapping.items():
            if target_keyword in monitoring_target:
                relevant_keys = param_keys
                break

        # 根据优先级排序技术参数
        sorted_params = []

        # 先添加优先级高的参数
        for key in relevant_keys:
            for param in tech_params:
                if param["key"] == key and param not in sorted_params:
                    sorted_params.append(param)

        # 再添加其他参数
        for param in tech_params:
            if param not in sorted_params:
                sorted_params.append(param)

        return sorted_params

    def _user_wants_technical_params(self, state: WorkflowState) -> bool:
        """判断用户是否需要设置技术参数"""
        user_messages = [msg.content for msg in state.messages if msg.role == "user"]
        if not user_messages:
            return False

        # 检查用户是否提到技术细节
        tech_keywords = ["分辨率", "精度", "波段", "光谱", "实时", "格式", "输出"]
        full_context = " ".join(user_messages).lower()

        return any(keyword in full_context for keyword in tech_keywords)

    def _get_relevant_technical_params(self, tech_params: List[Dict], existing_params: Dict) -> List[Dict]:
        """根据监测目标获取相关的技术参数"""
        monitoring_target = existing_params.get("monitoring_target", "")

        # 根据监测目标确定最相关的技术参数
        target_tech_mapping = {
            "水质": ["spectral_bands", "analysis_requirements", "accuracy_requirements"],
            "农业": ["spatial_resolution", "spectral_bands", "output_format"],
            "城市": ["spatial_resolution", "analysis_requirements", "output_format"],
            "灾害": ["time_criticality", "weather_dependency", "spatial_resolution"]
        }

        relevant_keys = []
        for target_keyword, tech_keys in target_tech_mapping.items():
            if target_keyword in monitoring_target:
                relevant_keys.extend(tech_keys)
                break

        # 如果没有匹配，返回通用技术参数
        if not relevant_keys:
            relevant_keys = ["spatial_resolution", "analysis_requirements"]

        # 过滤出相关的技术参数
        relevant_params = []
        for param in tech_params:
            if param["key"] in relevant_keys:
                relevant_params.append(param)

        return relevant_params


    def _build_missing_params_identification_prompt(self, user_context: str, existing_params: Dict[str, Any],
                                                    state: WorkflowState) -> str:
        """构建缺失参数识别的提示词"""

        # 获取之前的对话历史用于上下文
        conversation_history = state.get_conversation_history(max_messages=3)

        prompt = """你是一个虚拟星座方案设计专家，需要分析用户需求并识别出缺失的关键参数。

    ## 任务说明：
    1. 仔细分析用户的需求描述
    2. 结合虚拟星座设计的专业知识，识别出哪些关键参数缺失
    3. 评估每个缺失参数的重要性（high/medium/low）
    4. 说明为什么需要这个参数

    ## 可选参数类别：
    ### 空间参数
    - observation_area: 观测区域（地理位置）
    - coverage_type: 覆盖类型（全覆盖/重点区域）
    - observation_priority: 观测优先级

    ### 时间参数
    - observation_frequency: 观测频率（多久一次）
    - monitoring_period: 监测周期（总时长）
    - time_criticality: 时效性要求
    - specific_time_windows: 特定时间窗口

    ### 技术参数
    - spatial_resolution: 空间分辨率
    - spectral_bands: 光谱波段
    - weather_dependency: 天气依赖性
    - data_processing_level: 数据处理级别

    ### 应用参数
    - monitoring_target: 监测目标（监测什么）
    - analysis_requirements: 分析需求
    - accuracy_requirements: 精度要求
    - output_format: 输出格式

    ### 约束条件
    - budget_constraint: 预算约束
    - data_security: 数据安全要求
    - response_time: 响应时间

    ## 用户需求：
    {user_context}

    ## 已经识别的参数：
    {existing_params_str}

    ## 对话历史：
    {conversation_history}

    ## 请分析并输出：
    1. 根据用户需求的具体场景，哪些参数是必须的？
    2. 哪些参数虽然用户没提到，但对方案设计很重要？
    3. 考虑参数之间的关联性（如监测水质需要特定的光谱波段）

    输出JSON格式：
    {{
      "missing_parameters": [
        {{
          "parameter": "参数键名",
          "name": "参数中文名",
          "importance": "high/medium/low",
          "reason": "为什么需要这个参数",
          "custom_question": "如果是新参数，提供问题文本",
          "suggested_options": ["选项1", "选项2"],
          "suggested_examples": ["示例1", "示例2"]
        }}
      ],
      "analysis_notes": "整体分析说明"
    }}

    注意：
    - 只识别真正缺失且重要的参数，避免过度询问
    - 根据用户需求的明确程度调整参数数量
    - 如果用户需求已经很明确，只识别最关键的1-2个参数
    - 考虑不同应用场景的特殊需求
    """

        # 格式化已有参数
        existing_params_str = ""
        if existing_params:
            for key, value in existing_params.items():
                existing_params_str += f"- {key}: {value}\n"
        else:
            existing_params_str = "（暂无已识别参数）"

        return prompt.format(
            user_context=user_context,
            existing_params_str=existing_params_str,
            conversation_history=conversation_history
        )

    def _parse_ai_missing_params(self, model_output: str) -> Optional[List[Dict[str, Any]]]:
        """解析AI识别的缺失参数"""
        try:
            import re
            import json

            # 提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', model_output)
            if json_match:
                result = json.loads(json_match.group())

                missing_params = result.get('missing_parameters', [])
                analysis_notes = result.get('analysis_notes', '')

                if analysis_notes:
                    logger.info(f"AI参数分析说明: {analysis_notes}")

                return missing_params

        except Exception as e:
            logger.error(f"解析AI缺失参数识别结果失败: {e}")
            logger.debug(f"模型原始输出: {model_output[:500]}...")

        return None

    def _ai_smart_sort_and_filter(self, missing_params: List[Dict], existing_params: Dict, user_context: str) -> List[
        Dict]:
        """AI智能排序和过滤缺失参数"""

        # 根据多个因素对参数进行评分
        def calculate_score(param):
            score = 0

            # 基础优先级分数
            priority = param.get('priority', 3)
            score += (4 - priority) * 100

            # AI生成的参数加分
            if param.get('ai_generated'):
                score += 50

            # 有AI原因说明的加分
            if param.get('ai_reason'):
                score += 30

            # 根据用户需求的紧急程度调整
            urgent_keywords = ['紧急', '立即', '马上', '应急', '灾害']
            if any(keyword in user_context for keyword in urgent_keywords):
                # 紧急情况下，时间相关参数优先
                if param['key'] in ['observation_frequency', 'time_criticality', 'response_time']:
                    score += 80

            # 根据监测目标调整优先级
            target = existing_params.get('monitoring_target', '')
            if target:
                if '水' in target and param['key'] in ['spectral_bands', 'analysis_requirements']:
                    score += 60
                elif '农业' in target and param['key'] in ['monitoring_period', 'spectral_bands']:
                    score += 60
                elif '城市' in target and param['key'] in ['spatial_resolution', 'observation_frequency']:
                    score += 60

            return score

        # 对参数进行评分和排序
        for param in missing_params:
            param['_score'] = calculate_score(param)

        sorted_params = sorted(missing_params, key=lambda x: x['_score'], reverse=True)

        # 移除临时的评分字段
        for param in sorted_params:
            param.pop('_score', None)

        # 动态确定问题数量
        rules = self.parameters_config.get("clarification_rules", {})
        max_questions = rules.get("max_questions", 10)
        min_questions = rules.get("min_questions", 2)

        # 根据用户需求的明确程度调整问题数量
        if len(user_context) > 200 and existing_params.get('monitoring_target') and existing_params.get(
                'observation_area'):
            # 用户需求已经比较明确，减少问题数量
            max_questions = min(max_questions, 3)

        # 确保至少有最少数量的问题
        result_params = sorted_params[:max_questions]

        # 如果高优先级参数不够，添加一些有价值的中等优先级参数
        if len(result_params) < min_questions:
            medium_priority_params = [p for p in sorted_params[max_questions:] if p.get('priority', 3) == 2]
            result_params.extend(medium_priority_params[:min_questions - len(result_params)])

        return result_params

    def _rule_based_identify_missing_params(self, existing_params: Dict[str, Any], core_params: List[str]) -> List[
        Dict[str, Any]]:
        """基于规则的缺失参数识别（作为备选方案）"""
        missing_params = []
        param_config = self.parameters_config.get("parameter_categories", {})

        # 找出缺失的核心参数
        missing_core = [p for p in core_params if p not in existing_params]

        for category_key, category_info in param_config.items():
            for param_key, param_info in category_info.get("parameters", {}).items():
                if param_key in missing_core:
                    missing_params.append({
                        "key": param_key,
                        "name": param_info.get("name"),
                        "prompt": param_info.get("clarification_prompt"),
                        "options": param_info.get("options"),
                        "examples": param_info.get("examples"),
                        "category": category_key,
                        "priority": category_info.get("priority", 999),
                        "dynamic_options": param_info.get("dynamic_options"),
                        "categories": param_info.get("categories")
                    })

        # 使用原有的智能排序
        return self._smart_sort_parameters(missing_params, existing_params)

    async def _ai_identify_missing_params(self, user_context: str, existing_params: Dict[str, Any],
                                          state: WorkflowState) -> Optional[List[Dict[str, Any]]]:
        """使用九州模型智能识别缺失参数"""

        try:
            # 构建智能识别的提示词
            prompt = self._build_missing_params_identification_prompt(user_context, existing_params, state)

            # 调用九州模型
            response = await self.jiuzhou_manager.generate(prompt, max_tokens=800)

            # 解析AI的响应
            missing_params_info = self._parse_ai_missing_params(response)

            if not missing_params_info:
                return None

            # 将AI识别的参数转换为标准格式
            missing_params = []
            param_config = self.parameters_config.get("parameter_categories", {})

            for param_info in missing_params_info:
                param_key = param_info.get('parameter')
                importance = param_info.get('importance', 'medium')
                reason = param_info.get('reason', '')

                # 在配置中查找参数定义
                param_found = False
                for category_key, category_info in param_config.items():
                    if param_key in category_info.get("parameters", {}):
                        param_def = category_info["parameters"][param_key]

                        # 根据AI判断的重要性调整优先级
                        priority = 1 if importance == 'high' else (2 if importance == 'medium' else 3)

                        missing_params.append({
                            "key": param_key,
                            "name": param_def.get("name"),
                            "prompt": param_def.get("clarification_prompt"),
                            "options": param_def.get("options"),
                            "examples": param_def.get("examples"),
                            "category": category_key,
                            "priority": priority,
                            "dynamic_options": param_def.get("dynamic_options"),
                            "categories": param_def.get("categories"),
                            "ai_reason": reason  # AI给出的需要该参数的原因
                        })
                        param_found = True
                        break

                # 如果是AI建议的新参数（配置中没有）
                if not param_found and param_info.get('custom_question'):
                    missing_params.append({
                        "key": param_key,
                        "name": param_info.get('name', param_key),
                        "prompt": param_info.get('custom_question'),
                        "options": param_info.get('suggested_options', []),
                        "examples": param_info.get('suggested_examples', []),
                        "category": "custom",
                        "priority": 1 if importance == 'high' else 2,
                        "ai_generated": True,
                        "ai_reason": reason
                    })

            # 智能排序和限制数量
            missing_params = self._ai_smart_sort_and_filter(missing_params, existing_params, user_context)

            return missing_params

        except Exception as e:
            logger.error(f"AI识别缺失参数过程出错: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _smart_sort_parameters(self, params: List[Dict], existing_params: Dict) -> List[Dict]:
        """智能排序参数（保持原有实现）"""

        def get_weight(param):
            weight = param["priority"] * 10

            # 核心参数优先
            if param["key"] in ["monitoring_target", "observation_area"]:
                weight -= 100

            # 根据已有参数调整权重
            if "monitoring_target" in existing_params:
                target = existing_params["monitoring_target"]
                if "水" in target and param["key"] in ["spectral_bands", "observation_frequency"]:
                    weight -= 50
                elif "植被" in target and param["key"] in ["spectral_bands", "monitoring_period"]:
                    weight -= 50
                elif "城市" in target and param["key"] in ["spatial_resolution", "analysis_requirements"]:
                    weight -= 50

            return weight

        return sorted(params, key=get_weight)

    async def _enhance_questions_with_ai(self, questions: List[Dict], required_params: List[Dict],
                                         optional_params: List[Dict]) -> List[Dict]:
        """使用AI增强问题的表述和组织"""

        # 构建提示词
        prompt = f"""你是一个友好的虚拟星座助手。用户想要设计虚拟星座方案，现在需要收集以下参数。
    请优化这些问题的表述，使其更加友好和易懂。

    ## 必需参数（{len(required_params)}个）：
    """
        for param in required_params:
            prompt += f"- {param['name']}: {param['prompt']}\n"

        if optional_params:
            prompt += f"\n## 可选参数（{len(optional_params)}个）：\n"
            for param in optional_params:
                prompt += f"- {param['name']}: {param['prompt']}\n"

        prompt += """
    ## 优化要求：
    1. 保持问题的核心含义不变
    2. 使用更友好、自然的语言
    3. 可以添加简短的解释说明
    4. 对于技术性参数，用通俗的方式解释

    请直接返回优化后的问题文本，不需要其他格式。
    """

        # 这里简化处理，实际可以调用九州模型
        # response = await self.jiuzhou_manager.generate(prompt, max_tokens=800)

        return questions

    def _generate_rule_based_question(self, param: Dict) -> Dict[str, Any]:
        """基于规则生成问题"""
        return {
            "parameter_key": param["key"],
            "question": param["prompt"],
            "type": self._determine_question_type(param),
            "options": self._format_options(param),
            "examples": param.get("examples", []),
            "hint": self._generate_hint(param),
            "required": param.get("priority", 5) <= 2,
            "ai_generated": False
        }

    def _determine_question_type(self, param: Dict) -> str:
        """确定问题类型（保持原有实现）"""
        if param.get("options") and isinstance(param["options"], (list, dict)):
            if len(param.get("options", [])) <= 6:
                return "options"
            else:
                return "dropdown"
        elif param.get("categories"):
            return "categorized"
        elif param.get("examples") and len(param["examples"]) > 3:
            return "autocomplete"
        else:
            return "text"

    def _format_options(self, param: Dict) -> List[Dict[str, str]]:
        """格式化选项（保持原有实现）"""
        options = param.get("options", [])

        if isinstance(options, dict):
            return [{"value": k, "label": v} for k, v in options.items()]
        elif isinstance(options, list):
            return [{"value": opt, "label": opt} for opt in options]
        else:
            return []

    def _generate_hint(self, param: Dict) -> str:
        """生成参数提示（保持原有实现）"""
        hints = {
            "observation_area": "💡 提示：可以是具体地名、行政区域或经纬度范围",
            "monitoring_target": "💡 提示：请尽可能具体，如'水体富营养化'比'水质'更好",
            "spatial_resolution": "💡 提示：分辨率越高，能看到的细节越多，但覆盖范围越小",
            "observation_frequency": "💡 提示：频率越高，时间分辨率越好，但成本也越高",
            "spectral_bands": "💡 提示：不同波段适合不同应用，如植被监测适合多光谱"
        }

        return hints.get(param["key"], "")

    def should_skip_clarification(self, state: WorkflowState) -> bool:
        """判断是否应该跳过澄清 - 修复版本：考虑分阶段收集"""
        # 检查用户是否明确表示不需要澄清
        user_messages = [msg for msg in state.messages if msg.role == "user"]
        if user_messages:
            latest_message = user_messages[-1].content.lower()
            skip_keywords = ["直接生成方案", "跳过所有问题", "使用默认参数"]
            if any(keyword == latest_message.strip() for keyword in skip_keywords):
                return True

        # 🔧 修复：检查当前收集阶段
        current_stage = state.get_current_collection_stage()

        # 如果还在收集过程中（不是completed），不应该跳过
        if current_stage != "completed" and current_stage != "not_started":
            # 检查是否完成了所有阶段
            stage_order = ["purpose", "time", "location", "technical"]
            try:
                current_index = stage_order.index(current_stage)
                # 如果还没到技术参数阶段，不应该跳过
                if current_index < len(stage_order) - 1:
                    logger.info(f"当前阶段 {current_stage}，还有后续阶段需要收集")
                    return False
            except ValueError:
                pass

        # 🔧 修复：检查是否已经完成所有阶段（包括技术参数）
        if state.metadata.get("clarification_completed", False):
            # 检查是否是新的需求
            if self._is_new_requirement(state):
                state.metadata["clarification_completed"] = False
                state.metadata["extracted_parameters"] = {}  # 重置参数
                return False
            return True

        # 🔧 修复：从state中获取已收集的参数
        existing_params = state.metadata.get("extracted_parameters", {})

        # 🔧 修复：核心必需参数（不包含技术参数）
        essential_params = [
            "monitoring_target",  # 监测目标
            "observation_area",  # 监测区域
            "observation_frequency",  # 观测频率
            "monitoring_period"  # 监测周期
        ]

        # 检查每个参数是否有有效值
        missing_params = []
        for param in essential_params:
            if param not in existing_params or not existing_params[param]:
                missing_params.append(param)
                logger.info(f"缺少必需参数: {param}")

        # 如果有缺失参数，需要澄清
        if missing_params:
            logger.info(f"需要澄清的参数: {missing_params}")
            return False

        # 🔧 关键修复：即使必需参数完整，也要检查是否已经经过技术参数阶段
        # 通过检查收集历史来判断
        collection_history = state.parameter_collection_history
        has_technical_stage = any(
            record.get("stage") == "technical"
            for record in collection_history
        )

        if not has_technical_stage and current_stage != "technical":
            logger.info("必需参数已完整，但还未进行技术参数收集")
            return False

        # 所有阶段都完成时才跳过
        logger.info("所有参数收集阶段已完成，可以跳过澄清")
        return True

    def _is_new_requirement(self, state: WorkflowState) -> bool:
        """检查是否是新的需求（修复版）"""
        # 获取最新的用户消息
        user_messages = [msg for msg in state.messages if msg.role == "user"]
        if len(user_messages) < 2:
            return False

        latest_message = user_messages[-1].content.lower()

        # 🔧 关键修复：如果正在等待参数澄清，不应该判断为新需求
        if state.metadata.get("awaiting_clarification", False):
            return False

        # 🔧 修复：检查是否是参数澄清的回复
        # 如果上一条消息是助手的澄清问题，当前消息就是参数回复，不是新需求
        if len(state.messages) >= 2:
            prev_message = state.messages[-2]
            if prev_message.role == "assistant" and any(keyword in prev_message.content for keyword in
                                                        ["请提供", "需要了解", "参数收集", "请回答", "选择或输入"]):
                return False

        # 新需求的关键词（移除过于宽泛的"监测"）
        new_requirement_keywords = [
            "我想监测", "我需要监测", "我想要监测",  # 添加"我想要监测"
            "帮我设计", "换一个", "重新设计",
            "另外", "还想", "改为监测",
            "请为我规划", "请规划", "请帮我监测",
            "监测.*的.*情况",  # 新增：匹配"监测XX的XX情况"模式
        ]

        # 🔧 新增：如果最新消息包含地名和监测目标，且与之前不同，也视为新需求
        if len(user_messages) >= 2:
            previous_message = user_messages[-2].content.lower()
            # 检查是否提到了不同的地点
            if ("柬埔寨" in latest_message and "柬埔寨" not in previous_message) or \
                    ("农业" in latest_message and "水质" in previous_message):
                return True

        return any(keyword in latest_message for keyword in new_requirement_keywords)

    def apply_smart_defaults(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """应用智能默认值 - 增强版"""
        monitoring_target = params.get("monitoring_target", "")
        observation_area = params.get("observation_area", "")
        # 获取智能默认值配置
        smart_defaults = self.parameters_config.get("smart_defaults", {})
        # 🆕 新增：覆盖范围默认值
        if "coverage_range" not in params:
            if "observation_area" in params:
                area = params["observation_area"]
                # 根据地点类型设置默认范围
                if "湖" in area or "水库" in area:
                    params["coverage_range"] = "whole_lake"
                elif "市" in area:
                    params["coverage_range"] = "urban_area"
                elif "县" in area or "区" in area:
                    params["coverage_range"] = "regional"
                elif "省" in area or any(country in area for country in ["柬埔寨", "越南", "泰国"]):
                    params["coverage_range"] = "large"
                else:
                    params["coverage_range"] = "regional"  # 默认区域范围
        # 查找匹配的默认值
        defaults = smart_defaults.get("default", {})
        for target_keyword, target_defaults in smart_defaults.items():
            if target_keyword in monitoring_target and target_keyword != "default":
                defaults = target_defaults
                logger.info(f"应用 {target_keyword} 的智能默认值")
                break

        # 只为缺失的技术参数添加默认值
        tech_params = ["spatial_resolution", "spectral_bands", "analysis_requirements",
                       "accuracy_requirements", "time_criticality", "weather_dependency",
                       "output_format"]

        for param_key in tech_params:
            if param_key not in params and param_key in defaults:
                params[param_key] = defaults[param_key]
                logger.info(f"添加默认值: {param_key} = {defaults[param_key]}")

        return params

    def _build_smart_clarification_message(questions: List[Dict], existing_params: Dict) -> str:
        """构建分类清晰的澄清消息"""
        # 按类别分组问题
        categories = {
            "monitoring_target": [],
            "monitoring_area": [],
            "monitoring_time": [],
            "technical_params": []
        }

        for question in questions:
            category = question.get("category", "technical_params")
            if category in categories:
                categories[category].append(question)

        # 构建消息
        message = "🤖 为了设计最适合的虚拟星座方案，我需要了解以下信息：\n\n"

        # 显示已收集的参数
        if existing_params:
            message += "✅ **已了解的信息**：\n"
            param_names = {
                "monitoring_target": "监测目标",
                "observation_area": "监测区域",
                "observation_frequency": "观测频率",
                "monitoring_period": "监测周期"
            }
            for key, value in existing_params.items():
                if key in param_names:
                    message += f"• {param_names[key]}: {value}\n"
            message += "\n"

        # 核心参数部分
        core_categories = ["monitoring_target", "monitoring_area", "monitoring_time"]
        has_core_questions = any(categories[cat] for cat in core_categories)

        if has_core_questions:
            message += "### 🔴 必需信息\n\n"

            question_number = 1
            for cat_key in core_categories:
                if categories[cat_key]:
                    cat_name = {
                        "monitoring_target": "监测目标",
                        "monitoring_area": "监测区域",
                        "monitoring_time": "监测时间要求"
                    }.get(cat_key, cat_key)

                    if len(categories[cat_key]) == 1:
                        question = categories[cat_key][0]
                        message += f"**{question_number}. {question['prompt']}**\n"

                        if question.get('examples'):
                            message += f"   例如：{' | '.join(question['examples'][:3])}\n"
                        elif question.get('options'):
                            message += "   选项：\n"
                            for opt in question['options'][:4]:
                                message += f"   • {opt}\n"

                        message += "\n"
                        question_number += 1
                    else:
                        # 多个相关问题合并显示
                        message += f"**{question_number}. {cat_name}**\n"
                        for q in categories[cat_key]:
                            message += f"   • {q['name']}: {q.get('examples', [''])[0] if q.get('examples') else '请填写'}\n"
                        message += "\n"
                        question_number += 1

        # 技术参数部分（可选）
        if categories["technical_params"]:
            message += "### 🟡 可选信息（提供后能优化方案）\n\n"
            for i, question in enumerate(categories["technical_params"],
                                         len([q for cat in core_categories for q in categories[cat]]) + 1):
                message += f"**{i}. {question['prompt']}**\n"
                if question.get('options'):
                    message += f"   选项：{' | '.join(question['options'][:3])}\n"
                message += "\n"

        # 添加提示
        message += "\n💡 **回答提示**：\n"
        message += "• 请回答必需信息，技术参数可选填\n"
        message += "• 您可以逐一回答，也可以用一句话描述所有需求\n"
        message += "• 输入「跳过技术参数」将使用智能推荐的技术配置\n"

        # 添加示例
        message += "\n**回答示例**：\n"
        message += "「我需要监测青海湖的水质变化，每周观测2次，持续6个月」"

        return message

    async def parse_user_response(self, response: str, pending_questions: List[Dict]) -> Dict[str, Any]:
        """解析用户回复 - AI增强版"""

        parsed_params = {}

        if self.ai_mode_enabled:
            try:
                # 使用九州模型分析用户回复
                ai_analysis = await self.jiuzhou_manager.analyze_user_response(
                    response,
                    pending_questions
                )

                parsed_params = ai_analysis.get('parsed_parameters', {})
                skip_remaining = ai_analysis.get('skip_remaining', False)

                logger.info(f"AI解析用户回复: {parsed_params}")

                # 如果AI没有解析出参数，尝试规则方法
                if not parsed_params:
                    parsed_params = self._parse_response_by_rules(response, pending_questions)

                return {
                    'parameters': parsed_params,
                    'skip_remaining': skip_remaining
                }

            except Exception as e:
                logger.error(f"AI解析失败，使用规则方法: {e}")

        # 使用规则方法解析
        parsed_params = self._parse_response_by_rules(response, pending_questions)
        skip_remaining = self._check_skip_remaining(response)

        return {
            'parameters': parsed_params,
            'skip_remaining': skip_remaining
        }

    def _parse_response_by_rules(self, response: str, questions: List[Dict]) -> Dict[str, Any]:
        """基于规则解析用户回复 - 增强版：支持自定义输入和完整选项匹配"""
        parsed = {}
        response_lower = response.lower()

        # 检查是否明确要跳过
        if any(skip_word in response_lower for skip_word in
               ["跳过技术参数", "技术参数用默认", "使用推荐参数", "使用默认值"]):
            return parsed

        # 🔧 关键修复：先尝试精确匹配选项
        for question in questions:
            param_key = question['parameter_key']

            # 如果问题有选项，先尝试精确匹配
            if question.get('options'):
                for option in question['options']:
                    if isinstance(option, dict):
                        # 完整匹配选项的value或label
                        if option['value'] in response or option['label'] in response:
                            parsed[param_key] = option['value']
                            logger.info(f"精确匹配到选项: {param_key} = {option['value']}")
                            break
                    else:
                        # 简单选项的匹配
                        if str(option) in response:
                            parsed[param_key] = option
                            break

        # 如果已经通过精确匹配找到了所有参数，直接返回
        if len(parsed) == len(questions):
            return parsed

        # 对于没有匹配到的参数，继续使用原有的规则
        for question in questions:
            param_key = question['parameter_key']

            # 如果已经匹配过，跳过
            if param_key in parsed:
                continue

            # 1. 尝试按分隔符解析（支持多种分隔符）
            delimiters = [' | ', '|', '，', ',', '；', ';', '\n']
            parts = [response]

            for delimiter in delimiters:
                if delimiter in response:
                    parts = response.split(delimiter)
                    break

            # 2. 如果分割后的部分数量与问题数量匹配，按顺序匹配
            if len(parts) == len(questions):
                for i, part in enumerate(parts):
                    if i < len(questions) and questions[i]['parameter_key'] not in parsed:
                        parsed[questions[i]['parameter_key']] = part.strip()
            else:
                # 3. 否则，尝试智能匹配每个参数
                # 检查是否有明确的参数标记
                param_patterns = [
                    f"{question.get('parameter_name', param_key)}[:：]\\s*(.+?)(?=\\s*(?:{question.get('parameter_name', param_key)}|$))",
                    f"{param_key}[:：]\\s*(.+?)(?=\\s*(?:{param_key}|$))",
                ]

                for pattern in param_patterns:
                    match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                    if match:
                        value = match.group(1).strip()
                        # 清理值（去除多余的标点符号）
                        value = re.sub(r'[。，,;；]+$', '', value)
                        parsed[param_key] = value
                        break

                # 如果没有找到，使用更宽松的匹配
                if param_key not in parsed:
                    value = self._extract_param_value_from_response(response, question)
                    if value:
                        parsed[param_key] = value

        # 4. 验证和后处理
        for param_key, value in list(parsed.items()):
            # 清理值
            value = value.strip()

            # 如果值太短或无意义，删除
            if len(value) < 2 or value in ['是', '否', '好', '可以']:
                del parsed[param_key]

        return parsed

    def _extract_param_value_from_response(self, response: str, question: Dict) -> Optional[str]:
        """从响应中提取特定参数的值 - 增强版"""
        param_key = question['parameter_key']
        response_lower = response.lower()

        # 🔧 特殊处理覆盖范围参数
        if param_key == "coverage_range":
            # 覆盖范围的各种模式
            coverage_patterns = [
                # 完整描述模式
                r'(覆盖[^，。,;；\n]+(?:,|，)[^，。,;；\n]+)',
                r'(覆盖约?\d+万?平方公里[^，。,;；\n]*)',
                # 面积+描述模式
                r'(\d+万?平方公里[^，。,;；\n]*)',
                # 描述性模式
                r'(全[^，。,;；\n]+范围[^，。,;；\n]*)',
                r'(整个[^，。,;；\n]+)',
                # 英文模式
                r'(whole_lake|key_areas|sample_points|custom|city|urban_area|downtown|key_districts|county|town_centers|national|capital_region|key_provinces|border_areas|large|regional|local|field|point)',
            ]

            for pattern in coverage_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        # 根据参数类型使用不同的提取策略
        elif param_key == "observation_area":
            # 提取地名
            location_patterns = [
                r'([^省]+省|[^市]+市|[^区]+区|[^县]+县|[^湖]+湖|[^江]+江|[^河]+河)',
                r'(柬埔寨|越南|泰国|老挝|缅甸|马来西亚|新加坡|印度尼西亚|菲律宾)',
                r'(青海湖|长江|黄河|太湖|洞庭湖|鄱阳湖|珠江)'
            ]
            for pattern in location_patterns:
                match = re.search(pattern, response)
                if match:
                    return match.group(1)

        elif param_key == "observation_frequency":

            # 提取频率

            freq_patterns = {

                r'每小时': '每小时1次',

                r'每天|每日': '每天1次',

                r'每(\d+)天': lambda m: f'每{m.group(1)}天1次',

                r'每周(\d+)次': lambda m: f'每周{m.group(1)}次',

                r'每周': '每周1次',

                r'每月(\d+)次': lambda m: f'每月{m.group(1)}次',

                r'每月': '每月1次',

                r'实时': '每小时1次',

                r'每隔(\d+)天': lambda m: f'每{m.group(1)}天1次',

                r'(\d+)天一次': lambda m: f'每{m.group(1)}天1次'

            }

            for pattern, handler in freq_patterns.items():

                match = re.search(pattern, response_lower)

                if match:

                    if callable(handler):
                        return handler(match)

                    return handler

        elif param_key == "monitoring_period":
            # 提取周期
            period_patterns = {
                r'(\d+)\s*个?月': lambda m: f'{m.group(1)}个月',
                r'(\d+)\s*年': lambda m: f'{m.group(1)}年',
                r'半年': '6个月',
                r'一年': '1年',
                r'长期': '长期监测'
            }
            for pattern, handler in period_patterns.items():
                match = re.search(pattern, response_lower)
                if match:
                    if callable(handler):
                        return handler(match)
                    return handler

        elif param_key == "monitoring_target":
            # 提取监测目标
            target_keywords = {
                "水质": ["水质", "水体", "水污染", "富营养化"],
                "农业监测": ["农业", "农作物", "作物", "种植"],
                "城市扩张": ["城市", "城镇", "建筑", "扩张"],
                "植被覆盖": ["植被", "森林", "绿化", "草地"],
                "灾害监测": ["灾害", "洪水", "火灾", "应急"]
            }
            for target, keywords in target_keywords.items():
                if any(kw in response_lower for kw in keywords):
                    return target

        # 检查选项匹配（作为后备方案）
        if question.get('options'):
            for option in question['options']:
                if isinstance(option, dict):
                    # 部分匹配选项内容
                    if option['value'] in response or option['label'] in response:
                        return option['value']
                    # 检查描述中的关键词
                    if option.get('description') and any(word in response for word in option['description'].split()):
                        return option['value']
                else:
                    if str(option).lower() in response_lower:
                        return option

        return None


    def _check_skip_remaining(self, response: str) -> bool:
        """检查是否跳过剩余问题 - 增强版：支持跳过技术参数"""
        skip_phrases = [
            "跳过", "默认", "推荐", "自动", "快速生成",
            "不用问了", "直接生成", "都行", "随便",
            "跳过技术参数", "技术参数用默认", "使用推荐参数"
        ]

        response_lower = response.lower()
        return any(phrase in response_lower for phrase in skip_phrases)

    async def generate_dynamic_options(self, param: Dict[str, Any], state: WorkflowState) -> List[Dict[str, str]]:
        """根据参数类型和上下文动态生成选项"""
        param_key = param["key"]
        param_name = param["name"]

        # 获取用户上下文
        user_messages = [msg.content for msg in state.messages if msg.role == "user"]
        user_context = " ".join(user_messages) if user_messages else ""

        # 已收集的参数
        existing_params = state.metadata.get("extracted_parameters", {})

        try:
            # 使用九州模型生成智能选项
            if self.ai_mode_enabled and self.jiuzhou_manager:
                options = await self._generate_ai_dynamic_options(
                    param_key, param_name, user_context, existing_params
                )
                if options:
                    return options
        except Exception as e:
            logger.error(f"AI生成动态选项失败: {e}")

        # 回退到规则生成
        return self._generate_rule_based_options(param_key, param_name, user_context, existing_params)

    async def _generate_ai_dynamic_options(
            self,
            param_key: str,
            param_name: str,
            user_context: str,
            existing_params: Dict
    ) -> List[Dict[str, str]]:
        """使用AI生成动态选项 - 改用DeepSeek，包含分析需求参数"""

        # 添加参数详细说明，避免AI混淆 - 扩展版本
        param_descriptions = {
            "observation_frequency": {
                "name": "观测频率",
                "description": "指卫星过境拍摄的频率，即多久获取一次新的遥感影像数据",
                "unit": "次/时间段",
                "examples": "每天1次、每周1次、每月1次"
            },
            "monitoring_period": {
                "name": "监测周期",
                "description": "指整个监测项目的持续时间，即从开始到结束的总时长",
                "unit": "时间长度",
                "examples": "3个月、6个月、1年、长期监测"
            },
            "observation_area": {
                "name": "观测区域",
                "description": "需要监测的具体地理位置，如城市名、湖泊名、省份名等",
                "unit": "地名",
                "examples": "青海湖、北京市、长江流域、柬埔寨",
                "special_instruction": "请生成具体的地理位置选项，不要生成面积范围"
            },
            "spatial_resolution": {
                "name": "空间分辨率",
                "description": "指遥感影像上一个像素代表的地面实际距离",
                "unit": "米",
                "examples": "高分辨率(<5米)、中分辨率(5-30米)"
            },
            "analysis_requirements": {
                "name": "分析需求",
                "description": "指需要对遥感数据进行的具体分析类型和方法",
                "unit": "分析类型",
                "examples": "变化检测、分类识别、定量反演、趋势分析、异常检测",
                "context_mapping": {
                    "水质监测": ["定量反演", "变化检测", "异常检测", "趋势分析"],
                    "农业监测": ["分类识别", "参数提取", "变化检测", "产量预测", "病虫害监测"],
                    "城市监测": ["变化检测", "目标识别", "热岛分析", "违建监测"],
                    "灾害应急": ["灾害识别", "损失评估", "风险分析", "应急响应"],
                    "环境监测": ["污染监测", "生态评估", "碳排放", "生物多样性"]
                }
            },
            "accuracy_requirements": {
                "name": "精度要求",
                "description": "指对分析结果准确性的具体要求和质量标准",
                "unit": "精度百分比",
                "examples": "科研级(>95%)、业务级(85-95%)、应用级(70-85%)"
            },
            "spectral_bands": {
                "name": "光谱波段",
                "description": "不同波段的电磁波用于不同的监测目的",
                "unit": "波段类型",
                "examples": "可见光、多光谱、热红外、雷达"
            },
            "output_format": {
                "name": "输出格式",
                "description": "最终交付给用户的数据产品和报告格式",
                "unit": "格式类型",
                "examples": "遥感影像、专题图、分析报告、实时预警"
            }
        }

        # 获取参数的详细说明
        param_info = param_descriptions.get(param_key, {
            "name": param_name,
            "description": "",
            "unit": "",
            "examples": ""
        })

        system_prompt = """你是一个虚拟星座设计专家，擅长根据用户需求生成合适的参数选项。
    请严格按照参数的定义生成选项，避免混淆不同参数的含义。

    特别注意各参数的区别：
    - 观测频率：指多久拍摄一次，如"每天1次"
    - 监测周期：指项目总时长，如"3个月"、"1年"
    - 观测区域：指具体的地理位置名称，如"青海湖"、"北京市"、"长江流域"
    - 分析需求：指要进行的数据分析类型，如"变化检测"、"分类识别"
    - 精度要求：指对分析结果准确性的要求
    
    请确保生成的选项符合参数的实际含义，不要混淆。"""

        prompt = f"""为虚拟星座参数生成合适的选项。

        参数详细信息：
        - 参数键：{param_key}
        - 参数名称：{param_info['name']}
        - 参数含义：{param_info['description']}
        - 单位/格式：{param_info['unit']}
        - 示例：{param_info['examples']}

        用户需求：{user_context}
        已收集参数：{json.dumps(existing_params, ensure_ascii=False)}

        🔧 重要提示：
        1. 根据参数类型和用户场景，智能决定选项数量：
           - 通常3-4个选项即可
        2. 选项要有明显的数量级差异，能够涵盖用户场景的大部分情况，并避免过于相似的选项
        3. 确保选项按照从高到低（频率）或从短到长（周期）的顺序排列
        4. 每个选项的说明要突出其适用场景，此外值和说明必须都是中文，且专业

        输出格式：
        {{
            "options": [
                {{"value": "选项值", "label": "和value保持一致", "description": "选项说明"}},
                ...
            ],
            "default_option": "推荐的默认选项值"
        }}"""

        # 特别处理分析需求参数
        if param_key == "analysis_requirements":
            monitoring_target = existing_params.get("monitoring_target", "")
            prompt += f"""
    特别针对分析需求参数：
    - 这是数据分析类型参数，不是频率、周期或分辨率
    - 需要根据监测目标"{monitoring_target}"生成合适的分析方法
    - 可选的分析类型包括：{param_info.get('examples', '')}

    基于监测目标的推荐分析需求："""

            # 根据监测目标添加具体建议
            context_mapping = param_info.get('context_mapping', {})
            for target_type, analysis_types in context_mapping.items():
                if target_type in monitoring_target:
                    prompt += f"\n- 对于{target_type}，推荐：{', '.join(analysis_types)}"

        # 特别处理覆盖范围参数
        if param_key == "coverage_range":
            observation_area = existing_params.get("observation_area", "")
            prompt += f"""
    特别针对覆盖范围参数：
    - 观测区域是：{observation_area}
    - 请根据该区域的特点生成合适的覆盖范围选项
    - 🔧 重要：每个选项的value必须同时包含数值范围和描述性表述
    - 格式示例：
      - "覆盖流域面积约200平方公里"
      - "山谷地区南北跨度约约200公里"

    生成原则：
    1. 根据观测区域的实际大小，提供合理的数值范围
    2. 每个选项必须包含具体的平方公里数值或范围
    3. 同时包含描述性说明（如全覆盖、重点区域、采样点位等）
    4. 对于湖泊、城市、省份等不同类型的区域，提供符合实际的面积选项
    5. 提供3-4个不同量级的选项，从小到大排列"""

        if param_key == "observation_area":
            monitoring_target = existing_params.get("monitoring_target", "")
            prompt += f"""

        特别针对观测区域参数：
        - 这是地理位置参数，不是范围大小
        - 必须生成具体的地名，如城市名、湖泊名、河流名、省份名、国家名等
        - 不要生成面积、范围描述（如"100平方公里"、"大范围"等）
        - 根据监测目标"{monitoring_target}"生成相关的地理位置选项

        生成要求：
        1. 每个选项必须是具体的地理名称
        2. 优先考虑与监测目标相关的典型地点
        3. 提供不同规模的地理位置（如湖泊、城市、省份）
        4. 如果用户提到了某个地区，优先推荐该地区的具体地点

        示例格式：
        - 湖泊类：青海湖、太湖、洞庭湖
        - 城市类：北京市、上海市、深圳市
        - 流域类：长江流域、黄河流域、珠江流域
        - 省份类：浙江省、广东省、江苏省
        - 国家类：柬埔寨、越南、泰国"""

        prompt += f"""

    生成选项的严格要求：
    1. 必须符合该参数的实际含义：{param_info['description']}
    2. 针对"{param_info['name']}"生成3-4个合适的选项
    3. 每个选项要有清晰的值和说明
    4. 根据用户的具体需求（如{existing_params.get('monitoring_target', '监测需求')}）定制选项

    输出格式：
    {{
        "options": [
            {{"value": "选项值", "label": "和value保持一致", "description": "选项说明"}},
            {{"value": "选项值2", "label": "和value保持一致", "description": "选项说明2"}}
        ],
        "default_option": "推荐的默认选项值"
    }}"""

        try:
            # 使用DeepSeek生成选项
            if self.use_deepseek_for_options:
                response = await self._call_deepseek_api(prompt, system_prompt, max_tokens=800)
                print(response)
                if response:
                    result = self._parse_ai_options_response(response)
                    if result:
                        # 添加选项验证
                        validated_result = self._validate_options_for_param(result, param_key)
                        logger.info(f"DeepSeek成功生成 {len(validated_result)} 个选项 for {param_name}")
                        return validated_result
                    else:
                        logger.warning("DeepSeek生成的选项解析失败，使用规则方法")
                else:
                    logger.warning("DeepSeek未返回有效响应，使用规则方法")

        except Exception as e:
            logger.error(f"AI生成选项出错: {e}")
            import traceback
            logger.error(traceback.format_exc())

        # 回退到规则生成
        return []

    def _validate_and_optimize_options(self, options: List[Dict[str, str]], param_key: str) -> List[Dict[str, str]]:
        """验证和优化选项列表"""

        if param_key == "observation_frequency":
            # 确保频率选项有合理的量级差异
            frequency_order = {
                "每小时1次": 24,
                "每3小时1次": 8,
                "每6小时1次": 4,
                "每12小时1次": 2,
                "每天1次": 1,
                "每2天1次": 0.5,
                "每3天1次": 0.33,
                "每5天1次": 0.2,
                "每周1次": 0.14,
                "每周2次": 0.29,  # 修正：每周2次应该是大约0.29次/天
                "每10天1次": 0.1,
                "每两周1次": 0.07,
                "每月2次": 0.067,
                "每月1次": 0.033
            }

            # 移除过于相似的选项
            filtered_options = []
            last_frequency = None

            for option in sorted(options, key=lambda x: frequency_order.get(x['value'], 0), reverse=True):
                current_frequency = frequency_order.get(option['value'], 0)

                # 确保频率差异至少有2倍（更大的差异）
                if last_frequency is None or last_frequency / current_frequency >= 2:
                    filtered_options.append(option)
                    last_frequency = current_frequency

            # 限制选项数量为3-4个
            if len(filtered_options) > 4:
                # 选择分布最均匀的4个选项
                step = len(filtered_options) // 4
                filtered_options = filtered_options[::step][:4]

            return filtered_options

        elif param_key == "monitoring_period":
            # 确保周期选项有合理的时长差异
            period_order = {
                "1周": 0.25,
                "2周": 0.5,
                "1个月": 1,
                "2个月": 2,
                "3个月": 3,
                "6个月": 6,
                "9个月": 9,
                "1年": 12,
                "2年": 24,
                "长期监测": 999,
                "完整生长季": 8,  # 特殊处理
                "下一生长季": 8
            }

            # 类似的过滤逻辑
            filtered_options = []
            last_period = None

            for option in sorted(options, key=lambda x: period_order.get(x['value'], 0)):
                current_period = period_order.get(option['value'], 0)

                # 确保周期差异至少有1.5倍
                if last_period is None or current_period / last_period >= 1.5:
                    filtered_options.append(option)
                    last_period = current_period

            return filtered_options[:4]  # 监测周期通常3-4个选项即可

        # 其他参数类型直接返回
        return options


    def _validate_options_for_param(self, options: List[Dict[str, str]], param_key: str) -> List[Dict[str, str]]:
        """验证生成的选项是否符合参数定义 - 扩展版本"""
        validated_options = []

        for option in options:
            value = option.get('value', '')
            label = option.get('label', '')

            # 对观测频率进行验证
            if param_key == "observation_frequency":
                frequency_keywords = ['次', '每天', '每周', '每月', '每小时', '实时']
                if any(keyword in value or keyword in label for keyword in frequency_keywords):
                    validated_options.append(option)
                else:
                    logger.warning(f"过滤掉不符合观测频率定义的选项: {value}")

            # 对监测周期进行验证
            elif param_key == "monitoring_period":
                period_keywords = ['个月', '年', '周', '天', '长期', '短期', '季']
                frequency_exclusions = ['每天', '每周', '每月', '次']

                has_period_keyword = any(keyword in value or keyword in label for keyword in period_keywords)
                has_frequency_keyword = any(keyword in value or keyword in label for keyword in frequency_exclusions)

                if has_period_keyword and not has_frequency_keyword:
                    validated_options.append(option)
                else:
                    logger.warning(f"过滤掉不符合监测周期定义的选项: {value}")

            # 🆕 对分析需求进行验证
            elif param_key == "analysis_requirements":
                analysis_keywords = [
                    '检测', '识别', '分类', '反演', '分析', '监测', '评估',
                    '提取', '预测', '预警', '变化', '趋势', '异常', '目标',
                    '定量', '定性', '参数', '算法', '模型'
                ]
                # 排除不相关的词汇
                exclusion_keywords = ['频率', '周期', '分辨率', '时间', '米', '次']

                has_analysis_keyword = any(keyword in value or keyword in label for keyword in analysis_keywords)
                has_exclusion_keyword = any(keyword in value or keyword in label for keyword in exclusion_keywords)

                if has_analysis_keyword and not has_exclusion_keyword:
                    validated_options.append(option)
                else:
                    logger.warning(f"过滤掉不符合分析需求定义的选项: {value}")

            # 🆕 对精度要求进行验证
            elif param_key == "accuracy_requirements":
                accuracy_keywords = ['%', '精度', '级', '准确', '质量', '标准']
                if any(keyword in value or keyword in label for keyword in accuracy_keywords):
                    validated_options.append(option)
                else:
                    logger.warning(f"过滤掉不符合精度要求定义的选项: {value}")

            # 🆕 对输出格式进行验证
            elif param_key == "output_format":
                format_keywords = [
                    '图', '表', '报告', '数据', '影像', '产品', '文件',
                    '预警', '接口', '系统', '专题', '统计', '分析'
                ]
                if any(keyword in value or keyword in label for keyword in format_keywords):
                    validated_options.append(option)
                else:
                    logger.warning(f"过滤掉不符合输出格式定义的选项: {value}")

            # 🆕 对光谱波段进行验证
            elif param_key == "spectral_bands":
                spectral_keywords = [
                    '光', '波段', '光谱', '红外', '可见', '雷达', '多光谱',
                    '高光谱', '热红外', 'RGB', 'NIR', 'SWIR'
                ]
                if any(keyword in value or keyword in label for keyword in spectral_keywords):
                    validated_options.append(option)
                else:
                    logger.warning(f"过滤掉不符合光谱波段定义的选项: {value}")

            # 其他参数直接通过
            else:
                validated_options.append(option)

        # 如果验证后没有有效选项，返回空列表让系统使用规则生成
        if not validated_options:
            logger.warning(f"参数 {param_key} 验证后无有效选项，将使用规则生成")

        return validated_options

    def _parse_ai_options_response(self, response: str) -> List[Dict[str, str]]:
        """解析AI生成的选项 - 增强对DeepSeek响应的处理"""
        try:
            import re

            # 记录原始响应以便调试
            logger.debug(f"AI选项原始响应: {response[:500]}...")

            # 清理响应文本
            cleaned_response = response.strip()

            # 尝试直接解析
            try:
                data = json.loads(cleaned_response)
                options = data.get('options', [])

                # 确保选项格式正确
                formatted_options = []
                for opt in options:
                    if isinstance(opt, dict) and 'value' in opt and 'label' in opt:
                        formatted_options.append({
                            'value': str(opt['value']),
                            'label': str(opt['label']),
                            'description': str(opt.get('description', ''))
                        })

                if formatted_options:
                    # 🔧 修复：添加更详细的日志
                    logger.info(f"成功解析 {len(formatted_options)} 个选项")
                    logger.debug(f"选项详情: {formatted_options}")
                    return formatted_options

            except json.JSONDecodeError as e:
                logger.debug(f"直接JSON解析失败: {e}")

                # 如果直接解析失败，尝试提取JSON部分
                json_match = re.search(r'\{[\s\S]*\}', cleaned_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group()

                    # 修复常见的JSON格式问题
                    # 1. 修复缺少逗号的问题
                    json_str = re.sub(r'"\s*\n\s*"', '",\n"', json_str)
                    json_str = re.sub(r'}\s*\n\s*{', '},\n{', json_str)

                    # 2. 修复多余的逗号
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)

                    try:
                        data = json.loads(json_str)
                        options = data.get('options', [])

                        formatted_options = []
                        for opt in options:
                            if isinstance(opt, dict) and 'value' in opt and 'label' in opt:
                                formatted_options.append({
                                    'value': str(opt['value']),
                                    'label': str(opt['label']),
                                    'description': str(opt.get('description', ''))
                                })

                        if formatted_options:
                            # 🔧 修复：添加更详细的日志
                            logger.info(f"通过修复解析到 {len(formatted_options)} 个选项")
                            logger.debug(f"选项详情: {formatted_options}")
                            return formatted_options

                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {e}")

        except Exception as e:
            logger.error(f"解析AI选项响应失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())

        # 返回空列表，让系统使用规则生成的选项
        logger.warning("AI选项解析失败，将使用规则生成的选项")
        return []

    def _generate_rule_based_options(
            self,
            param_key: str,
            param_name: str,
            user_context: str,
            existing_params: Dict
    ) -> List[Dict[str, str]]:
        """基于规则生成动态选项 - 改进版"""

        options = []

        # 监测目标
        monitoring_target = existing_params.get("monitoring_target", "")
        observation_area = existing_params.get("observation_area", "")
        # === 新增：分析需求参数处理 ===
        if param_key == "analysis_requirements":
            # 根据监测目标生成分析需求选项
            if "水质" in monitoring_target or "水体" in monitoring_target:
                options = [
                    {"value": "定量反演", "label": "定量反演",
                     "description": "精确计算水质参数（叶绿素a、悬浮物、透明度等），适合科研和精准监测"},
                    {"value": "变化检测", "label": "变化检测",
                     "description": "追踪水质时空变化趋势，发现污染源和扩散路径"},
                    {"value": "异常检测", "label": "异常检测",
                     "description": "及时发现水华、污染等异常事件，支持预警决策"},
                    {"value": "分类识别", "label": "分类识别",
                     "description": "区分不同水体类型和水质等级，支持分级管理"},
                    {"value": "趋势分析", "label": "趋势分析",
                     "description": "基于历史数据预测未来水质变化，支持长期规划"}
                ]
            elif "农业" in monitoring_target or "作物" in monitoring_target or "植被" in monitoring_target:
                options = [
                    {"value": "分类识别", "label": "作物分类识别", "description": "不同作物类型自动识别和分布制图"},
                    {"value": "参数提取", "label": "生长参数提取", "description": "LAI、NDVI、生物量等植被参数反演"},
                    {"value": "变化检测", "label": "生长变化检测", "description": "作物生长状态和物候期变化监测"},
                    {"value": "产量预测", "label": "产量预测", "description": "基于遥感数据的作物产量估算"},
                    {"value": "病虫害监测", "label": "病虫害监测", "description": "作物病虫害早期识别和分布监测"},
                    {"value": "精准农业", "label": "精准农业分析", "description": "田块级精细化管理分析"}
                ]
            elif "城市" in monitoring_target or "建筑" in monitoring_target:
                options = [
                    {"value": "变化检测", "label": "城市扩张检测", "description": "城市建设用地变化和扩张分析"},
                    {"value": "目标识别", "label": "建筑物识别", "description": "建筑物自动提取和分类"},
                    {"value": "热岛分析", "label": "热岛效应分析", "description": "城市热岛强度分布和变化分析"},
                    {"value": "人口估算", "label": "人口密度估算", "description": "基于建筑密度的人口分布估算"},
                    {"value": "违建监测", "label": "违章建筑监测", "description": "新增违章建筑自动发现"}
                ]
            elif "灾害" in monitoring_target or "应急" in monitoring_target:
                options = [
                    {"value": "灾害识别", "label": "灾害识别", "description": "洪水、火灾、滑坡等灾害自动识别"},
                    {"value": "损失评估", "label": "损失评估", "description": "灾害损失范围和程度评估"},
                    {"value": "风险分析", "label": "风险分析", "description": "灾害易发区识别和风险等级划分"},
                    {"value": "应急响应", "label": "应急响应", "description": "实时灾情监测和应急决策支持"},
                    {"value": "恢复监测", "label": "恢复监测", "description": "灾后恢复重建进展监测"}
                ]
            elif "环境" in monitoring_target:
                options = [
                    {"value": "污染监测", "label": "污染监测", "description": "大气、水体、土壤污染源识别和扩散分析"},
                    {"value": "生态评估", "label": "生态系统评估", "description": "生态系统健康状况和服务功能评估"},
                    {"value": "碳排放", "label": "碳排放监测", "description": "碳源汇识别和碳排放量估算"},
                    {"value": "生物多样性", "label": "生物多样性", "description": "栖息地质量和生物多样性评估"}
                ]
            else:
                # 通用分析需求选项
                options = [
                    {"value": "变化检测", "label": "变化检测", "description": "时间序列变化分析和趋势识别"},
                    {"value": "分类识别", "label": "分类识别", "description": "地物类型自动分类和制图"},
                    {"value": "目标识别", "label": "目标识别", "description": "特定目标的自动识别和提取"},
                    {"value": "定量反演", "label": "定量参数反演", "description": "物理参数定量计算和反演"},
                    {"value": "异常检测", "label": "异常检测", "description": "异常事件和突发状况识别"},
                    {"value": "趋势分析", "label": "趋势分析", "description": "长期变化趋势和规律分析"}
                ]
        if param_key == "observation_area":
            # 从用户上下文中提取可能的地理位置
            possible_locations = []

            # 1. 尝试从用户上下文中提取地名
            # 国家级
            countries = ["柬埔寨", "越南", "泰国", "老挝", "缅甸", "马来西亚", "新加坡", "印度尼西亚", "菲律宾", "中国"]
            for country in countries:
                if country in user_context and country not in possible_locations:
                    possible_locations.append(country)

            # 中国省级行政区
            provinces = ["北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
                         "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
                         "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海",
                         "内蒙古", "广西", "西藏", "宁夏", "新疆"]
            for province in provinces:
                if province in user_context and province not in possible_locations:
                    possible_locations.append(province)

            # 著名地理位置
            famous_locations = ["青海湖", "太湖", "洞庭湖", "鄱阳湖", "长江", "黄河", "珠江",
                                "秦岭", "太行山", "昆仑山", "天山", "祁连山",
                                "华北平原", "长三角", "珠三角", "京津冀", "成渝地区"]
            for location in famous_locations:
                if location in user_context and location not in possible_locations:
                    possible_locations.append(location)

            # 2. 根据监测目标推荐相关地理位置
            if "水质" in monitoring_target or "水体" in monitoring_target:
                # 推荐著名湖泊和河流
                water_locations = ["青海湖", "太湖", "洞庭湖", "鄱阳湖", "滇池", "长江流域", "黄河流域"]
                for loc in water_locations[:3]:  # 只取前3个
                    if loc not in possible_locations:
                        possible_locations.append(loc)

            elif "农业" in monitoring_target or "作物" in monitoring_target:
                # 推荐农业主产区
                agri_locations = ["东北平原", "华北平原", "长江中下游平原", "河南省", "山东省", "江苏省"]
                for loc in agri_locations[:3]:
                    if loc not in possible_locations:
                        possible_locations.append(loc)

            elif "城市" in monitoring_target:
                # 推荐主要城市
                city_locations = ["北京市", "上海市", "广州市", "深圳市", "成都市", "武汉市"]
                for loc in city_locations[:3]:
                    if loc not in possible_locations:
                        possible_locations.append(loc)

            # 3. 如果找到了可能的地点，生成选项
            if possible_locations:
                for i, location in enumerate(possible_locations[:5]):  # 最多显示5个选项
                    # 根据地点类型添加描述
                    description = ""
                    if "湖" in location:
                        description = "湖泊水体监测"
                    elif "江" in location or "河" in location:
                        description = "河流流域监测"
                    elif "省" in location or "市" in location:
                        description = "行政区域监测"
                    elif "平原" in location:
                        description = "大范围区域监测"
                    elif location in countries:
                        description = "国家级大范围监测"
                    else:
                        description = "特定区域监测"

                    options.append({
                        "value": location,
                        "label": location,
                        "description": description
                    })
            # 4. 如果没有找到合适的选项，返回空列表
            # 这样前端会显示纯输入框
            return options
        # 🔧 改进：覆盖范围选项生成 - 现在可以基于已知的observation_area
        if param_key == "coverage_range":
            # 根据观测区域类型智能推荐范围
            if observation_area:  # 🔧 关键：现在observation_area已经被收集了
                if "湖" in observation_area or "水库" in observation_area:
                    options = [
                        {"value": "whole_lake", "label": "整个湖面", "description": f"覆盖整个{observation_area}范围"},
                        {"value": "key_areas", "label": "关键水域（50-70%）",
                         "description": "重点监测区域如入湖口、出湖口"},
                        {"value": "sample_points", "label": "采样点位（10-20%）", "description": "代表性点位监测"},
                        {"value": "custom", "label": "自定义范围", "description": "指定具体的平方公里数"}
                    ]
                elif "市" in observation_area:
                    options = [
                        {"value": "city", "label": f"全{observation_area}范围",
                         "description": f"覆盖整个{observation_area}行政区"},
                        {"value": "urban_area", "label": "建成区（100-500平方公里）", "description": "城市主要建成区"},
                        {"value": "downtown", "label": "中心城区（50-100平方公里）", "description": "城市核心区域"},
                        {"value": "key_districts", "label": "重点区域", "description": "特定开发区或新区"}
                    ]
                elif "县" in observation_area or "区" in observation_area:
                    options = [
                        {"value": "county", "label": f"全{observation_area}范围", "description": f"覆盖整个行政区"},
                        {"value": "town_centers", "label": "乡镇中心（10-50平方公里）", "description": "主要乡镇区域"},
                        {"value": "key_areas", "label": "重点区域", "description": "特定监测区域"},
                        {"value": "custom", "label": "自定义范围", "description": "指定具体范围"}
                    ]
                elif any(country in observation_area for country in ["柬埔寨", "越南", "泰国", "老挝", "缅甸"]):
                    options = [
                        {"value": "national", "label": "全国范围", "description": f"覆盖整个{observation_area}"},
                        {"value": "capital_region", "label": "首都及周边地区", "description": "重点城市区域"},
                        {"value": "key_provinces", "label": "重点省份", "description": "选择特定省份监测"},
                        {"value": "border_areas", "label": "边境地区", "description": "跨境区域监测"}
                    ]
                elif "农业" in monitoring_target:
                    options = [
                        {"value": "large", "label": "大面积农田（>1000平方公里）", "description": "县级或更大范围"},
                        {"value": "regional", "label": "区域农田（100-1000平方公里）", "description": "乡镇级范围"},
                        {"value": "local", "label": "示范区（10-100平方公里）", "description": "农业示范区或试验田"},
                        {"value": "field", "label": "单个地块（<10平方公里）", "description": "精准农业管理"}
                    ]
                else:
                    # 通用选项
                    options = [
                        {"value": "point", "label": "单点监测（<1平方公里）", "description": "特定位置精细监测"},
                        {"value": "local", "label": "局部区域（1-10平方公里）", "description": "小范围监测"},
                        {"value": "regional", "label": "区域范围（10-100平方公里）", "description": "中等范围监测"},
                        {"value": "large", "label": "大范围（>100平方公里）", "description": "大区域监测"}
                    ]
            else:
                # 如果还没有observation_area，提供通用选项
                options = [
                    {"value": "to_be_determined", "label": "待定（需先确定观测区域）",
                     "description": "请先提供观测区域信息"}
                ]

        if param_key == "observation_frequency":
            # 🔧 修改：根据监测目标动态调整频率选项的数量和内容
            if "水质" in monitoring_target:
                # 水质监测需要较高频率
                options = [
                    {"value": "每天1次", "label": "每天1次",
                     "description": "高频监测，适合水质快速变化期如藻类爆发季节"},
                    {"value": "每3天1次", "label": "每3天1次",
                     "description": "中频监测，平衡时效性和成本"},
                    {"value": "每周1次", "label": "每周1次",
                     "description": "常规监测，适合水质相对稳定期"},
                    {"value": "每月2次", "label": "每月2次",
                     "description": "低频监测，适合长期趋势观察"}
                ]
            elif "农业" in monitoring_target or "作物" in monitoring_target:
                # 农业监测根据生长阶段调整
                options = [
                    {"value": "每3天1次", "label": "每3天1次",
                     "description": "关键生育期高频监测"},
                    {"value": "每5天1次", "label": "每5天1次",
                     "description": "生长旺盛期标准监测"},
                    {"value": "每周1次", "label": "每周1次",
                     "description": "常规生长监测"},
                    {"value": "每10天1次", "label": "每10天1次",
                     "description": "成熟期或休眠期监测"}
                ]
            elif "灾害" in monitoring_target or "应急" in monitoring_target:
                # 灾害监测需要超高频率
                options = [
                    {"value": "每小时1次", "label": "每小时1次",
                     "description": "灾害应急实时监测"},
                    {"value": "每3小时1次", "label": "每3小时1次",
                     "description": "准实时灾害跟踪"},
                    {"value": "每6小时1次", "label": "每6小时1次",
                     "description": "高频灾害监测"},
                    {"value": "每天1次", "label": "每天1次",
                     "description": "常规灾害巡查"}
                ]
            elif "城市" in monitoring_target:
                # 城市监测频率相对较低
                options = [
                    {"value": "每周1次", "label": "每周1次",
                     "description": "城市建设动态监测"},
                    {"value": "每周2次", "label": "每周2次",
                     "description": "加密城市变化监测"},
                    {"value": "每月2次", "label": "每月2次",
                     "description": "城市扩张定期监测"},
                    {"value": "每月1次", "label": "每月1次",
                     "description": "城市发展趋势监测"}
                ]
            else:
                # 通用选项 - 提供3-4个合理的频率选项
                options = [
                    {"value": "每天1次", "label": "每天1次",
                     "description": "高频监测，适合快速变化的目标"},
                    {"value": "每3天1次", "label": "每3天1次",
                     "description": "中频监测，平衡效果与成本"},
                    {"value": "每周1次", "label": "每周1次",
                     "description": "常规监测，适合稳定变化的目标"},
                    {"value": "每月2次", "label": "每月2次",
                     "description": "低频监测，适合缓慢变化的目标"}
                ]

        elif param_key == "monitoring_period":
            # 监测周期也根据场景调整选项数量
            current_month = datetime.now().month

            if "水质" in monitoring_target:
                options = [
                    {"value": "3个月", "label": "3个月", "description": "季节性水质变化评估"},
                    {"value": "6个月", "label": "6个月", "description": "半年度水质趋势分析"},
                    {"value": "1年", "label": "1年", "description": "完整年度水文周期监测"},
                    {"value": "长期监测", "label": "长期监测", "description": "建立长期水质数据库"}
                ]
            elif "农业" in monitoring_target:
                # 根据当前月份智能推荐
                if 3 <= current_month <= 10:  # 生长季
                    options = [
                        {"value": "完整生长季", "label": "完整生长季(3-10月)", "description": "覆盖播种到收获全过程"},
                        {"value": "3个月", "label": "关键生育期(3个月)", "description": "重点监测关键生长阶段"},
                        {"value": "全年监测", "label": "全年监测", "description": "包含生长季和休耕期"}
                    ]
                else:  # 非生长季
                    options = [
                        {"value": "下一生长季", "label": "下一生长季(明年3-10月)", "description": "为下季种植做准备"},
                        {"value": "3个月", "label": "土壤准备期(3个月)", "description": "休耕期土壤监测"},
                        {"value": "全年监测", "label": "全年监测", "description": "持续监测土地变化"}
                    ]
            else:
                # 通用选项
                options = [
                    {"value": "1个月", "label": "1个月", "description": "短期试点或紧急监测"},
                    {"value": "3个月", "label": "3个月", "description": "季度项目标准周期"},
                    {"value": "6个月", "label": "6个月", "description": "半年期项目监测"},
                    {"value": "1年", "label": "1年", "description": "年度监测项目"}
                ]

        elif param_key == "spatial_resolution":
            # 空间分辨率选项保持不变
            if "城市" in monitoring_target or "建筑" in monitoring_target:
                options = [
                    {"value": "very_high", "label": "超高分辨率(<1米)", "description": "识别单个建筑物细节"},
                    {"value": "high", "label": "高分辨率(1-5米)", "description": "街道级别精细监测"},
                    {"value": "medium", "label": "中分辨率(5-10米)", "description": "街区级别整体分析"}
                ]
            elif "水质" in monitoring_target:
                options = [
                    {"value": "medium", "label": "中分辨率(10-30米)", "description": "适合大中型水体监测"},
                    {"value": "high", "label": "高分辨率(5-10米)", "description": "小型水体或精细岸线监测"},
                    {"value": "low", "label": "低分辨率(30-100米)", "description": "大型湖泊整体监测"}
                ]
            else:
                options = self._get_default_resolution_options()

        elif param_key == "spectral_bands":
            # 光谱波段选项保持不变
            if "植被" in monitoring_target or "农业" in monitoring_target:
                options = [
                    {"value": "multispectral", "label": "多光谱(含红边)", "description": "植被健康监测最佳选择"},
                    {"value": "hyperspectral", "label": "高光谱", "description": "精细植被分类和参数反演"},
                    {"value": "visible_nir", "label": "可见光+近红外", "description": "基础植被指数计算"}
                ]
            elif "水质" in monitoring_target:
                options = [
                    {"value": "multispectral", "label": "多光谱", "description": "叶绿素、悬浮物等参数监测"},
                    {"value": "thermal", "label": "热红外", "description": "水温分布监测"},
                    {"value": "combined", "label": "多光谱+热红外", "description": "综合水质参数分析"}
                ]
            else:
                options = self._get_default_spectral_options()

        elif param_key == "accuracy_requirements":
            # 精度要求根据分析需求调整
            analysis_req = existing_params.get("analysis_requirements", "")
            if "定量反演" in analysis_req or "参数提取" in analysis_req:
                options = [
                    {"value": "科研级（>95%）", "label": "科研级（>95%）", "description": "适合科学研究和精确参数反演"},
                    {"value": "业务级（85-95%）", "label": "业务级（85-95%）", "description": "适合业务化运营和决策支持"},
                    {"value": "应用级（70-85%）", "label": "应用级（70-85%）", "description": "适合一般应用和趋势分析"}
                ]
            elif "分类识别" in analysis_req:
                options = [
                    {"value": "高精度分类（>90%）", "label": "高精度分类（>90%）", "description": "精细分类和专业制图"},
                    {"value": "标准分类（80-90%）", "label": "标准分类（80-90%）", "description": "常规分类应用"},
                    {"value": "快速分类（>75%）", "label": "快速分类（>75%）", "description": "快速概览和初步分析"}
                ]
            else:
                options = [
                    {"value": "高精度（>90%）", "label": "高精度（>90%）", "description": "精确分析和科学研究"},
                    {"value": "标准精度（80-90%）", "label": "标准精度（80-90%）", "description": "业务应用和决策支持"},
                    {"value": "一般精度（70-80%）", "label": "一般精度（70-80%）", "description": "趋势分析和概况了解"}
                ]

        elif param_key == "output_format":
            # 输出格式根据分析需求调整
            analysis_req = existing_params.get("analysis_requirements", "")
            if "变化检测" in analysis_req:
                options = [
                    {"value": "变化图", "label": "变化检测图", "description": "变化区域标注和统计图表"},
                    {"value": "时间序列图", "label": "时间序列图", "description": "变化趋势曲线和时序分析"},
                    {"value": "专题报告", "label": "变化分析报告", "description": "包含变化统计和原因分析"},
                    {"value": "预警系统", "label": "实时预警", "description": "变化阈值监测和自动预警"}
                ]
            elif "分类识别" in analysis_req:
                options = [
                    {"value": "分类图", "label": "分类专题图", "description": "不同类别色彩编码的分类图"},
                    {"value": "统计表格", "label": "分类统计表", "description": "各类别面积占比统计"},
                    {"value": "精度报告", "label": "分类精度报告", "description": "包含混淆矩阵和精度指标"}
                ]
            else:
                options = [
                    {"value": "遥感影像", "label": "遥感影像", "description": "原始或处理后的卫星影像"},
                    {"value": "专题图", "label": "专题图", "description": "针对特定主题的制图产品"},
                    {"value": "分析报告", "label": "分析报告", "description": "包含图表和文字的综合报告"},
                    {"value": "数据产品", "label": "数据产品", "description": "标准化的数据产品和元数据"}
                ]


        # 如果没有生成选项，返回通用选项
        if not options:
            options = self._get_generic_options(param_key)

        return options

    def _get_default_frequency_options(self) -> List[Dict[str, str]]:
        """默认观测频率选项"""
        return [
            {"value": "每天1次", "label": "每天1次", "description": "日常监测，获取高时间分辨率数据"},
            {"value": "每3天1次", "label": "每3天1次", "description": "中频监测，兼顾时效性和成本"},
            {"value": "每周1次", "label": "每周1次", "description": "常规监测，适合大多数应用场景"},
            {"value": "每月2次", "label": "每月2次", "description": "长期趋势监测，成本效益最优"}
        ]

    def _get_default_period_options(self) -> List[Dict[str, str]]:
        """默认监测周期选项"""
        return [
            {"value": "1个月", "label": "1个月", "description": "短期项目"},
            {"value": "3个月", "label": "3个月", "description": "季度监测"},
            {"value": "6个月", "label": "6个月", "description": "半年项目"},
            {"value": "1年", "label": "1年", "description": "年度监测"}
        ]

    def _get_default_resolution_options(self) -> List[Dict[str, str]]:
        """默认分辨率选项"""
        return [
            {"value": "high", "label": "高分辨率(<5米)", "description": "详细观测"},
            {"value": "medium", "label": "中分辨率(5-30米)", "description": "常规监测"},
            {"value": "low", "label": "低分辨率(>30米)", "description": "大范围观测"}
        ]

    def _get_default_spectral_options(self) -> List[Dict[str, str]]:
        """默认光谱选项"""
        return [
            {"value": "visible", "label": "可见光", "description": "真彩色影像"},
            {"value": "multispectral", "label": "多光谱", "description": "多波段分析"},
            {"value": "radar", "label": "雷达", "description": "全天候观测"}
        ]

    def _get_generic_options(self, param_key: str) -> List[Dict[str, str]]:
        """通用选项生成"""
        # 从配置中获取
        param_config = self.parameters_config.get("parameter_categories", {})

        for category in param_config.values():
            if param_key in category.get("parameters", {}):
                param_info = category["parameters"][param_key]
                if param_info.get("options"):
                    return self._format_options(param_info)

        return []

    async def generate_batch_dynamic_options(
            self,
            params: List[Dict[str, Any]],
            state: WorkflowState
    ) -> Dict[str, List[Dict[str, str]]]:
        """批量生成多个参数的动态选项"""

        if not params:
            return {}

        # 如果只有一个参数，直接调用单个生成方法
        if len(params) == 1:
            options = await self.generate_dynamic_options(params[0], state)
            return {params[0]["key"]: options}

        # 批量生成
        if self.use_batch_options_generation and self.use_deepseek_for_options:
            try:
                logger.info(f"🚀 批量生成 {len(params)} 个参数的选项")
                batch_options = await self._generate_ai_batch_options(params, state)

                if batch_options:
                    return batch_options
                else:
                    logger.warning("批量生成失败，降级到逐个生成")
            except Exception as e:
                logger.error(f"批量生成选项出错: {e}")

        # 降级方案：逐个生成
        result = {}
        for param in params:
            options = await self.generate_dynamic_options(param, state)
            result[param["key"]] = options

        return result

    async def _generate_ai_batch_options(
            self,
            params: List[Dict[str, Any]],
            state: WorkflowState
    ) -> Dict[str, List[Dict[str, str]]]:
        """使用AI批量生成多个参数的选项"""

        # 获取用户上下文
        user_messages = [msg.content for msg in state.messages if msg.role == "user"]
        user_context = " ".join(user_messages) if user_messages else ""

        # 已收集的参数
        existing_params = state.metadata.get("extracted_parameters", {})

        # 构建批量生成的提示词
        system_prompt = """你是一个虚拟星座设计专家，擅长根据用户需求批量生成合适的参数选项。
    请为多个参数同时生成选项，确保选项之间的一致性和关联性。

    特别注意：
    1. 根据用户的具体需求生成相互关联的选项
    2. 技术参数要与监测目标相匹配
    3. 根据参数类型和用户场景，智能决定选项数量,通常3-4个选项即可
    5. 选项要有明显的差异，能够涵盖用户场景的大部分情况，并避免过于相似的选项
    6. 每个选项要有清晰的值和说明，说明要突出其适用场景，此外值和说明必须都是中文
    """

        prompt = f"""为以下多个虚拟星座参数批量生成选项。

    用户需求：{user_context}
    已收集参数：{json.dumps(existing_params, ensure_ascii=False)}

    需要生成选项的参数：
    """

        # 添加每个参数的详细信息
        for param in params:
            param_key = param["key"]
            param_name = param["name"]

            # 获取参数描述（从参数配置中）

            param_descriptions = {
                "observation_frequency": {
                    "name": "观测频率",
                    "description": "指卫星过境拍摄的频率，即多久获取一次新的遥感影像数据",
                    "unit": "次/时间段",
                    "examples": "每天1次、每周1次、每月1次"
                },
                "monitoring_period": {
                    "name": "监测周期",
                    "description": "指整个监测项目的持续时间，即从开始到结束的总时长",
                    "unit": "时间长度",
                    "examples": "3个月、6个月、1年"
                },
                "observation_area": {
                    "name": "观测区域",
                    "description": "需要监测的具体地理位置，如城市名、湖泊名、省份名等",
                    "unit": "地名",
                    "examples": "青海湖、北京市、长江流域、柬埔寨",
                    "special_instruction": "请生成具体的地理位置选项，不要生成面积范围"
                },
                "spatial_resolution": {
                    "name": "空间分辨率",
                    "description": "指遥感影像上一个像素代表的地面实际距离",
                    "unit": "米",
                    "examples": "高分辨率(<5米)、中分辨率(5-30米)"
                },
                "analysis_requirements": {
                    "name": "分析需求",
                    "description": "指需要对遥感数据进行的具体分析类型和方法",
                    "unit": "分析类型",
                    "examples": "变化检测、分类识别、定量反演、趋势分析、异常检测",
                    "context_mapping": {
                        "水质监测": ["定量反演", "变化检测", "异常检测", "趋势分析"],
                        "农业监测": ["分类识别", "参数提取", "变化检测", "产量预测", "病虫害监测"],
                        "城市监测": ["变化检测", "目标识别", "热岛分析", "违建监测"],
                        "灾害应急": ["灾害识别", "损失评估", "风险分析", "应急响应"],
                        "环境监测": ["污染监测", "生态评估", "碳排放", "生物多样性"]
                    }
                },
                "accuracy_requirements": {
                    "name": "精度要求",
                    "description": "指对分析结果准确性的具体要求和质量标准",
                    "unit": "精度百分比",
                    "examples": "科研级(>95%)、业务级(85-95%)、应用级(70-85%)"
                },
                "spectral_bands": {
                    "name": "光谱波段",
                    "description": "不同波段的电磁波用于不同的监测目的",
                    "unit": "波段类型",
                    "examples": "可见光、多光谱、热红外、雷达"
                },
                "output_format": {
                    "name": "输出格式",
                    "description": "最终交付给用户的数据产品和报告格式",
                    "unit": "格式类型",
                    "examples": "遥感影像、专题图、分析报告、实时预警"
                }
            }

            # 获取参数的详细说明
            param_info = param_descriptions.get(param_key, {
                "name": param_name,
                "description": "",
                "unit": "",
                "examples": ""
            })

            prompt += f"\n- 参数键：{param_key} - 参数名称：{param_info['name']} - 参数含义：{param_info['description']} - 单位/格式：{param_info['unit']} - 示例：{param_info['examples']}"

        prompt += """

        
    请以JSON格式输出所有参数的选项：
    {
        "参数key1": {
            "options": [
                {"value": "选项值", "label": "选项值", "description": "选项说明"},
                ...
            ],
            "default_option": "推荐的默认选项值"
        },
        "参数key2": {
            ...
        }
    }
"""

        try:
            # 调用DeepSeek API
            response = await self._call_deepseek_api(prompt, system_prompt, max_tokens=1500)
            print(response)
            if response:
                result = self._parse_batch_options_response(response, [p["key"] for p in params])

                # 验证每个参数的选项
                validated_result = {}
                for param_key, options_data in result.items():
                    if isinstance(options_data, dict) and "options" in options_data:
                        validated_options = self._validate_options_for_param(
                            options_data["options"],
                            param_key
                        )
                        validated_result[param_key] = validated_options
                    else:
                        validated_result[param_key] = []

                logger.info(f"✅ 批量生成成功，共 {len(validated_result)} 个参数")
                return validated_result

        except Exception as e:
            logger.error(f"批量生成选项失败: {e}")
            import traceback
            logger.error(traceback.format_exc())

        return {}

    def _parse_batch_options_response(self, response: str, param_keys: List[str]) -> Dict[str, Dict]:
        """解析批量选项响应"""
        try:
            import re

            logger.debug(f"批量选项原始响应: {response[:500]}...")

            # 尝试直接解析JSON
            try:
                data = json.loads(response.strip())

                # 确保所有参数都有选项
                result = {}
                for param_key in param_keys:
                    if param_key in data:
                        result[param_key] = data[param_key]
                    else:
                        logger.warning(f"批量响应中缺少参数 {param_key} 的选项")
                        result[param_key] = {"options": [], "default_option": ""}

                return result

            except json.JSONDecodeError:
                # 尝试提取JSON部分
                json_match = re.search(r'\{[\s\S]*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group()

                    # 修复常见JSON问题
                    json_str = re.sub(r'"\s*\n\s*"', '",\n"', json_str)
                    json_str = re.sub(r'}\s*\n\s*{', '},\n{', json_str)
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)

                    try:
                        data = json.loads(json_str)

                        result = {}
                        for param_key in param_keys:
                            if param_key in data:
                                result[param_key] = data[param_key]
                            else:
                                result[param_key] = {"options": [], "default_option": ""}

                        return result

                    except json.JSONDecodeError as e:
                        logger.error(f"批量JSON解析失败: {e}")

        except Exception as e:
            logger.error(f"解析批量选项响应失败: {e}")

        # 返回空结果
        return {key: {"options": [], "default_option": ""} for key in param_keys}

    def _determine_question_type_with_options(self, param: Dict, options: List[Dict]) -> str:
        """根据选项数量确定问题类型"""
        if options and len(options) > 0:
            if len(options) <= 4:
                return "options"  # 单选按钮
            elif len(options) <= 8:
                return "dropdown"  # 下拉菜单
            else:
                return "searchable_dropdown"  # 可搜索下拉
        else:
            return "text"  # 文本输入

    def _generate_contextual_hint(self, param: Dict, state: WorkflowState) -> str:
        """生成基于上下文的提示"""
        existing_params = state.metadata.get("extracted_parameters", {})
        monitoring_target = existing_params.get("monitoring_target", "")

        hints = {
            "observation_area": f"💡 基于您的{monitoring_target}需求，请选择或输入具体监测区域",
            "observation_frequency": f"💡 {monitoring_target}的观测频率建议，请根据实际需求选择",
            "spatial_resolution": f"💡 {monitoring_target}所需的图像清晰度，影响能看到的细节",
            "monitoring_period": f"💡 您计划进行{monitoring_target}的时间长度",
            "spectral_bands": f"💡 {monitoring_target}适用的光谱类型，不同波段有不同用途"
        }

        return hints.get(param["key"], self._generate_hint(param))


def _build_batch_followup_message(questions: List[Dict], all_params: Dict, just_collected: Dict) -> str:
    """构建批量收集后的补充消息"""

    message = "🤖 感谢您的回答！我已经收集到以下参数：\n\n"

    # 显示刚刚收集的参数
    param_names = {
        "monitoring_target": "监测目标",
        "observation_area": "观测区域",
        "observation_frequency": "观测频率",
        "monitoring_period": "监测周期",
        "spatial_resolution": "空间分辨率",
        "spectral_bands": "光谱波段",
        "analysis_requirements": "分析需求"
    }

    for key, value in just_collected.items():
        if key in param_names:
            message += f"✅ {param_names[key]}: {value}\n"

    message += "\n但还有少量必需参数需要补充：\n\n"

    for i, question in enumerate(questions, 1):
        message += f"**{question['question']}**\n"
        if question.get('examples'):
            message += f"例如：{', '.join(question['examples'][:2])}\n"
        message += "\n"

    message += "请提供这些信息以完成方案设计。"

    return message


def _build_enhanced_clarification_message(questions: List[Dict], existing_params: Dict) -> str:
    """构建增强的澄清消息 - 改进版：明确技术参数的可选性"""

    # 分组问题 - 按照逻辑类别分组
    categories = {
        "monitoring_target": [],
        "monitoring_area": [],
        "monitoring_time": [],
        "technical_params": []
    }

    for question in questions:
        category = question.get("category", "technical_params")
        if category in categories:
            categories[category].append(question)

    # 开场白
    intro = "🤖 为了给您设计最合适的虚拟星座方案，我需要了解以下信息"

    # 如果已有部分参数，先确认
    if existing_params:
        param_summaries = []
        param_names = {
            "monitoring_target": "监测目标",
            "observation_area": "观测区域",
            "observation_frequency": "观测频率",
            "spatial_resolution": "空间分辨率",
            "monitoring_period": "监测周期"
        }

        for key, value in existing_params.items():
            if key in param_names:
                param_summaries.append(f"**{param_names[key]}**: {value}")

        if param_summaries:
            intro = f"🤖 我已经了解到您的需求：\n" + " | ".join(param_summaries) + "\n\n为了完善方案，还需要了解以下信息"

    message = f"{intro}：\n\n"

    # 核心参数部分
    core_categories = ["monitoring_target", "monitoring_area", "monitoring_time"]
    core_questions = []
    for cat in core_categories:
        core_questions.extend(categories.get(cat, []))

    if core_questions:
        message += "### 🔴 核心参数（必需）\n"
        message += "_请提供以下必要信息，这些是生成方案的基础_\n\n"

        for i, question in enumerate(core_questions, 1):
            message += f"**{i}. {question['question']}**\n"

            if question.get('hint'):
                message += f"   {question['hint']}\n"

            if question['type'] == 'options' and question.get('options'):
                message += "   选项：\n"
                for opt in question['options'][:4]:
                    if isinstance(opt, dict):
                        message += f"   • {opt['label']}"
                        if opt.get('description'):
                            message += f" - {opt['description']}"
                        message += "\n"
                    else:
                        message += f"   • {opt}\n"
            elif question.get('examples'):
                message += f"   例如：{' | '.join(question['examples'][:3])}\n"

            message += "\n"

    # 技术参数部分（可选）
    tech_questions = categories.get("technical_params", [])
    if tech_questions:
        message += "### 🟡 技术参数（可选）\n"
        message += "_以下参数可以帮助优化方案，您可以选择设置或使用智能推荐_\n\n"

        for i, question in enumerate(tech_questions, len(core_questions) + 1):
            message += f"**{i}. {question['question']}**\n"

            if question.get('options'):
                options_display = []
                for opt in question['options'][:4]:
                    if isinstance(opt, dict):
                        options_display.append(opt['label'])
                    else:
                        options_display.append(str(opt))
                message += f"   选项：{' | '.join(options_display)}"
                if len(question['options']) > 4:
                    message += " ..."
                message += "\n"
            elif question.get('examples'):
                message += f"   例如：{', '.join(question['examples'][:3])}\n"

            message += "\n"

    # 添加智能提示
    message += "\n💡 **填写说明**：\n"
    message += "• ✅ **必填项**：请完成前面标红的核心参数（1-" + str(len(core_questions)) + "项）\n"

    if tech_questions:
        message += "• 💭 **可选项**：技术参数（" + str(len(core_questions) + 1) + "-" + str(
            len(core_questions) + len(tech_questions)) + "项）您可以：\n"
        message += "  - 选择设置以获得更精准的方案\n"
        message += "  - 留空让系统智能推荐\n"
        message += "  - 输入「跳过技术参数」仅回答必填项\n"

    message += "• 📝 支持多种回答方式：逐一回答、自然语言描述或结构化填写\n"

    # 示例
    message += "\n**回答示例**：\n"

    # 根据问题数量提供不同的示例
    total_questions = len(core_questions) + len(tech_questions)

    if total_questions >= 5:
        message += "• 完整回答：`1. 农业监测 2. 柬埔寨 3. 每周2次 4. 6个月 5. 中分辨率 6. 变化检测`\n"
        message += "• 只答必填：`1. 农业监测 2. 柬埔寨 3. 每周2次 4. 6个月，技术参数使用推荐`\n"
        message += "• 自然语言：「监测柬埔寨的农业情况，每周观测2次，持续6个月」"
    else:
        message += "• 结构化：`1. 水质监测 2. 青海湖 3. 每周2次 4. 6个月`\n"
        message += "• 自然语言：「我需要监测青海湖的水质变化，每周观测2次，持续6个月」"

    # 添加快速选项
    if tech_questions:
        message += "\n\n🚀 **快速选项**：\n"
        message += "• 输入「使用推荐参数」- 所有参数使用智能推荐\n"
        message += "• 输入「跳过技术参数」- 只回答必填项，技术参数用默认值"

    return message


def _build_enhanced_followup_message(questions: List[Dict], collected_params: Dict) -> str:
    """构建增强的后续澄清消息"""
    message = "🤖 感谢您的回答！AI已经理解了您的部分需求。还需要了解以下信息：\n\n"

    for i, question in enumerate(questions, 1):
        message += f"**{question['question']}**\n"

        if question.get('ai_generated'):
            message += "🧠 *基于您之前的回答智能生成*\n"

        if question.get('hint'):
            message += f"{question['hint']}\n"

        if question.get('examples'):
            message += f"例如：{', '.join(question['examples'][:3])}\n"

        message += "\n"

    message += "💡 您也可以输入「使用推荐参数」让AI为您自动选择合适的参数。"

    return message


def _generate_enhanced_parameter_confirmation(params: Dict[str, Any]) -> str:
    """生成增强的参数确认消息 - 4类别版本"""
    param_display_names = {
        "monitoring_target": "监测目标",
        "observation_area": "监测区域",
        "coverage_range": "覆盖范围",  # 🆕 新增
        "observation_frequency": "观测频率",
        "monitoring_period": "监测周期",
        "spatial_resolution": "空间分辨率",
        "spectral_bands": "光谱波段",
        "analysis_requirements": "分析需求",
        "time_criticality": "时效性要求",
        "accuracy_requirements": "精度要求",
        "output_format": "输出格式",
        "weather_dependency": "天气依赖性"
    }

    message = "✅ **参数收集完成！**\n\n我已经了解了您的需求：\n\n"

    # 1. 监测目标
    if "monitoring_target" in params:
        message += f"**1️⃣ 监测目标**\n"
        message += f"• {params['monitoring_target']}\n\n"

    # 2. 监测区域和范围
    if "observation_area" in params or "coverage_range" in params:
        message += f"**2️⃣ 监测位置与范围**\n"
        if "observation_area" in params:
            message += f"• 监测区域: {params['observation_area']}\n"
        if "coverage_range" in params:
            message += f"• 覆盖范围: {params['coverage_range']}\n"
        message += "\n"

    # 3. 监测频率和周期
    time_params = ["observation_frequency", "monitoring_period"]
    if any(p in params for p in time_params):
        message += f"**3️⃣ 监测时间要求**\n"
        for param in time_params:
            if param in params:
                message += f"• {param_display_names.get(param, param)}: {params[param]}\n"
        message += "\n"

    # 4. 技术参数（如果有）
    tech_params = ["spatial_resolution", "spectral_bands", "analysis_requirements",
                   "accuracy_requirements", "time_criticality", "weather_dependency",
                   "output_format"]

    tech_values = [(p, params[p]) for p in tech_params if p in params]

    if tech_values:
        message += f"**4️⃣ 技术参数**\n"
        for param, value in tech_values:
            message += f"• {param_display_names.get(param, param)}: {value}\n"
    else:
        message += f"**4️⃣ 技术参数**\n"
        message += "• 将使用基于您监测目标的智能推荐配置\n"

    # 🔧 关键修改：明确说明接下来要做什么，但不包含方案内容
    message += "\n🚀 参数收集完成，正在基于这些参数为您设计最优的虚拟星座方案..."
    message += "\n\n_（方案生成中，请稍候...）_"  # 🆕 添加提示

    return message