import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, Tuple, Optional, List
from pathlib import Path
import re

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


class ParameterUncertaintyCalculator:
    """参数不确定性计算器"""

    def __init__(self):
        self.vocabulary = self._load_vocabulary()
        # 权重配置
        self.weights = {
            "knowledge_base": 0.2,  # 知识库权重最高
            "web_search": 0.3,  # 网络搜索次之
            "llm_judgment": 0.5  # 大模型判断权重最低
        }
        self.threshold = 0.5  # 使用web_search的权重作为阈值

    def _load_vocabulary(self) -> Dict:
        """加载监测目标专业词汇库"""
        vocab_path = Path(__file__).parent.parent.parent.parent / "data" / "monitoring_target_vocabulary.json"
        try:
            with open(vocab_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载词汇库失败: {e}")
            return {"professional_terms": {}, "synonyms": {}}

    async def calculate_monitoring_target_uncertainty(
            self,
            target_text: Optional[str],
            enable_web_search: bool = True,
            enable_llm: bool = True
    ) -> Dict[str, any]:
        """计算监测目标的不确定性

        Returns:
            {
                "uncertainty_score": float (0-1),
                "needs_clarification": bool,
                "details": {
                    "existence": bool,
                    "knowledge_base_match": bool,
                    "web_search_match": bool,
                    "llm_professional": bool,
                    "matched_terms": List[str],
                    "confidence_level": str ("high", "medium", "low")
                }
            }
        """
        # 1. 存在性判断
        if not target_text or not target_text.strip():
            return {
                "uncertainty_score": 1.0,
                "needs_clarification": True,
                "details": {
                    "existence": False,
                    "knowledge_base_match": False,
                    "web_search_match": False,
                    "llm_professional": False,
                    "matched_terms": [],
                    "confidence_level": "none"
                }
            }

        target_text = target_text.strip()

        # 2. 清晰度得分计算
        # ① 知识库匹配
        kb_match, matched_terms = self._check_knowledge_base(target_text)

        # ② 网络搜索验证（可选）
        web_match = False
        if enable_web_search:
            web_match = await self._check_web_search(target_text)

        # ③ 大模型判断（可选）
        llm_professional = False
        if enable_llm:
            llm_professional = await self._check_llm_professional(target_text)

        # 计算总体不确定性得分
        clarity_score = (
                self.weights["knowledge_base"] * (1 if kb_match else 0) +
                self.weights["web_search"] * (1 if web_match else 0) +
                self.weights["llm_judgment"] * (1 if llm_professional else 0)
        )

        # 不确定性是清晰度的反向
        uncertainty_score = 1 - clarity_score

        # 判断是否需要澄清（不确定性超过阈值）
        needs_clarification = uncertainty_score > self.threshold

        # 确定置信度级别
        if clarity_score >= 0.7:
            confidence_level = "high"
        elif clarity_score >= 0.4:
            confidence_level = "medium"
        else:
            confidence_level = "low"

        return {
            "uncertainty_score": round(uncertainty_score, 2),
            "needs_clarification": needs_clarification,
            "details": {
                "existence": True,
                "knowledge_base_match": kb_match,
                "web_search_match": web_match,
                "llm_professional": llm_professional,
                "matched_terms": matched_terms,
                "confidence_level": confidence_level,
                "clarity_score": round(clarity_score, 2)
            }
        }

    def _check_knowledge_base(self, target_text: str) -> Tuple[bool, List[str]]:
        """检查知识库中是否有匹配的专业术语"""
        target_lower = target_text.lower()
        matched_terms = []

        # 检查专业术语
        for term, info in self.vocabulary.get("professional_terms", {}).items():
            if term in target_text or term.lower() in target_lower:
                matched_terms.append(term)
                return True, matched_terms

            # 检查关键词
            for keyword in info.get("keywords", []):
                if keyword in target_text or keyword.lower() in target_lower:
                    matched_terms.append(f"{term}(关键词:{keyword})")
                    return True, matched_terms

        # 检查同义词
        for synonym, main_terms in self.vocabulary.get("synonyms", {}).items():
            if synonym in target_text or synonym.lower() in target_lower:
                matched_terms.extend(main_terms)
                return True, matched_terms

        return False, []

    async def calculate_time_uncertainty(
            self,
            frequency_text: Optional[str],
            period_text: Optional[str],
            enable_llm: bool = True
    ) -> Dict[str, any]:
        """计算时间参数的不确定性

        包括观测频率和监测周期两个参数的不确定性计算

        Returns:
            {
                "observation_frequency": {
                    "uncertainty_score": float (0 or 1),
                    "needs_clarification": bool,
                    "details": {
                        "existence": bool,
                        "valid_format": bool,
                        "missing_info": str,
                        "confidence_level": str ("high", "low", "none")
                    }
                },
                "monitoring_period": {
                    "uncertainty_score": float (0 or 1),
                    "needs_clarification": bool,
                    "details": {
                        "existence": bool,
                        "completeness": bool,
                        "has_duration": bool,
                        "has_start_end": bool,
                        "missing_info": str,
                        "confidence_level": str ("high", "low", "none")
                    }
                }
            }
        """

        results = {}

        # 1. 计算观测频率的不确定性
        frequency_result = await self._calculate_frequency_uncertainty(frequency_text, enable_llm)
        results["observation_frequency"] = frequency_result

        # 2. 计算监测周期的不确定性
        period_result = await self._calculate_period_uncertainty(period_text, enable_llm)
        results["monitoring_period"] = period_result

        return results

    async def _calculate_frequency_uncertainty(
            self,
            frequency_text: Optional[str],
            enable_llm: bool = True
    ) -> Dict[str, any]:
        """计算观测频率的不确定性"""

        # 1. 存在性判断
        if not frequency_text or not frequency_text.strip():
            return {
                "uncertainty_score": 1.0,
                "needs_clarification": True,
                "details": {
                    "existence": False,
                    "valid_format": False,
                    "missing_info": "未提供观测频率信息",
                    "confidence_level": "none"
                }
            }

        frequency_text = frequency_text.strip()

        # 2. 格式验证 - 检查是否符合标准频率格式
        valid_format = self._check_frequency_format(frequency_text)

        # 3. 使用LLM辅助判断（可选）
        llm_valid = False
        if enable_llm and not valid_format:
            llm_valid = await self._check_frequency_with_llm(frequency_text)

        # 确定不确定性分数
        if valid_format or llm_valid:
            uncertainty_score = 0.0
            confidence_level = "high"
            missing_info = ""
        else:
            uncertainty_score = 1.0
            confidence_level = "low"
            missing_info = "观测频率格式不明确，需要澄清具体的观测间隔"

        return {
            "uncertainty_score": uncertainty_score,
            "needs_clarification": uncertainty_score > 0.5,
            "details": {
                "existence": True,
                "valid_format": valid_format or llm_valid,
                "missing_info": missing_info,
                "confidence_level": confidence_level,
                "provided_text": frequency_text
            }
        }

    async def _calculate_period_uncertainty(
            self,
            period_text: Optional[str],
            enable_llm: bool = True
    ) -> Dict[str, any]:
        """计算监测周期的不确定性"""

        # 1. 存在性判断
        if not period_text or not period_text.strip():
            return {
                "uncertainty_score": 1.0,
                "needs_clarification": True,
                "details": {
                    "existence": False,
                    "completeness": False,
                    "has_duration": False,
                    "has_start_end": False,
                    "missing_info": "未提供监测周期信息",
                    "confidence_level": "none"
                }
            }

        period_text = period_text.strip()

        # 2. 完整性判断
        has_duration, duration_info = self._check_duration_info(period_text)
        has_start_end, start_end_info = self._check_start_end_info(period_text)

        # 3. 使用LLM辅助判断（可选）
        llm_valid = False
        if enable_llm and not (has_duration or has_start_end):
            llm_valid = await self._check_period_with_llm(period_text)

        # 确定完整性
        is_complete = has_duration or has_start_end or llm_valid

        # 确定缺失信息
        missing_info = []
        if not has_duration and not has_start_end:
            if llm_valid:
                missing_info.append("监测周期表述不够明确")
            else:
                missing_info.append("缺少具体的监测时长或起止时间")

        # 确定不确定性分数
        if is_complete:
            uncertainty_score = 0.0
            confidence_level = "high"
        else:
            uncertainty_score = 1.0
            confidence_level = "low"

        return {
            "uncertainty_score": uncertainty_score,
            "needs_clarification": uncertainty_score > 0.5,
            "details": {
                "existence": True,
                "completeness": is_complete,
                "has_duration": has_duration,
                "has_start_end": has_start_end,
                "duration_info": duration_info,
                "start_end_info": start_end_info,
                "missing_info": " | ".join(missing_info) if missing_info else "",
                "confidence_level": confidence_level,
                "provided_text": period_text
            }
        }

    async def calculate_location_uncertainty(
            self,
            area_text: Optional[str],
            range_text: Optional[str],
            enable_llm: bool = True
    ) -> Dict[str, any]:
        """计算地点参数的不确定性

        包括观测区域和覆盖范围两个参数的不确定性计算

        Returns:
            {
                "observation_area": {
                    "uncertainty_score": float (0 or 1),
                    "needs_clarification": bool,
                    "details": {
                        "existence": bool,
                        "valid_location": bool,
                        "location_type": str,  # "specific", "administrative", "coordinates", "vague"
                        "missing_info": str,
                        "confidence_level": str ("high", "low", "none"),
                        "provided_text": str
                    }
                },
                "coverage_range": {
                    "uncertainty_score": float (0 or 1),
                    "needs_clarification": bool,
                    "details": {
                        "existence": bool,
                        "has_numeric_value": bool,
                        "has_descriptive_value": bool,
                        "unit_type": str,  # "area", "descriptive", "relative"
                        "missing_info": str,
                        "confidence_level": str ("high", "low", "none"),
                        "provided_text": str
                    }
                }
            }
        """

        results = {}

        # 1. 计算观测区域的不确定性
        area_result = await self._calculate_area_uncertainty(area_text, enable_llm)
        results["observation_area"] = area_result

        # 2. 计算覆盖范围的不确定性
        range_result = await self._calculate_range_uncertainty(range_text, enable_llm)
        results["coverage_range"] = range_result

        return results

    async def _calculate_area_uncertainty(
            self,
            area_text: Optional[str],
            enable_llm: bool = True
    ) -> Dict[str, any]:
        """计算观测区域的不确定性"""

        # 1. 存在性判断
        if not area_text or not area_text.strip():
            return {
                "uncertainty_score": 1.0,
                "needs_clarification": True,
                "details": {
                    "existence": False,
                    "valid_location": False,
                    "location_type": "none",
                    "missing_info": "未提供观测区域信息",
                    "confidence_level": "none"
                }
            }

        area_text = area_text.strip()

        # 2. 检查是否为有效的地点信息
        is_valid, location_type, location_info = self._check_location_validity(area_text)

        # 3. 使用LLM辅助判断（可选）
        llm_valid = False
        if enable_llm and not is_valid:
            llm_valid = await self._check_area_with_llm(area_text)

        # 确定不确定性分数
        if is_valid or llm_valid:
            uncertainty_score = 0.0
            confidence_level = "high"
            missing_info = ""
        else:
            uncertainty_score = 1.0
            confidence_level = "low"
            missing_info = "观测区域不明确，需要提供具体的地理位置（如城市、湖泊、经纬度等）"

        return {
            "uncertainty_score": uncertainty_score,
            "needs_clarification": uncertainty_score > 0.5,
            "details": {
                "existence": True,
                "valid_location": is_valid or llm_valid,
                "location_type": location_type,
                "location_info": location_info,
                "missing_info": missing_info,
                "confidence_level": confidence_level,
                "provided_text": area_text
            }
        }

    async def _calculate_range_uncertainty(
            self,
            range_text: Optional[str],
            enable_llm: bool = True
    ) -> Dict[str, any]:
        """计算覆盖范围的不确定性"""

        # 1. 存在性判断
        if not range_text or not range_text.strip():
            return {
                "uncertainty_score": 1.0,
                "needs_clarification": True,
                "details": {
                    "existence": False,
                    "has_numeric_value": False,
                    "has_descriptive_value": False,
                    "unit_type": "none",
                    "missing_info": "未提供覆盖范围信息",
                    "confidence_level": "none"
                }
            }

        range_text = range_text.strip()

        # 2. 检查是否包含数值范围
        has_numeric, numeric_info = self._check_numeric_range(range_text)

        # 3. 检查是否包含描述性范围
        has_descriptive, descriptive_info = self._check_descriptive_range(range_text)

        # 4. 使用LLM辅助判断（可选）
        llm_valid = False
        if enable_llm and not (has_numeric or has_descriptive):
            llm_valid = await self._check_range_with_llm(range_text)

        # 确定有效性
        is_valid = has_numeric or has_descriptive or llm_valid

        # 确定单位类型
        if has_numeric:
            unit_type = "area"
            range_info = numeric_info
        elif has_descriptive:
            unit_type = "descriptive"
            range_info = descriptive_info
        else:
            unit_type = "unknown"
            range_info = ""

        # 确定不确定性分数
        if is_valid:
            uncertainty_score = 0.0
            confidence_level = "high"
            missing_info = ""
        else:
            uncertainty_score = 1.0
            confidence_level = "low"
            missing_info = "覆盖范围不明确，需要提供具体的面积或范围描述（如100平方公里、全市范围等）"

        return {
            "uncertainty_score": uncertainty_score,
            "needs_clarification": uncertainty_score > 0.5,
            "details": {
                "existence": True,
                "has_numeric_value": has_numeric,
                "has_descriptive_value": has_descriptive,
                "unit_type": unit_type,
                "range_info": range_info,
                "missing_info": missing_info,
                "confidence_level": confidence_level,
                "provided_text": range_text
            }
        }

    async def validate_custom_input(self, param_key: str, custom_value: str) -> Dict[str, any]:
        """验证自定义输入的有效性"""

        # 基础验证
        if not custom_value or len(custom_value.strip()) < 2:
            return {
                "valid": False,
                "reason": "输入内容太短",
                "suggestion": f"请提供更详细的{self._get_param_display_name(param_key)}信息"
            }

        # 根据参数类型进行特定验证
        if param_key == "monitoring_target":
            # 检查是否包含监测相关关键词
            monitoring_keywords = ["监测", "观测", "检测", "分析", "评估", "调查"]
            if not any(keyword in custom_value for keyword in monitoring_keywords):
                # 尝试理解用户意图
                return {
                    "valid": True,
                    "normalized_value": f"{custom_value}监测",
                    "confidence": 0.8
                }

        elif param_key == "observation_frequency":
            # 尝试规范化频率表述
            normalized = self._normalize_frequency_expression(custom_value)
            if normalized:
                return {
                    "valid": True,
                    "normalized_value": normalized,
                    "confidence": 0.9
                }

        elif param_key == "observation_area":
            # 验证地理位置
            is_valid_location = await self._validate_location_with_ai(custom_value)
            return {
                "valid": is_valid_location,
                "normalized_value": custom_value,
                "confidence": 0.85 if is_valid_location else 0.3
            }

        # 默认接受自定义输入
        return {
            "valid": True,
            "normalized_value": custom_value,
            "confidence": 0.7
        }

    def _normalize_frequency_expression(self, expr: str) -> Optional[str]:
        """规范化频率表达式"""
        expr_lower = expr.lower()

        # 常见表述映射
        frequency_mappings = {
            "每天": "每天1次",
            "天天": "每天1次",
            "每日": "每天1次",
            "一天一次": "每天1次",
            "一天两次": "每天2次",
            "一周一次": "每周1次",
            "每星期": "每周1次",
            "每礼拜": "每周1次",
            "两天一次": "每2天1次",
            "三天一次": "每3天1次",
            "实时": "每小时1次",
            "准实时": "每2小时1次",
            "尽可能频繁": "每天3次",
            "高频": "每天多次",
            "常规": "每周2次"
        }

        # 直接匹配
        for key, value in frequency_mappings.items():
            if key in expr_lower:
                return value

        # 模式匹配
        patterns = [
            (r'(\d+)\s*天\s*(\d+)\s*次', lambda m: f"每{m.group(1)}天{m.group(2)}次"),
            (r'(\d+)\s*小时\s*(\d+)\s*次', lambda m: f"每{m.group(1)}小时{m.group(2)}次"),
            (r'一个?月\s*(\d+)\s*次', lambda m: f"每月{m.group(1)}次"),
            (r'(\d+)\s*次/天', lambda m: f"每天{m.group(1)}次"),
            (r'(\d+)\s*次/周', lambda m: f"每周{m.group(1)}次")
        ]

        for pattern, handler in patterns:
            match = re.search(pattern, expr_lower)
            if match:
                return handler(match)

        # 如果无法规范化，返回原始输入
        return None

    def _check_location_validity(self, area_text: str) -> Tuple[bool, str, str]:
        """检查地点信息的有效性"""

        # 1. 检查具体地名
        specific_locations = [
            # 湖泊
            "青海湖", "太湖", "洞庭湖", "鄱阳湖", "洪泽湖", "巢湖", "滇池", "抚仙湖",
            # 河流
            "长江", "黄河", "珠江", "松花江", "淮河", "海河", "辽河",
            # 山脉
            "秦岭", "太行山", "昆仑山", "天山", "祁连山",
            # 地区
            "华北平原", "长三角", "珠三角", "京津冀", "成渝地区"
        ]

        for location in specific_locations:
            if location in area_text:
                return True, "specific", location

        # 2. 检查行政区划
        # 省级
        provinces = [
            "北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林", "黑龙江",
            "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
            "广东", "海南", "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾",
            "内蒙古", "广西", "西藏", "宁夏", "新疆", "香港", "澳门"
        ]

        for province in provinces:
            if province in area_text:
                return True, "administrative", f"{province}省" if province not in ["北京", "天津", "上海",
                                                                                   "重庆"] else province

        # 市县区级
        admin_patterns = [
            r'([^省]+省)',
            r'([^市]+市)',
            r'([^区]+区)',
            r'([^县]+县)',
            r'([^州]+州)',
            r'([^盟]+盟)'
        ]

        for pattern in admin_patterns:
            match = re.search(pattern, area_text)
            if match:
                return True, "administrative", match.group(1)

        # 3. 检查国家名称
        countries = [
            "中国", "柬埔寨", "越南", "泰国", "老挝", "缅甸", "马来西亚", "新加坡",
            "印度尼西亚", "菲律宾", "日本", "韩国", "印度", "巴基斯坦", "孟加拉国",
            "俄罗斯", "蒙古", "哈萨克斯坦"
        ]

        for country in countries:
            if country in area_text:
                return True, "country", country

        # 4. 检查经纬度
        coord_patterns = [
            r'(\d+\.?\d*)[°度]\s*[EW东西经]?\s*[,，]\s*(\d+\.?\d*)[°度]\s*[NS南北纬]?',
            r'[东西经]\s*(\d+\.?\d*)[°度]?\s*[,，]\s*[南北纬]\s*(\d+\.?\d*)[°度]?',
            r'(\d+\.?\d*)[,，]\s*(\d+\.?\d*)',  # 简单的数字对
            r'经度[:：]?\s*(\d+\.?\d*)\s*[,，]?\s*纬度[:：]?\s*(\d+\.?\d*)'
        ]

        for pattern in coord_patterns:
            match = re.search(pattern, area_text)
            if match:
                return True, "coordinates", f"经度{match.group(1)}, 纬度{match.group(2)}"

        return False, "unknown", ""

    def _check_numeric_range(self, range_text: str) -> Tuple[bool, str]:
        """检查是否包含数值范围信息"""

        # 面积单位模式
        area_patterns = [
            # 平方公里
            (r'(\d+\.?\d*)\s*平方公里', lambda m: f"{m.group(1)}平方公里"),
            (r'(\d+\.?\d*)\s*平方千米', lambda m: f"{m.group(1)}平方公里"),
            (r'(\d+\.?\d*)\s*km²', lambda m: f"{m.group(1)}平方公里"),
            (r'(\d+\.?\d*)\s*km2', lambda m: f"{m.group(1)}平方公里"),

            # 公顷
            (r'(\d+\.?\d*)\s*公顷', lambda m: f"{float(m.group(1)) / 100}平方公里"),
            (r'(\d+\.?\d*)\s*ha', lambda m: f"{float(m.group(1)) / 100}平方公里"),

            # 亩（重要：普通人常用）
            (r'(\d+\.?\d*)\s*亩', lambda m: f"{float(m.group(1)) * 0.000667}平方公里"),
            (r'(\d+\.?\d*)\s*万亩', lambda m: f"{float(m.group(1)) * 6.67}平方公里"),

            # 平方米
            (r'(\d+\.?\d*)\s*平方米', lambda m: f"{float(m.group(1)) / 1000000}平方公里"),
            (r'(\d+\.?\d*)\s*m²', lambda m: f"{float(m.group(1)) / 1000000}平方公里"),
            (r'(\d+\.?\d*)\s*m2', lambda m: f"{float(m.group(1)) / 1000000}平方公里"),

            # 范围表述
            (r'(\d+)\s*[-到至]\s*(\d+)\s*平方公里',
             lambda m: f"{m.group(1)}-{m.group(2)}平方公里"),
            (r'大约\s*(\d+\.?\d*)\s*平方公里',
             lambda m: f"约{m.group(1)}平方公里"),
            (r'约\s*(\d+\.?\d*)\s*平方公里',
             lambda m: f"约{m.group(1)}平方公里"),
        ]

        for pattern, handler in area_patterns:
            match = re.search(pattern, range_text)
            if match:
                try:
                    area_info = handler(match)
                    return True, area_info
                except:
                    pass

        return False, ""

    def _check_descriptive_range(self, range_text: str) -> Tuple[bool, str]:
        """检查是否包含描述性范围信息"""

        descriptive_patterns = {
            # 行政区划范围
            "全市": "city",
            "全省": "province",
            "全县": "county",
            "全区": "district",
            "全流域": "basin",
            "全境": "entire_area",

            # 相对范围
            "整个": "entire",
            "局部": "partial",
            "重点区域": "key_areas",
            "核心区": "core_area",
            "中心区": "central_area",
            "周边": "surrounding",

            # 大小描述
            "大范围": "large_scale",
            "中等范围": "medium_scale",
            "小范围": "small_scale",
            "点位": "point",
            "单点": "single_point",

            # 覆盖类型
            "全覆盖": "full_coverage",
            "部分覆盖": "partial_coverage",
            "重点覆盖": "key_coverage",
            "密集覆盖": "dense_coverage",
            "稀疏覆盖": "sparse_coverage"
        }

        for pattern, range_type in descriptive_patterns.items():
            if pattern in range_text:
                return True, f"{pattern}（{range_type}）"

        return False, ""

    async def _check_area_with_llm(self, area_text: str) -> bool:
        """使用LLM判断是否为有效的观测区域"""
        if not DEEPSEEK_API_KEY:
            return False

        prompt = f"""请判断以下文本是否为有效的地理位置或观测区域描述：

    文本："{area_text}"

    判断标准：
    1. 是否包含具体的地名、行政区划或地理坐标
    2. 是否可以在地图上定位到具体位置
    3. 是否为明确的地理区域

    请只回答"是"或"否"。"""

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }

            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个地理信息专家，精通各类地理位置的表述方式。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 10
            }

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(DEEPSEEK_API_URL, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        answer = result["choices"][0]["message"]["content"].strip()
                        return "是" in answer

        except Exception as e:
            logger.error(f"LLM地点判断失败: {e}")

        return False

    async def _check_range_with_llm(self, range_text: str) -> bool:
        """使用LLM判断是否为有效的覆盖范围"""
        if not DEEPSEEK_API_KEY:
            return False

        prompt = f"""请判断以下文本是否为有效的监测覆盖范围描述：

    文本："{range_text}"

    判断标准：
    1. 是否包含具体的面积数值（如平方公里、亩、公顷等）
    2. 是否包含范围大小的描述（如全市、局部、大范围等）
    3. 是否可以理解为具体的空间范围

    请只回答"是"或"否"。"""

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }

            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个遥感监测专家，精通各类空间范围的表述方式。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 10
            }

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(DEEPSEEK_API_URL, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        answer = result["choices"][0]["message"]["content"].strip()
                        return "是" in answer

        except Exception as e:
            logger.error(f"LLM范围判断失败: {e}")

        return False

    def _check_frequency_format(self, frequency_text: str) -> bool:
        """检查频率格式是否有效"""
        frequency_patterns = [
            r'每\s*小时\s*\d*\s*次?',
            r'每\s*天\s*\d*\s*次?',
            r'每\s*日\s*\d*\s*次?',
            r'每\s*周\s*\d*\s*次?',
            r'每\s*月\s*\d*\s*次?',
            r'每\s*年\s*\d*\s*次?',
            r'\d+\s*次\s*/\s*[天日周月年]',
            r'\d+\s*[天日]\s*\d*\s*次',
            r'实时',
            r'准实时',
            r'连续'
        ]

        for pattern in frequency_patterns:
            if re.search(pattern, frequency_text):
                return True

        return False

    def _check_duration_info(self, period_text: str) -> Tuple[bool, str]:
        """检查是否包含时长信息"""
        duration_patterns = [
            (r'(\d+)\s*个?月', lambda m: f"{m.group(1)}个月"),
            (r'(\d+)\s*年', lambda m: f"{m.group(1)}年"),
            (r'(\d+)\s*周', lambda m: f"{m.group(1)}周"),
            (r'(\d+)\s*天', lambda m: f"{m.group(1)}天"),
            (r'半年', lambda m: "6个月"),
            (r'一年', lambda m: "1年"),
            (r'长期', lambda m: "长期监测"),
            (r'短期', lambda m: "短期监测"),
            (r'全年', lambda m: "全年"),
            (r'生长季', lambda m: "生长季")
        ]

        for pattern, handler in duration_patterns:
            match = re.search(pattern, period_text)
            if match:
                duration_info = handler(match) if callable(handler) else handler
                return True, duration_info

        return False, ""

    def _check_start_end_info(self, period_text: str) -> Tuple[bool, str]:
        """检查是否包含起止时间信息"""
        # 检查具体的起止时间
        start_end_patterns = [
            r'从?\s*(\d+)\s*月\s*到\s*(\d+)\s*月',
            r'(\d+)\s*月\s*-\s*(\d+)\s*月',
            r'(\d{4})\s*年\s*(\d+)\s*月\s*到\s*(\d{4})\s*年\s*(\d+)\s*月',
            r'(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})\s*[到至\-]\s*(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})'
        ]

        for pattern in start_end_patterns:
            match = re.search(pattern, period_text)
            if match:
                return True, f"起止时间: {match.group(0)}"

        return False, ""

    async def _check_frequency_with_llm(self, frequency_text: str) -> bool:
        """使用LLM判断频率是否有效"""
        if not DEEPSEEK_API_KEY:
            return False

        prompt = f"""请判断以下文本是否为有效的观测频率描述：

    文本："{frequency_text}"

    判断标准：
    1. 是否明确指出了观测的时间间隔
    2. 是否可以理解为具体的观测频率
    3. 是否包含频率相关的关键词

    请只回答"是"或"否"。"""

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }

            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个遥感监测专家，精通各类观测频率的表述方式。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 10
            }

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(DEEPSEEK_API_URL, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        answer = result["choices"][0]["message"]["content"].strip()
                        return "是" in answer

        except Exception as e:
            logger.error(f"LLM频率判断失败: {e}")

        return False

    async def _check_period_with_llm(self, period_text: str) -> bool:
        """使用LLM判断监测周期是否有效"""
        if not DEEPSEEK_API_KEY:
            return False

        prompt = f"""请判断以下文本是否为有效的监测周期描述：

    文本："{period_text}"

    判断标准：
    1. 是否明确指出了监测的持续时间
    2. 是否可以理解为具体的监测时长

    请只回答"是"或"否"。"""

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }

            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个项目管理专家，精通各类时间周期的表述方式。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 10
            }

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(DEEPSEEK_API_URL, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        answer = result["choices"][0]["message"]["content"].strip()
                        return "是" in answer

        except Exception as e:
            logger.error(f"LLM周期判断失败: {e}")

        return False

    async def _check_web_search(self, target_text: str) -> bool:
        """通过网络搜索验证是否为有效的监测目标"""
        try:
            # 使用已有的web_search_tools
            from backend.src.tools.web_search_tools import WebSearchTool

            search_tool = WebSearchTool()
            # 搜索"遥感监测 + 目标"相关内容
            query = f"{target_text} 遥感监测 卫星观测"
            results = await search_tool.search(query, max_results=3, search_type="technical")

            # 检查搜索结果中是否包含相关关键词
            if results:
                relevant_keywords = ["监测", "遥感", "卫星", "观测", "分析", "评估"]
                for result in results:
                    content = (result.get("title", "") + " " + result.get("snippet", "")).lower()
                    if any(keyword in content for keyword in relevant_keywords):
                        return True

            return False

        except Exception as e:
            logger.error(f"网络搜索验证失败: {e}")
            return False

    async def _check_llm_professional(self, target_text: str) -> bool:
        """使用大模型判断是否为专业的监测目标"""
        if not DEEPSEEK_API_KEY:
            logger.warning("DeepSeek API密钥未设置，跳过LLM判断")
            return False

        prompt = f"""请判断以下文本是否为专业的遥感监测目标或监测任务描述：

文本："{target_text}"

判断标准：
1. 是否包含明确的监测目标（如人口密度分布、水质变化）
2. 是否符合遥感监测的常见应用场景
3. 是否使用了相关专业术语

请只回答"是"或"否"，不要有其他内容。"""

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }

            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个遥感监测专家，精通各类监测任务的专业术语。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 10
            }

            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(DEEPSEEK_API_URL, headers=headers, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        answer = result["choices"][0]["message"]["content"].strip()
                        return "是" in answer
                    else:
                        logger.error(f"DeepSeek API调用失败: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"LLM专业性判断失败: {e}")
            return False

    async def calculate_all_parameters_uncertainty(
            self,
            parameters: Dict[str, any]
    ) -> Dict[str, Dict]:
        """计算所有必需参数的不确定性"""
        results = {}

        # 1. 监测目标
        if "monitoring_target" in parameters:
            results["monitoring_target"] = await self.calculate_monitoring_target_uncertainty(
                parameters.get("monitoring_target")
            )

        # 2. 时间参数（频率和周期）
        time_uncertainty = await self.calculate_time_uncertainty(
            parameters.get("observation_frequency"),
            parameters.get("monitoring_period")
        )
        results.update(time_uncertainty)

        # 3. 地点参数（区域和范围）
        location_uncertainty = await self.calculate_location_uncertainty(
            parameters.get("observation_area"),
            parameters.get("coverage_range")
        )
        results.update(location_uncertainty)

        return results



# 创建全局实例
_uncertainty_calculator = None


def get_uncertainty_calculator() -> ParameterUncertaintyCalculator:
    """获取不确定性计算器单例"""
    global _uncertainty_calculator
    if _uncertainty_calculator is None:
        _uncertainty_calculator = ParameterUncertaintyCalculator()
    return _uncertainty_calculator