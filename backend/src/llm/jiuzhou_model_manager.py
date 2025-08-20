# backend/src/llm/jiuzhou_model_manager.py

import os
import torch
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
logger = logging.getLogger(__name__)


class JiuzhouModelManager:
    """九州模型管理器 - 处理模型加载和推理"""

    def __init__(self, model_path: str = None):
        self.model_path = model_path or "/root/autodl-tmp/virtual_constellation_assistant/backend/src/llm/JiuZhou-Instruct-v0.2"
        self.device = torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")
        self.model = None
        self.tokenizer = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._initialized = False

        # 加载示例案例
        self.example_cases = self._load_example_cases()

    def _load_example_cases(self) -> List[Dict]:
        """加载虚拟星座小样本案例"""
        examples_path = Path(__file__).parent.parent.parent.parent / "backend/data" / "example_constellations.json"
        try:
            with open(examples_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("example_plans", [])
        except Exception as e:
            logger.error(f"加载示例案例失败: {e}")
            return []

    def initialize(self):
        """延迟初始化模型"""
        if self._initialized:
            logger.info("九州模型已经初始化，跳过重复初始化")
            return

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                logger.info(f"正在加载九州模型 (尝试 {retry_count + 1}/{max_retries}): {self.model_path}")
                start_time = time.time()

                # 检查模型路径是否存在
                if not os.path.exists(self.model_path):
                    raise FileNotFoundError(f"模型路径不存在: {self.model_path}")

                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_path,
                    trust_remote_code=True
                )

                # 设置pad_token
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token

                # 根据可用设备加载模型
                if torch.cuda.is_available():
                    logger.info(f"使用GPU加载模型: {self.device}")
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_path,
                        torch_dtype=torch.bfloat16,
                        device_map="cuda:0",
                        trust_remote_code=True,
                        low_cpu_mem_usage=True  # 减少CPU内存使用
                    )
                else:
                    logger.info("使用CPU加载模型")
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_path,
                        torch_dtype=torch.float32,
                        device_map="cpu",
                        trust_remote_code=True,
                        low_cpu_mem_usage=True
                    )

                self._initialized = True
                load_time = time.time() - start_time
                logger.info(f"✅ 九州模型加载成功，耗时: {load_time:.2f}秒")

                # 预热模型
                self._warmup_model()

                return  # 成功加载，退出重试循环

            except Exception as e:
                retry_count += 1
                logger.error(f"九州模型加载失败 (尝试 {retry_count}/{max_retries}): {e}")

                if retry_count < max_retries:
                    wait_time = retry_count * 2  # 递增等待时间
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error("九州模型加载失败，已达到最大重试次数")
                    raise

    def _warmup_model(self):
        """预热模型，进行一次简单的推理"""
        try:
            logger.info("开始预热九州模型...")
            warmup_prompt = "你好"
            self._sync_generate(warmup_prompt, max_tokens=10)
            logger.info("九州模型预热完成")
        except Exception as e:
            logger.warning(f"模型预热失败: {e}")




    def _sync_generate(self, prompt: str, max_tokens: int = 600) -> str:
        """同步生成文本"""
        if not self._initialized:
            self.initialize()

        try:
            messages = [{"role": "user", "content": prompt}]

            # 修复：正确处理tokenizer输出
            # 先检查tokenizer是否有apply_chat_template方法
            if hasattr(self.tokenizer, 'apply_chat_template'):
                # 使用apply_chat_template
                input_text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                inputs = self.tokenizer(input_text, return_tensors="pt", padding=True, truncation=True)
            else:
                # 备用方法：直接使用prompt
                inputs = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True)

            # 将inputs移到正确的设备
            input_ids = inputs.input_ids.to(self.device)
            attention_mask = inputs.attention_mask.to(self.device) if 'attention_mask' in inputs else None

            with torch.no_grad():
                # 构建生成参数
                generate_kwargs = {
                    "input_ids": input_ids,
                    "max_new_tokens": max_tokens,
                    "do_sample": True,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "pad_token_id": self.tokenizer.pad_token_id,
                    "eos_token_id": self.tokenizer.eos_token_id,
                }

                # 如果有attention_mask，添加到参数中
                if attention_mask is not None:
                    generate_kwargs["attention_mask"] = attention_mask

                outputs_id = self.model.generate(**generate_kwargs)

            # 解码输出
            outputs = self.tokenizer.batch_decode(outputs_id, skip_special_tokens=True)[0]

            # 提取生成的部分（去除输入部分）
            if len(outputs) > len(prompt):
                response = outputs[len(prompt):].strip()
            else:
                response = outputs

            # 尝试提取助手回复
            if "assistant" in response:
                return response.split("assistant")[-1].strip()

            return response

        except Exception as e:
            logger.error(f"生成文本时出错: {e}")
            import traceback
            traceback.print_exc()
            # 返回一个默认响应而不是抛出异常
            return "抱歉，生成回复时出现错误。"

    async def identify_missing_parameters(
            self,
            user_context: str,
            existing_params: Dict[str, Any],
            conversation_history: str = "",
            domain_knowledge: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """使用九州模型智能识别缺失的参数

        Args:
            user_context: 用户的需求描述
            existing_params: 已经识别出的参数
            conversation_history: 对话历史
            domain_knowledge: 领域知识（可选）

        Returns:
            包含缺失参数列表和分析说明的字典
        """
        try:
            # 构建提示词
            prompt = self._build_identify_missing_params_prompt(
                user_context,
                existing_params,
                conversation_history,
                domain_knowledge
            )

            # 调用模型
            response = await self.generate(prompt, max_tokens=1000)

            # 解析响应
            result = self._parse_missing_params_response(response)

            return result

        except Exception as e:
            logger.error(f"识别缺失参数时出错: {e}")
            import traceback
            traceback.print_exc()
            return {
                "missing_parameters": [],
                "analysis_notes": f"AI分析失败: {str(e)}"
            }

    def _build_identify_missing_params_prompt(
            self,
            user_context: str,
            existing_params: Dict[str, Any],
            conversation_history: str,
            domain_knowledge: Dict[str, Any] = None
    ) -> str:
        """构建识别缺失参数的提示词"""

        # 领域知识示例
        domain_examples = """
    ## 虚拟星座设计的典型参数需求：

    ### 1. 水质监测场景
    必需参数：监测目标（水质）、观测区域、观测频率（建议每周2次以上）、光谱波段（多光谱或高光谱）
    重要参数：监测周期、分析需求（水质参数反演）、空间分辨率（10-30米）
    可选参数：时效性要求、输出格式

    ### 2. 农业监测场景  
    必需参数：监测目标（农业/作物）、观测区域、监测周期（覆盖生长季）、空间分辨率
    重要参数：光谱波段（含红边波段）、观测频率（关键生育期加密）、分析需求
    可选参数：精度要求、天气依赖性

    ### 3. 城市监测场景
    必需参数：监测目标（城市扩张/建筑）、观测区域、空间分辨率（高分辨率<5米）
    重要参数：观测频率、分析需求（变化检测）、监测周期
    可选参数：数据处理级别、输出格式

    ### 4. 灾害应急场景
    必需参数：监测目标（具体灾害类型）、观测区域、时效性要求（准实时）
    重要参数：观测频率（高频）、天气依赖性（全天候）、响应时间
    可选参数：数据安全要求、输出格式
    """

        prompt = f"""你是一个经验丰富的虚拟星座设计专家，精通遥感应用和卫星任务规划。
    请分析用户的需求，识别出设计虚拟星座方案所需但尚未提供的关键参数。

    {domain_examples}

    ## 参数重要性判断原则：
    1. **高重要性(high)**：缺少该参数将无法设计有效方案
    2. **中重要性(medium)**：该参数会显著影响方案质量
    3. **低重要性(low)**：该参数是锦上添花，可以使用默认值

    ## 用户需求：
    {user_context}

    ## 已识别参数：
    {self._format_existing_params(existing_params)}

    ## 对话历史：
    {conversation_history if conversation_history else "（无历史对话）"}

    ## 分析任务：
    1. 理解用户的核心需求和应用场景
    2. 基于专业知识判断哪些参数是必需的
    3. 考虑参数之间的关联性和依赖关系
    4. 避免过度询问，只识别真正重要的缺失参数
    5. 如果用户需求已经足够明确，可以只识别1-2个最关键的参数

    ## 输出要求：
    请以JSON格式输出分析结果，包含：
    - missing_parameters: 缺失参数列表
    - analysis_notes: 整体分析说明
    - scenario_type: 识别的场景类型

    示例输出：
    {{
      "scenario_type": "水质监测",
      "missing_parameters": [
        {{
          "parameter": "observation_frequency",
          "name": "观测频率",
          "importance": "high",
          "reason": "水质监测需要足够的时间分辨率来捕捉水体变化，建议每周2次以上",
          "suggested_default": "每周2次",
          "related_params": ["monitoring_period", "time_criticality"]
        }}
      ],
      "analysis_notes": "用户需要监测青海湖水质，已有区域和目标，但缺少时间维度的参数。水质变化具有时间动态性，需要明确观测频率。"
    }}
    """

        return prompt

    def _format_existing_params(self, params: Dict[str, Any]) -> str:
        """格式化已有参数用于提示词"""
        if not params:
            return "（暂无已识别参数）"

        formatted = []
        param_names = {
            "monitoring_target": "监测目标",
            "observation_area": "观测区域",
            "observation_frequency": "观测频率",
            "spatial_resolution": "空间分辨率",
            "monitoring_period": "监测周期",
            "spectral_bands": "光谱波段",
            "analysis_requirements": "分析需求",
            "time_criticality": "时效性要求"
        }

        for key, value in params.items():
            name = param_names.get(key, key)
            formatted.append(f"- {name}: {value}")

        return "\n".join(formatted)

    def _parse_missing_params_response(self, model_output: str) -> Dict[str, Any]:
        """解析模型识别的缺失参数"""
        try:
            import re
            import json

            # 提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', model_output)
            if json_match:
                result = json.loads(json_match.group())

                # 验证输出格式
                if 'missing_parameters' in result:
                    # 确保每个参数都有必要的字段
                    for param in result.get('missing_parameters', []):
                        if 'parameter' not in param:
                            continue
                        # 设置默认值
                        param.setdefault('importance', 'medium')
                        param.setdefault('reason', '需要该参数以完善方案设计')
                        param.setdefault('name', param['parameter'])

                    return result
                else:
                    logger.warning("模型输出缺少missing_parameters字段")
                    return {
                        "missing_parameters": [],
                        "analysis_notes": "AI分析结果格式不正确"
                    }

        except Exception as e:
            logger.error(f"解析缺失参数响应失败: {e}")
            logger.debug(f"原始输出: {model_output[:500]}...")

        return {
            "missing_parameters": [],
            "analysis_notes": "解析AI响应失败"
        }

    async def generate_contextual_questions(
            self,
            missing_params_info: List[Dict[str, Any]],
            user_profile: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """基于缺失参数信息生成上下文相关的问题

        这个方法会根据用户画像和场景生成更加个性化的问题
        """
        try:
            prompt = f"""作为虚拟星座设计助手，请为以下缺失参数生成友好、专业的澄清问题。

    ## 缺失参数信息：
    {json.dumps(missing_params_info, ensure_ascii=False, indent=2)}

    ## 用户画像：
    {json.dumps(user_profile, ensure_ascii=False) if user_profile else "普通用户"}

    ## 生成要求：
    1. 问题要自然、友好、易懂
    2. 根据参数的重要性调整问题的详细程度
    3. 高重要性参数要解释为什么需要这个信息
    4. 提供具体的例子帮助用户理解
    5. 考虑参数之间的关联，可以在一个问题中询问相关的多个参数

    ## 输出格式：
    {{
      "questions": [
        {{
          "parameter_key": "参数键名",
          "question": "问题文本",
          "explanation": "为什么需要这个信息（可选）",
          "examples": ["示例1", "示例2"],
          "quick_options": ["快速选项1", "快速选项2"],
          "allow_custom": true
        }}
      ]
    }}
    """

            response = await self.generate(prompt, max_tokens=800)
            return self._parse_contextual_questions(response)

        except Exception as e:
            logger.error(f"生成上下文问题失败: {e}")
            # 返回基础问题
            return self._generate_basic_questions(missing_params_info)

    def _parse_contextual_questions(self, model_output: str) -> List[Dict[str, Any]]:
        """解析生成的上下文问题"""
        try:
            import re
            import json

            json_match = re.search(r'\{[\s\S]*\}', model_output)
            if json_match:
                result = json.loads(json_match.group())
                return result.get('questions', [])
        except Exception as e:
            logger.error(f"解析上下文问题失败: {e}")

        return []

    def _generate_basic_questions(self, missing_params_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成基础问题作为备选"""
        questions = []

        for param_info in missing_params_info:
            param_key = param_info.get('parameter')
            param_name = param_info.get('name', param_key)
            reason = param_info.get('reason', '')

            question = {
                'parameter_key': param_key,
                'question': f'请提供{param_name}信息',
                'explanation': reason,
                'examples': [],
                'quick_options': [],
                'allow_custom': True
            }

            # 根据参数类型定制问题
            if param_key == 'observation_frequency':
                question['question'] = '您需要多长时间获取一次观测数据？'
                question['examples'] = ['每天1次', '每周2次', '每月1次']
                question['quick_options'] = ['每天1次', '每周2次', '每月1次', '实时监测']
            elif param_key == 'spatial_resolution':
                question['question'] = '您需要什么级别的图像清晰度？'
                question['examples'] = ['高清晰度(能看清建筑物)', '中等清晰度(能看清街道)', '一般清晰度(能看清区域)']
                question['quick_options'] = ['高(<5米)', '中(5-30米)', '低(>30米)']

            questions.append(question)

        return questions

    async def generate(self, prompt: str, max_tokens: int = 600) -> str:
        """异步生成文本"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self._sync_generate, prompt, max_tokens)

    async def extract_parameters(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """使用九州模型智能提取参数"""
        try:
            # 添加输入验证
            if not user_input or not isinstance(user_input, str):
                logger.warning(f"无效的用户输入: {type(user_input)}")
                return {}

            logger.info(f"开始提取参数，用户输入: {user_input[:100]}...")

            # 构建提示
            prompt = self._build_parameter_extraction_prompt(user_input, context)
            logger.debug(f"构建的提示词长度: {len(prompt)}")

            # 调用模型
            response = await self.generate(prompt, max_tokens=800)
            logger.info(f"模型响应长度: {len(response)}")

            # 解析输出
            extracted_params = self._parse_parameter_extraction(response)
            logger.info(f"成功提取参数: {extracted_params}")

            return extracted_params

        except Exception as e:
            logger.error(f"参数提取过程出错: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _build_parameter_extraction_prompt(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """构建参数提取的提示词 - 修复版本"""

        # 🔧 新增：检查是否是新需求
        is_new_requirement = context.get('is_new_requirement', False) if context else False

        # 使用更清晰的提示词，避免格式化问题
        prompt = """你是一个虚拟星座参数识别专家。你的任务是分析用户需求，识别出用户明确提到的参数，不要自行推断或补充。

    ## 重要原则：
    1. 只提取用户明确提到的参数
    2. 不要自行推断或补充参数值
    3. 如果用户没有明确说明某个参数，就不要提取该参数
    4. **时间参数必须保留完整的表达，包括数字和单位，例如："1个月"、"每天1次"、"每周2次"**
    5. **不要只提取数字，必须包含单位和完整描述**
    """

        if is_new_requirement:
            prompt += """
    4. **注意：这是一个新的监测需求，请忽略之前的对话历史，只关注当前用户输入**
    5. 不要混入任何历史对话中的参数
    """

        prompt += """
    ## 参数类别说明：
    1. **监测目标 (monitoring_target)**：
       - 只有当用户明确说"监测XX"、"观测XX"、"关注XX"时才提取
       - 例如："监测水质"→提取"水质变化"

    2. **观测区域 (observation_area)**：
       - 只有当用户提到具体地名时才提取
       - 例如："青海湖"、"北京市"、"长江流域"

    3. **观测频率 (observation_frequency)**：
       - 只有当用户明确说明频率时才提取
       - **必须保留完整表达**，例如：
         - "每天一次" → 提取 "每天1次"
         - "每周两次" → 提取 "每周2次"
         - "每月一次" → 提取 "每月1次"
       - **错误示例**：不要只提取 "1"，必须包含"每天"、"每周"等单位
    
    4. **监测周期 (monitoring_period)**：
       - 只有当用户明确说明时长时才提取
       - **必须保留完整表达**，例如：
         - "监测3个月" → 提取 "3个月"
         - "一年" → 提取 "1年"
         - "长期监测" → 提取 "长期监测"
       - **错误示例**：不要只提取 "3" 或 "1"，必须包含时间单位

    5. **空间分辨率 (spatial_resolution)**：
       - 只有当用户明确要求分辨率时才提取
       - 例如："高分辨率"、"10米分辨率"

    ## 输出格式要求：
    请严格按照以下JSON格式输出，不要添加任何其他文字：
    {
      "extracted_parameters": {
        "参数名": "具体参数"
      },
      "confidence": 0.9
    }

    ## 示例：
    用户输入："我需要监测柬埔寨的农业信息"
    输出：
    {
      "extracted_parameters": {
        "monitoring_target": "农业监测",
        "observation_area": "柬埔寨"
      },
      "confidence": 0.9
    }

    ## 当前用户需求：
    """ + user_input

        # 如果有已知参数且不是新需求，添加到提示中
        if context and context.get('existing_params') and not is_new_requirement:
            prompt += "\n\n## 已经识别的参数（请勿重复提取）：\n"
            for key, value in context['existing_params'].items():
                prompt += f"- {key}: {value}\n"

        prompt += "\n\n请分析上述用户需求，只提取明确提到的参数，直接输出JSON格式，不要有其他文字。"

        return prompt

    def _select_relevant_examples(self, user_input: str, num_examples: int = 3) -> List[Dict]:
        """选择相关的示例案例"""
        # 简单的关键词匹配，后续可以改进为语义相似度
        user_input_lower = user_input.lower()

        scored_examples = []
        for example in self.example_cases:
            score = 0
            # 检查关键词匹配
            for keyword in example.get('keywords', []):
                if keyword in user_input_lower:
                    score += 1

            # 检查监测目标匹配
            if 'parameters' in example:
                target = example['parameters'].get('monitoring_target', '')
                if target and target in user_input:
                    score += 2

            scored_examples.append((score, example))

        # 按分数排序并返回前N个
        scored_examples.sort(key=lambda x: x[0], reverse=True)
        return [ex[1] for ex in scored_examples[:num_examples]]

    def _parse_parameter_extraction(self, model_output: str) -> Dict[str, Any]:
        """解析模型输出的参数 - 增强版本（包含参数名称映射）"""

        # 定义参数名称映射表
        PARAMETER_NAME_MAPPING = {
            # 时间相关参数映射
            "monitoring_frequency": "observation_frequency",
            "monitor_frequency": "observation_frequency",
            "observing_frequency": "observation_frequency",
            "监测频率": "observation_frequency",

            # 周期相关参数映射
            "monitor_period": "monitoring_period",
            "observation_period": "monitoring_period",
            "monitoring_duration": "monitoring_period",
            "监测周期": "monitoring_period",

            # 目标相关参数映射
            "monitor_target": "monitoring_target",
            "observation_target": "monitoring_target",
            "monitoring_objective": "monitoring_target",
            "监测目标": "monitoring_target",

            # 区域相关参数映射
            "monitor_area": "observation_area",
            "monitoring_area": "observation_area",
            "observation_region": "observation_area",
            "观测区域": "observation_area",

            # 范围相关参数映射
            "cover_range": "coverage_range",
            "monitoring_range": "coverage_range",
            "observation_range": "coverage_range",
            "覆盖范围": "coverage_range"
        }

        try:
            # 清理模型输出
            cleaned_output = model_output.strip()
            logger.debug(f"模型原始输出: {cleaned_output[:500]}...")

            # 尝试多种方式提取JSON
            json_str = None

            # 方法1：直接尝试解析整个输出
            try:
                result = json.loads(cleaned_output)
                if isinstance(result, dict) and 'extracted_parameters' in result:
                    extracted_params = result.get('extracted_parameters', {})

                    # 应用参数名称映射
                    mapped_params = {}
                    for key, value in extracted_params.items():
                        # 检查是否需要映射
                        mapped_key = PARAMETER_NAME_MAPPING.get(key, key)
                        mapped_params[mapped_key] = value

                        if mapped_key != key:
                            logger.info(f"参数名称映射: {key} -> {mapped_key}")

                    return mapped_params
            except:
                pass

            # 方法2：查找JSON块
            import re
            json_pattern = r'\{[^{}]*\{[^{}]*\}[^{}]*\}'
            json_matches = re.findall(json_pattern, cleaned_output, re.DOTALL)

            for match in json_matches:
                try:
                    result = json.loads(match)
                    if isinstance(result, dict) and 'extracted_parameters' in result:
                        extracted_params = result.get('extracted_parameters', {})

                        # 应用参数名称映射
                        mapped_params = {}
                        for key, value in extracted_params.items():
                            mapped_key = PARAMETER_NAME_MAPPING.get(key, key)
                            mapped_params[mapped_key] = value

                            if mapped_key != key:
                                logger.info(f"参数名称映射: {key} -> {mapped_key}")

                        return mapped_params
                except:
                    continue

            # 方法3：更宽松的JSON提取
            brace_pattern = r'\{([^}]+)\}'
            brace_matches = re.findall(brace_pattern, cleaned_output, re.DOTALL)

            for content in brace_matches:
                try:
                    test_json = '{' + content + '}'
                    result = json.loads(test_json)
                    if isinstance(result, dict):
                        # 应用参数名称映射
                        mapped_params = {}
                        for key, value in result.items():
                            mapped_key = PARAMETER_NAME_MAPPING.get(key, key)
                            mapped_params[mapped_key] = value

                            if mapped_key != key:
                                logger.info(f"参数名称映射: {key} -> {mapped_key}")

                        return mapped_params
                except:
                    pass

            # 方法4：手动提取关键信息
            logger.warning("无法解析JSON，尝试手动提取参数")
            params = {}

            # 定义更全面的参数提取模式
            param_patterns = {
                # observation_frequency 的各种可能形式
                "observation_frequency": [
                    r'"observation_frequency"\s*:\s*"([^"]+)"',
                    r'"monitoring_frequency"\s*:\s*"([^"]+)"',
                    r'"monitor_frequency"\s*:\s*"([^"]+)"',
                    r'"observing_frequency"\s*:\s*"([^"]+)"'
                ],

                # monitoring_period 的各种可能形式
                "monitoring_period": [
                    r'"monitoring_period"\s*:\s*"([^"]+)"',
                    r'"monitor_period"\s*:\s*"([^"]+)"',
                    r'"observation_period"\s*:\s*"([^"]+)"',
                    r'"monitoring_duration"\s*:\s*"([^"]+)"'
                ],

                # monitoring_target 的各种可能形式
                "monitoring_target": [
                    r'"monitoring_target"\s*:\s*"([^"]+)"',
                    r'"monitor_target"\s*:\s*"([^"]+)"',
                    r'"observation_target"\s*:\s*"([^"]+)"',
                    r'"monitoring_objective"\s*:\s*"([^"]+)"'
                ],

                # observation_area 的各种可能形式
                "observation_area": [
                    r'"observation_area"\s*:\s*"([^"]+)"',
                    r'"monitor_area"\s*:\s*"([^"]+)"',
                    r'"monitoring_area"\s*:\s*"([^"]+)"',
                    r'"observation_region"\s*:\s*"([^"]+)"'
                ]
            }

            # 尝试所有模式
            for param_key, patterns in param_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, cleaned_output)
                    if match:
                        params[param_key] = match.group(1)
                        logger.info(f"手动提取到参数 {param_key}: {match.group(1)}")
                        break

            if params:
                logger.info(f"手动提取到参数: {params}")
                return params

        except Exception as e:
            logger.error(f"解析模型输出失败: {e}")
            logger.error(f"模型输出内容: {model_output[:200]}...")
            import traceback
            traceback.print_exc()

        # 如果所有方法都失败，使用基于规则的备用提取
        return self._fallback_extraction(model_output)

    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """备用的规则提取方法 - 增强版本"""
        params = {}

        # 监测目标提取
        if any(keyword in text for keyword in ['监测水质', '水质变化', '水质监测']):
            params['monitoring_target'] = '水质变化'
        elif any(keyword in text for keyword in ['监测农业', '农业监测', '作物监测']):
            params['monitoring_target'] = '农业监测'
        elif any(keyword in text for keyword in ['城市监测', '城市扩张', '建筑变化']):
            params['monitoring_target'] = '城市扩张'

        # 地理位置提取
        import re

        # 中国地名
        chinese_locations = ['青海湖', '长江', '黄河', '太湖', '洞庭湖', '鄱阳湖', '珠江', '北京', '上海', '武汉']
        for loc in chinese_locations:
            if loc in text:
                params['observation_area'] = loc
                break

        # 国家名称
        countries = ['柬埔寨', '越南', '泰国', '老挝', '缅甸', '马来西亚', '新加坡', '印度尼西亚', '菲律宾']
        for country in countries:
            if country in text:
                params['observation_area'] = country
                break

        # 频率提取
        freq_patterns = {
            '每天': '每天1次',
            '每日': '每天1次',
            '每周': '每周2次',
            '每月': '每月1次'
        }

        for pattern, value in freq_patterns.items():
            if pattern in text:
                params['observation_frequency'] = value
                break

        # 分辨率提取
        if any(keyword in text for keyword in ['高分辨率', '高清', '精细']):
            params['spatial_resolution'] = 'high'
        elif any(keyword in text for keyword in ['中分辨率', '中等分辨率']):
            params['spatial_resolution'] = 'medium'
        elif any(keyword in text for keyword in ['低分辨率', '粗分辨率']):
            params['spatial_resolution'] = 'low'

        logger.info(f"备用方法提取的参数: {params}")
        return params

    async def generate_clarification_questions(
            self,
            missing_params: List[str],
            context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """使用九州模型生成智能澄清问题"""
        try:
            prompt = self._build_question_generation_prompt(missing_params, context)
            response = await self.generate(prompt, max_tokens=1000)

            questions = self._parse_generated_questions(response, missing_params)
            return questions
        except Exception as e:
            logger.error(f"生成澄清问题出错: {e}")
            import traceback
            traceback.print_exc()
            # 返回默认问题
            return [self._get_default_question(param) for param in missing_params]

    def _build_question_generation_prompt(self, missing_params: List[str], context: Dict[str, Any]) -> str:
        """构建问题生成的提示词"""

        # 参数描述映射
        param_descriptions = {
            'observation_area': '观测区域 - 需要监测的地理位置',
            'monitoring_target': '监测目标 - 具体要监测什么内容',
            'observation_frequency': '观测频率 - 多久获取一次数据',
            'monitoring_period': '监测周期 - 总体监测时长',
            'spatial_resolution': '空间分辨率 - 影像的清晰度',
            'spectral_bands': '光谱波段 - 需要的数据类型',
            'analysis_requirements': '分析需求 - 需要进行的分析类型'
        }

        prompt = """你是一个友好的虚拟星座助手。用户想要设计虚拟星座方案，但缺少一些必要的参数信息。
请为每个缺失的参数生成一个自然、友好的澄清问题。

## 已知信息：
"""

        if context and context.get('existing_params'):
            for key, value in context['existing_params'].items():
                desc = param_descriptions.get(key, key)
                prompt += f"- {desc}: {value}\n"
        else:
            prompt += "- 暂无已知参数\n"

        prompt += "\n## 缺失的参数：\n"
        for param in missing_params:
            desc = param_descriptions.get(param, param)
            prompt += f"- {param}: {desc}\n"

        prompt += """
## 问题生成要求：
1. 每个问题都要自然、友好、易懂
2. 避免使用过于专业的术语，或者要解释清楚
3. 可以提供一些例子帮助用户理解
4. 根据已知信息调整问题的表述
5. 输出JSON格式，包含questions数组

## 输出格式示例：
{
  "questions": [
    {
      "parameter": "observation_area",
      "question": "您需要监测哪个地区呢？可以是具体的湖泊、城市或者区域，比如青海湖、北京市等",
      "examples": ["青海湖", "长江流域", "北京市五环内"],
      "hint": "💡 可以提供地名、行政区域或经纬度范围"
    }
  ]
}

请生成友好的澄清问题：
"""

        return prompt

    def _parse_generated_questions(self, model_output: str, missing_params: List[str]) -> List[Dict[str, Any]]:
        """解析生成的问题"""
        questions = []

        try:
            # 尝试解析JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', model_output)
            if json_match:
                result = json.loads(json_match.group())
                generated_questions = result.get('questions', [])

                # 确保每个缺失参数都有问题
                for param in missing_params:
                    question_data = next(
                        (q for q in generated_questions if q.get('parameter') == param),
                        None
                    )

                    if question_data:
                        questions.append({
                            'parameter_key': param,
                            'question': question_data.get('question', f"请提供{param}"),
                            'examples': question_data.get('examples', []),
                            'hint': question_data.get('hint', ''),
                            'type': 'text'  # 默认类型
                        })
                    else:
                        # 使用默认问题
                        questions.append(self._get_default_question(param))

        except Exception as e:
            logger.error(f"解析生成的问题失败: {e}")
            # 使用默认问题
            for param in missing_params:
                questions.append(self._get_default_question(param))

        return questions

    def _get_default_question(self, param: str) -> Dict[str, Any]:
        """获取默认问题"""
        default_questions = {
            'observation_area': {
                'parameter_key': 'observation_area',
                'question': '您需要监测哪个地理区域？',
                'examples': ['青海湖', '长江流域', '北京市'],
                'hint': '💡 可以是具体地名、行政区域或经纬度范围',
                'type': 'text'
            },
            'monitoring_target': {
                'parameter_key': 'monitoring_target',
                'question': '您的主要监测目标是什么？',
                'examples': ['水质变化', '植被覆盖', '城市扩张'],
                'hint': '💡 请尽可能具体描述您想观测的内容',
                'type': 'text'
            },
            'observation_frequency': {
                'parameter_key': 'observation_frequency',
                'question': '您需要多长时间获取一次观测数据？',
                'examples': ['每天1次', '每周2次', '每月1次'],
                'hint': '💡 频率越高，时间分辨率越好',
                'type': 'text'
            },
            'monitoring_period': {
                'parameter_key': 'monitoring_period',
                'question': '您计划监测多长时间？',
                'examples': ['1个月', '3个月', '1年', '长期监测'],
                'hint': '💡 是短期项目还是长期监测',
                'type': 'text'
            },
            'spatial_resolution': {
                'parameter_key': 'spatial_resolution',
                'question': '您需要什么级别的空间分辨率？',
                'examples': ['高分辨率(<5米)', '中分辨率(5-30米)', '低分辨率(>30米)'],
                'hint': '💡 分辨率越高，能看到的细节越多',
                'type': 'text'
            }
        }

        return default_questions.get(param, {
            'parameter_key': param,
            'question': f'请提供{param}信息',
            'examples': [],
            'hint': '',
            'type': 'text'
        })

    async def analyze_user_response(self, response: str, pending_questions: List[Dict]) -> Dict[str, Any]:
        """使用九州模型分析用户回复"""
        try:
            prompt = f"""分析用户对参数澄清问题的回复，提取参数值。

## 待回答的问题：
"""
            for q in pending_questions:
                prompt += f"- {q['parameter_key']}: {q['question']}\n"

            prompt += f"\n## 用户回复：\n{response}\n"
            prompt += """
## 任务：
1. 分析用户回复中包含的参数值
2. 将回复内容映射到对应的参数
3. 如果用户想跳过或使用默认值，标记为"skip"

输出JSON格式：
{
  "parsed_parameters": {
    "参数名": "参数值"
  },
  "skip_remaining": false
}
"""

            model_response = await self.generate(prompt, max_tokens=400)
            return self._parse_user_response_analysis(model_response)
        except Exception as e:
            logger.error(f"分析用户回复出错: {e}")
            return {
                "parsed_parameters": {},
                "skip_remaining": False
            }

    def _parse_user_response_analysis(self, model_output: str) -> Dict[str, Any]:
        """解析用户回复分析结果"""
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', model_output)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"解析用户回复分析失败: {e}")

        return {
            "parsed_parameters": {},
            "skip_remaining": False
        }

    def close(self):
        """清理资源"""
        self.executor.shutdown(wait=True)
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        torch.cuda.empty_cache()


# 单例模式
_jiuzhou_instance = None


def get_jiuzhou_manager() -> JiuzhouModelManager:
    """获取九州模型管理器单例"""
    global _jiuzhou_instance
    if _jiuzhou_instance is None:
        _jiuzhou_instance = JiuzhouModelManager()
    return _jiuzhou_instance