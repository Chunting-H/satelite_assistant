# backend/src/tools/crawler_agent/crawler_workflow.py

import os
import sys
import json
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

# 确保项目根目录在sys.path中
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent
sys.path.append(str(project_root))

from backend.config.config import settings
from .state import CrawlerState, CrawlJob
from .nodes import crawler_nodes

logger = logging.getLogger(__name__)


class CrawlerWorkflow:
    """智能爬虫工作流管理器"""
    
    def __init__(self):
        self.active_jobs: Dict[str, CrawlJob] = {}
        self.job_history: List[CrawlJob] = []
        self.nodes = crawler_nodes
        
        # 定义工作流路径
        self.workflow_graph = {
            "START": "parameter_parsing",
            "parameter_parsing": "web_crawler", 
            "web_crawler": "data_cleaning",
            "data_cleaning": "duplicate_check",
            "duplicate_check": "file_write",
            "file_write": "logging",
            "logging": "END",
            "error_handler": "END"
        }
    
    async def create_crawl_job(
        self, 
        target_sites: List[str] = None, 
        keywords: List[str] = None,
        max_satellites: int = 10
    ) -> str:
        """创建爬取任务"""
        try:
            job_id = str(uuid.uuid4())
            
            # 创建任务对象
            job = CrawlJob(
                job_id=job_id,
                target_sites=target_sites or ["Gunter's Space Page"],
                keywords=keywords or [],
                max_satellites=max_satellites,
                status="pending"
            )
            
            self.active_jobs[job_id] = job
            
            logger.info(f"📋 创建爬取任务: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"创建爬取任务失败: {str(e)}")
            raise
    
    async def execute_crawl_job(
        self, 
        job_id: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """执行爬取任务"""
        try:
            if job_id not in self.active_jobs:
                raise ValueError(f"任务不存在: {job_id}")
            
            job = self.active_jobs[job_id]
            job.status = "running"
            job.started_at = datetime.now().timestamp()
            
            logger.info(f"🚀 开始执行爬取任务: {job_id}")
            
            # 创建初始状态
            state: CrawlerState = {
                "task_id": job_id,
                "target_sites": job.target_sites,
                "keywords": job.keywords,
                "max_satellites": job.max_satellites,
                "raw_satellite_data": [],
                "formatted_satellite_data": [],
                "new_satellites_count": 0,
                "existing_satellites_count": 0,
                "failed_satellites_count": 0,
                "processing_errors": [],
                "crawl_start_time": None,
                "crawl_end_time": None,
                "execution_time": 0.0,
                "log_file_path": "",
                "current_node": "START",
                "error_occurred": False,
                "error_message": "",
                "storage_stats": {}
            }
            
            # 执行工作流
            final_state = await self._execute_workflow(state, progress_callback)
            
            # 更新任务状态
            job.completed_at = datetime.now().timestamp()
            if final_state['error_occurred']:
                job.status = "failed"
                job.error_message = final_state['error_message']
            else:
                job.status = "completed"
            
            # 保存结果
            job.results = {
                "new_satellites": final_state['new_satellites_count'],
                "existing_satellites": final_state['existing_satellites_count'],
                "failed_satellites": final_state['failed_satellites_count'],
                "execution_time": final_state['execution_time'],
                "log_file_path": final_state['log_file_path'],
                "storage_stats": final_state['storage_stats']
            }
            
            # 移动到历史记录
            self.job_history.append(job)
            del self.active_jobs[job_id]
            
            logger.info(f"✅ 爬取任务完成: {job_id}")
            
            return {
                "job_id": job_id,
                "status": job.status,
                "results": job.results,
                "error_message": job.error_message
            }
            
        except Exception as e:
            logger.error(f"执行爬取任务失败: {job_id}, 错误: {str(e)}")
            
            # 更新任务为失败状态
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime.now().timestamp()
                
                self.job_history.append(job)
                del self.active_jobs[job_id]
            
            raise
    
    async def _execute_workflow(
        self, 
        state: CrawlerState, 
        progress_callback: Optional[Callable] = None
    ) -> CrawlerState:
        """执行工作流图"""
        try:
            current_node = "parameter_parsing"
            
            while current_node != "END":
                logger.info(f"📍 执行节点: {current_node}")
                
                # 发送进度更新
                if progress_callback:
                    await progress_callback({
                        "current_node": current_node,
                        "task_id": state["task_id"]
                    })
                
                # 执行当前节点
                if current_node == "parameter_parsing":
                    state = await self.nodes.parameter_parsing_node(state)
                elif current_node == "web_crawler":
                    state = await self.nodes.web_crawler_node(state)
                elif current_node == "data_cleaning":
                    state = await self.nodes.data_cleaning_node(state)
                elif current_node == "duplicate_check":
                    state = await self.nodes.duplicate_check_node(state)
                elif current_node == "file_write":
                    state = await self.nodes.file_write_node(state)
                elif current_node == "logging":
                    state = await self.nodes.logging_node(state)
                elif current_node == "error_handler":
                    state = await self.nodes.error_handler_node(state)
                else:
                    raise ValueError(f"未知节点: {current_node}")
                
                # 检查是否出错
                if state['error_occurred']:
                    logger.error(f"节点执行出错: {current_node}, 错误: {state['error_message']}")
                    current_node = "error_handler"
                else:
                    # 获取下一个节点
                    current_node = self.workflow_graph.get(current_node, "END")
                
                # 添加小延迟，避免过快执行
                await asyncio.sleep(0.1)
            
            logger.info(f"🏁 工作流执行完成: {state['task_id']}")
            return state
            
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            state['error_occurred'] = True
            state['error_message'] = f"工作流执行失败: {str(e)}"
            
            # 执行错误处理节点
            state = await self.nodes.error_handler_node(state)
            return state
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        # 检查活跃任务
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            return job.to_dict()
        
        # 检查历史任务
        for job in self.job_history:
            if job.job_id == job_id:
                return job.to_dict()
        
        return None
    
    def list_jobs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出任务"""
        all_jobs = list(self.active_jobs.values()) + self.job_history
        
        if status:
            all_jobs = [job for job in all_jobs if job.status == status]
        
        # 按创建时间倒序排列
        all_jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        return [job.to_dict() for job in all_jobs]
    
    async def get_crawl_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取爬取日志"""
        try:
            logs_file = os.path.join(settings.data_dir, "crawlLogs.json")
            
            if not os.path.exists(logs_file):
                return []
            
            with open(logs_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
                
                if not isinstance(logs, list):
                    return []
                
                # 按时间倒序排列，返回最近的记录
                logs.sort(key=lambda x: x.get('crawlTime', ''), reverse=True)
                return logs[:limit]
                
        except Exception as e:
            logger.error(f"获取爬取日志失败: {str(e)}")
            return []
    
    async def get_crawl_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取爬取统计信息"""
        try:
            logs = await self.get_crawl_logs(limit=1000)
            
            # 计算统计信息
            total_crawls = len(logs)
            total_new_satellites = sum(log.get('newDataCount', 0) for log in logs)
            total_failed = sum(log.get('failedCount', 0) for log in logs)
            
            # 按日期分组统计
            daily_stats = {}
            for log in logs:
                date_str = log.get('crawlTime', '')[:10]  # 获取日期部分
                if date_str not in daily_stats:
                    daily_stats[date_str] = {
                        'date': date_str,
                        'crawls': 0,
                        'new_satellites': 0,
                        'failed': 0
                    }
                
                daily_stats[date_str]['crawls'] += 1
                daily_stats[date_str]['new_satellites'] += log.get('newDataCount', 0)
                daily_stats[date_str]['failed'] += log.get('failedCount', 0)
            
            # 按站点统计
            site_stats = {}
            for log in logs:
                for site in log.get('targetSites', []):
                    if site not in site_stats:
                        site_stats[site] = {
                            'site': site,
                            'crawls': 0,
                            'new_satellites': 0
                        }
                    
                    site_stats[site]['crawls'] += 1
                    site_stats[site]['new_satellites'] += log.get('newDataCount', 0)
            
            return {
                'total_crawls': total_crawls,
                'total_new_satellites': total_new_satellites,
                'total_failed': total_failed,
                'daily_stats': list(daily_stats.values()),
                'site_stats': list(site_stats.values()),
                'recent_logs': logs[:10]  # 最近10条日志
            }
            
        except Exception as e:
            logger.error(f"获取爬取统计失败: {str(e)}")
            return {
                'total_crawls': 0,
                'total_new_satellites': 0,
                'total_failed': 0,
                'daily_stats': [],
                'site_stats': [],
                'recent_logs': []
            }


# 创建全局工作流实例
crawler_workflow = CrawlerWorkflow()
