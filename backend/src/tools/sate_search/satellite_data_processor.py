# backend/src/tools/satellite_data_processor.py

import os
import sys
import json
import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# 确保项目根目录在sys.path中
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent
sys.path.append(str(project_root))

from backend.config.config import settings

logger = logging.getLogger(__name__)


class SatelliteDataProcessor:
    """卫星数据处理器 - 负责数据清洗、格式化和存储"""

    def __init__(self):
        self.data_file_path = os.path.join(settings.data_dir, "eo_satellite.json")
        self.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.deepseek_api_url = "https://api.deepseek.com/v1/chat/completions"
        
    async def clean_and_format_data(self, raw_satellite_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用DeepSeek大模型清洗和格式化卫星数据"""
        try:
            if not self.deepseek_api_key:
                logger.warning("未配置DeepSeek API密钥，使用默认格式化")
                return await self._default_format_data(raw_satellite_data)
            
            logger.info(f"开始使用DeepSeek模型格式化 {len(raw_satellite_data)} 个卫星数据")
            
            formatted_satellites = []
            
            # 批量处理（每次处理2-3个卫星，避免API调用过长）
            batch_size = 2
            for i in range(0, len(raw_satellite_data), batch_size):
                batch = raw_satellite_data[i:i + batch_size]
                formatted_batch = await self._format_batch_with_deepseek(batch)
                formatted_satellites.extend(formatted_batch)
                
                # 添加延迟避免API限制
                await asyncio.sleep(1)
            
            logger.info(f"成功格式化 {len(formatted_satellites)} 个卫星数据")
            return formatted_satellites
            
        except Exception as e:
            logger.error(f"数据格式化时出错: {str(e)}")
            # 降级到默认格式化
            return await self._default_format_data(raw_satellite_data)

    async def _format_batch_with_deepseek(self, batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用DeepSeek API格式化一批数据"""
        try:
            # 构建prompt
            prompt = self._build_formatting_prompt(batch_data)
            
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": """你是一个专业的卫星数据格式化专家。请将提供的原始卫星数据转换为标准的JSON格式。

⚠️ 重要输出要求：
1. 必须返回纯JSON格式，不要包含任何markdown标记（如```json或```）
2. 不要添加任何解释文字或前导说明
3. 直接返回JSON数组或对象
4. 确保JSON格式完全有效

数据格式要求：
1. 严格按照提供的JSON模板格式
2. 提取所有可用的数值参数
3. 清理和标准化文本内容
4. 补充缺失字段（设为空值或默认值）
5. 确保数据类型正确（数字、字符串、数组等）
6. null值用于缺失的数字字段，空字符串用于缺失的文本字段

字段要求：
- satelliteName: 卫星主要名称
- alternateNames: 所有别名的数组（不包含重复的主名称）
- launchDate: 发射日期 (YYYY-MM-DD格式)
- applications: 应用领域数组
- 轨道参数: period, inclination, apogee, perigee等数值字段（使用数字类型）
- 质量参数: dryMass, launchMass等数值字段（使用数字类型）
- 空值处理: 数字字段用null，字符串字段用""，数组字段用[]"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 4000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.deepseek_api_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result["choices"][0]["message"]["content"]
                        
                        # 解析JSON响应（处理markdown格式）
                        try:
                            # 清理可能的markdown格式
                            cleaned_content = self._clean_json_response(content)
                            formatted_data = json.loads(cleaned_content)
                            if isinstance(formatted_data, list):
                                return formatted_data
                            else:
                                return [formatted_data]
                        except json.JSONDecodeError as e:
                            logger.error(f"DeepSeek返回的JSON解析失败: {str(e)}")
                            logger.error(f"原始内容: {content}")
                            # 尝试更激进的清理
                            try:
                                fallback_content = self._extract_json_from_text(content)
                                if fallback_content:
                                    formatted_data = json.loads(fallback_content)
                                    if isinstance(formatted_data, list):
                                        return formatted_data
                                    else:
                                        return [formatted_data]
                            except Exception as fallback_e:
                                logger.error(f"备用JSON解析也失败: {str(fallback_e)}")
                            
                            return await self._default_format_data(batch_data)
                    else:
                        error_text = await response.text()
                        logger.error(f"DeepSeek API调用失败: {response.status}, {error_text}")
                        return await self._default_format_data(batch_data)
        
        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {str(e)}")
            return await self._default_format_data(batch_data)

    def _build_formatting_prompt(self, batch_data: List[Dict[str, Any]]) -> str:
        """构建格式化提示词（增强版 - 包含详情页面数据）"""
        # JSON模板
        template = {
            "satelliteName": "示例卫星名称",
            "alternateNames": ["别名1", "别名2"],
            "COSPARId": "2024-001A",
            "NORADId": 12345,
            "objectType": "PAY",
            "operStatusCode": "Operational",
            "satelliteAgencies": "NASA",
            "owner": "United States",
            "launchDate": "2024-01-01",
            "launchSite": "发射场",
            "eolDate": "",
            "period": 95.46,
            "inclination": 50.28,
            "apogee": 617.0,
            "perigee": 465.0,
            "rcs": 0.5003,
            "dryMass": 41.0,
            "launchMass": 41.0,
            "orbitCenter": "EA",
            "orbitType": "LEO",
            "orbitAltitude": "722",
            "repeatCycle": "",
            "ect": "",
            "orbitLongitude": "",
            "orbitSense": "",
            "applications": ["Earth observation"],
            "webInfo": [],
            "dataPortal": [],
            "instrumentNames": [],
            "instrumentIds": [],
            "isEO": "Earth observation",
            "relatedSatIds": [],
            "eoPortal": "",
            "hasInstrumentId": []
        }
        
        # 为每个卫星构建详细的数据描述
        enhanced_data_description = []
        
        for satellite in batch_data:
            sat_desc = {
                "基本信息": {
                    "卫星名称": satellite.get('satellite_name', ''),
                    "发射日期": satellite.get('launch_date', ''),
                    "发射载具": satellite.get('vehicle', ''),
                    "发射场": satellite.get('site', ''),
                    "备注": satellite.get('remark', '')
                }
            }
            
            # 添加详细规格（如果有的话）
            if 'detailed_specs' in satellite:
                sat_desc["详细技术规格"] = satellite['detailed_specs']
            
            # 添加卫星描述
            if 'description' in satellite:
                sat_desc["卫星描述"] = satellite['description']
            
            # 添加卫星全名和缩写
            if 'full_name' in satellite:
                sat_desc["全名"] = satellite['full_name']
            if 'short_name' in satellite:
                sat_desc["缩写"] = satellite['short_name']
            
            # 添加轨道参数
            if 'orbit_parameters' in satellite:
                sat_desc["轨道参数"] = satellite['orbit_parameters']
            
            # 添加质量信息
            if 'mass_kg' in satellite:
                sat_desc["质量(kg)"] = satellite['mass_kg']
            
            # 添加应用分类
            if 'primary_application' in satellite:
                sat_desc["主要应用"] = satellite['primary_application']
            
            # 添加发射相关详细信息
            launch_details = {}
            for key in ['launch_date_detail', 'launch_site_detail', 'launch_vehicle_detail', 'cospar_id', 'norad_id']:
                if key in satellite:
                    launch_details[key] = satellite[key]
            if launch_details:
                sat_desc["发射详情"] = launch_details
            
            enhanced_data_description.append(sat_desc)
        
        prompt = f"""请将以下包含详细信息的卫星数据转换为标准JSON格式。

数据来源：已从Gunter's Space Page详情页面爬取了完整的卫星技术规格和描述信息。

标准格式模板：
{json.dumps(template, indent=2, ensure_ascii=False)}

详细的原始卫星数据：
{json.dumps(enhanced_data_description, indent=2, ensure_ascii=False)}

格式化要求：
1. 使用"基本信息"中的卫星名称作为satelliteName
2. 如果有"全名"和"缩写"，将它们加入alternateNames数组
3. 从"详细技术规格"中提取对应的技术参数：
   - nation → owner
   - type_application → applications (转换为数组)
   - operator → satelliteAgencies
   - contractors → 可作为补充信息
   - mass → dryMass和launchMass
   - orbit → 分析提取轨道参数 (period, inclination, apogee, perigee, orbitType)
4. 从"轨道参数"中提取数值：apogee, perigee, inclination, period等
5. 从"发射详情"中提取：cospar_id → COSPARId, norad_id → NORADId
6. 根据"主要应用"确定applications数组和isEO字段
7. 将"卫星描述"信息整合到相关字段中
8. 所有数值字段确保是数字类型，字符串字段确保是字符串类型
9. 如果某个字段无法从原始数据中获取，使用合适的默认值

⚠️ 输出要求：
1. 必须返回纯JSON格式
2. 不要使用markdown代码块标记（```json或```）
3. 不要添加任何说明文字
4. 直接输出JSON数组
5. 确保所有字段类型正确
6. 数字字段使用数字类型，不要用字符串包裹"""
        
        return prompt

    async def _default_format_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """默认格式化方法（增强版 - 当DeepSeek不可用时）"""
        formatted_satellites = []
        
        for raw_sat in raw_data:
            try:
                # 基础信息
                satellite_name = raw_sat.get('satellite_name', 'Unknown')
                
                # 构建alternateNames数组
                alternate_names = []
                if raw_sat.get('short_name') and raw_sat.get('short_name') != satellite_name:
                    alternate_names.append(raw_sat.get('short_name'))
                if raw_sat.get('full_name') and raw_sat.get('full_name') != satellite_name:
                    alternate_names.append(raw_sat.get('full_name'))
                
                # 从详细规格中提取信息
                detailed_specs = raw_sat.get('detailed_specs', {})
                
                formatted_sat = {
                    "satelliteName": satellite_name,
                    "alternateNames": alternate_names,
                    "COSPARId": raw_sat.get('cospar_id', ''),
                    "NORADId": int(raw_sat.get('norad_id')) if raw_sat.get('norad_id') else None,
                    "objectType": "PAY",
                    "operStatusCode": "Unknown",
                    "satelliteAgencies": detailed_specs.get('operator', raw_sat.get('agency', 'Unknown')),
                    "owner": detailed_specs.get('nation', 'Unknown'),
                    "launchDate": self._format_date(raw_sat.get('launch_date', '')),
                    "launchSite": raw_sat.get('site', ''),
                    "eolDate": "",
                    "period": None,
                    "inclination": None,
                    "apogee": None,
                    "perigee": None,
                    "rcs": None,
                    "dryMass": None,
                    "launchMass": None,
                    "orbitCenter": "EA",
                    "orbitType": "Unknown",
                    "orbitAltitude": "",
                    "repeatCycle": "",
                    "ect": "",
                    "orbitLongitude": "",
                    "orbitSense": "",
                    "applications": [],
                    "webInfo": [raw_sat.get('source_url', '')],
                    "dataPortal": [],
                    "instrumentNames": [],
                    "instrumentIds": [],
                    "isEO": "Unknown",
                    "relatedSatIds": [],
                    "eoPortal": "",
                    "hasInstrumentId": [],
                    # 添加爬取相关的元数据
                    "_crawl_metadata": {
                        "crawl_time": raw_sat.get('crawl_time'),
                        "source_url": raw_sat.get('source_url'),
                        "launch_id": raw_sat.get('launch_id'),
                        "vehicle": raw_sat.get('vehicle'),
                        "remark": raw_sat.get('remark'),
                        "description": raw_sat.get('description', ''),
                        "detailed_specs": detailed_specs
                    }
                }
                
                # 处理质量信息
                if raw_sat.get('mass_kg'):
                    formatted_sat['dryMass'] = float(raw_sat['mass_kg'])
                    formatted_sat['launchMass'] = float(raw_sat['mass_kg'])
                elif detailed_specs.get('mass'):
                    mass_number = self._extract_number(detailed_specs['mass'])
                    if mass_number:
                        formatted_sat['dryMass'] = mass_number
                        formatted_sat['launchMass'] = mass_number
                
                # 处理轨道参数（增强版）
                orbit_params = raw_sat.get('orbit_parameters', {})
                if isinstance(orbit_params, dict):
                    if 'apogee' in orbit_params:
                        formatted_sat['apogee'] = float(orbit_params['apogee'])
                    if 'perigee' in orbit_params:
                        formatted_sat['perigee'] = float(orbit_params['perigee'])
                    if 'inclination' in orbit_params:
                        formatted_sat['inclination'] = float(orbit_params['inclination'])
                    if 'period' in orbit_params:
                        formatted_sat['period'] = float(orbit_params['period'])
                    if 'orbit_type' in orbit_params:
                        formatted_sat['orbitType'] = orbit_params['orbit_type']
                
                # 从详细规格中提取轨道信息
                if detailed_specs.get('orbit'):
                    formatted_sat['orbitType'] = self._determine_orbit_type(detailed_specs['orbit'])
                
                # 处理应用类型
                applications = []
                if raw_sat.get('primary_application'):
                    applications = self._categorize_application_simple(raw_sat['primary_application'])
                elif detailed_specs.get('type_application'):
                    applications = self._categorize_application_simple(detailed_specs['type_application'])
                elif raw_sat.get('applications'):
                    applications = raw_sat['applications']
                
                formatted_sat['applications'] = applications
                
                # 确定是否为地球观测卫星
                if applications:
                    earth_obs_keywords = ['earth observation', 'monitoring', 'remote sensing', 'imaging']
                    is_eo = any(keyword in app.lower() for app in applications for keyword in earth_obs_keywords)
                    formatted_sat['isEO'] = "Earth observation" if is_eo else "Other"
                
                formatted_satellites.append(formatted_sat)
                
            except Exception as e:
                logger.error(f"默认格式化单个卫星时出错: {str(e)}")
                continue
        
        return formatted_satellites
    
    def _extract_number(self, text: str) -> Optional[float]:
        """从文本中提取数字"""
        try:
            import re
            matches = re.findall(r'\d+\.?\d*', str(text))
            if matches:
                return float(matches[0])
        except:
            pass
        return None
    
    def _determine_orbit_type(self, orbit_text: str) -> str:
        """确定轨道类型"""
        orbit_lower = orbit_text.lower()
        if 'geo' in orbit_lower or 'geostationary' in orbit_lower:
            return 'GEO'
        elif 'leo' in orbit_lower or 'low earth' in orbit_lower:
            return 'LEO'
        elif 'meo' in orbit_lower or 'medium earth' in orbit_lower:
            return 'MEO'
        elif 'sun-synchronous' in orbit_lower or 'sso' in orbit_lower:
            return 'SSO'
        else:
            return 'Unknown'
    
    def _categorize_application_simple(self, app_type: str) -> List[str]:
        """简单的应用分类"""
        applications = []
        app_lower = app_type.lower()
        
        if 'communication' in app_lower:
            applications.append('Communication')
        if any(keyword in app_lower for keyword in ['observation', 'monitoring', 'imaging', 'remote sensing']):
            applications.append('Earth observation')
        if 'navigation' in app_lower:
            applications.append('Navigation')
        if any(keyword in app_lower for keyword in ['weather', 'meteorology', 'climate']):
            applications.append('Meteorology')
        if any(keyword in app_lower for keyword in ['scientific', 'research', 'experiment']):
            applications.append('Scientific')
        
        # 如果没有匹配到任何分类，使用原始文本
        if not applications:
            applications.append(app_type)
        
        return applications

    def _clean_json_response(self, content: str) -> str:
        """清理DeepSeek响应中的markdown格式和其他干扰内容"""
        try:
            # 移除markdown代码块标记
            content = content.strip()
            
            # 移除开头的```json或```
            if content.startswith('```json'):
                content = content[7:]  # 移除```json
            elif content.startswith('```'):
                content = content[3:]   # 移除```
            
            # 移除结尾的```
            if content.endswith('```'):
                content = content[:-3]
            
            # 移除首尾空白
            content = content.strip()
            
            # 移除可能的前导文本（如"以下是格式化后的JSON："）
            lines = content.split('\n')
            start_idx = 0
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if line_stripped.startswith('[') or line_stripped.startswith('{'):
                    start_idx = i
                    break
            
            if start_idx > 0:
                content = '\n'.join(lines[start_idx:])
            
            return content.strip()
            
        except Exception as e:
            logger.warning(f"清理JSON响应时出错: {str(e)}")
            return content

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """从文本中提取JSON内容（更激进的方法）"""
        try:
            import re
            
            # 尝试找到JSON数组的开始和结束
            # 查找第一个 [ 或 {
            start_chars = ['[', '{']
            end_chars = [']', '}']
            
            for start_char, end_char in zip(start_chars, end_chars):
                start_idx = text.find(start_char)
                if start_idx != -1:
                    # 从后往前找对应的结束字符
                    end_idx = text.rfind(end_char)
                    if end_idx != -1 and end_idx > start_idx:
                        json_candidate = text[start_idx:end_idx + 1]
                        
                        # 验证这是否是有效的JSON
                        try:
                            json.loads(json_candidate)
                            return json_candidate
                        except json.JSONDecodeError:
                            continue
            
            # 如果上面的方法失败，尝试使用正则表达式
            # 查找JSON数组模式
            json_array_pattern = r'\[[\s\S]*\]'
            matches = re.findall(json_array_pattern, text)
            
            for match in matches:
                try:
                    json.loads(match)
                    return match
                except json.JSONDecodeError:
                    continue
            
            # 查找JSON对象模式
            json_object_pattern = r'\{[\s\S]*\}'
            matches = re.findall(json_object_pattern, text)
            
            for match in matches:
                try:
                    json.loads(match)
                    return match
                except json.JSONDecodeError:
                    continue
                    
            return None
            
        except Exception as e:
            logger.warning(f"从文本提取JSON时出错: {str(e)}")
            return None

    def _format_date(self, date_str: str) -> str:
        """格式化日期字符串"""
        if not date_str:
            return ""
        
        try:
            # 常见日期格式转换
            if '.' in date_str:
                # DD.MM.YYYY 格式
                parts = date_str.split('.')
                if len(parts) == 3:
                    day, month, year = parts
                    return f"20{year}-{month.zfill(2)}-{day.zfill(2)}" if len(year) == 2 else f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            return date_str
        except:
            return date_str

    async def check_and_store_satellites(self, formatted_satellites: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查数据库中是否存在卫星，并存储新卫星"""
        try:
            # 读取现有数据
            existing_satellites = await self._load_existing_satellites()
            
            # 统计信息
            stats = {
                "total_processed": len(formatted_satellites),
                "new_satellites": 0,
                "existing_satellites": 0,
                "updated_satellites": 0,
                "errors": 0
            }
            
            new_satellites = []
            
            for satellite in formatted_satellites:
                try:
                    satellite_name = satellite.get('satelliteName', '')
                    
                    # 检查是否已存在（基于卫星名称）
                    existing_sat = self._find_existing_satellite(existing_satellites, satellite_name)
                    
                    if existing_sat:
                        # 卫星已存在，可以选择更新或跳过
                        stats["existing_satellites"] += 1
                        logger.info(f"卫星已存在: {satellite_name}")
                        
                        # 可以在这里添加更新逻辑
                        # if self._should_update_satellite(existing_sat, satellite):
                        #     self._update_satellite(existing_satellites, satellite)
                        #     stats["updated_satellites"] += 1
                    else:
                        # 新卫星，添加到列表
                        new_satellites.append(satellite)
                        stats["new_satellites"] += 1
                        logger.info(f"发现新卫星: {satellite_name}")
                
                except Exception as e:
                    logger.error(f"处理单个卫星时出错: {str(e)}")
                    stats["errors"] += 1
            
            # 保存新卫星到数据库
            if new_satellites:
                await self._save_new_satellites(existing_satellites, new_satellites)
                logger.info(f"成功保存 {len(new_satellites)} 个新卫星")
            
            return stats
            
        except Exception as e:
            logger.error(f"检查和存储卫星时出错: {str(e)}")
            return {"error": str(e)}

    async def _load_existing_satellites(self) -> List[Dict[str, Any]]:
        """加载现有卫星数据"""
        try:
            if os.path.exists(self.data_file_path):
                with open(self.data_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    else:
                        logger.warning("数据文件格式不正确，应为数组")
                        return []
            else:
                logger.info("数据文件不存在，将创建新文件")
                return []
        except Exception as e:
            logger.error(f"加载现有卫星数据时出错: {str(e)}")
            return []

    def _find_existing_satellite(self, existing_satellites: List[Dict[str, Any]], satellite_name: str) -> Optional[Dict[str, Any]]:
        """查找现有卫星"""
        for sat in existing_satellites:
            if sat.get('satelliteName', '').lower() == satellite_name.lower():
                return sat
            
            # 检查别名
            alternate_names = sat.get('alternateNames', [])
            if isinstance(alternate_names, list):
                for alt_name in alternate_names:
                    if alt_name.lower() == satellite_name.lower():
                        return sat
        
        return None

    async def _save_new_satellites(self, existing_satellites: List[Dict[str, Any]], new_satellites: List[Dict[str, Any]]):
        """保存新卫星到数据文件"""
        try:
            # 合并现有和新卫星
            all_satellites = existing_satellites + new_satellites
            
            # 创建备份
            if os.path.exists(self.data_file_path):
                backup_path = f"{self.data_file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.data_file_path, backup_path)
                logger.info(f"创建数据备份: {backup_path}")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.data_file_path), exist_ok=True)
            
            # 保存更新后的数据
            with open(self.data_file_path, 'w', encoding='utf-8') as f:
                json.dump(all_satellites, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存数据到: {self.data_file_path}")
            
        except Exception as e:
            logger.error(f"保存卫星数据时出错: {str(e)}")
            raise

    def create_crawl_log(self, crawl_stats: Dict[str, Any], execution_time: float, target_website: str) -> str:
        """创建爬取日志"""
        try:
            log_dir = os.path.join(settings.data_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = os.path.join(log_dir, f"satellite_crawl_{timestamp}.json")
            
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "execution_time": execution_time,
                "target_website": target_website,
                "statistics": crawl_stats,
                "status": "success" if crawl_stats.get("new_satellites", 0) > 0 else "no_new_data"
            }
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"爬取日志已保存: {log_file}")
            return log_file
            
        except Exception as e:
            logger.error(f"创建爬取日志时出错: {str(e)}")
            return ""


# 测试函数
async def test_data_processor():
    """测试数据处理器"""
    processor = SatelliteDataProcessor()
    
    # 模拟原始数据
    raw_data = [
        {
            "satellite_name": "测试卫星1",
            "launch_date": "05.08.2025",
            "agency": "NASA",
            "mass": 500.0,
            "applications": ["Earth observation"],
            "source_url": "https://example.com/sat1"
        }
    ]
    
    # 测试格式化
    formatted_data = await processor.clean_and_format_data(raw_data)
    print("格式化后的数据:")
    print(json.dumps(formatted_data, ensure_ascii=False, indent=2))
    
    # 测试存储
    stats = await processor.check_and_store_satellites(formatted_data)
    print(f"\n存储统计: {stats}")


if __name__ == "__main__":
    asyncio.run(test_data_processor())
