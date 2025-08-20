# backend/src/tools/satellite_crawler.py

import os
import sys
import json
import logging
import asyncio
import aiohttp
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import chardet

# 确保项目根目录在sys.path中
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent
sys.path.append(str(project_root))

logger = logging.getLogger(__name__)


class SatelliteCrawler:
    """卫星信息爬虫工具 - 专门用于抓取Gunter's Space Page网站"""

    def __init__(self):
        self.base_url = "https://space.skyrocket.de"
        self.session = None
        self.crawl_results = []
        
        # 请求头配置
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    async def create_session(self):
        """创建HTTP会话"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout,
                connector=connector
            )
    
    async def close_session(self):
        """关闭HTTP会话"""
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch_page(self, url: str, max_retries: int = 3) -> Optional[str]:
        """获取网页内容（带重试机制）"""
        for attempt in range(max_retries):
            try:
                await self.create_session()
                
                logger.info(f"正在获取页面: {url} (尝试 {attempt + 1}/{max_retries})")
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        # 获取原始字节数据
                        raw_content = await response.read()
                        
                        # 1. 首先尝试从响应头获取编码
                        charset = None
                        content_type = response.headers.get('content-type', '')
                        if 'charset=' in content_type:
                            charset = content_type.split('charset=')[1].strip()
                            logger.info(f"从响应头检测到编码: {charset}")
                        
                        # 2. 使用chardet自动检测编码
                        if not charset:
                            try:
                                detected = chardet.detect(raw_content)
                                charset = detected.get('encoding', 'utf-8')
                                confidence = detected.get('confidence', 0)
                                logger.info(f"自动检测编码: {charset} (置信度: {confidence:.2f})")
                            except Exception as e:
                                logger.warning(f"编码自动检测失败: {str(e)}")
                                charset = 'utf-8'
                        
                        # 3. 尝试使用检测到的编码解码
                        if charset:
                            try:
                                content = raw_content.decode(charset)
                                logger.info(f"成功获取页面: {url} (编码: {charset})")
                                return content
                            except UnicodeDecodeError as e:
                                logger.warning(f"使用检测编码 {charset} 解码失败: {str(e)}")
                        
                        # 4. 备用编码列表
                        fallback_encodings = ['utf-8', 'iso-8859-1', 'windows-1252', 'latin1', 'cp1252']
                        
                        for encoding in fallback_encodings:
                            try:
                                content = raw_content.decode(encoding)
                                logger.info(f"成功获取页面: {url} (备用编码: {encoding})")
                                return content
                            except UnicodeDecodeError:
                                continue
                        
                        # 5. 最后的尝试：使用错误处理模式
                        try:
                            content = raw_content.decode('utf-8', errors='replace')
                            logger.warning(f"使用UTF-8替换错误模式解码: {url}")
                            return content
                        except Exception:
                            logger.error(f"所有解码尝试都失败: {url}")
                            if attempt < max_retries - 1:
                                logger.info(f"将在 2 秒后重试...")
                                await asyncio.sleep(2)
                                continue
                            return None
                    else:
                        logger.warning(f"HTTP状态码: {response.status} (尝试 {attempt + 1}/{max_retries})")
                        if attempt < max_retries - 1:
                            logger.info(f"将在 2 秒后重试...")
                            await asyncio.sleep(2)
                            continue
                        else:
                            logger.error(f"获取页面失败: {url}, 最终状态码: {response.status}")
                            return None
                        
            except Exception as e:
                logger.error(f"请求页面时出错 (尝试 {attempt + 1}/{max_retries}): {url}, 错误: {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"将在 3 秒后重试...")
                    await asyncio.sleep(3)
                    continue
                else:
                    logger.error(f"所有重试都失败: {url}")
                    return None
        
        return None

    def parse_recent_launches(self, html_content: str) -> List[Dict[str, str]]:
        """解析最近发射的卫星列表"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找主页上的表格
            table = soup.find('table', class_='hplist')
            if not table:
                logger.warning("未找到卫星列表表格")
                return []
            
            satellites = []
            rows = table.find_all('tr')[1:]  # 跳过表头
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 6:
                    launch_id = cells[0].get_text(strip=True)
                    launch_date = cells[1].get_text(strip=True)
                    
                    # 获取卫星链接和名称
                    payload_cell = cells[2]
                    links = payload_cell.find_all('a')
                    
                    for link in links:
                        satellite_name = link.get_text(strip=True)
                        satellite_url = link.get('href', '')
                        
                        # 如果是相对URL，补全为绝对URL
                        if satellite_url.startswith('doc_sdat/'):
                            satellite_url = f"{self.base_url}/{satellite_url}"
                        
                        vehicle = cells[3].get_text(strip=True)
                        site = cells[4].get_text(strip=True)
                        remark = cells[5].get_text(strip=True)
                        
                        satellites.append({
                            'launch_id': launch_id,
                            'launch_date': launch_date,
                            'satellite_name': satellite_name,
                            'satellite_url': satellite_url,
                            'vehicle': vehicle,
                            'site': site,
                            'remark': remark
                        })
            
            logger.info(f"解析到 {len(satellites)} 个卫星条目")
            return satellites
            
        except Exception as e:
            logger.error(f"解析最近发射列表时出错: {str(e)}")
            return []

    async def crawl_satellite_detail(self, satellite_url: str, satellite_name: str) -> Optional[Dict[str, Any]]:
        """爬取单个卫星的详细信息（增强版 - 解析satdescription和satdata）"""
        try:
            html_content = await self.fetch_page(satellite_url)
            if not html_content:
                return None
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取基本信息
            satellite_info = {
                'satellite_name': satellite_name,
                'source_url': satellite_url,
                'crawl_time': datetime.now().isoformat(),
            }
            
            # 1. 提取卫星描述信息 (satdescription div)
            description_div = soup.find('div', id='satdescription')
            if description_div:
                description_text = description_div.get_text(separator=' ', strip=True)
                satellite_info['description'] = description_text
                logger.info(f"提取到卫星描述: {satellite_name}")
                
                # 从描述中提取卫星全名
                strong_tags = description_div.find_all('strong')
                if len(strong_tags) >= 2:
                    # 通常第一个strong是缩写，第二个是全名
                    satellite_info['short_name'] = strong_tags[0].get_text(strip=True)
                    satellite_info['full_name'] = strong_tags[1].get_text(strip=True)
                elif len(strong_tags) == 1:
                    satellite_info['short_name'] = strong_tags[0].get_text(strip=True)
            
            # 2. 提取卫星数据表格 (satdata table)
            satdata_table = soup.find('table', id='satdata')
            if satdata_table:
                satellite_data = {}
                rows = satdata_table.find_all('tr')
                
                for row in rows:
                    th = row.find('th', class_='lhead')
                    td = row.find('td', class_='rcont')
                    
                    if th and td:
                        key = th.get_text(strip=True).replace(':', '').lower()
                        value = td.get_text(strip=True)
                        
                        # 标准化字段名
                        field_mapping = {
                            'nation': 'nation',
                            'type / application': 'type_application', 
                            'operator': 'operator',
                            'contractors': 'contractors',
                            'equipment': 'equipment',
                            'configuration': 'configuration',
                            'propulsion': 'propulsion',
                            'power': 'power',
                            'lifetime': 'lifetime',
                            'mass': 'mass',
                            'orbit': 'orbit'
                        }
                        
                        mapped_key = field_mapping.get(key, key.replace(' ', '_').replace('/', '_'))
                        if value:  # 只保存非空值
                            satellite_data[mapped_key] = value
                
                satellite_info['detailed_specs'] = satellite_data
                logger.info(f"提取到 {len(satellite_data)} 个技术参数: {satellite_name}")
            
            # 3. 处理质量信息
            if 'detailed_specs' in satellite_info and 'mass' in satellite_info['detailed_specs']:
                mass_text = satellite_info['detailed_specs']['mass']
                mass_number = self._extract_number(mass_text)
                if mass_number:
                    satellite_info['mass_kg'] = mass_number
            
            # 4. 处理轨道信息
            if 'detailed_specs' in satellite_info and 'orbit' in satellite_info['detailed_specs']:
                orbit_text = satellite_info['detailed_specs']['orbit']
                satellite_info['orbit_info'] = orbit_text
                
                # 尝试从轨道信息中提取数值参数
                orbit_params = self._parse_orbit_parameters(orbit_text)
                if orbit_params:
                    satellite_info['orbit_parameters'] = orbit_params
            
            # 5. 处理应用类型
            if 'detailed_specs' in satellite_info and 'type_application' in satellite_info['detailed_specs']:
                app_type = satellite_info['detailed_specs']['type_application']
                satellite_info['primary_application'] = app_type
                
                # 分类应用类型
                applications = self._categorize_application(app_type)
                if applications:
                    satellite_info['applications'] = applications
            
            # 6. 查找发射相关信息（可能在其他表格中）
            all_tables = soup.find_all('table')
            for table in all_tables:
                if table.get('id') != 'satdata':  # 跳过已处理的satdata表格
                    self._extract_launch_info(table, satellite_info)
            
            # 7. 保存处理过的HTML内容用于调试（限制长度）
            satellite_info['raw_content_sample'] = html_content[:3000]
            
            logger.info(f"成功爬取卫星详细信息: {satellite_name}")
            return satellite_info
            
        except Exception as e:
            logger.error(f"爬取卫星详情时出错: {satellite_name}, 错误: {str(e)}")
            return None

    def _extract_number(self, text: str) -> Optional[float]:
        """从文本中提取数字"""
        try:
            # 匹配数字（包括小数）
            matches = re.findall(r'\d+\.?\d*', text)
            if matches:
                return float(matches[0])
        except:
            pass
        return None

    def _parse_orbit_parameters(self, orbit_text: str) -> Dict[str, Any]:
        """解析轨道参数文本"""
        orbit_params = {}
        
        try:
            # 常见轨道参数模式
            patterns = {
                'altitude': r'(\d+\.?\d*)\s*(?:km|kilometers?)\s*(?:altitude|高度)',
                'apogee': r'(\d+\.?\d*)\s*(?:km|kilometers?)\s*(?:×|x)\s*(\d+\.?\d*)\s*(?:km|kilometers?)',
                'inclination': r'(?:inclination|倾角)\s*[:\-]?\s*(\d+\.?\d*)\s*(?:°|degrees?|度)?',
                'period': r'(?:period|周期)\s*[:\-]?\s*(\d+\.?\d*)\s*(?:min|minutes?|分钟)',
                'eccentricity': r'(?:eccentricity|偏心率)\s*[:\-]?\s*(\d+\.?\d*)'
            }
            
            for param_name, pattern in patterns.items():
                matches = re.findall(pattern, orbit_text, re.IGNORECASE)
                if matches:
                    if param_name == 'apogee' and len(matches[0]) == 2:
                        # 椭圆轨道: apogee x perigee
                        orbit_params['apogee'] = float(matches[0][0])
                        orbit_params['perigee'] = float(matches[0][1])
                    else:
                        orbit_params[param_name] = float(matches[0][0] if isinstance(matches[0], tuple) else matches[0])
            
            # 检测轨道类型
            orbit_lower = orbit_text.lower()
            if 'geo' in orbit_lower or 'geostationary' in orbit_lower:
                orbit_params['orbit_type'] = 'GEO'
            elif 'leo' in orbit_lower or 'low earth' in orbit_lower:
                orbit_params['orbit_type'] = 'LEO'
            elif 'meo' in orbit_lower or 'medium earth' in orbit_lower:
                orbit_params['orbit_type'] = 'MEO'
            elif 'heo' in orbit_lower or 'highly elliptical' in orbit_lower:
                orbit_params['orbit_type'] = 'HEO'
            elif 'sun-synchronous' in orbit_lower or 'sso' in orbit_lower:
                orbit_params['orbit_type'] = 'SSO'
                
        except Exception as e:
            logger.warning(f"解析轨道参数时出错: {str(e)}")
        
        return orbit_params

    def _categorize_application(self, app_type: str) -> List[str]:
        """分类应用类型"""
        applications = []
        app_lower = app_type.lower()
        
        # 应用类型关键词映射
        app_keywords = {
            'communication': ['communication', 'telecom', 'relay', 'broadcast'],
            'earth observation': ['observation', 'monitoring', 'imaging', 'remote sensing', 'surveillance'],
            'navigation': ['navigation', 'gps', 'glonass', 'galileo', 'beidou'],
            'meteorology': ['weather', 'meteorology', 'climate', 'atmospheric'],
            'scientific': ['scientific', 'research', 'experiment', 'technology demonstration'],
            'military': ['military', 'defense', 'reconnaissance', 'surveillance'],
            'technology demonstration': ['technology', 'demonstration', 'test', 'experimental']
        }
        
        for category, keywords in app_keywords.items():
            if any(keyword in app_lower for keyword in keywords):
                applications.append(category)
        
        # 如果没有匹配到任何分类，使用原始文本
        if not applications:
            applications.append(app_type)
        
        return applications

    def _extract_launch_info(self, table, satellite_info: Dict[str, Any]):
        """从表格中提取发射相关信息"""
        try:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    # 查找发射相关信息
                    if 'launch' in key and 'date' in key:
                        satellite_info['launch_date_detail'] = value
                    elif 'launch' in key and 'site' in key:
                        satellite_info['launch_site_detail'] = value
                    elif 'launch' in key and 'vehicle' in key:
                        satellite_info['launch_vehicle_detail'] = value
                    elif 'cospar' in key:
                        satellite_info['cospar_id'] = value
                    elif 'norad' in key or 'catalog' in key:
                        satellite_info['norad_id'] = self._extract_number(value)
                        
        except Exception as e:
            logger.warning(f"提取发射信息时出错: {str(e)}")

    async def crawl_recent_satellites(self, max_satellites: int = 10) -> List[Dict[str, Any]]:
        """爬取最近发射的卫星信息"""
        try:
            logger.info("开始爬取Gunter's Space Page最近发射的卫星")
            
            # 1. 获取主页内容
            main_page_content = await self.fetch_page(self.base_url)
            if not main_page_content:
                logger.error("无法获取主页内容")
                return []
            
            # 2. 解析最近发射列表
            recent_satellites = self.parse_recent_launches(main_page_content)
            
            if not recent_satellites:
                logger.warning("未找到最近发射的卫星")
                return []
            
            # 3. 限制爬取数量
            satellites_to_crawl = recent_satellites[:max_satellites]
            logger.info(f"准备爬取 {len(satellites_to_crawl)} 个卫星的详细信息")
            
            # 4. 并发爬取详细信息
            detail_tasks = []
            for sat in satellites_to_crawl:
                if sat['satellite_url']:
                    task = self.crawl_satellite_detail(sat['satellite_url'], sat['satellite_name'])
                    detail_tasks.append(task)
            
            # 执行并发爬取
            detailed_results = await asyncio.gather(*detail_tasks, return_exceptions=True)
            
            # 5. 整合结果
            final_results = []
            for i, (basic_info, detailed_info) in enumerate(zip(satellites_to_crawl, detailed_results)):
                if isinstance(detailed_info, Exception):
                    logger.error(f"爬取详情失败: {basic_info['satellite_name']}, 错误: {detailed_info}")
                    # 即使详情爬取失败，也保存基本信息
                    final_results.append({**basic_info, 'detail_error': str(detailed_info)})
                elif detailed_info:
                    # 合并基本信息和详细信息
                    combined_info = {**basic_info, **detailed_info}
                    final_results.append(combined_info)
                else:
                    # 详情爬取失败，只保存基本信息
                    final_results.append(basic_info)
            
            logger.info(f"成功爬取 {len(final_results)} 个卫星信息")
            return final_results
            
        except Exception as e:
            logger.error(f"爬取最近卫星时出错: {str(e)}")
            return []
        finally:
            await self.close_session()

    async def search_single_satellite(self, satellite_name: str) -> Optional[Dict[str, Any]]:
        """搜索单个卫星的信息"""
        try:
            logger.info(f"搜索单个卫星: {satellite_name}")
            
            # 构建搜索URL（这里需要根据实际网站的搜索功能调整）
            # 由于Gunter's Space Page可能没有直接的搜索API，
            # 我们可以尝试通过页面名称模式来构建URL
            
            # 常见的页面命名模式
            possible_urls = [
                f"{self.base_url}/doc_sdat/{satellite_name.lower().replace(' ', '-')}.htm",
                f"{self.base_url}/doc_sdat/{satellite_name.lower().replace(' ', '_')}.htm",
                f"{self.base_url}/doc_sdat/{satellite_name.lower()}.htm"
            ]
            
            for url in possible_urls:
                detail_info = await self.crawl_satellite_detail(url, satellite_name)
                if detail_info:
                    logger.info(f"成功找到卫星: {satellite_name}")
                    return detail_info
            
            logger.warning(f"未找到卫星: {satellite_name}")
            return None
            
        except Exception as e:
            logger.error(f"搜索单个卫星时出错: {satellite_name}, 错误: {str(e)}")
            return None
        finally:
            await self.close_session()


# 测试函数
async def test_satellite_crawler():
    """测试卫星爬虫功能"""
    crawler = SatelliteCrawler()
    
    try:
        # 测试爬取最近发射的卫星
        print("测试爬取最近发射的卫星...")
        recent_satellites = await crawler.crawl_recent_satellites(max_satellites=3)
        
        print(f"\n成功爬取 {len(recent_satellites)} 个卫星")
        for sat in recent_satellites:
            print(f"- {sat.get('satellite_name', 'Unknown')}: {sat.get('launch_date', 'Unknown')}")
        
        if recent_satellites:
            print(f"\n第一个卫星的详细信息示例:")
            first_sat = recent_satellites[0]
            for key, value in first_sat.items():
                if key != 'raw_content':  # 跳过原始内容
                    print(f"  {key}: {value}")
    
    except Exception as e:
        print(f"测试失败: {str(e)}")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_satellite_crawler())
