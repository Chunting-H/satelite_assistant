# backend/src/tools/crawler_agent/nodes.py

import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# 确保项目根目录在sys.path中
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent
sys.path.append(str(project_root))

from backend.config.config import settings
from backend.src.llm.multi_model_manager import get_multi_model_manager
from backend.src.tools.sate_search.satellite_crawler import SatelliteCrawler
from backend.src.tools.sate_search.satellite_data_processor import SatelliteDataProcessor
from .state import CrawlerState, CrawlLogEntry

logger = logging.getLogger(__name__)


class CrawlerNodes:
    """爬虫工作流节点集合"""
    
    def __init__(self):
        self.crawler = SatelliteCrawler()
        self.processor = SatelliteDataProcessor()
        self.model_manager = get_multi_model_manager()
        
    async def parameter_parsing_node(self, state: CrawlerState) -> CrawlerState:
        """参数解析节点 - 解析和验证任务参数"""
        try:
            logger.info(f"🔧 参数解析节点: 任务ID {state['task_id']}")
            
            # 验证目标站点
            supported_sites = ["Gunter's Space Page", "NASA EO Portal"]
            if not state['target_sites']:
                state['target_sites'] = ["Gunter's Space Page"]  # 默认站点
            
            # 验证关键词（可选）
            if not state['keywords']:
                state['keywords'] = []
            
            # 验证最大卫星数量
            if state['max_satellites'] <= 0:
                state['max_satellites'] = 10
            elif state['max_satellites'] > 50:
                state['max_satellites'] = 50  # 限制最大数量
            
            # 设置起始时间
            state['crawl_start_time'] = datetime.now().timestamp()
            state['current_node'] = 'parameter_parsing'
            state['error_occurred'] = False
            
            logger.info(f"✅ 参数解析完成: 站点{state['target_sites']}, 关键词{state['keywords']}, 最大数量{state['max_satellites']}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ 参数解析节点出错: {str(e)}")
            state['error_occurred'] = True
            state['error_message'] = f"参数解析失败: {str(e)}"
            return state
    
    async def web_crawler_node(self, state: CrawlerState) -> CrawlerState:
        """网页爬虫节点 - 爬取卫星数据"""
        try:
            logger.info(f"🕷️ 网页爬虫节点: 开始爬取 {state['target_sites']}")
            
            state['current_node'] = 'web_crawler'
            raw_data = []
            
            for site in state['target_sites']:
                if site == "Gunter's Space Page":
                    # 爬取Gunter's Space Page
                    site_data = await self.crawler.crawl_recent_satellites(
                        max_satellites=state['max_satellites']
                    )
                    raw_data.extend(site_data)
                    logger.info(f"📡 从 {site} 爬取到 {len(site_data)} 个卫星")
                
                # 这里可以添加其他网站的爬取逻辑
                # elif site == "NASA EO Portal":
                #     pass
            
            state['raw_satellite_data'] = raw_data
            
            if not raw_data:
                logger.warning("⚠️ 未爬取到任何卫星数据")
                state['processing_errors'] = ["未爬取到任何卫星数据"]
            else:
                logger.info(f"✅ 爬虫节点完成: 总共爬取 {len(raw_data)} 个卫星")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ 网页爬虫节点出错: {str(e)}")
            state['error_occurred'] = True
            state['error_message'] = f"网页爬虫失败: {str(e)}"
            return state
    
    async def data_cleaning_node(self, state: CrawlerState) -> CrawlerState:
        """数据清洗节点 - 使用大模型结构化数据"""
        try:
            logger.info(f"🧹 数据清洗节点: 处理 {len(state['raw_satellite_data'])} 个原始数据")
            
            state['current_node'] = 'data_cleaning'
            
            if not state['raw_satellite_data']:
                logger.warning("⚠️ 没有原始数据需要清洗")
                state['formatted_satellite_data'] = []
                return state
            
            # 使用数据处理器进行结构化
            formatted_data = await self.processor.clean_and_format_data(
                state['raw_satellite_data']
            )
            
            state['formatted_satellite_data'] = formatted_data
            
            # 统计处理结果
            success_count = len([d for d in formatted_data if d.get('satelliteName')])
            failed_count = len(state['raw_satellite_data']) - success_count
            
            logger.info(f"✅ 数据清洗完成: 成功{success_count}个, 失败{failed_count}个")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ 数据清洗节点出错: {str(e)}")
            state['error_occurred'] = True
            state['error_message'] = f"数据清洗失败: {str(e)}"
            return state
    
    async def duplicate_check_node(self, state: CrawlerState) -> CrawlerState:
        """重复检查节点 - 检查数据库中是否已存在"""
        try:
            logger.info(f"🔍 重复检查节点: 检查 {len(state['formatted_satellite_data'])} 个格式化数据")
            
            state['current_node'] = 'duplicate_check'
            
            if not state['formatted_satellite_data']:
                logger.warning("⚠️ 没有格式化数据需要检查")
                state['new_satellites_count'] = 0
                state['existing_satellites_count'] = 0
                return state
            
            # 使用数据处理器检查重复和存储
            storage_stats = await self.processor.check_and_store_satellites(
                state['formatted_satellite_data']
            )
            
            state['storage_stats'] = storage_stats
            state['new_satellites_count'] = storage_stats.get('new_satellites', 0)
            state['existing_satellites_count'] = storage_stats.get('existing_satellites', 0)
            state['failed_satellites_count'] = storage_stats.get('errors', 0)
            
            logger.info(f"✅ 重复检查完成: 新增{state['new_satellites_count']}个, 已存在{state['existing_satellites_count']}个")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ 重复检查节点出错: {str(e)}")
            state['error_occurred'] = True
            state['error_message'] = f"重复检查失败: {str(e)}"
            return state
    
    async def file_write_node(self, state: CrawlerState) -> CrawlerState:
        """文件写入节点 - 已在duplicate_check_node中处理"""
        try:
            logger.info(f"💾 文件写入节点: 数据已在重复检查节点中写入")
            
            state['current_node'] = 'file_write'
            
            # 数据已在duplicate_check_node中写入到eo_satellite.json
            # 这里主要是确认操作完成
            
            if state['new_satellites_count'] > 0:
                logger.info(f"✅ 文件写入完成: 新增 {state['new_satellites_count']} 个卫星到数据库")
            else:
                logger.info("ℹ️ 没有新卫星需要写入数据库")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ 文件写入节点出错: {str(e)}")
            state['error_occurred'] = True
            state['error_message'] = f"文件写入失败: {str(e)}"
            return state
    
    async def logging_node(self, state: CrawlerState) -> CrawlerState:
        """日志记录节点 - 记录爬取结果"""
        try:
            logger.info(f"📝 日志记录节点: 创建爬取日志")
            
            state['current_node'] = 'logging'
            state['crawl_end_time'] = datetime.now().timestamp()
            state['execution_time'] = state['crawl_end_time'] - state['crawl_start_time']
            
            # 创建日志条目
            log_entry = CrawlLogEntry()
            log_entry.target_sites = state['target_sites']
            log_entry.new_data_count = state['new_satellites_count']
            log_entry.updated_data_count = 0  # 暂时不支持更新
            log_entry.failed_count = state['failed_satellites_count']
            log_entry.fail_reasons = state['processing_errors']
            log_entry.execution_time = state['execution_time']
            log_entry.total_processed = len(state['raw_satellite_data'])
            
            # 提取卫星名称列表
            log_entry.data_list = [
                sat.get('satelliteName', 'Unknown') 
                for sat in state['formatted_satellite_data']
                if sat.get('satelliteName')
            ]
            
            # 保存到crawlLogs.json
            log_file_path = await self._save_crawl_log(log_entry)
            state['log_file_path'] = log_file_path
            
            # 同时创建详细的执行日志
            detailed_log_path = self.processor.create_crawl_log(
                state['storage_stats'], 
                state['execution_time'], 
                ', '.join(state['target_sites'])
            )
            
            logger.info(f"✅ 日志记录完成: {log_file_path}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ 日志记录节点出错: {str(e)}")
            state['error_occurred'] = True
            state['error_message'] = f"日志记录失败: {str(e)}"
            return state
    
    async def _save_crawl_log(self, log_entry: CrawlLogEntry) -> str:
        """保存爬取日志到crawlLogs.json"""
        try:
            logs_file = os.path.join(settings.data_dir, "crawlLogs.json")
            
            # 读取现有日志
            existing_logs = []
            if os.path.exists(logs_file):
                try:
                    with open(logs_file, 'r', encoding='utf-8') as f:
                        existing_logs = json.load(f)
                        if not isinstance(existing_logs, list):
                            existing_logs = []
                except Exception as e:
                    logger.warning(f"读取现有日志失败: {e}")
                    existing_logs = []
            
            # 添加新日志条目
            existing_logs.append(log_entry.to_dict())
            
            # 保持最近100条日志
            if len(existing_logs) > 100:
                existing_logs = existing_logs[-100:]
            
            # 保存日志文件
            os.makedirs(os.path.dirname(logs_file), exist_ok=True)
            with open(logs_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)
            
            return logs_file
            
        except Exception as e:
            logger.error(f"保存爬取日志失败: {e}")
            return ""
    
    async def error_handler_node(self, state: CrawlerState) -> CrawlerState:
        """错误处理节点"""
        try:
            logger.error(f"❌ 错误处理节点: {state['error_message']}")
            
            state['current_node'] = 'error_handler'
            state['crawl_end_time'] = datetime.now().timestamp()
            state['execution_time'] = state['crawl_end_time'] - state['crawl_start_time']
            
            # 创建错误日志
            log_entry = CrawlLogEntry()
            log_entry.target_sites = state['target_sites']
            log_entry.failed_count = 1
            log_entry.fail_reasons = [state['error_message']]
            log_entry.execution_time = state['execution_time']
            
            # 保存错误日志
            log_file_path = await self._save_crawl_log(log_entry)
            state['log_file_path'] = log_file_path
            
            return state
            
        except Exception as e:
            logger.error(f"错误处理节点也出错了: {str(e)}")
            return state


# 创建全局节点实例
crawler_nodes = CrawlerNodes()
