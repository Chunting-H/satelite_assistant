# backend/src/tools/knowledge_tools.py

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path

# 添加项目根目录到Python路径
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent  # 上溯四级目录到项目根目录
sys.path.append(str(project_root))

from backend.src.rag.knowledge_base import get_knowledge_base
from backend.src.graph.state import WorkflowState, Requirement

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def retrieve_satellite_knowledge(
        query: str,
        top_k: int = 5,
        min_score: float = 0.2
) -> List[Dict[str, Any]]:
    """
    从知识库中检索与查询相关的卫星和传感器信息

    Args:
        query: 查询文本
        top_k: 返回的最相关结果数量
        min_score: 最小相关度分数阈值

    Returns:
        包含相关知识的列表
    """
    try:
        # 获取知识库实例
        kb = get_knowledge_base()

        # 执行检索前检查向量存储
        if not hasattr(kb, 'vector_store') or kb.vector_store is None:
            logger.warning("知识库向量存储未加载，尝试重建索引")
            kb.build_index(force_rebuild=False)

            # 如果仍然未加载，返回空结果
            if not hasattr(kb, 'vector_store') or kb.vector_store is None:
                logger.error("无法加载或构建知识库索引")
                return []

        # 执行检索
        results = kb.search(query, top_k=top_k)

        # 过滤低相关度结果
        filtered_results = [
            {
                "content": r["document"],
                "score": r["score"]
            }
            for r in results if r["score"] >= min_score
        ]

        logger.info(f"检索到 {len(filtered_results)} 条相关知识，查询: '{query}'")
        return filtered_results

    except Exception as e:
        logger.error(f"知识检索出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def extract_satellite_info(
        knowledge_items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    从知识条目中提取结构化的卫星信息

    Args:
        knowledge_items: 从知识库检索到的知识条目

    Returns:
        结构化的卫星信息列表
    """
    satellite_info = []

    # 这里我们保持简单，将每个知识条目视为一个卫星描述
    # 在实际场景中，可能需要使用LLM来从文本中提取结构化信息
    for item in knowledge_items:
        content = item["content"]

        # 简单的卫星信息结构
        # 注意：实际应用中可能需要更复杂的提取逻辑
        satellite = {
            "description": content,
            "relevance_score": item["score"],
            "raw_text": content
        }

        satellite_info.append(satellite)

    return satellite_info


def generate_query_from_requirement(requirement: Requirement) -> str:
    """
    根据用户需求生成知识检索查询

    Args:
        requirement: 用户需求对象

    Returns:
        优化的查询字符串
    """
    # 如果有原始描述，直接使用
    if requirement.raw_description:
        return requirement.raw_description

    # 否则，从结构化字段构建查询
    query_parts = []

    if requirement.area_of_interest:
        query_parts.append(f"区域: {requirement.area_of_interest}")

    if requirement.spatial_resolution:
        query_parts.append(f"空间分辨率: {requirement.spatial_resolution}")

    if requirement.spectral_bands:
        bands_str = " ".join(requirement.spectral_bands)
        query_parts.append(f"光谱波段: {bands_str}")

    if requirement.revisit_frequency:
        query_parts.append(f"重访频率: {requirement.revisit_frequency}")

    if requirement.application_scenario:
        query_parts.append(f"应用场景: {requirement.application_scenario}")

    # 如果没有足够信息，返回默认查询
    if not query_parts:
        return "卫星 遥感 对地观测"

    return " ".join(query_parts)


def retrieve_knowledge_for_workflow(
        state: WorkflowState,
        override_query: Optional[str] = None,
        top_k: int = 7
) -> WorkflowState:
    """
    为工作流状态检索知识，并更新状态

    Args:
        state: 工作流状态
        override_query: 可选的覆盖查询字符串
        top_k: 返回的最相关结果数量

    Returns:
        更新后的工作流状态
    """
    # 添加思考步骤
    state.add_thinking_step("知识检索", "准备从知识库中检索相关卫星信息")

    # 生成查询
    if override_query:
        query = override_query
    else:
        query = generate_query_from_requirement(state.requirement)

    # 记录查询
    state.add_thinking_step("知识检索查询", f"生成查询: '{query}'")

    # 执行检索
    knowledge_items = retrieve_satellite_knowledge(query, top_k=top_k)

    # 提取卫星信息
    satellite_info = extract_satellite_info(knowledge_items)

    # 更新状态
    state.retrieved_knowledge = satellite_info

    # 添加思考步骤
    state.add_thinking_step(
        "知识检索结果",
        f"检索到 {len(satellite_info)} 条相关卫星信息"
    )

    # 记录检索到的内容摘要
    if satellite_info:
        summary = "\n".join([
            f"- 相关度 {item['relevance_score']:.2f}: " +
            item['description'][:100] + "..." if len(item['description']) > 100 else item['description']
            for item in satellite_info[:3]
        ])
        state.add_thinking_step("知识检索摘要", summary)

    return state


def search_satellites_by_criteria(
        criteria: Dict[str, Any],
        top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    根据特定标准搜索卫星

    Args:
        criteria: 搜索标准字典
        top_k: 返回的最相关结果数量

    Returns:
        符合标准的卫星信息列表
    """
    # 构建查询字符串
    query_parts = []

    for key, value in criteria.items():
        if value:
            query_parts.append(f"{key}: {value}")

    query = " ".join(query_parts)

    # 执行检索
    results = retrieve_satellite_knowledge(query, top_k=top_k)

    # 提取卫星信息
    satellite_info = extract_satellite_info(results)

    return satellite_info


def get_satellite_details(satellite_name: str) -> Optional[Dict[str, Any]]:
    """
    获取特定卫星的详细信息

    Args:
        satellite_name: 卫星名称

    Returns:
        卫星详细信息，如果未找到则返回None
    """
    # 直接用卫星名称作为查询
    results = retrieve_satellite_knowledge(satellite_name, top_k=3, min_score=0.3)

    if not results:
        return None

    # 找到最相关的结果
    best_match = max(results, key=lambda x: x["score"])

    # 提取详细信息
    satellite_detail = {
        "name": satellite_name,
        "description": best_match["content"],
        "relevance_score": best_match["score"]
    }

    return satellite_detail


def find_complementary_satellites(
        main_satellite: str,
        requirement: Requirement,
        count: int = 2
) -> List[Dict[str, Any]]:
    """
    找到与主卫星互补的其他卫星，以形成虚拟星座

    Args:
        main_satellite: 主卫星名称
        requirement: 用户需求对象
        count: 寻找的卫星数量

    Returns:
        互补卫星的列表
    """
    # 获取主卫星信息
    main_satellite_info = get_satellite_details(main_satellite)
    if not main_satellite_info:
        return []

    # 分析主卫星不足之处，构建互补查询
    # 这里简化处理，实际应用可能需要更复杂的分析
    query = f"与{main_satellite}互补 更高时间分辨率 "

    if requirement.application_scenario:
        query += f"{requirement.application_scenario} "

    # 执行检索
    results = retrieve_satellite_knowledge(query, top_k=count + 2)  # 多检索几条以防主卫星也在结果中

    # 过滤掉主卫星本身
    complementary_satellites = [
                                   item for item in results
                                   if main_satellite.lower() not in item["content"].lower()
                               ][:count]

    # 提取卫星信息
    satellite_info = extract_satellite_info(complementary_satellites)

    return satellite_info


# 如果直接运行此文件，执行简单测试
if __name__ == "__main__":
    print("=" * 50)
    print("测试知识检索工具")
    print("=" * 50)

    try:
        # 测试基本检索
        print("\n测试基本知识检索:")
        print("-" * 40)
        results = retrieve_satellite_knowledge("环境监测卫星 高分辨率", top_k=3)

        print(f"检索到 {len(results)} 条结果")
        for i, result in enumerate(results):
            print(f"\n结果 {i + 1} (相关度: {result['score']:.4f}):")
            print("-" * 30)
            content = result["content"]
            print(content[:200] + "..." if len(content) > 200 else content)

        # 测试从需求生成查询
        print("\n测试从需求生成查询:")
        print("-" * 40)
        from backend.src.graph.state import Requirement

        req = Requirement(
            area_of_interest="青海湖",
            spatial_resolution="高分辨率",
            spectral_bands=["多光谱", "高光谱"],
            application_scenario="水质监测"
        )

        query = generate_query_from_requirement(req)
        print(f"生成的查询: '{query}'")

        # 测试工作流集成
        print("\n测试工作流集成:")
        print("-" * 40)
        from backend.src.graph.state import WorkflowState

        state = WorkflowState()
        state.requirement = req

        updated_state = retrieve_knowledge_for_workflow(state, top_k=3)

        print(f"检索到 {len(updated_state.retrieved_knowledge)} 条知识")
        print("\n思考步骤:")
        for step in updated_state.thinking_steps:
            print(f"- {step['step']}: {step['details']}")

        # 测试根据条件搜索卫星
        print("\n测试根据条件搜索卫星:")
        print("-" * 40)
        criteria = {
            "分辨率": "高分辨率",
            "应用": "水质监测",
            "波段": "多光谱"
        }

        satellites = search_satellites_by_criteria(criteria, top_k=2)
        print(f"找到 {len(satellites)} 颗符合条件的卫星")

        if satellites:
            print("\n符合条件的卫星:")
            for i, sat in enumerate(satellites):
                print(f"卫星 {i + 1} (相关度: {sat['relevance_score']:.4f}):")
                print(sat['description'][:150] + "..." if len(sat['description']) > 150 else sat['description'])

        # 测试获取卫星详细信息
        print("\n测试获取卫星详细信息:")
        print("-" * 40)
        # 使用一个可能存在于知识库中的卫星名称
        satellite_detail = get_satellite_details("高分一号")

        if satellite_detail:
            print(f"找到卫星详细信息 (相关度: {satellite_detail['relevance_score']:.4f}):")
            print(satellite_detail['description'][:200] + "..." if len(satellite_detail['description']) > 200 else
                  satellite_detail['description'])
        else:
            print("未找到卫星详细信息")

        # 测试寻找互补卫星
        print("\n测试寻找互补卫星:")
        print("-" * 40)
        complementary_sats = find_complementary_satellites("高分一号", req, count=2)

        print(f"找到 {len(complementary_sats)} 颗互补卫星")
        for i, sat in enumerate(complementary_sats):
            print(f"\n互补卫星 {i + 1} (相关度: {sat['relevance_score']:.4f}):")
            print(sat['description'][:150] + "..." if len(sat['description']) > 150 else sat['description'])

        print("\n测试完成!")

    except Exception as e:
        print(f"测试时出错: {str(e)}")
        import traceback

        traceback.print_exc()