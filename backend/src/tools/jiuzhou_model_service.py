# backend/src/tools/jiuzhou_model_service.py - 修复版本

import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta

# 导入配置
import sys

project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from backend.config.config import settings, get_jiuzhou_config

logger = logging.getLogger(__name__)


class JiuzhouModelService:
    """九州地理知识问答模型服务 - 修复版"""

    def __init__(self):
        # 从配置中读取设置
        self.config = get_jiuzhou_config()
        self.base_url = self.config.base_url
        self.api_key = self.config.api_key
        self.publisher_name = self.config.publisher_name
        self.serving_name = self.config.serving_name
        self.model = self.config.model_name

        # 缓存相关配置
        self.enable_cache = self.config.enable_analysis_cache
        self.cache_max_size = self.config.cache_max_size
        self.cache_ttl = self.config.cache_ttl
        self._cache = {}  # 简单的内存缓存
        self._cache_timestamps = {}  # 缓存时间戳

        # 🔧 修复：系统提示词作为前缀，而不是system消息
        self.system_prompt_prefix = "作为一位专业的地理信息和遥感专家，请用中文回答。"

    def _get_cache_key(self, prompt: str, **kwargs) -> str:
        """生成缓存键"""
        cache_data = {
            'prompt': prompt[:200],  # 只使用前200个字符
            'temperature': kwargs.get('temperature', self.config.temperature),
            'model': self.model
        }
        return str(hash(json.dumps(cache_data, sort_keys=True)))

    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """从缓存获取结果"""
        if not self.enable_cache:
            return None

        if cache_key in self._cache:
            # 检查是否过期
            timestamp = self._cache_timestamps.get(cache_key, 0)
            if datetime.now().timestamp() - timestamp < self.cache_ttl:
                logger.debug(f"缓存命中: {cache_key}")
                return self._cache[cache_key]
            else:
                # 清理过期缓存
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]

        return None

    def _save_to_cache(self, cache_key: str, value: str):
        """保存到缓存"""
        if not self.enable_cache:
            return

        # 检查缓存大小
        if len(self._cache) >= self.cache_max_size:
            # 删除最旧的缓存项
            oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
            del self._cache[oldest_key]
            del self._cache_timestamps[oldest_key]

        self._cache[cache_key] = value
        self._cache_timestamps[cache_key] = datetime.now().timestamp()
        logger.debug(f"保存到缓存: {cache_key}")

    async def analyze_user_requirements(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """使用九州模型深度分析用户需求"""

        if not self.config.enable_ai_enhancement:
            logger.info("AI增强功能已禁用")
            return {"success": False, "error": "AI enhancement disabled"}

        prompt = self._build_requirement_analysis_prompt(user_input, context)

        # 检查缓存
        cache_key = self._get_cache_key(prompt)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            try:
                return json.loads(cached_result)
            except:
                pass

        try:
            response = await self._call_model(
                prompt,
                stream=False,  # 分析任务不使用流式
                temperature=0.7  # 🔧 修复：使用正常温度而不是0.35
            )
            result = self._parse_requirement_analysis(response)

            # 缓存结果
            if result.get("success", False):
                self._save_to_cache(cache_key, json.dumps(result))

            return result
        except Exception as e:
            logger.error(f"九州模型分析需求失败: {e}")
            return {"success": False, "error": str(e)}

    async def generate_intelligent_questions(
            self,
            user_input: str,
            missing_params: List[str],
            existing_params: Dict[str, Any],
            param_definitions: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成智能化的澄清问题"""

        if not self.config.enable_intelligent_questions:
            logger.info("智能问题生成功能已禁用")
            return []

        prompt = self._build_intelligent_question_prompt(
            user_input, missing_params, existing_params, param_definitions
        )

        try:
            response = await self._call_model(
                prompt,
                stream=False,
                temperature=0.8  # 🔧 修复：使用合适的温度
            )
            return self._parse_clarification_questions(response)
        except Exception as e:
            logger.error(f"九州模型生成问题失败: {e}")
            return []

    async def extract_implicit_parameters(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """提取文本中的隐含参数"""

        if not self.config.enable_implicit_parameter_extraction:
            logger.info("隐含参数提取功能已禁用")
            return {}

        # 🔧 修复：将系统提示整合到用户消息中
        prompt = f"""{self.system_prompt_prefix}深度分析以下文本，提取所有显式和隐含的监测需求参数。

文本：{text}

请分析并提取：
1. 显式参数（直接提到的）
2. 隐含参数（可以推断的）
3. 关联参数（相关但未提及的）

例如：
- "监测水质" → 隐含需要多光谱数据、定期观测
- "城市扩张" → 隐含需要高分辨率、变化检测
- "应急响应" → 隐含需要高时效性、全天候观测

返回JSON格式：
{{
    "explicit_params": {{
        "参数名": "参数值"
    }},
    "implicit_params": {{
        "参数名": {{
            "value": "推断值",
            "reason": "推断理由",
            "confidence": 0.9
        }}
    }},
    "suggested_params": {{
        "参数名": {{
            "value": "建议值",
            "reason": "建议理由"
        }}
    }}
}}"""

        try:
            response = await self._call_model(
                prompt,
                stream=False,
                temperature=0.6  # 🔧 修复：使用适中的温度
            )
            return self._parse_json_response(response)
        except Exception as e:
            logger.error(f"提取隐含参数失败: {e}")
            return {}

    async def _call_model(
            self,
            prompt: str,
            stream: bool = True,
            temperature: float = None,
            max_tokens: int = None
    ) -> str:
        """调用九州模型API - 修复版"""

        if temperature is None:
            temperature = self.config.temperature
        if max_tokens is None:
            max_tokens = self.config.max_tokens

        # 🔧 修复：确保温度在合理范围内
        temperature = max(0.1, min(1.0, temperature))

        # 🔧 修复：不使用system消息，将系统提示整合到user消息中
        enhanced_prompt = f"{self.system_prompt_prefix}\n\n{prompt}"

        # 构建请求体
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": enhanced_prompt
                }
            ],
            "stream": stream,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": self.config.top_p
        }

        # 构建请求头
        headers = {
            'Content-Type': 'application/json',
            'publisher-name': self.publisher_name,
            'api-key': self.api_key,
            'serving-name-en': self.serving_name,
        }

        logger.debug(f"九州API请求URL: {self.base_url}")
        logger.debug(f"九州API请求温度: {temperature}")

        timeout = aiohttp.ClientTimeout(total=self.config.timeout)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                        self.base_url,
                        headers=headers,
                        json=payload
                ) as response:
                    response_text = await response.text()

                    if response.status != 200:
                        logger.error(f"九州API返回错误状态码: {response.status}")
                        logger.error(f"错误响应内容: {response_text}")
                        raise Exception(f"API请求失败: {response.status}, {response_text}")

                    if stream:
                        # 🔧 修复：处理流式响应，正确处理None值
                        full_content = ""
                        lines = response_text.strip().split('\n')

                        for line in lines:
                            line = line.strip()
                            if line.startswith('data: '):
                                try:
                                    # 处理特殊的结束标记
                                    if line == 'data: [DONE]':
                                        break

                                    data = json.loads(line[6:])
                                    if 'choices' in data and data['choices']:
                                        delta = data['choices'][0].get('delta', {})
                                        # 🔧 修复：检查content是否为None
                                        if 'content' in delta and delta['content'] is not None:
                                            full_content += delta['content']
                                except json.JSONDecodeError as e:
                                    logger.debug(f"解析流式响应行失败: {line}, 错误: {e}")
                                    continue

                        logger.debug(f"流式响应完整内容: {full_content[:200]}...")
                        return full_content
                    else:
                        # 处理非流式响应
                        try:
                            result = json.loads(response_text)
                            if 'choices' in result and result['choices']:
                                content = result['choices'][0]['message']['content']
                                logger.debug(f"非流式响应内容: {content[:200]}...")
                                return content
                            else:
                                logger.error(f"API返回格式错误: {response_text[:200]}")
                                raise Exception("API返回格式错误")
                        except json.JSONDecodeError as e:
                            logger.error(f"解析非流式响应失败: {e}")
                            logger.error(f"原始响应: {response_text[:500]}")
                            raise Exception(f"API响应解析失败: {e}")

        except asyncio.TimeoutError:
            logger.error(f"九州API调用超时 ({self.config.timeout}秒)")
            raise Exception(f"API调用超时")
        except aiohttp.ClientError as e:
            logger.error(f"网络请求错误: {e}")
            raise Exception(f"网络请求错误: {e}")
        except Exception as e:
            logger.error(f"调用九州API时发生错误: {e}")
            raise

    def _build_requirement_analysis_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """构建需求分析提示词"""

        context_str = ""
        if context:
            if context.get("conversation_history"):
                context_str += f"\n对话历史：{context['conversation_history']}"
            if context.get("user_profile"):
                context_str += f"\n用户特征：{context['user_profile']}"

        return f"""深度分析用户的卫星监测需求，识别所有参数需求（显式和隐含）。

用户输入：{user_input}{context_str}

请分析：
1. 用户的核心监测意图
2. 已明确提供的参数
3. 可以推断的隐含参数
4. 可能需要但未提及的参数
5. 参数之间的关联性

返回JSON格式：
{{
    "intent": {{
        "primary": "主要意图",
        "secondary": ["次要意图1", "次要意图2"],
        "domain": "应用领域"
    }},
    "provided_params": {{
        "参数名": {{
            "value": "参数值",
            "confidence": 0.9,
            "source": "explicit/implicit"
        }}
    }},
    "missing_params": {{
        "参数名": {{
            "importance": "high/medium/low",
            "reason": "为什么需要",
            "default_applicable": true/false
        }}
    }},
    "param_relationships": [
        {{
            "params": ["参数1", "参数2"],
            "relationship": "关系描述"
        }}
    ],
    "recommendations": ["建议1", "建议2"]
}}"""

    def _build_intelligent_question_prompt(
            self,
            user_input: str,
            missing_params: List[str],
            existing_params: Dict[str, Any],
            param_definitions: Dict[str, Any]
    ) -> str:
        """构建智能问题生成提示词"""

        param_info = {}
        for param in missing_params:
            for category in param_definitions.get("parameter_categories", {}).values():
                if param in category.get("parameters", {}):
                    param_info[param] = category["parameters"][param]

        return f"""基于用户需求和上下文，生成自然、智能的参数澄清问题。

用户需求：{user_input}
已知参数：{json.dumps(existing_params, ensure_ascii=False)}
需澄清参数：{missing_params}
参数定义：{json.dumps(param_info, ensure_ascii=False)}

生成要求：
1. 问题要自然流畅，像专业顾问的提问
2. 根据用户需求定制问题内容
3. 提供相关的选项或示例，但要贴合用户场景
4. 问题之间要有逻辑关联
5. 优先级要合理（重要参数先问）
6. 语气友好专业

对每个参数生成：
{{
    "parameter_key": "参数名",
    "question": "定制化的澄清问题",
    "type": "options/text/numeric",
    "options": [
        {{"value": "选项值", "label": "选项描述", "scenario": "适用场景"}}
    ],
    "examples": ["贴合用户需求的示例"],
    "hint": "智能提示信息",
    "priority": 1-10,
    "context_dependent": true/false,
    "follow_up": "可能的后续问题"
}}

返回JSON数组格式。"""

    def _parse_requirement_analysis(self, response: str) -> Dict[str, Any]:
        """解析需求分析结果"""
        try:
            # 提取JSON部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                result["success"] = True
                return result
        except Exception as e:
            logger.error(f"解析需求分析结果失败: {e}, 原始响应: {response[:200]}")

        return {
            "success": False,
            "intent": {"primary": "", "secondary": [], "domain": ""},
            "provided_params": {},
            "missing_params": {},
            "recommendations": []
        }

    def _parse_clarification_questions(self, response: str) -> List[Dict[str, Any]]:
        """解析澄清问题"""
        try:
            # 提取JSON数组部分
            json_start = response.find('[')
            json_end = response.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"解析澄清问题失败: {e}")

        return []

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """通用JSON响应解析"""
        try:
            # 尝试直接解析
            return json.loads(response)
        except:
            try:
                # 提取JSON部分
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except Exception as e:
                logger.error(f"解析JSON响应失败: {e}")

        return {}

    async def optimize_question_flow(
            self,
            questions: List[Dict[str, Any]],
            user_profile: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """优化问题流程，使其更自然"""

        prompt = f"""优化以下参数澄清问题，使其更自然、更符合对话流程。

原始问题列表：
{json.dumps(questions, ensure_ascii=False, indent=2)}

用户画像：{json.dumps(user_profile or {}, ensure_ascii=False)}

优化要求：
1. 调整问题顺序，从易到难，从概括到具体
2. 合并相关问题，避免重复
3. 使问题更口语化、更友好
4. 根据参数关联性分组
5. 添加引导性说明

返回优化后的问题列表（JSON格式）。"""

        try:
            response = await self._call_model(
                prompt,
                stream=False,
                temperature=0.7
            )
            return self._parse_clarification_questions(response)
        except Exception as e:
            logger.error(f"优化问题流程失败: {e}")
            return questions

    async def analyze_clarification_response(
            self,
            user_response: str,
            questions: List[Dict[str, Any]],
            context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """智能分析用户的澄清回复"""

        prompt = f"""分析用户对参数澄清问题的回复，提取参数值并识别新的信息。

澄清问题：
{json.dumps(questions, ensure_ascii=False, indent=2)}

用户回复：{user_response}

对话上下文：{json.dumps(context, ensure_ascii=False)}

请分析：
1. 用户回答了哪些参数
2. 回答是否明确
3. 是否包含新的需求信息
4. 是否需要进一步澄清

返回JSON格式：
{{
    "answered_params": {{
        "参数名": "提取的值"
    }},
    "unclear_params": {{
        "参数名": "需要澄清的原因"
    }},
    "new_requirements": ["新需求1", "新需求2"],
    "follow_up_needed": true/false,
    "confidence": 0.9
}}"""

        try:
            response = await self._call_model(
                prompt,
                stream=False,
                temperature=0.6
            )
            return self._parse_json_response(response)
        except Exception as e:
            logger.error(f"分析澄清回复失败: {e}")
            return {}

    async def generate_parameter_recommendations(
            self,
            partial_params: Dict[str, Any],
            user_intent: str
    ) -> Dict[str, Any]:
        """基于部分参数生成智能推荐"""

        if not self.config.enable_parameter_recommendations:
            logger.info("参数推荐功能已禁用")
            return {}

        prompt = f"""基于用户意图和已有参数，推荐其他参数的最优值。

用户意图：{user_intent}
已有参数：{json.dumps(partial_params, ensure_ascii=False, indent=2)}

请推荐：
1. 其他参数的最优值
2. 参数组合的协同效应
3. 可能的优化建议

考虑因素：
- 技术可行性
- 成本效益
- 数据质量
- 实际应用效果

返回JSON格式的推荐。"""

        try:
            response = await self._call_model(
                prompt,
                stream=False,
                temperature=0.7
            )
            return self._parse_json_response(response)
        except Exception as e:
            logger.error(f"生成参数推荐失败: {e}")
            return {}

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("已清空九州模型缓存")


# 创建单例实例
jiuzhou_service = JiuzhouModelService()


# 便捷函数
async def analyze_requirements_with_jiuzhou(user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """使用九州模型分析用户需求"""
    return await jiuzhou_service.analyze_user_requirements(user_input, context)


async def generate_smart_questions(
        user_input: str,
        missing_params: List[str],
        existing_params: Dict[str, Any],
        param_definitions: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """使用九州模型生成智能澄清问题"""
    return await jiuzhou_service.generate_intelligent_questions(
        user_input, missing_params, existing_params, param_definitions
    )


async def extract_implicit_params(text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """提取隐含参数"""
    return await jiuzhou_service.extract_implicit_parameters(text, context)


async def analyze_user_clarification(
        response: str,
        questions: List[Dict[str, Any]],
        context: Dict[str, Any]
) -> Dict[str, Any]:
    """分析用户的澄清回复"""
    return await jiuzhou_service.analyze_clarification_response(response, questions, context)


async def get_param_recommendations(
        partial_params: Dict[str, Any],
        user_intent: str
) -> Dict[str, Any]:
    """获取参数推荐"""
    return await jiuzhou_service.generate_parameter_recommendations(partial_params, user_intent)


# 测试修复
if __name__ == "__main__":
    async def test_fixed_service():
        print("测试修复后的九州模型服务...")

        # 测试1：基础调用
        print("\n1. 测试基础调用（无system消息）")
        result = await jiuzhou_service._call_model(
            "什么是遥感卫星？",
            stream=False,
            temperature=0.7
        )
        print(f"响应: {result[:100]}...")

        # 测试2：流式调用
        print("\n2. 测试流式调用")
        result = await jiuzhou_service._call_model(
            "请介绍一下卫星监测水质的方法",
            stream=True,
            temperature=0.7
        )
        print(f"响应: {result[:100]}...")

        # 测试3：需求分析
        print("\n3. 测试需求分析功能")
        analysis = await analyze_requirements_with_jiuzhou(
            "我需要监测青海湖的水质变化"
        )
        print(f"分析结果: {json.dumps(analysis, ensure_ascii=False, indent=2)}")


    asyncio.run(test_fixed_service())