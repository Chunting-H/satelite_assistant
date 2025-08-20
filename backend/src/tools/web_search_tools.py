# backend/src/tools/web_search_tools.py

import os
import logging
import aiohttp
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class WebSearchTool:
    """网络搜索工具 - 支持多种搜索引擎"""

    def __init__(self):
        self.tavily_api_key = os.environ.get("TAVILY_API_KEY", "")
        self.serp_api_key = os.environ.get("SERP_API_KEY", "")
        self.bing_api_key = os.environ.get("BING_API_KEY", "")

        # 搜索API配置
        self.search_apis = {
            "tavily": {
                "url": "https://api.tavily.com/search",
                "enabled": bool(self.tavily_api_key),
                "headers": {"api-key": self.tavily_api_key}
            },
            "serp": {
                "url": "https://serpapi.com/search.json",
                "enabled": bool(self.serp_api_key),
                "params": {"api_key": self.serp_api_key}
            },
            "bing": {
                "url": "https://api.bing.microsoft.com/v7.0/search",
                "enabled": bool(self.bing_api_key),
                "headers": {"Ocp-Apim-Subscription-Key": self.bing_api_key}
            }
        }

        # 设置默认搜索提供商
        self.default_provider = self._get_available_provider()

    def _get_available_provider(self) -> Optional[str]:
        """获取可用的搜索提供商"""
        for provider, config in self.search_apis.items():
            if config["enabled"]:
                logger.info(f"使用搜索提供商: {provider}")
                return provider
        logger.warning("没有配置任何搜索API密钥")
        return None

    async def search(self, query: str, max_results: int = 5, search_type: str = "general") -> List[Dict[str, Any]]:
        """执行网络搜索

        Args:
            query: 搜索查询
            max_results: 最大结果数
            search_type: 搜索类型 (general, satellite, technical)

        Returns:
            搜索结果列表
        """
        if not self.default_provider:
            logger.warning("没有可用的搜索提供商，返回空结果")
            return []

        # 根据搜索类型优化查询
        optimized_query = self._optimize_query(query, search_type)

        try:
            if self.default_provider == "tavily":
                return await self._search_tavily(optimized_query, max_results)
            elif self.default_provider == "serp":
                return await self._search_serp(optimized_query, max_results)
            elif self.default_provider == "bing":
                return await self._search_bing(optimized_query, max_results)
            else:
                return []
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            return []

    def _optimize_query(self, query: str, search_type: str) -> str:
        """根据搜索类型优化查询"""
        if search_type == "satellite":
            # 添加卫星相关关键词
            keywords = ["satellite", "遥感", "对地观测", "remote sensing", "earth observation"]
            query = f"{query} {' OR '.join(keywords)}"
        elif search_type == "technical":
            # 添加技术规格关键词
            keywords = ["specifications", "technical data", "parameters", "技术参数"]
            query = f"{query} {' '.join(keywords)}"

        return query

    async def _search_tavily_with_bearer(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """使用Bearer token方式调用Tavily API"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": max_results,
                    "include_answer": True,
                    "include_raw_content": False
                }

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.tavily_api_key}"  # Bearer token方式
                }

                async with session.post(self.search_apis["tavily"]["url"],
                                        json=payload,
                                        headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_tavily_results(data)
                    else:
                        error_text = await response.text()
                        logger.error(f"Tavily API Bearer认证错误: {response.status}, 响应: {error_text}")
                        return []

        except Exception as e:
            logger.error(f"Tavily API Bearer请求异常: {str(e)}")
            return []

    async def _search_tavily(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """使用Tavily API搜索"""
        try:
            async with aiohttp.ClientSession() as session:
                # 方案1：将API key放在请求体中
                payload = {
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": max_results,
                    "include_answer": True,
                    "include_raw_content": False,
                    "api_key": self.tavily_api_key  # API key在payload中
                }

                headers = {
                    "Content-Type": "application/json"
                }

                logger.debug(f"Tavily API请求: URL={self.search_apis['tavily']['url']}, Query={query}")

                async with session.post(self.search_apis["tavily"]["url"],
                                        json=payload,
                                        headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Tavily搜索成功，返回 {len(data.get('results', []))} 条结果")
                        return self._format_tavily_results(data)
                    else:
                        error_text = await response.text()
                        logger.error(f"Tavily API错误: {response.status}, 响应: {error_text}")

                        # 如果方案1失败，尝试方案2
                        if response.status == 401:
                            logger.info("尝试使用Bearer token认证方式")
                            return await self._search_tavily_with_bearer(query, max_results)

                        return []

        except Exception as e:
            logger.error(f"Tavily API请求异常: {str(e)}")
            return []

    def _format_tavily_results(self, data: Dict) -> List[Dict[str, Any]]:
        """格式化Tavily搜索结果"""
        results = []

        # 添加答案摘要
        if "answer" in data:
            results.append({
                "title": "AI总结",
                "snippet": data["answer"],
                "url": "",
                "source": "Tavily AI",
                "relevance_score": 1.0
            })

        # 添加搜索结果
        for result in data.get("results", []):
            results.append({
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "url": result.get("url", ""),
                "source": result.get("source", ""),
                "relevance_score": result.get("score", 0.5)
            })

        return results

    async def _search_serp(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """使用SerpAPI搜索"""
        async with aiohttp.ClientSession() as session:
            params = {
                "q": query,
                "api_key": self.serp_api_key,
                "num": max_results,
                "engine": "google"
            }

            async with session.get(self.search_apis["serp"]["url"], params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._format_serp_results(data)
                else:
                    logger.error(f"SerpAPI错误: {response.status}")
                    return []

    def _format_serp_results(self, data: Dict) -> List[Dict[str, Any]]:
        """格式化SerpAPI搜索结果"""
        results = []

        for result in data.get("organic_results", []):
            results.append({
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "url": result.get("link", ""),
                "source": result.get("source", ""),
                "relevance_score": 0.8
            })

        return results

    async def _search_bing(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """使用Bing API搜索"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Ocp-Apim-Subscription-Key": self.bing_api_key
            }

            params = {
                "q": query,
                "count": max_results,
                "textFormat": "HTML"
            }

            async with session.get(self.search_apis["bing"]["url"],
                                   headers=headers,
                                   params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._format_bing_results(data)
                else:
                    logger.error(f"Bing API错误: {response.status}")
                    return []

    def _format_bing_results(self, data: Dict) -> List[Dict[str, Any]]:
        """格式化Bing搜索结果"""
        results = []

        for result in data.get("webPages", {}).get("value", []):
            results.append({
                "title": result.get("name", ""),
                "snippet": result.get("snippet", ""),
                "url": result.get("url", ""),
                "source": "Bing",
                "relevance_score": 0.7
            })

        return results

    async def search_satellite_info(self, satellite_names: List[str]) -> Dict[str, List[Dict]]:
        """搜索卫星相关信息

        Args:
            satellite_names: 卫星名称列表

        Returns:
            卫星名称到搜索结果的映射
        """
        results = {}

        # 并发搜索所有卫星
        tasks = []
        for satellite in satellite_names:
            query = f"{satellite} 卫星 技术参数 specifications"
            task = self.search(query, max_results=3, search_type="satellite")
            tasks.append(task)

        search_results = await asyncio.gather(*tasks)

        # 组织结果
        for satellite, result in zip(satellite_names, search_results):
            results[satellite] = result

        return results

    async def search_application_cases(self, monitoring_target: str, satellites: List[str]) -> List[Dict]:
        """搜索应用案例

        Args:
            monitoring_target: 监测目标
            satellites: 使用的卫星列表

        Returns:
            相关应用案例
        """
        # 构建搜索查询
        satellite_str = " OR ".join(satellites[:3])  # 限制卫星数量避免查询过长
        query = f"{monitoring_target} {satellite_str} 应用案例 case study"

        results = await self.search(query, max_results=5, search_type="general")

        # 过滤和排序结果
        filtered_results = []
        for result in results:
            # 检查相关性
            if any(sat in result.get("snippet", "") for sat in satellites):
                filtered_results.append(result)

        return filtered_results

    async def search_latest_developments(self, topic: str) -> List[Dict]:
        """搜索最新发展动态

        Args:
            topic: 搜索主题

        Returns:
            最新动态列表
        """
        # 添加时间限定词
        query = f"{topic} latest news 2024 最新进展"

        results = await self.search(query, max_results=5, search_type="general")

        # 按时间排序（如果有时间信息）
        return results


def integrate_search_with_knowledge(knowledge_results: List[Dict], search_results: List[Dict]) -> str:
    """整合知识库结果和搜索结果

    Args:
        knowledge_results: 知识库检索结果
        search_results: 网络搜索结果

    Returns:
        整合后的知识文本
    """
    integrated_text = "## 知识库信息\n\n"

    # 添加知识库结果
    if knowledge_results:
        for i, result in enumerate(knowledge_results[:3], 1):
            integrated_text += f"{i}. {result.get('content', '')}\n\n"
    else:
        integrated_text += "知识库中暂无相关信息。\n\n"

    integrated_text += "## 网络搜索补充\n\n"

    # 添加搜索结果
    if search_results:
        for i, result in enumerate(search_results[:3], 1):
            title = result.get('title', '未知标题')
            snippet = result.get('snippet', '')
            source = result.get('source', '')

            integrated_text += f"**{i}. {title}**\n"
            integrated_text += f"{snippet}\n"
            if source:
                integrated_text += f"*来源: {source}*\n\n"
    else:
        integrated_text += "暂无相关网络信息。\n"

    return integrated_text


# 测试函数
async def test_web_search():
    """测试网络搜索功能"""
    tool = WebSearchTool()

    # 测试一般搜索
    results = await tool.search("高分一号卫星", max_results=3)
    print("一般搜索结果:")
    for result in results:
        print(f"- {result['title']}: {result['snippet'][:100]}...")

    # 测试卫星信息搜索
    satellite_results = await tool.search_satellite_info(["高分一号", "Sentinel-2"])
    print("\n卫星信息搜索结果:")
    for satellite, results in satellite_results.items():
        print(f"\n{satellite}:")
        for result in results:
            print(f"  - {result['title']}")

    # 测试应用案例搜索
    case_results = await tool.search_application_cases("水质监测", ["高分一号", "Sentinel-2"])
    print("\n应用案例搜索结果:")
    for result in case_results:
        print(f"- {result['title']}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_web_search())