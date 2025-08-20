# backend/src/graph/nodes/enhanced_visualization_nodes.py - 完整修复版本

import json
import logging
from typing import Dict, List, Any, Optional
from backend.src.graph.state import WorkflowState
import random
from collections import defaultdict
import re

logger = logging.getLogger(__name__)


class VisualizationDataGenerator:
    """生成可视化数据的辅助类 - 增强版本"""

    def __init__(self):
        # 更完整的卫星协同模式
        self.known_collaborations = {
            ("高分一号", "高分二号"): {"frequency": 15, "type": "同系列协同", "effectiveness": 0.9},
            ("高分一号", "Sentinel-2"): {"frequency": 12, "type": "跨国协同", "effectiveness": 0.85},
            ("高分一号", "哨兵-2号"): {"frequency": 12, "type": "跨国协同", "effectiveness": 0.85},
            ("Landsat-8", "Sentinel-2"): {"frequency": 20, "type": "经典组合", "effectiveness": 0.95},
            ("Landsat-8", "哨兵-2号"): {"frequency": 20, "type": "经典组合", "effectiveness": 0.95},
            ("高分三号", "Sentinel-1"): {"frequency": 8, "type": "雷达协同", "effectiveness": 0.88},
            ("高分三号", "哨兵-1号"): {"frequency": 8, "type": "雷达协同", "effectiveness": 0.88},
            ("风云四号", "葵花8号"): {"frequency": 10, "type": "静止轨道协同", "effectiveness": 0.87},
            ("高分一号", "Landsat-8"): {"frequency": 14, "type": "中分辨率协同", "effectiveness": 0.82},
            ("高分二号", "WorldView"): {"frequency": 9, "type": "高分辨率协同", "effectiveness": 0.89},
            ("Pleiades", "WorldView-3"): {"frequency": 10, "type": "超高分辨率协同", "effectiveness": 0.92},
            ("PlanetScope", "珠海一号"): {"frequency": 8, "type": "小卫星群协同", "effectiveness": 0.80},
        }

        # 更完整的卫星能力评分
        self.satellite_capabilities = {
            # 中国卫星
            "高分一号": {"spatialResolution": 85, "temporalResolution": 70, "spectralResolution": 75, "coverage": 80,
                         "dataQuality": 85, "realtime": 60},
            "高分二号": {"spatialResolution": 95, "temporalResolution": 60, "spectralResolution": 70, "coverage": 50,
                         "dataQuality": 90, "realtime": 55},
            "高分三号": {"spatialResolution": 90, "temporalResolution": 80, "spectralResolution": 50, "coverage": 75,
                         "dataQuality": 88, "realtime": 85},
            "高分7号": {"spatialResolution": 93, "temporalResolution": 65, "spectralResolution": 75, "coverage": 60,
                        "dataQuality": 91, "realtime": 60},
            "风云四号": {"spatialResolution": 60, "temporalResolution": 95, "spectralResolution": 80, "coverage": 100,
                         "dataQuality": 85, "realtime": 95},
            "环境一号": {"spatialResolution": 75, "temporalResolution": 75, "spectralResolution": 85, "coverage": 85,
                         "dataQuality": 80, "realtime": 70},
            "海洋一号": {"spatialResolution": 65, "temporalResolution": 85, "spectralResolution": 90, "coverage": 95,
                         "dataQuality": 82, "realtime": 75},
            "珠海一号": {"spatialResolution": 80, "temporalResolution": 90, "spectralResolution": 70, "coverage": 85,
                         "dataQuality": 83, "realtime": 80},
            "ZY-1": {"spatialResolution": 80, "temporalResolution": 90, "spectralResolution": 70, "coverage": 85,
                     "dataQuality": 83, "realtime": 80},
            "SuperView-1": {"spatialResolution": 94, "temporalResolution": 65, "spectralResolution": 72, "coverage": 55,
                            "dataQuality": 89, "realtime": 62},

            # 欧洲卫星
            "Sentinel-2": {"spatialResolution": 80, "temporalResolution": 85, "spectralResolution": 90, "coverage": 95,
                           "dataQuality": 88, "realtime": 75},
            "哨兵-2号": {"spatialResolution": 80, "temporalResolution": 85, "spectralResolution": 90, "coverage": 95,
                         "dataQuality": 88, "realtime": 75},
            "Sentinel-1": {"spatialResolution": 70, "temporalResolution": 90, "spectralResolution": 40, "coverage": 90,
                           "dataQuality": 85, "realtime": 90},
            "哨兵-1号": {"spatialResolution": 70, "temporalResolution": 90, "spectralResolution": 40, "coverage": 90,
                         "dataQuality": 85, "realtime": 90},

            # 美国卫星
            "Landsat-8": {"spatialResolution": 70, "temporalResolution": 60, "spectralResolution": 85, "coverage": 90,
                          "dataQuality": 85, "realtime": 65},
            "WorldView-3": {"spatialResolution": 98, "temporalResolution": 55, "spectralResolution": 88, "coverage": 45,
                            "dataQuality": 95, "realtime": 58},
            "WorldView-2": {"spatialResolution": 94, "temporalResolution": 58, "spectralResolution": 85, "coverage": 48,
                            "dataQuality": 92, "realtime": 60},

            # 法国卫星
            "Pleiades": {"spatialResolution": 94, "temporalResolution": 70, "spectralResolution": 78, "coverage": 60,
                         "dataQuality": 92, "realtime": 65},
            "Pleiades Neo": {"spatialResolution": 96, "temporalResolution": 72, "spectralResolution": 80,
                             "coverage": 58,
                             "dataQuality": 94, "realtime": 68},

            # 其他商业卫星
            "PlanetScope": {"spatialResolution": 75, "temporalResolution": 95, "spectralResolution": 65,
                            "coverage": 100,
                            "dataQuality": 80, "realtime": 85},
        }
        # 🆕 新增：真实的卫星技术参数
        self.satellite_real_params = {
            # 中国卫星
            "高分一号": {
                "spatial_resolution": "2米/8米",
                "temporal_resolution": "4天",
                "spectral_resolution": "4个波段（全色+多光谱）",
                "coverage": "60公里",
                "data_quality": "10位",
                "realtime": "24小时内"
            },
            "高分二号": {
                "spatial_resolution": "1米/4米",
                "temporal_resolution": "69天",
                "spectral_resolution": "4个波段（全色+多光谱）",
                "coverage": "45公里",
                "data_quality": "10位",
                "realtime": "24小时内"
            },
            "高分三号": {
                "spatial_resolution": "1米-500米",
                "temporal_resolution": "29天",
                "spectral_resolution": "SAR C波段",
                "coverage": "10-650公里",
                "data_quality": "16位",
                "realtime": "准实时"
            },
            "高分7号": {
                "spatial_resolution": "0.65米/2.6米",
                "temporal_resolution": "5天",
                "spectral_resolution": "4个波段（全色+多光谱）",
                "coverage": "20公里",
                "data_quality": "10位",
                "realtime": "24小时内"
            },
            "风云四号": {
                "spatial_resolution": "500米-4公里",
                "temporal_resolution": "15分钟",
                "spectral_resolution": "14个通道",
                "coverage": "全球",
                "data_quality": "12位",
                "realtime": "准实时"
            },
            "环境一号": {
                "spatial_resolution": "30米",
                "temporal_resolution": "4天",
                "spectral_resolution": "4个波段",
                "coverage": "720公里",
                "data_quality": "12位",
                "realtime": "24小时内"
            },
            "海洋一号": {
                "spatial_resolution": "250米-1.1公里",
                "temporal_resolution": "3天",
                "spectral_resolution": "10个波段",
                "coverage": "2900公里",
                "data_quality": "12位",
                "realtime": "24小时内"
            },
            "珠海一号": {
                "spatial_resolution": "0.9米/3.2米",
                "temporal_resolution": "1天",
                "spectral_resolution": "4个波段",
                "coverage": "12公里",
                "data_quality": "12位",
                "realtime": "准实时"
            },

            # 欧洲卫星
            "Sentinel-2": {
                "spatial_resolution": "10米/20米/60米",
                "temporal_resolution": "5天",
                "spectral_resolution": "13个波段（可见光-短波红外）",
                "coverage": "290公里",
                "data_quality": "12位",
                "realtime": "准实时"
            },
            "哨兵-2号": {
                "spatial_resolution": "10米/20米/60米",
                "temporal_resolution": "5天",
                "spectral_resolution": "13个波段（可见光-短波红外）",
                "coverage": "290公里",
                "data_quality": "12位",
                "realtime": "准实时"
            },
            "Sentinel-1": {
                "spatial_resolution": "5米-40米",
                "temporal_resolution": "6天",
                "spectral_resolution": "SAR C波段",
                "coverage": "250公里",
                "data_quality": "16位",
                "realtime": "准实时"
            },
            "哨兵-1号": {
                "spatial_resolution": "5米-40米",
                "temporal_resolution": "6天",
                "spectral_resolution": "SAR C波段",
                "coverage": "250公里",
                "data_quality": "16位",
                "realtime": "准实时"
            },

            # 美国卫星
            "Landsat-8": {
                "spatial_resolution": "15米/30米",
                "temporal_resolution": "16天",
                "spectral_resolution": "11个波段（可见光-热红外）",
                "coverage": "185公里",
                "data_quality": "12位",
                "realtime": "24小时内"
            },
            "WorldView-3": {
                "spatial_resolution": "0.31米/1.24米",
                "temporal_resolution": "1-4.5天",
                "spectral_resolution": "29个波段（全色+多光谱+短波红外）",
                "coverage": "13.1公里",
                "data_quality": "11位",
                "realtime": "数小时内"
            },
            "WorldView-2": {
                "spatial_resolution": "0.46米/1.85米",
                "temporal_resolution": "1.1天",
                "spectral_resolution": "8个波段",
                "coverage": "16.4公里",
                "data_quality": "11位",
                "realtime": "数小时内"
            },

            # 法国卫星
            "Pleiades": {
                "spatial_resolution": "0.5米/2米",
                "temporal_resolution": "26天",
                "spectral_resolution": "4个波段（全色+多光谱）",
                "coverage": "20公里",
                "data_quality": "12位",
                "realtime": "24小时内"
            },
            "Pleiades Neo": {
                "spatial_resolution": "0.3米/1.2米",
                "temporal_resolution": "1天",
                "spectral_resolution": "6个波段",
                "coverage": "14公里",
                "data_quality": "12位",
                "realtime": "数小时内"
            },

            # 其他商业卫星
            "PlanetScope": {
                "spatial_resolution": "3米",
                "temporal_resolution": "1天",
                "spectral_resolution": "4个波段",
                "coverage": "24公里",
                "data_quality": "12位",
                "realtime": "准实时"
            },
        }

    def generate_collaboration_data(self, satellites: List[str]) -> List[Dict]:
        """生成卫星协同数据 - 确保每个卫星都有协同关系"""
        collaborations = []

        logger.info(f"为 {len(satellites)} 颗卫星生成协同数据: {satellites}")

        # 确保至少每个卫星都有一些协同关系
        for i, sat1 in enumerate(satellites):
            for j, sat2 in enumerate(satellites[i + 1:], i + 1):
                # 尝试多种名称匹配方式
                possible_keys = [
                    tuple(sorted([sat1, sat2])),
                    (sat1, sat2),
                    (sat2, sat1)
                ]

                collab_info = None
                for key in possible_keys:
                    if key in self.known_collaborations:
                        collab_info = self.known_collaborations[key]
                        break

                if collab_info:
                    collaborations.append({
                        "satellite1": sat1,
                        "satellite2": sat2,
                        "frequency": collab_info["frequency"],
                        "type": collab_info["type"],
                        "effectiveness": collab_info["effectiveness"]
                    })
                else:
                    # 为所有卫星对生成基础协同关系，确保图表有数据
                    frequency = random.randint(5, 18)
                    effectiveness = round(random.uniform(0.65, 0.88), 2)

                    # 根据卫星类型推断协同类型
                    collab_type = "常规协同"
                    if "高分" in sat1 and "高分" in sat2:
                        collab_type = "同系列协同"
                        effectiveness += 0.05
                    elif any(word in sat1.lower() for word in ["sentinel", "哨兵"]) and any(
                            word in sat2.lower() for word in ["landsat"]):
                        collab_type = "国际协同"
                        effectiveness += 0.08
                    elif "雷达" in sat1 or "雷达" in sat2 or "三号" in sat1 or "三号" in sat2:
                        collab_type = "雷达协同"
                    elif ("PlanetScope" in sat1 and "珠海一号" in sat2) or (
                            "珠海一号" in sat1 and "PlanetScope" in sat2):
                        collab_type = "小卫星群协同"
                        frequency = random.randint(10, 20)

                    collaborations.append({
                        "satellite1": sat1,
                        "satellite2": sat2,
                        "frequency": frequency,
                        "type": collab_type,
                        "effectiveness": min(effectiveness, 0.95)
                    })

        logger.info(f"生成了 {len(collaborations)} 个协同关系")
        return collaborations

    def generate_capability_data(self, satellites: List[str]) -> Dict[str, Dict]:
        """生成卫星能力数据 - 增强版"""
        capabilities = {}

        for sat in satellites:
            # 检查各种可能的名称格式
            if sat in self.satellite_capabilities:
                capabilities[sat] = self.satellite_capabilities[sat]
            elif sat == "珠海一号" and "ZY-1" in self.satellite_capabilities:
                capabilities[sat] = self.satellite_capabilities["ZY-1"]
            elif sat == "ZY-1" and "珠海一号" in self.satellite_capabilities:
                capabilities[sat] = self.satellite_capabilities["珠海一号"]
            else:
                # 根据卫星名称智能生成更合理的能力数据
                base_capabilities = {
                    "spatialResolution": 70,
                    "temporalResolution": 70,
                    "spectralResolution": 70,
                    "coverage": 70,
                    "dataQuality": 75,
                    "realtime": 65
                }

                # 根据卫星类型调整
                if "高分" in sat:
                    number = re.search(r'\d+', sat)
                    if number:
                        num = int(number.group())
                        if num <= 3:
                            base_capabilities.update({
                                "spatialResolution": 90 + random.randint(-5, 5),
                                "temporalResolution": 70 + random.randint(-5, 5),
                                "spectralResolution": 75 + random.randint(-5, 5),
                                "coverage": 75 + random.randint(-5, 5),
                                "dataQuality": 88 + random.randint(-3, 3),
                                "realtime": 65 + random.randint(-5, 5)
                            })
                        else:
                            base_capabilities.update({
                                "spatialResolution": 92 + random.randint(-3, 3),
                                "temporalResolution": 65 + random.randint(-5, 5),
                                "spectralResolution": 77 + random.randint(-5, 5),
                                "coverage": 65 + random.randint(-5, 5),
                                "dataQuality": 90 + random.randint(-3, 3),
                                "realtime": 60 + random.randint(-5, 5)
                            })

                elif any(word in sat.lower() for word in ["pleiades", "worldview", "superview"]):
                    base_capabilities.update({
                        "spatialResolution": 94 + random.randint(-2, 2),
                        "temporalResolution": 60 + random.randint(-5, 5),
                        "spectralResolution": 80 + random.randint(-5, 5),
                        "coverage": 55 + random.randint(-5, 5),
                        "dataQuality": 92 + random.randint(-3, 3),
                        "realtime": 62 + random.randint(-5, 5)
                    })

                elif "planetscope" in sat.lower():
                    base_capabilities.update({
                        "spatialResolution": 75 + random.randint(-5, 5),
                        "temporalResolution": 95 + random.randint(-3, 3),
                        "spectralResolution": 65 + random.randint(-5, 5),
                        "coverage": 100,
                        "dataQuality": 80 + random.randint(-3, 3),
                        "realtime": 85 + random.randint(-5, 5)
                    })

                elif "珠海" in sat or "ZY-1" in sat:
                    base_capabilities.update({
                        "spatialResolution": 80 + random.randint(-5, 5),
                        "temporalResolution": 90 + random.randint(-5, 5),
                        "spectralResolution": 70 + random.randint(-5, 5),
                        "coverage": 85 + random.randint(-5, 5),
                        "dataQuality": 83 + random.randint(-3, 3),
                        "realtime": 80 + random.randint(-5, 5)
                    })

                # 确保所有值在0-100范围内
                for key in base_capabilities:
                    base_capabilities[key] = max(0, min(100, base_capabilities[key]))

                capabilities[sat] = base_capabilities

        return capabilities


def extract_satellites_from_state(state: WorkflowState) -> List[str]:
    """从状态中提取卫星信息 - 增强版本（同步版本）"""
    satellites = []

    logger.info("🔍 开始从状态中提取卫星信息...")

    # 1. 优先从 extracted_satellites 获取
    if hasattr(state, 'extracted_satellites') and state.extracted_satellites:
        satellites = state.extracted_satellites
        logger.info(f"✅ 从 extracted_satellites 获取卫星: {satellites}")
        return satellites

    # 2. 从 metadata 获取
    if state.metadata.get('extracted_satellites'):
        satellites = state.metadata['extracted_satellites']
        logger.info(f"✅ 从 metadata 获取卫星: {satellites}")
        return satellites

    # 3. 从方案内容中提取（使用同步方法）
    if state.main_plan and isinstance(state.main_plan, str):
        logger.info("🔄 尝试从方案内容中提取卫星...")
        # 使用同步提取方法
        from backend.src.tools.satellite_extractor import extract_satellites_from_composition
        satellites = extract_satellites_from_composition(state.main_plan)
        logger.info(f"📝 从方案内容提取结果: {satellites}")

        # 更新状态
        if satellites:
            state.set_extracted_satellites(satellites)
            # 🔧 新增：同时更新metadata
            state.metadata['extracted_satellites'] = satellites
            logger.info(f"✅ 更新状态中的卫星信息: {satellites}")
            return satellites
        else:
            logger.warning("⚠️ 从方案内容中未提取到卫星")

    # 4. 从最新的助手消息中提取
    logger.info("🔄 尝试从助手消息中提取卫星...")
    for msg in reversed(state.messages):
        if msg.role == "assistant" and msg.content:
            if "卫星组成" in msg.content or "虚拟星座方案" in msg.content:
                from backend.src.tools.satellite_extractor import extract_satellites_from_composition
                satellites = extract_satellites_from_composition(msg.content)
                if satellites:
                    logger.info(f"✅ 从助手消息提取卫星: {satellites}")
                    state.set_extracted_satellites(satellites)
                    state.metadata['extracted_satellites'] = satellites
                    return satellites

    # 5. 如果都没有，使用默认卫星
    logger.warning("❌ 未找到卫星信息，使用默认卫星")
    default_satellites = ["高分一号", "Sentinel-2", "Landsat-8"]

    # 🔧 新增：将默认卫星也设置到状态中
    state.set_extracted_satellites(default_satellites)
    state.metadata['extracted_satellites'] = default_satellites

    return default_satellites


def enhance_plan_with_visualization(state: WorkflowState) -> Dict[str, Any]:
    """
    简化版本 - 不再生成可视化数据，仅返回空字典
    可视化数据将由前端通过文本解析生成
    """
    logger.info("跳过后端可视化数据生成，将由前端处理")
    return None


def _analyze_combination_patterns(collaborations: List[Dict]) -> Dict:
    """分析卫星组合模式"""
    combination_stats = defaultdict(int)
    type_stats = defaultdict(int)

    for collab in collaborations:
        combo_name = f"{collab['satellite1']} + {collab['satellite2']}"
        combination_stats[combo_name] += collab['frequency']
        type_stats[collab['type']] += 1

    # 找出最佳组合
    best_combinations = sorted(
        combination_stats.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    return {
        "combination_stats": dict(combination_stats),
        "type_distribution": dict(type_stats),
        "best_combinations": best_combinations,
        "total_collaborations": len(collaborations)
    }


def _get_satellite_country(satellite_name: str) -> str:
    """获取卫星所属国家"""
    country_mapping = {
        "高分": "中国", "风云": "中国", "海洋": "中国", "资源": "中国", "环境": "中国",
        "珠海": "中国", "ZY-1": "中国", "SuperView": "中国",
        "Sentinel": "欧洲", "哨兵": "欧洲",
        "Landsat": "美国", "MODIS": "美国", "WorldView": "美国",
        "Pleiades": "法国", "SPOT": "法国",
        "PlanetScope": "美国", "Planet": "美国",
        "葵花": "日本", "Himawari": "日本"
    }

    for key, country in country_mapping.items():
        if key in satellite_name:
            return country
    return "其他"


def _get_satellite_launch_date(satellite_name: str) -> str:
    """获取卫星发射日期"""
    launch_dates = {
        "高分一号": "2013-04-26", "高分二号": "2014-08-19", "高分三号": "2016-08-10",
        "高分7号": "2019-11-03", "SuperView-1": "2016-12-28",
        "Sentinel-2": "2015-06-23", "哨兵-2号": "2015-06-23",
        "Landsat-8": "2013-02-11", "风云四号": "2016-12-11",
        "WorldView-3": "2014-08-13", "Pleiades": "2011-12-17",
        "Pleiades Neo": "2021-04-29", "PlanetScope": "2016-02-14",
        "珠海一号": "2017-06-15", "ZY-1": "2017-06-15"
    }
    return launch_dates.get(satellite_name, "2020-01-01")


def _calculate_satellite_importance(satellite: str, collaborations: List[Dict]) -> int:
    """计算卫星重要性"""
    importance = 5
    for collab in collaborations:
        if satellite in [collab['satellite1'], collab['satellite2']]:
            importance += collab['frequency'] * 0.5
    return min(int(importance), 10)


def _generate_visualization_recommendations(pattern_analysis: Dict, satellites: List[str], capabilities: Dict) -> List[
    str]:
    """生成可视化建议 - 增强版"""
    recommendations = []

    # 分析卫星能力
    if capabilities:
        # 找出各维度最强的卫星
        best_spatial = max(capabilities.items(), key=lambda x: x[1].get('spatialResolution', 0))[0]
        best_temporal = max(capabilities.items(), key=lambda x: x[1].get('temporalResolution', 0))[0]
        best_spectral = max(capabilities.items(), key=lambda x: x[1].get('spectralResolution', 0))[0]

        recommendations.append(f"🎯 {best_spatial} 具有最高的空间分辨率，适合精细目标识别")
        recommendations.append(f"⏱️ {best_temporal} 时间分辨率最优，适合高频监测需求")
        recommendations.append(f"🌈 {best_spectral} 光谱分辨率出色，适合多光谱分析")

    if len(satellites) >= 3:
        recommendations.append(f"🌐 您的方案包含 {len(satellites)} 颗卫星，形成了互补的观测能力")

    # 分析协同模式
    if pattern_analysis and pattern_analysis.get('best_combinations'):
        best_combo = pattern_analysis['best_combinations'][0]
        recommendations.append(f"🤝 最佳协同组合是 {best_combo[0]}，协同频率达 {best_combo[1]} 次")

    # 特殊卫星组合建议
    sat_names = [s.lower() for s in satellites]
    if any('planetscope' in s for s in sat_names):
        recommendations.append("🛰️ PlanetScope提供每日全球覆盖能力，适合高频次监测")
    if any('worldview' in s for s in sat_names) or any('pleiades' in s for s in sat_names):
        recommendations.append("🔍 超高分辨率卫星群组合，可实现亚米级精细观测")

    return recommendations


def add_visualization_to_response(state: WorkflowState) -> str:
    """
    简化版本 - 不再添加可视化提示
    """
    logger.info("跳过可视化提示添加")
    return ""