# backend/src/graph/nodes/parameter_clarification_node.py

import os
import json
import logging
import re
from typing import Dict, List, Any, Optional, Callable, Tuple
from pathlib import Path
import asyncio

from backend.src.graph.state import WorkflowState

logger = logging.getLogger(__name__)


class ParameterClarificationNode:
    """增强的参数澄清节点 - 支持更智能的参数收集"""

    def __init__(self):
        self.parameters_config = self._load_parameters_config()
        self.example_plans = self._load_example_plans()
        self.collected_params = {}
        self.question_history = []

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
        """获取默认参数配置"""
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
                            "examples": ["青海湖", "长江流域", "北京市"],
                            "clarification_prompt": "您需要监测哪个具体的地理区域？"
                        }
                    }
                },
                "temporal": {
                    "name": "时间参数",
                    "priority": 2,
                    "parameters": {
                        "observation_frequency": {
                            "name": "观测频率",
                            "description": "多久需要获取一次数据",
                            "required": True,
                            "examples": ["每天1次", "每周2次", "每月1次"],
                            "clarification_prompt": "您需要多长时间获取一次观测数据？"
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
                            "options": ["高分辨率(<5米)", "中分辨率(5-30米)", "低分辨率(>30米)"],
                            "clarification_prompt": "您需要什么级别的空间分辨率？"
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
                            "examples": ["水质变化", "植被覆盖", "城市扩张"],
                            "clarification_prompt": "您的主要监测目标是什么？"
                        }
                    }
                }
            },
            "clarification_rules": {
                "max_questions": 3,
                "skip_option": True
            }
        }

    def extract_existing_parameters(self, state: WorkflowState) -> Dict[str, Any]:
        """智能提取已有参数 - 增强版"""
        existing_params = {}

        # 获取所有用户消息
        user_messages = [msg.content for msg in state.messages if msg.role == "user"]
        full_context = " ".join(user_messages)

        # 1. 监测目标提取（增强）
        target_patterns = {
            "water": {
                "keywords": ["水质", "水体", "水位", "富营养化", "藻类", "水污染", "水资源"],
                "targets": ["水质变化", "水位监测", "水体面积", "富营养化", "藻类爆发"]
            },
            "vegetation": {
                "keywords": ["植被", "森林", "草地", "作物", "农业", "绿化", "生态"],
                "targets": ["植被覆盖", "作物长势", "森林变化", "草地退化", "物候监测"]
            },
            "urban": {
                "keywords": ["城市", "建筑", "热岛", "交通", "违建", "城镇", "扩张"],
                "targets": ["城市扩张", "建筑变化", "热岛效应", "交通流量", "违建监测"]
            },
            "disaster": {
                "keywords": ["灾害", "洪水", "火灾", "滑坡", "旱灾", "地震", "应急"],
                "targets": ["洪水淹没", "火灾监测", "滑坡识别", "旱情评估", "地震影响"]
            }
        }

        for category, config in target_patterns.items():
            for keyword in config["keywords"]:
                if keyword in full_context:
                    # 选择最相关的目标
                    for target in config["targets"]:
                        if any(t in full_context for t in target.split()):
                            existing_params["monitoring_target"] = target
                            break
                    if "monitoring_target" in existing_params:
                        break

        # 2. 地理位置提取（增强）
        # 省市区县
        location_pattern = r'([^省]+省|[^市]+市|[^区]+区|[^县]+县)'
        locations = re.findall(location_pattern, full_context)
        if locations:
            existing_params["observation_area"] = locations[0]

        # 特定地名
        specific_locations = ["青海湖", "长江", "黄河", "太湖", "洞庭湖", "鄱阳湖", "珠江"]
        for loc in specific_locations:
            if loc in full_context:
                existing_params["observation_area"] = loc
                break

        # 3. 时间频率提取（增强）
        frequency_patterns = {
            r"每小时": "每小时1次",
            r"每天|每日|日常": "每天1次",
            r"每周": "每周2次",
            r"每月": "每月1次",
            r"实时|准实时": "每小时1次",
            r"定期": "每周2次"
        }

        for pattern, freq in frequency_patterns.items():
            if re.search(pattern, full_context):
                existing_params["observation_frequency"] = freq
                break

        # 4. 分辨率需求提取（增强）
        resolution_patterns = {
            r"高分辨率|精细|详细|清晰": "high",
            r"中等分辨率|一般|常规": "medium",
            r"低分辨率|概览|宏观": "low",
            r"超高分辨率|极其精细": "very_high"
        }

        for pattern, res in resolution_patterns.items():
            if re.search(pattern, full_context):
                existing_params["spatial_resolution"] = res
                break

        # 5. 光谱需求提取
        spectral_patterns = {
            r"可见光|真彩色|RGB": "visible",
            r"多光谱|NDVI|植被指数": "multispectral",
            r"热红外|温度|热量": "thermal",
            r"雷达|SAR|全天候": "radar",
            r"高光谱|光谱分析": "hyperspectral"
        }

        for pattern, spec in spectral_patterns.items():
            if re.search(pattern, full_context):
                existing_params["spectral_bands"] = spec
                break

        # 6. 监测周期提取
        period_patterns = {
            r"(\d+)个?月": lambda m: f"{m.group(1)}个月",
            r"(\d+)年": lambda m: f"{m.group(1)}年",
            r"长期|持续|连续": "长期监测",
            r"短期|临时|应急": "1个月"
        }

        for pattern, handler in period_patterns.items():
            match = re.search(pattern, full_context)
            if match:
                if callable(handler):
                    existing_params["monitoring_period"] = handler(match)
                else:
                    existing_params["monitoring_period"] = handler
                break

        # 7. 分析需求提取
        analysis_keywords = {
            "变化检测": ["变化", "对比", "差异", "演变"],
            "分类识别": ["分类", "识别", "区分", "辨别"],
            "定量反演": ["定量", "参数", "浓度", "含量"],
            "趋势分析": ["趋势", "走势", "发展", "预测"],
            "异常检测": ["异常", "突发", "预警", "报警"]
        }

        for analysis_type, keywords in analysis_keywords.items():
            if any(kw in full_context for kw in keywords):
                existing_params["analysis_requirements"] = analysis_type
                break

        logger.info(f"智能提取到的参数: {existing_params}")
        return existing_params

    def identify_missing_parameters(self, existing_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别缺失的关键参数 - 智能版本"""
        missing_params = []
        param_config = self.parameters_config.get("parameter_categories", {})
        rules = self.parameters_config.get("clarification_rules", {})

        # 根据已有参数智能决定需要询问的参数
        required_params = self._get_contextual_required_params(existing_params)

        # 按优先级排序的参数类别
        for category_key, category_info in param_config.items():
            category_priority = category_info.get("priority", 999)

            for param_key, param_info in category_info.get("parameters", {}).items():
                # 检查是否是必需参数或上下文相关参数
                is_required = param_info.get("required", False) or param_key in required_params

                if is_required and param_key not in existing_params:
                    missing_params.append({
                        "key": param_key,
                        "name": param_info.get("name"),
                        "prompt": param_info.get("clarification_prompt"),
                        "options": param_info.get("options"),
                        "examples": param_info.get("examples"),
                        "category": category_key,
                        "priority": category_priority,
                        "dynamic_options": param_info.get("dynamic_options"),
                        "categories": param_info.get("categories")
                    })

        # 智能排序：根据上下文调整优先级
        missing_params = self._smart_sort_parameters(missing_params, existing_params)

        # 限制问题数量
        max_questions = rules.get("max_questions", 5)
        min_questions = rules.get("min_questions", 2)

        # 确保至少询问最少数量的问题
        if len(missing_params) < min_questions:
            # 添加一些有价值的可选参数
            optional_params = self._get_valuable_optional_params(existing_params)
            missing_params.extend(optional_params[:min_questions - len(missing_params)])

        return missing_params[:max_questions]

    def _get_contextual_required_params(self, existing_params: Dict[str, Any]) -> List[str]:
        """根据上下文确定需要的参数"""
        required = []

        # 基础必需参数
        if "monitoring_target" not in existing_params:
            required.append("monitoring_target")
        if "observation_area" not in existing_params:
            required.append("observation_area")

        # 根据监测目标确定技术参数
        target = existing_params.get("monitoring_target", "")

        if "水" in target or "water" in target.lower():
            required.extend(["spectral_bands", "observation_frequency"])
        elif "植被" in target or "vegetation" in target.lower():
            required.extend(["spectral_bands", "monitoring_period"])
        elif "城市" in target or "urban" in target.lower():
            required.extend(["spatial_resolution", "observation_frequency"])
        elif "灾害" in target or "disaster" in target.lower():
            required.extend(["observation_frequency", "time_criticality"])

        # 如果没有任何技术参数，至少需要一个
        tech_params = ["spatial_resolution", "spectral_bands", "observation_frequency"]
        if not any(p in existing_params for p in tech_params):
            required.append("spatial_resolution")

        return list(set(required))  # 去重

    def _smart_sort_parameters(self, params: List[Dict], existing_params: Dict) -> List[Dict]:
        """智能排序参数"""

        # 定义排序权重
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

    def _get_valuable_optional_params(self, existing_params: Dict) -> List[Dict]:
        """获取有价值的可选参数"""
        optional_params = []
        param_config = self.parameters_config.get("parameter_categories", {})

        # 根据已有参数推荐相关的可选参数
        valuable_optional = {
            "analysis_requirements": "了解分析需求有助于优化方案",
            "accuracy_requirements": "精度要求影响卫星选择",
            "output_format": "明确输出格式便于后续应用",
            "time_criticality": "时效性要求影响数据获取策略",
            "weather_dependency": "天气依赖性影响卫星类型选择"
        }

        for param_key, reason in valuable_optional.items():
            if param_key not in existing_params:
                # 查找参数定义
                for category_key, category in param_config.items():
                    if param_key in category.get("parameters", {}):
                        param_info = category["parameters"][param_key]
                        optional_params.append({
                            "key": param_key,
                            "name": param_info.get("name"),
                            "prompt": param_info.get("clarification_prompt"),
                            "options": param_info.get("options"),
                            "examples": param_info.get("examples"),
                            "category": category_key,
                            "priority": 5,  # 较低优先级
                            "reason": reason
                        })
                        break

        return optional_params

    def generate_clarification_questions(self, missing_params: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成智能澄清问题"""
        questions = []

        for param in missing_params:
            question = {
                "parameter_key": param["key"],
                "question": param["prompt"],
                "type": self._determine_question_type(param),
                "options": self._format_options(param),
                "examples": param.get("examples", []),
                "hint": self._generate_hint(param),
                "required": param.get("priority", 5) <= 2
            }

            # 添加动态选项
            if param.get("dynamic_options"):
                question["dynamic_options"] = param["dynamic_options"]

            # 添加分类选项
            if param.get("categories"):
                question["categories"] = param["categories"]

            questions.append(question)

        return questions

    def _determine_question_type(self, param: Dict) -> str:
        """确定问题类型"""
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
        """格式化选项"""
        options = param.get("options", [])

        if isinstance(options, dict):
            # 处理带描述的选项
            return [{"value": k, "label": v} for k, v in options.items()]
        elif isinstance(options, list):
            # 处理简单选项列表
            return [{"value": opt, "label": opt} for opt in options]
        else:
            return []

    def _generate_hint(self, param: Dict) -> str:
        """生成参数提示"""
        hints = {
            "observation_area": "💡 提示：可以是具体地名、行政区域或经纬度范围",
            "monitoring_target": "💡 提示：请尽可能具体，如'水体富营养化'比'水质'更好",
            "spatial_resolution": "💡 提示：分辨率越高，能看到的细节越多，但覆盖范围越小",
            "observation_frequency": "💡 提示：频率越高，时间分辨率越好，但成本也越高",
            "spectral_bands": "💡 提示：不同波段适合不同应用，如植被监测适合多光谱"
        }

        return hints.get(param["key"], "")

    def should_skip_clarification(self, state: WorkflowState) -> bool:
        """判断是否应该跳过澄清"""
        # 检查用户是否明确表示不需要澄清
        user_messages = [msg for msg in state.messages if msg.role == "user"]
        if user_messages:
            latest_message = user_messages[-1].content.lower()
            skip_keywords = ["直接生成", "不用问", "跳过", "默认", "随便", "都行", "快速", "马上"]
            if any(keyword in latest_message for keyword in skip_keywords):
                return True

        # 检查是否已经进行过澄清
        if state.metadata.get("clarification_completed", False):
            return True

        # 检查是否已经有足够的参数
        existing_params = self.extract_existing_parameters(state)
        essential_params = ["monitoring_target", "observation_area", "observation_frequency", "spatial_resolution"]
        if all(param in existing_params for param in essential_params):
            return True

        return False

    def apply_smart_defaults(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """应用智能默认值"""
        defaults = {
            "observation_frequency": "每天1次",
            "monitoring_period": "3个月",
            "spatial_resolution": "medium",
            "spectral_bands": "multispectral",
            "coverage_type": "重点区域密集观测",
            "analysis_requirements": "变化检测",
            "accuracy_requirements": "应用级（>85%）",
            "output_format": "遥感影像"
        }

        # 根据监测目标智能调整默认值
        target = params.get("monitoring_target", "")

        if "水质" in target:
            defaults.update({
                "spectral_bands": "multispectral",
                "observation_frequency": "每周2次",
                "analysis_requirements": "定量反演"
            })
        elif "城市" in target:
            defaults.update({
                "spatial_resolution": "high",
                "observation_frequency": "每月1次",
                "analysis_requirements": "变化检测"
            })
        elif "灾害" in target or "应急" in target:
            defaults.update({
                "observation_frequency": "每天2-3次",
                "monitoring_period": "应急期间（1-2周）",
                "time_criticality": "准实时（1小时内）"
            })
        elif "农业" in target or "作物" in target:
            defaults.update({
                "spectral_bands": "multispectral",
                "monitoring_period": "生长季（4-10月）",
                "analysis_requirements": "分类识别"
            })

        # 合并默认值
        for key, value in defaults.items():
            if key not in params:
                params[key] = value

        return params


# 继续之前的其他函数定义...
async def process_parameter_clarification(
        state: WorkflowState,
        streaming_callback: Optional[Callable] = None
) -> WorkflowState:
    """处理参数澄清流程 - 增强版"""

    node = ParameterClarificationNode()

    # 发送开始信号
    if streaming_callback:
        await streaming_callback({
            "type": "clarification_start",
            "message": "正在智能分析您的需求..."
        })

    # 检查是否应该跳过澄清
    if node.should_skip_clarification(state):
        logger.info("用户选择跳过参数澄清或参数已充足")
        state.metadata["clarification_skipped"] = True

        # 应用智能默认值
        existing_params = node.extract_existing_parameters(state)
        complete_params = node.apply_smart_defaults(existing_params)
        state.metadata["extracted_parameters"] = complete_params
        state.metadata["clarification_completed"] = True

        return state

    # 提取已有参数
    existing_params = node.extract_existing_parameters(state)
    state.metadata["extracted_parameters"] = existing_params

    # 识别缺失参数
    missing_params = node.identify_missing_parameters(existing_params)

    if not missing_params:
        logger.info("所有必要参数已齐全")
        state.metadata["clarification_completed"] = True
        # 应用智能默认值补充可选参数
        complete_params = node.apply_smart_defaults(existing_params)
        state.metadata["extracted_parameters"] = complete_params
        return state

    # 生成澄清问题
    questions = node.generate_clarification_questions(missing_params)
    state.metadata["pending_questions"] = questions

    # 构建智能澄清消息
    clarification_message = _build_smart_clarification_message(questions, existing_params)

    # 添加澄清消息到对话
    state.add_message("assistant", clarification_message)
    state.metadata["awaiting_clarification"] = True
    state.current_stage = "parameter_clarification"

    # 发送澄清问题
    if streaming_callback:
        await streaming_callback({
            "type": "clarification_questions",
            "questions": questions,
            "message": clarification_message,
            "existing_params": existing_params
        })

    return state


# 保留其他所有辅助函数定义...
def _build_smart_clarification_message(questions: List[Dict], existing_params: Dict) -> str:
    """构建智能的澄清消息"""
    # 开场白
    intro = "为了给您设计最合适的虚拟星座方案，我需要了解一些关键信息"

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
                param_summaries.append(f"{param_names[key]}: {value}")

        if param_summaries:
            intro = f"我已经了解到您的部分需求：\n" + "、".join(param_summaries) + "\n\n还需要了解以下信息"

    message = f"{intro}：\n\n"

    # 根据问题类型分组
    required_questions = [q for q in questions if q.get("required", False)]
    optional_questions = [q for q in questions if not q.get("required", False)]

    # 必需问题
    if required_questions:
        for i, question in enumerate(required_questions, 1):
            message += f"**{i}. {question['question']}**\n"

            # 添加提示
            if question.get('hint'):
                message += f"   {question['hint']}\n"

            # 添加选项或示例
            if question['type'] == 'options' and question.get('options'):
                message += "   选项：\n"
                for opt in question['options']:
                    if isinstance(opt, dict):
                        message += f"   • {opt['label']}\n"
                    else:
                        message += f"   • {opt}\n"
            elif question['type'] == 'categorized' and question.get('categories'):
                message += "   常见选择：\n"
                for category, items in list(question['categories'].items())[:3]:
                    message += f"   • {category}类：{', '.join(items[:3])}\n"
            elif question.get('examples'):
                message += f"   例如：{', '.join(question['examples'][:3])}\n"

            message += "\n"

    # 可选问题（如果有）
    if optional_questions:
        message += "\n**可选信息**（有助于优化方案）：\n"
        for question in optional_questions[:2]:  # 只显示前2个可选问题
            message += f"• {question['question']}\n"

    # 添加智能提示
    message += "\n💡 **回答提示**：\n"
    message += "• 您可以逐一回答，也可以用自然语言一次性描述\n"
    message += "• 如果某些参数不确定，我会为您推荐合适的默认值\n"
    message += "• 输入「跳过」或「快速生成」可使用智能推荐参数\n"

    # 添加示例
    if len(questions) >= 3:
        message += "\n**回答示例**：\n"
        message += "「我需要监测青海湖的水质变化，每周观测2次，需要10米分辨率的多光谱数据，计划监测6个月」"

    return message


async def process_clarification_response(
        state: WorkflowState,
        user_response: str,
        streaming_callback: Optional[Callable] = None
) -> WorkflowState:
    """处理用户对澄清问题的回复 - 智能版本"""

    # 检查是否在等待澄清
    if not state.metadata.get("awaiting_clarification", False):
        return state

    # 获取待回答的问题
    pending_questions = state.metadata.get("pending_questions", [])
    if not pending_questions:
        state.metadata["awaiting_clarification"] = False
        return state

    # 解析用户回复
    node = ParameterClarificationNode()
    extracted_params = state.metadata.get("extracted_parameters", {})

    # 智能解析回复
    parsed_params = _parse_intelligent_response(user_response, pending_questions, extracted_params)

    # 更新参数
    extracted_params.update(parsed_params)
    state.metadata["extracted_parameters"] = extracted_params

    # 检查是否要跳过剩余问题
    if _check_skip_remaining(user_response):
        # 应用智能默认值
        complete_params = node.apply_smart_defaults(extracted_params)
        state.metadata["extracted_parameters"] = complete_params
        state.metadata["clarification_completed"] = True
        state.metadata["awaiting_clarification"] = False
        state.add_thinking_step("参数澄清", "用户选择使用推荐参数")

        if streaming_callback:
            await streaming_callback({
                "type": "clarification_complete",
                "parameters": complete_params,
                "message": "已使用智能推荐参数，正在为您生成方案..."
            })

        return state

    # 检查是否还有未回答的必要问题
    remaining_missing = node.identify_missing_parameters(extracted_params)
    required_remaining = [p for p in remaining_missing if p.get("priority", 5) <= 2]

    if not required_remaining:
        # 所有必需参数已收集，应用默认值补充其他参数
        complete_params = node.apply_smart_defaults(extracted_params)
        state.metadata["extracted_parameters"] = complete_params
        state.metadata["clarification_completed"] = True
        state.metadata["awaiting_clarification"] = False
        state.add_thinking_step("参数澄清完成", f"收集到参数: {list(complete_params.keys())}")

        # 生成参数确认消息
        confirmation_message = _generate_parameter_confirmation(complete_params)

        if streaming_callback:
            await streaming_callback({
                "type": "clarification_complete",
                "parameters": complete_params,
                "message": confirmation_message
            })
    else:
        # 还有未回答的问题，生成后续问题
        next_questions = node.generate_clarification_questions(required_remaining[:2])  # 每次最多问2个
        state.metadata["pending_questions"] = next_questions

        # 生成后续澄清消息
        followup_message = _build_followup_clarification_message(next_questions, extracted_params)
        state.add_message("assistant", followup_message)

        if streaming_callback:
            await streaming_callback({
                "type": "clarification_followup",
                "questions": next_questions,
                "message": followup_message,
                "collected_params": extracted_params
            })

    return state


# 继续保留所有其他辅助函数...
def _parse_intelligent_response(response: str, questions: List[Dict], existing_params: Dict) -> Dict[str, Any]:
    """智能解析用户回复"""
    parsed = {}
    response_lower = response.lower()

    # 1. 尝试结构化解析（用户按格式回答）
    # 匹配 "1. xxx 2. yyy" 格式
    structured_pattern = r'(\d+)[.、]\s*([^0-9]+?)(?=\d+[.、]|$)'
    structured_matches = re.findall(structured_pattern, response, re.DOTALL)

    if structured_matches:
        for idx, answer in structured_matches:
            try:
                q_idx = int(idx) - 1
                if 0 <= q_idx < len(questions):
                    question = questions[q_idx]
                    parsed[question['parameter_key']] = _extract_answer_value(
                        answer.strip(), question
                    )
            except:
                pass

    # 2. 自然语言解析（用户用一句话描述）
    if not parsed:
        parsed = _parse_natural_language_response(response, questions)

    # 3. 补充解析（查找遗漏的参数）
    for question in questions:
        if question['parameter_key'] not in parsed:
            value = _find_parameter_in_text(response, question)
            if value:
                parsed[question['parameter_key']] = value

    return parsed


def _extract_answer_value(answer: str, question: Dict) -> Any:
    """从答案中提取参数值"""
    answer_lower = answer.lower().strip()

    # 处理选项类型
    if question['type'] == 'options' and question.get('options'):
        # 模糊匹配选项
        for option in question['options']:
            if isinstance(option, dict):
                if option['value'].lower() in answer_lower or option['label'].lower() in answer_lower:
                    return option['value']
            else:
                if str(option).lower() in answer_lower:
                    return option

    # 处理分类类型
    if question['type'] == 'categorized' and question.get('categories'):
        for category, items in question['categories'].items():
            for item in items:
                if item.lower() in answer_lower:
                    return item

    # 默认返回清理后的答案
    return answer.strip()


def _parse_natural_language_response(response: str, questions: List[Dict]) -> Dict[str, Any]:
    """解析自然语言回复"""
    parsed = {}

    # 定义参数关键词映射
    param_keywords = {
        "observation_area": ["监测", "观测", "地区", "区域", "位置", "地点"],
        "monitoring_target": ["目标", "监测什么", "观测什么", "关注"],
        "observation_frequency": ["频率", "多久", "几次", "每天", "每周", "每月"],
        "monitoring_period": ["周期", "多长时间", "持续", "几个月", "几年"],
        "spatial_resolution": ["分辨率", "精度", "清晰度", "米"],
        "spectral_bands": ["波段", "光谱", "多光谱", "可见光", "红外"],
        "analysis_requirements": ["分析", "检测", "识别", "反演", "评估"]
    }

    # 对每个参数尝试提取
    for param_key, keywords in param_keywords.items():
        # 查找相关的问题
        question = next((q for q in questions if q['parameter_key'] == param_key), None)
        if not question:
            continue

        # 查找关键词附近的内容
        for keyword in keywords:
            pattern = rf'{keyword}[是为：]?\s*([^，。,\s]+)'
            match = re.search(pattern, response)
            if match:
                value = match.group(1).strip()
                # 验证和标准化值
                if question.get('options'):
                    # 尝试匹配到标准选项
                    value = _match_to_standard_option(value, question['options'])
                parsed[param_key] = value
                break

    return parsed


def _find_parameter_in_text(text: str, question: Dict) -> Optional[str]:
    """在文本中查找特定参数"""
    text_lower = text.lower()

    # 根据参数类型使用不同的提取策略
    param_key = question['parameter_key']

    if param_key == "observation_area":
        # 提取地名
        location_pattern = r'([^省]+省|[^市]+市|[^区]+区|[^县]+县|[^湖]+湖|[^江]+江|[^河]+河)'
        match = re.search(location_pattern, text)
        if match:
            return match.group(1)

    elif param_key == "observation_frequency":
        # 提取频率
        freq_patterns = {
            r'每小时': '每小时1次',
            r'每天|每日': '每天1次',
            r'每周': '每周2次',
            r'每月': '每月1次',
            r'(\d+)天一次': lambda m: f'每{m.group(1)}天1次',
            r'一天(\d+)次': lambda m: f'每天{m.group(1)}次'
        }

        for pattern, value in freq_patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                if callable(value):
                    return value(match)
                return value

    elif param_key == "monitoring_period":
        # 提取时间周期
        period_patterns = {
            r'(\d+)\s*个月': lambda m: f'{m.group(1)}个月',
            r'(\d+)\s*年': lambda m: f'{m.group(1)}年',
            r'半年': '6个月',
            r'一年': '1年',
            r'长期': '长期监测'
        }

        for pattern, value in period_patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                if callable(value):
                    return value(match)
                return value

    elif param_key == "spatial_resolution":
        # 提取分辨率
        res_match = re.search(r'(\d+)\s*米', text)
        if res_match:
            meters = int(res_match.group(1))
            if meters < 1:
                return "very_high"
            elif meters <= 5:
                return "high"
            elif meters <= 30:
                return "medium"
            else:
                return "low"

    return None


def _match_to_standard_option(value: str, options: List) -> str:
    """匹配到标准选项"""
    value_lower = value.lower()

    for option in options:
        if isinstance(option, dict):
            if value_lower in option['value'].lower() or value_lower in option['label'].lower():
                return option['value']
        else:
            if value_lower in str(option).lower():
                return option

    # 如果没有精确匹配，返回原值
    return value


def _check_skip_remaining(response: str) -> bool:
    """检查是否跳过剩余问题"""
    skip_phrases = [
        "跳过", "默认", "推荐", "自动", "快速生成",
        "不用问了", "直接生成", "都行", "随便"
    ]

    response_lower = response.lower()
    return any(phrase in response_lower for phrase in skip_phrases)


def _generate_parameter_confirmation(params: Dict[str, Any]) -> str:
    """生成参数确认消息"""
    param_display_names = {
        "monitoring_target": "监测目标",
        "observation_area": "观测区域",
        "observation_frequency": "观测频率",
        "monitoring_period": "监测周期",
        "spatial_resolution": "空间分辨率",
        "spectral_bands": "光谱波段",
        "analysis_requirements": "分析需求",
        "time_criticality": "时效性要求",
        "accuracy_requirements": "精度要求",
        "output_format": "输出格式"
    }

    message = "✅ **参数收集完成！**\n\n我已经了解了您的需求：\n\n"

    # 核心参数
    core_params = ["monitoring_target", "observation_area", "observation_frequency", "monitoring_period"]
    message += "**核心需求：**\n"
    for param in core_params:
        if param in params:
            message += f"• {param_display_names.get(param, param)}: {params[param]}\n"

    # 技术参数
    tech_params = ["spatial_resolution", "spectral_bands", "analysis_requirements"]
    if any(p in params for p in tech_params):
        message += "\n**技术要求：**\n"
        for param in tech_params:
            if param in params:
                message += f"• {param_display_names.get(param, param)}: {params[param]}\n"

    # 其他参数
    other_params = [p for p in params if p not in core_params + tech_params]
    if other_params:
        message += "\n**其他要求：**\n"
        for param in other_params:
            message += f"• {param_display_names.get(param, param)}: {params[param]}\n"

    message += "\n🚀 现在我将基于这些参数为您设计最优的虚拟星座方案..."

    return message


def _build_followup_clarification_message(questions: List[Dict], collected_params: Dict) -> str:
    """构建后续澄清消息"""
    message = "感谢您的回答！还需要了解以下信息：\n\n"

    for i, question in enumerate(questions, 1):
        message += f"**{question['question']}**\n"

        if question.get('hint'):
            message += f"{question['hint']}\n"

        if question['type'] == 'options' and question.get('options'):
            message += "选项：" + " / ".join([
                opt['label'] if isinstance(opt, dict) else str(opt)
                for opt in question['options']
            ]) + "\n"
        elif question.get('examples'):
            message += f"例如：{', '.join(question['examples'][:3])}\n"

        message += "\n"

    message += "💡 您也可以输入「使用推荐参数」让我为您自动选择合适的参数。"

    return message