# backend/src/llm/multi_model_manager.py

import json
import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from backend.config.ai_config import ai_settings

logger = logging.getLogger(__name__)

class MultiModelManager:
    """多模型管理器 - 支持ChatGPT、通义千问、DeepSeek"""
    
    def __init__(self):
        self.model_configs = {
            "chatgpt": {
                "api_key": ai_settings.openai_api_key,
                "base_url": ai_settings.openai_base_url,
                "model": "gpt-3.5-turbo"
            },
            "qwen": {
                "api_key": ai_settings.qwen_api_key,
                "base_url": "https://dashscope.aliyuncs.com",  # 使用固定的DashScope地址
                "model": "qwen-plus"  # 使用qwen-plus模型
            },
            "deepseek": {
                "api_key": ai_settings.deepseek_api_key,
                "base_url": ai_settings.deepseek_base_url,
                "model": "deepseek-chat"
            }
        }
    
    async def query_satellite_info(self, user_query: str, model_name: str, satellites_context: str = "") -> Dict[str, Any]:
        """查询卫星信息并提取筛选参数"""
        try:
            # 构建提示词
            prompt = self._build_satellite_query_prompt(user_query, satellites_context)
            
            # 调用对应模型
            if model_name not in self.model_configs:
                raise ValueError(f"不支持的模型: {model_name}")
                
            response = await self._call_model_api(model_name, prompt)
            
            # 解析响应
            result = self._parse_satellite_response(response)
            
            return result
            
        except Exception as e:
            logger.error(f"查询卫星信息失败: {e}")
            return {
                "answer": f"抱歉，处理您的查询时出现错误: {str(e)}",
                "filters": {},
                "search_query": ""
            }
    
    def _build_satellite_query_prompt(self, user_query: str, satellites_context: str) -> str:
        """构建卫星查询提示词"""
        prompt = f"""你是一个专业的卫星查询助手。用户想要查询卫星信息，请根据用户的描述：
1. 给出友好的自然语言回答
2. 提取用户查询中的关键筛选条件
3.如果用户说"清除"或"重置"，返回空的filters
用户查询: {user_query}
当前卫星数据库信息: {satellites_context[:1000]}
特别注意：satellites_context如果是字典，其中currentFiltered表示当前筛选后的卫星数量。
请以JSON格式回复，包含以下字段：
{{
    "answer": "自然语言回答，告诉用户你理解了他们的需求并已进行筛选",
    "filters": {{
        "status": ["运行状态列表，如Operational、Nonoperational等"],
        "owner": ["所有者/国家列表，如China、United States等"],
        "orbitType": ["轨道类型列表，如LLEO_S、GEO_S等"],
        "launchDateRange": {{"start": "开始日期", "end": "结束日期"}}
    }},
    "search_query": "用于名称搜索的关键词"
}}

关键映射：
- 中国/China → owner: ["China", "中国"]
- 美国/USA → owner: ["United States", "美国"]
- 正在运行/operational → status: ["Operational"]
- 太阳同步轨道 → orbitType: ["LLEO_S"]
- 地球同步轨道 → orbitType: ["GEO_S"]
- 高分/GF → search_query: "高分"
- 风云 → search_query: "风云"
"""
        return prompt
    
    async def _call_model_api(self, model_name: str, prompt: str) -> str:
        """调用模型API"""
        config = self.model_configs[model_name]
        
        if not config["api_key"]:
            raise ValueError(f"{model_name} API密钥未配置")
        
        # 统一使用OpenAI兼容格式
        data = {
            "model": config["model"],
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        # 设置不同模型的endpoint
        if model_name == "qwen":
            # 通义千问使用OpenAI兼容接口
            endpoint = f"{config['base_url']}/compatible-mode/v1/chat/completions"
        else:
            # ChatGPT和DeepSeek使用标准OpenAI接口
            endpoint = f"{config['base_url']}/chat/completions"
        
        # 设置超时时间，解决ChatGPT超时问题
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                logger.info(f"🔗 调用 {model_name} API: {endpoint}")
                
                async with session.post(endpoint, headers=headers, json=data) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"❌ {model_name} API调用失败: {resp.status} - {error_text}")
                        raise ValueError(f"API调用失败: {resp.status} - {error_text}")
                    
                    # 检查响应内容类型
                    content_type = resp.headers.get('content-type', '')
                    if 'application/json' not in content_type:
                        error_text = await resp.text()
                        logger.error(f"❌ {model_name} 返回非JSON响应: {content_type} - {error_text[:200]}")
                        raise ValueError(f"API返回非JSON响应: {content_type}")
                    
                    response_data = await resp.json()
                    logger.info(f"✅ {model_name} API调用成功")
                    
                    # 所有模型都使用OpenAI兼容格式的响应
                    return response_data["choices"][0]["message"]["content"]
                    
        except asyncio.TimeoutError:
            logger.error(f"❌ {model_name} API调用超时")
            raise ValueError(f"API调用超时，请检查网络连接")
        except aiohttp.ClientError as e:
            logger.error(f"❌ {model_name} 网络连接错误: {str(e)}")
            raise ValueError(f"网络连接错误: {str(e)}")
        except Exception as e:
            logger.error(f"❌ {model_name} API调用异常: {str(e)}")
            raise ValueError(f"API调用异常: {str(e)}")
    
    def _parse_satellite_response(self, response: str) -> Dict[str, Any]:
        """解析模型响应"""
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # 验证和清理结果
                clean_result = {
                    "answer": result.get("answer", "已为您筛选相关卫星"),
                    "filters": self._clean_filters(result.get("filters", {})),
                    "search_query": result.get("search_query", "")
                }
                
                return clean_result
            else:
                # 如果没有找到JSON，返回纯文本回答
                return {
                    "answer": response,
                    "filters": {},
                    "search_query": ""
                }
                
        except Exception as e:
            logger.error(f"解析响应失败: {e}")
            return {
                "answer": response[:200] + "..." if len(response) > 200 else response,
                "filters": {},
                "search_query": ""
            }
    
    def _clean_filters(self, filters: Dict) -> Dict:
        """清理和验证筛选条件"""
        clean_filters = {}
        
        # 处理数组字段
        for field in ["status", "owner", "orbitType"]:
            if field in filters and isinstance(filters[field], list):
                clean_filters[field] = filters[field]
        
        # 处理日期范围
        if "launchDateRange" in filters and isinstance(filters["launchDateRange"], dict):
            date_range = filters["launchDateRange"]
            if "start" in date_range or "end" in date_range:
                clean_filters["launchDateRange"] = {
                    "start": date_range.get("start", ""),
                    "end": date_range.get("end", "")
                }
        
        return clean_filters

# 全局实例
_multi_model_manager = None

def get_multi_model_manager() -> MultiModelManager:
    """获取多模型管理器单例"""
    global _multi_model_manager
    if _multi_model_manager is None:
        _multi_model_manager = MultiModelManager()
    return _multi_model_manager