# backend/src/tools/crawler_agent/state.py

import json
from datetime import datetime
from typing import List, Dict, Any, Optional, TypedDict
from dataclasses import dataclass, field


class CrawlerState(TypedDict):
    """爬虫工作流状态"""
    
    # 输入参数
    task_id: str
    target_sites: List[str]
    keywords: List[str]
    max_satellites: int
    
    # 爬取数据
    raw_satellite_data: List[Dict[str, Any]]
    formatted_satellite_data: List[Dict[str, Any]]
    
    # 处理结果
    new_satellites_count: int
    existing_satellites_count: int
    failed_satellites_count: int
    processing_errors: List[str]
    
    # 日志信息
    crawl_start_time: Optional[float]
    crawl_end_time: Optional[float]
    execution_time: float
    log_file_path: str
    
    # 状态控制
    current_node: str
    error_occurred: bool
    error_message: str
    
    # 数据库状态
    storage_stats: Dict[str, Any]


@dataclass
class CrawlJob:
    """爬取任务类"""
    
    job_id: str
    target_sites: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list) 
    max_satellites: int = 10
    status: str = "pending"  # pending, running, completed, failed
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "job_id": self.job_id,
            "target_sites": self.target_sites,
            "keywords": self.keywords,
            "max_satellites": self.max_satellites,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "results": self.results,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CrawlJob':
        """从字典创建实例"""
        return cls(
            job_id=data["job_id"],
            target_sites=data.get("target_sites", []),
            keywords=data.get("keywords", []),
            max_satellites=data.get("max_satellites", 10),
            status=data.get("status", "pending"),
            created_at=data.get("created_at", datetime.now().timestamp()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            results=data.get("results"),
            error_message=data.get("error_message")
        )


class CrawlLogEntry:
    """爬取日志条目"""
    
    def __init__(self):
        self.timestamp = datetime.now().isoformat()
        self.target_sites = []
        self.new_data_count = 0
        self.updated_data_count = 0
        self.failed_count = 0
        self.fail_reasons = []
        self.data_list = []
        self.execution_time = 0.0
        self.total_processed = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "crawlTime": self.timestamp,
            "targetSites": self.target_sites,
            "newDataCount": self.new_data_count,
            "updatedDataCount": self.updated_data_count,
            "failedCount": self.failed_count,
            "failReasons": self.fail_reasons,
            "dataList": self.data_list,
            "executionTime": self.execution_time,
            "totalProcessed": self.total_processed
        }
