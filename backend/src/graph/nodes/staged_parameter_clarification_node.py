import logging
from typing import Dict, List, Any, Optional, Callable, Tuple
from backend.src.graph.state import WorkflowState
from backend.src.graph.nodes.uncertainty_calculator import get_uncertainty_calculator
from backend.src.graph.nodes.enhanced_parameter_clarification_node import EnhancedParameterClarificationNode
import time
logger = logging.getLogger(__name__)


class StagedParameterClarificationNode(EnhancedParameterClarificationNode):
    """分阶段参数收集节点"""

    # 定义收集阶段 - 修改：将location拆分为两个阶段
    COLLECTION_STAGES = {
        "purpose": {
            "name": "监测目标",
            "params": ["monitoring_target"],
            "required": True,
            "max_retries": 2
        },
        "time": {
            "name": "时间参数",
            "params": ["observation_frequency", "monitoring_period"],
            "required": True,
            "max_retries": 2
        },
        "location_area": {  # 🔧 修改：先询问观测区域
            "name": "观测区域",
            "params": ["observation_area"],
            "required": True,
            "max_retries": 2
        },
        "location_range": {  # 🔧 新增：后询问覆盖范围
            "name": "覆盖范围",
            "params": ["coverage_range"],
            "required": True,
            "max_retries": 2
        },
        "technical": {
            "name": "技术参数",
            "params": ["spatial_resolution", "spectral_bands", "analysis_requirements",
                       "output_format", "accuracy_requirements"],
            "required": False,
            "max_retries": 1
        }
    }

    async def get_next_collection_stage(self, state: WorkflowState) -> Optional[str]:
        """获取下一个需要收集的阶段"""
        current_stage = state.get_current_collection_stage()
        extracted_params = state.metadata.get("extracted_parameters", {})

        # 🔧 修改：更新阶段顺序
        stage_order = ["purpose", "time", "location_area", "location_range", "technical"]

        if current_stage == "not_started":
            return "purpose"

        if current_stage == "completed":
            return None

        # 查找当前阶段的索引
        try:
            current_index = stage_order.index(current_stage)
        except ValueError:
            return "purpose"

        # 检查是否需要进入下一阶段
        for i in range(current_index + 1, len(stage_order)):
            next_stage = stage_order[i]
            stage_info = self.COLLECTION_STAGES[next_stage]

            # 检查该阶段的参数是否已经收集完整
            missing_params = [p for p in stage_info["params"] if p not in extracted_params]

            if missing_params and (stage_info["required"] or self._user_wants_stage(state, next_stage)):
                return next_stage

        return None

    async def check_stage_uncertainty(self, state: WorkflowState, stage: str) -> Dict[str, Any]:
        """检查特定阶段参数的不确定性"""
        calculator = get_uncertainty_calculator()
        extracted_params = state.metadata.get("extracted_parameters", {})

        logger.info(f"检查阶段 {stage} 的不确定性，当前已收集参数: {extracted_params}")

        stage_info = self.COLLECTION_STAGES[stage]
        uncertainty_results = {}

        if stage == "purpose":
            if "monitoring_target" in extracted_params:
                uncertainty_results["monitoring_target"] = await calculator.calculate_monitoring_target_uncertainty(
                    extracted_params.get("monitoring_target"),
                    enable_web_search=True,
                    enable_llm=True
                )

        elif stage == "time":
            time_uncertainty = await calculator.calculate_time_uncertainty(
                extracted_params.get("observation_frequency"),
                extracted_params.get("monitoring_period"),
                enable_llm=True
            )
            uncertainty_results.update(time_uncertainty)

        # 🔧 修改：分别处理两个location阶段
        elif stage == "location_area":
            if "observation_area" in extracted_params:
                location_uncertainty = await calculator.calculate_location_uncertainty(
                    extracted_params.get("observation_area"),
                    None,  # 还没有coverage_range
                    enable_llm=True
                )
                if "observation_area" in location_uncertainty:
                    uncertainty_results["observation_area"] = location_uncertainty["observation_area"]

        elif stage == "location_range":
            if "coverage_range" in extracted_params:
                location_uncertainty = await calculator.calculate_location_uncertainty(
                    extracted_params.get("observation_area"),  # 使用已收集的area
                    extracted_params.get("coverage_range"),
                    enable_llm=True
                )
                if "coverage_range" in location_uncertainty:
                    uncertainty_results["coverage_range"] = location_uncertainty["coverage_range"]

        return uncertainty_results

    def should_retry_stage(self, uncertainty_results: Dict[str, Any], stage: str, retry_count: int) -> bool:
        """判断是否应该重试当前阶段"""
        stage_info = self.COLLECTION_STAGES[stage]

        # 如果已经达到最大重试次数，不再重试
        if retry_count >= stage_info.get("max_retries", 2):
            logger.info(f"阶段 {stage} 已达最大重试次数 {retry_count}")
            return False

        # 检查不确定性
        high_uncertainty_params = []
        for param_key, result in uncertainty_results.items():
            if result.get("needs_clarification", False):
                high_uncertainty_params.append(param_key)

        if high_uncertainty_params:
            logger.info(f"阶段 {stage} 中参数 {high_uncertainty_params} 仍有高不确定性，需要重试")
            return True

        return False

    def _get_relevant_technical_params_for_stage(
            self,
            monitoring_target: str,
            existing_params: Dict
    ) -> List[str]:
        """根据监测目标和已有参数，智能选择相关的技术参数"""

        # 基础技术参数（通用）
        base_tech_params = ["spatial_resolution", "analysis_requirements", "output_format"]

        # 根据监测目标的特定技术参数映射
        target_specific_params = {
            "水质": ["spectral_bands", "accuracy_requirements", "analysis_requirements"],
            "农业": ["spatial_resolution", "spectral_bands", "monitoring_season"],
            "城市": ["spatial_resolution", "analysis_requirements", "data_processing_level"],
            "灾害": ["time_criticality", "weather_dependency", "spatial_resolution"],
            "植被": ["spectral_bands", "spatial_resolution", "analysis_requirements"],
            "环境": ["spectral_bands", "analysis_requirements", "accuracy_requirements"]
        }

        # 选择相关参数
        selected_params = list(base_tech_params)  # 从基础参数开始

        # 根据监测目标添加特定参数
        for target_keyword, specific_params in target_specific_params.items():
            if target_keyword in monitoring_target:
                for param in specific_params:
                    if param not in selected_params and param not in existing_params:
                        selected_params.append(param)
                break

        # 确保不重复已收集的参数
        final_params = [p for p in selected_params if p not in existing_params]

        logger.info(f"为监测目标 '{monitoring_target}' 选择的技术参数: {final_params}")
        return final_params

    async def generate_stage_questions(
            self,
            state: WorkflowState,
            stage: str,
            uncertainty_results: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """为特定阶段生成问题 - 支持批量选项生成"""
        stage_info = self.COLLECTION_STAGES[stage]
        extracted_params = state.metadata.get("extracted_parameters", {})
        retry_count = state.stage_retry_count.get(stage, 0)

        questions = []

        # 确定需要收集的参数
        params_to_collect = []

        if stage == "technical":
            monitoring_target = extracted_params.get("monitoring_target", "")
            relevant_tech_params = self._get_relevant_technical_params_for_stage(
                monitoring_target, extracted_params
            )
            params_to_collect = relevant_tech_params[:4]
        else:
            for param_key in stage_info["params"]:
                if retry_count > 0 and uncertainty_results:
                    param_uncertainty = uncertainty_results.get(param_key, {})
                    if param_uncertainty.get("needs_clarification", False):
                        params_to_collect.append(param_key)
                elif param_key not in extracted_params:
                    params_to_collect.append(param_key)

        if not params_to_collect:
            return questions

        # 🔧 批量生成选项（对于时间和技术参数阶段）
        if stage in ["technical"] and len(params_to_collect) > 1:
            logger.info(f"🚀 为 {stage} 阶段批量生成 {len(params_to_collect)} 个参数的选项")

            # 准备批量参数
            batch_params = []
            for param_key in params_to_collect:
                param_config = self._get_param_config(param_key)
                if param_config:
                    batch_params.append({
                        "key": param_key,
                        "name": param_config.get("name", param_key)
                    })

            # 批量生成选项
            batch_options = await self.generate_batch_dynamic_options(batch_params, state)

            # 构建问题
            for param_key in params_to_collect:
                param_config = self._get_param_config(param_key)
                if not param_config:
                    continue

                prompt = param_config.get("clarification_prompt", "")
                if retry_count > 0:
                    prompt = f"您之前提供的{param_config.get('name', param_key)}不够明确，请重新提供。{prompt}"

                # 使用批量生成的选项
                options = batch_options.get(param_key, [])

                question = {
                    "parameter_key": param_key,
                    "parameter_name": param_config.get("name", param_key),
                    "question": prompt,
                    "type": "options" if options else "text",
                    "options": options,
                    "examples": param_config.get("examples", []),
                    "hint": self._generate_stage_hint(param_key, stage, retry_count),
                    "required": True if stage != "technical" else False,
                    "stage": stage,
                    "retry_count": retry_count
                }

                if uncertainty_results and param_key in uncertainty_results:
                    question["uncertainty_info"] = uncertainty_results[param_key]

                questions.append(question)

        else:
            # 原有的逐个生成逻辑（用于其他阶段）
            for param_key in params_to_collect:
                param_config = self._get_param_config(param_key)
                if not param_config:
                    continue

                prompt = param_config.get("clarification_prompt", "")
                if retry_count > 0:
                    prompt = f"您之前提供的{param_config.get('name', param_key)}不够明确，请重新提供。{prompt}"

                # 单个生成选项
                options = await self.generate_dynamic_options(
                    {"key": param_key, "name": param_config.get("name", param_key)},
                    state
                )

                question = {
                    "parameter_key": param_key,
                    "parameter_name": param_config.get("name", param_key),
                    "question": prompt,
                    "type": "options" if options else "text",
                    "options": options,
                    "examples": param_config.get("examples", []),
                    "hint": self._generate_stage_hint(param_key, stage, retry_count),
                    "required": True if stage != "technical" else False,
                    "stage": stage,
                    "retry_count": retry_count
                }

                if uncertainty_results and param_key in uncertainty_results:
                    question["uncertainty_info"] = uncertainty_results[param_key]

                questions.append(question)

        return questions

    def _get_param_config(self, param_key: str) -> Dict[str, Any]:
        """获取参数配置"""
        for category in self.parameters_config.get("parameter_categories", {}).values():
            if param_key in category.get("parameters", {}):
                return category["parameters"][param_key]
        return {}

    def _generate_stage_hint(self, param_key: str, stage: str, retry_count: int) -> str:
        """生成阶段性提示"""
        base_hints = {
            "monitoring_target": "请具体说明您要监测什么，如'水质变化'、'农业长势'等",
            "observation_frequency": "请说明多久获取一次数据，如'每天1次'、'每周2次'",
            "monitoring_period": "请说明监测持续多长时间，如'3个月'、'1年'",
            "observation_area": "请提供具体的地理位置，如'青海湖'、'北京市'",
            "coverage_range": "请说明监测的空间范围，如'100平方公里'、'全市范围'"
        }

        hint = base_hints.get(param_key, "")

        if retry_count > 0:
            hint = f"💡 提示：{hint} (请提供更具体的信息)"
        else:
            hint = f"💡 {hint}"

        return hint

    def _user_wants_stage(self, state: WorkflowState, stage: str) -> bool:
        """判断用户是否需要设置某阶段的参数"""
        if stage == "technical":
            # 🔧 修复：技术参数阶段应该始终出现，让用户选择或跳过
            # 而不是依赖于用户是否提到技术关键词
            return True

            # 原来的逻辑（注释掉）：
            # user_messages = [msg.content for msg in state.messages if msg.role == "user"]
            # tech_keywords = ["分辨率", "精度", "波段", "光谱", "输出格式"]
            # full_context = " ".join(user_messages).lower()
            # return any(keyword in full_context for keyword in tech_keywords)

        return True

    def build_stage_clarification_message(
            self,
            questions: List[Dict],
            stage: str,
            retry_count: int,
            uncertainty_info: Dict[str, Any] = None
    ) -> str:
        """构建阶段性澄清消息"""
        stage_info = self.COLLECTION_STAGES[stage]
        stage_name = stage_info["name"]

        # 开场白
        if retry_count == 0:
            message = f"🤖 现在我们来确定**{stage_name}**：\n\n"
        else:
            message = f"🤖 让我们再次确认**{stage_name}**，以确保准确理解您的需求：\n\n"

        # 如果有不确定性信息，展示给用户
        if uncertainty_info:
            message += self._format_uncertainty_feedback(uncertainty_info)
            message += "\n"

        # 显示问题
        for i, question in enumerate(questions, 1):
            message += f"**{question['question']}**\n"

            if question.get('hint'):
                message += f"{question['hint']}\n"

            if question.get('options'):
                message += "推荐选项：\n"
                for opt in question['options'][:4]:
                    if isinstance(opt, dict):
                        message += f"• {opt['label']}"
                        if opt.get('description'):
                            message += f" - {opt['description']}"
                        message += "\n"
                    else:
                        message += f"• {opt}\n"
            elif question.get('examples'):
                message += f"例如：{' | '.join(question['examples'][:3])}\n"

            message += "\n"

        # 阶段性提示
        if stage == "purpose":
            message += "💡 监测目标是整个方案设计的基础，请尽可能具体描述您要监测什么。\n"
        elif stage == "location_area":  # 🔧 修改
            message += "💡 请提供具体的地理位置，可以是地名、行政区域或经纬度范围。\n"
        elif stage == "location_range":  # 🔧 新增
            message += "💡 基于您选择的观测区域，请确定监测的覆盖范围。\n"
        elif stage == "time":
            message += "💡 时间参数决定了数据采集的频率和项目持续时间，对成本和效果有重要影响。\n"
        elif stage == "technical":
            message += "💡 **技术参数说明**：\n"
            message += "• 这些参数能帮助优化您的虚拟星座方案\n"
            message += "• 您可以选择设置以获得更精准的方案\n"
            message += "• 也可以输入「跳过技术参数」使用智能推荐值\n"
            message += "• 如有其他技术需求，可以直接说明\n"

        return message

    def _format_uncertainty_feedback(self, uncertainty_info: Dict[str, Any]) -> str:
        """格式化不确定性反馈信息"""
        feedback = "⚠️ **参数澄清原因**：\n"

        for param_key, info in uncertainty_info.items():
            if info.get("needs_clarification"):
                details = info.get("details", {})
                score = info.get("uncertainty_score", 0)

                feedback += f"\n• **{self._get_param_display_name(param_key)}**"
                feedback += f"（不确定性：{int(score * 100)}%）\n"

                if details.get("missing_info"):
                    feedback += f"  - {details['missing_info']}\n"

                if details.get("matched_terms"):
                    feedback += f"  - 识别到的相关词汇：{', '.join(details['matched_terms'])}\n"

        return feedback

    def _get_param_display_name(self, param_key: str) -> str:
        """获取参数的显示名称"""
        display_names = {
            "monitoring_target": "监测目标",
            "observation_frequency": "观测频率",
            "monitoring_period": "监测周期",
            "observation_area": "观测区域",
            "coverage_range": "覆盖范围"
        }
        return display_names.get(param_key, param_key)


async def process_staged_parameter_clarification(
        state: WorkflowState,
        streaming_callback: Optional[Callable] = None
) -> WorkflowState:
    """处理分阶段参数收集"""

    node = StagedParameterClarificationNode()

    # 初始化参数收集
    if state.get_current_collection_stage() == "not_started":
        state.set_collection_stage("purpose")

        if streaming_callback:
            await streaming_callback({
                "type": "clarification_start",
                "message": "开始分步收集参数，首先确定您的监测目标..."
            })

    # 获取当前阶段
    current_stage = state.get_current_collection_stage()

    if current_stage == "completed":
        logger.info("参数收集已完成")
        return state

    # 检查是否应该跳过澄清
    if node.should_skip_clarification(state):
        # 🔧 修复：只有在真正完成所有阶段后才跳过
        collection_history = state.parameter_collection_history
        has_all_stages = all(
            any(record.get("stage") == stage for record in collection_history)
            for stage in ["purpose", "time", "location", "technical"]
        )

        if not has_all_stages:
            logger.info("还有阶段未完成，继续收集")
            # 继续下一个阶段
            next_stage = await node.get_next_collection_stage(state)
            if next_stage:
                state.set_collection_stage(next_stage)
                return await process_staged_parameter_clarification(state, streaming_callback)

        logger.info("用户选择跳过参数澄清")
        state.metadata["clarification_skipped"] = True
        state.metadata["clarification_completed"] = True
        state.set_collection_stage("completed")

        # 应用默认值
        complete_params = node.apply_smart_defaults(
            state.metadata.get("extracted_parameters", {})
        )
        state.metadata["extracted_parameters"] = complete_params

        return state

    # 🔧 关键修复：优先使用已收集的参数，只在首次或没有参数时才提取
    existing_params = state.metadata.get("extracted_parameters", {})

    # 只有在没有任何参数或者是第一次进入时才重新提取
    if not existing_params and state.get_current_collection_stage() == "purpose":
        # 🔧 使用新的提取方法，只从最新方案请求后的消息中提取
        existing_params = await node.extract_existing_parameters(state)
        state.metadata["extracted_parameters"] = existing_params

        logger.info(f"🔖 从最新方案请求后提取到参数: {existing_params}")

    # 🔧 确保 node 的 collected_params 与 state 同步
    node.collected_params = existing_params.copy()

    # 计算当前阶段的不确定性
    uncertainty_results = await node.check_stage_uncertainty(state, current_stage)
    retry_count = state.stage_retry_count.get(current_stage, 0)

    # 判断是否需要重试当前阶段
    if uncertainty_results and node.should_retry_stage(uncertainty_results, current_stage, retry_count):
        state.increment_stage_retry(current_stage)
        logger.info(f"阶段 {current_stage} 需要重试，当前重试次数：{retry_count + 1}")
    else:
        # 检查是否可以进入下一阶段
        next_stage = await node.get_next_collection_stage(state)
        if next_stage:
            state.set_collection_stage(next_stage)
            current_stage = next_stage
            retry_count = 0
            uncertainty_results = {}
        else:
            # 所有阶段完成
            state.set_collection_stage("completed")
            state.metadata["clarification_completed"] = True

            # 应用智能默认值
            complete_params = node.apply_smart_defaults(existing_params)
            state.metadata["extracted_parameters"] = complete_params

            if streaming_callback:
                await streaming_callback({
                    "type": "clarification_complete",
                    "parameters": complete_params,
                    "message": "参数收集完成，正在生成方案..."
                })

            return state

    # 生成当前阶段的问题
    questions = await node.generate_stage_questions(state, current_stage, uncertainty_results)

    if not questions:
        # 当前阶段没有需要收集的参数，进入下一阶段
        next_stage = await node.get_next_collection_stage(state)
        if next_stage:
            state.set_collection_stage(next_stage)
            return await process_staged_parameter_clarification(state, streaming_callback)
        else:
            state.set_collection_stage("completed")
            state.metadata["clarification_completed"] = True
            return state

    # 保存待回答的问题
    state.metadata["pending_questions"] = questions
    state.metadata["current_stage_uncertainty"] = uncertainty_results
    state.metadata["awaiting_clarification"] = True
    state.current_stage = "parameter_clarification"

    # 构建澄清消息
    clarification_message = node.build_stage_clarification_message(
        questions, current_stage, retry_count, uncertainty_results
    )

    # 添加到对话
    state.add_message("assistant", clarification_message)

    # 发送给前端
    if streaming_callback:
        await streaming_callback({
            "type": "clarification_questions",
            "questions": questions,
            "message": clarification_message,
            "stage": current_stage,
            "stage_name": node.COLLECTION_STAGES[current_stage]["name"],
            "retry_count": retry_count,
            "uncertainty_results": uncertainty_results,
            "existing_params": existing_params  # 🔧 添加已收集的参数信息
        })

    # 记录思考步骤
    state.add_thinking_step(
        f"{node.COLLECTION_STAGES[current_stage]['name']}参数收集",
        f"需要澄清 {len(questions)} 个参数"
    )

    return state


async def process_staged_clarification_response(
        state: WorkflowState,
        user_response: str,
        streaming_callback: Optional[Callable] = None
) -> WorkflowState:
    """处理用户对分阶段澄清的回复"""

    if not state.metadata.get("awaiting_clarification", False):
        return state

    node = StagedParameterClarificationNode()
    current_stage = state.get_current_collection_stage()

    # 获取待回答的问题
    pending_questions = state.metadata.get("pending_questions", [])
    if not pending_questions:
        state.metadata["awaiting_clarification"] = False
        return state

    # 🔧 修复：直接从state恢复已收集的参数，不重新提取
    node.collected_params = state.metadata.get("extracted_parameters", {})

    # 解析用户回复
    parse_result = await node.parse_user_response(user_response, pending_questions)
    parsed_params = parse_result.get('parameters', {})
    skip_remaining = parse_result.get('skip_remaining', False)

    # 更新参数
    existing_params = state.metadata.get("extracted_parameters", {})
    existing_params.update(parsed_params)
    # state.metadata["extracted_parameters"] = existing_params
    node.collected_params.update(parsed_params)
    state.metadata["extracted_parameters"] = node.collected_params
    # 记录参数收集历史
    state.parameter_collection_history.append({
        "stage": current_stage,
        "retry_count": state.stage_retry_count.get(current_stage, 0),
        "user_response": user_response,
        "parsed_params": parsed_params,
        "timestamp": time.time()
    })

    logger.info(f"阶段 {current_stage} 收集到参数：{parsed_params}")

    # 清除等待状态
    state.metadata["awaiting_clarification"] = False
    state.metadata["pending_questions"] = []

    # 如果用户选择跳过
    if skip_remaining:
        # 对于技术参数阶段，允许跳过
        if current_stage == "technical":
            state.set_collection_stage("completed")
            state.metadata["clarification_completed"] = True

            # 🔧 确保应用智能默认值
            complete_params = node.apply_smart_defaults(node.collected_params)
            state.metadata["extracted_parameters"] = complete_params

            if streaming_callback:
                await streaming_callback({
                    "type": "clarification_complete",
                    "parameters": complete_params,
                    "message": "已使用智能推荐的技术参数，正在生成方案...",
                    "stage": "technical",
                    "skipped": True
                })
        else:
            # 对于必需阶段，使用默认值并继续
            stage_params = node.COLLECTION_STAGES[current_stage]["params"]
            for param in stage_params:
                if param not in existing_params:
                    default_value = node._get_stage_default(param, existing_params)
                    if default_value:
                        existing_params[param] = default_value

            state.metadata["extracted_parameters"] = existing_params

            # 继续下一阶段
            return await process_staged_parameter_clarification(state, streaming_callback)

    # 发送阶段确认
    if streaming_callback:
        stage_name = node.COLLECTION_STAGES[current_stage]["name"]
        await streaming_callback({
            "type": "stage_complete",
            "stage": current_stage,
            "stage_name": stage_name,
            "collected_params": parsed_params,
            "message": f"{stage_name}参数已收集"
        })

    # 继续下一个阶段或重试当前阶段
    return await process_staged_parameter_clarification(state, streaming_callback)