# backend/src/graph/state.py

import os
import sys
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import time
import uuid
from datetime import datetime
from pydantic import BaseModel, Field
logger = logging.getLogger(__name__)

class Message(BaseModel):
    """对话消息模型"""
    role: str  # "user", "assistant", "system", "function"
    content: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())


class Requirement(BaseModel):
    """用户需求模型 - 保持灵活性，不强制结构化"""
    area_of_interest: Optional[str] = None
    time_range: Optional[str] = None
    spatial_resolution: Optional[str] = None
    spectral_bands: Optional[List[str]] = None
    revisit_frequency: Optional[str] = None
    data_quality: Optional[str] = None
    priority_factor: Optional[str] = None
    application_scenario: Optional[str] = None
    additional_requirements: Optional[str] = None
    raw_description: Optional[str] = None


class SatelliteDataSource(BaseModel):
    """卫星数据源模型"""
    satellite_name: str                    # 卫星名称
    data_type: str                        # 数据类型 (optical/radar/multispectral)
    download_url: Optional[str] = None    # 下载地址
    local_path: Optional[str] = None      # 本地路径
    coverage_area: Optional[str] = None   # 覆盖区域
    temporal_resolution: Optional[str] = None  # 时间分辨率
    spatial_resolution: Optional[str] = None   # 空间分辨率


class DataProcessingOptions(BaseModel):
    """数据处理选项模型"""
    normalize_illumination: bool = True      # 匀光匀色
    radiometric_correction: bool = True      # 辐射校正
    atmospheric_correction: bool = False     # 大气校正
    geometric_correction: bool = False       # 几何校正
    output_format: str = "geotiff"          # 输出格式


class ConstellationPlan(BaseModel):
    """星座方案模型 - 保持灵活性"""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    satellites: List[Dict[str, Any]] = []
    advantages: Optional[List[str]] = None
    limitations: Optional[List[str]] = None
    additional_info: Dict[str, Any] = Field(default_factory=dict)
    # 🆕 新增：数据源信息
    data_sources: List[SatelliteDataSource] = Field(default_factory=list)
    processing_options: Optional[DataProcessingOptions] = None
    estimated_data_size: Optional[str] = None
    processing_time_estimate: Optional[str] = None


class WorkflowState(BaseModel):
    """工作流状态模型 - 主状态容器，保持简单灵活"""
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Message] = Field(default_factory=list)

    # 用户需求
    requirement: Requirement = Field(default_factory=Requirement)

    # 知识检索结果
    retrieved_knowledge: List[Dict[str, Any]] = Field(default_factory=list)

    # 生成的方案
    main_plan: Optional[Any] = None
    alternative_plans: List[Any] = Field(default_factory=list)

    # 当前工作流阶段
    current_stage: str = "requirement_analysis"

    # 思考过程记录
    thinking_steps: List[Dict[str, Any]] = Field(default_factory=list)

    # 🆕 新增：提取的卫星名称列表
    extracted_satellites: List[str] = Field(default_factory=list)

    # 自由格式的元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)
    latest_plan_request_index: int = Field(default=-1)
    # 新增：参数收集阶段跟踪
    parameter_collection_stage: str = "not_started"  # not_started, purpose, time, location, technical, completed
    parameter_collection_history: List[Dict[str, Any]] = Field(default_factory=list)
    stage_retry_count: Dict[str, int] = Field(default_factory=dict)  # 每个阶段的重试次数

    # 🆕 新增：意图确认相关
    awaiting_intent_confirmation: bool = Field(default=False)
    pending_intent: Optional[str] = Field(default=None)
    intent_confirmed: bool = Field(default=False)

    # 🆕 新增：数据处理相关状态
    data_processing_stage: str = "not_started"  # not_started, awaiting_confirmation, processing, completed, failed
    selected_satellites: List[str] = Field(default_factory=list)
    processing_progress: Dict[str, Any] = Field(default_factory=dict)
    processing_results: Optional[Dict[str, Any]] = Field(default=None)

    def add_message(self, role: str, content: str) -> Message:
        """添加新消息"""
        message = Message(role=role, content=content)
        self.messages.append(message)
        return message

    def get_conversation_history(self, max_messages: Optional[int] = None) -> str:
        """获取格式化的对话历史"""
        valid_messages = [
            msg for msg in self.messages
            if msg.role in ["user", "assistant"]
        ]

        if max_messages is not None:
            valid_messages = valid_messages[-max_messages:]

        history = ""
        for msg in valid_messages:
            history += f"{msg.role}: {msg.content}\n\n"

        return history.strip()

    def add_thinking_step(self, step_name: str, details: Any):
        """记录思考步骤"""
        self.thinking_steps.append({
            "step": step_name,
            "details": details,
            "timestamp": datetime.now().timestamp()
        })

    def add_extracted_satellite(self, satellite_name: str):
        """添加提取的卫星名称"""
        if satellite_name not in self.extracted_satellites:
            self.extracted_satellites.append(satellite_name)

    def set_extracted_satellites(self, satellites: List[str]):
        """设置提取的卫星名称列表"""
        self.extracted_satellites = satellites

    def get_current_collection_stage(self) -> str:
        """获取当前参数收集阶段"""
        return self.parameter_collection_stage

    def set_collection_stage(self, stage: str):
        """设置参数收集阶段"""
        self.parameter_collection_stage = stage
        self.add_thinking_step("参数收集阶段", f"进入 {stage} 阶段")

    def increment_stage_retry(self, stage: str):
        """增加某阶段的重试次数"""
        if stage not in self.stage_retry_count:
            self.stage_retry_count[stage] = 0
        self.stage_retry_count[stage] += 1

    def mark_new_plan_request(self):
        """标记新的方案请求开始位置"""
        self.latest_plan_request_index = len(self.messages) - 3
        self.add_thinking_step("新方案标记", f"标记新方案请求起始位置: 消息索引 {self.latest_plan_request_index}")
        logger.info(f"🔖 标记新方案请求，起始消息索引: {self.latest_plan_request_index}")

    def get_messages_since_latest_plan_request(self) -> List[Message]:
        """获取最新方案请求之后的所有消息"""
        if self.latest_plan_request_index < 0:
            print('hhhhhhhhhhhhh')
            return self.messages
        print('kkkkkkkkkkkk')
        return self.messages[self.latest_plan_request_index:]

    def get_conversation_history_since_latest_plan(self, max_messages: Optional[int] = None) -> str:
        """获取最新方案请求之后的对话历史"""
        messages = self.get_messages_since_latest_plan_request()
        valid_messages = [
            msg for msg in messages
            if msg.role in ["user", "assistant"]
        ]

        if max_messages is not None:
            valid_messages = valid_messages[-max_messages:]

        history = ""
        for msg in valid_messages:
            history += f"{msg.role}: {msg.content}\n\n"

        return history.strip()