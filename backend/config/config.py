# backend/config/config.py

import os
from typing import Dict, List, Any, Optional,Union
from pydantic_settings import BaseSettings
from pydantic import Field

# 获取项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FaissSettings(BaseSettings):
    """FAISS知识库配置"""
    index_name: str = "satellite_knowledge_index"
    index_directory: str = os.path.join(ROOT_DIR, "data", "faiss_indexes")
    embedding_model: str = "thenlper/gte-base-zh"  # 使用thenlper/gte-base-zh模型
    embedding_dimension: int = 768
    knowledge_file: str = os.path.join(ROOT_DIR, "data", "knowledge", "knowledge.txt")  # 单一知识库文件
    chunk_size: int = 512  # 知识块大小
    chunk_overlap: int = 100  # 块重叠大小

    model_config = {
        "env_file": os.path.join(ROOT_DIR, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 忽略额外的环境变量
    }


class LLMSettings(BaseSettings):
    """大语言模型配置"""
    model_name: str = "deepseek-llm"
    api_key: str = Field(default="", env="DEEPSEEK_API_KEY")
    api_base_url: str = "https://api.deepseek.com"
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.95
    timeout: int = 60  # 秒

    model_config = {
        "env_file": os.path.join(ROOT_DIR, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 忽略额外的环境变量
    }


class SearchSettings(BaseSettings):
    """搜索服务配置"""
    # 默认使用Tavily，但可以配置为其他搜索服务
    provider: str = "tavily"
    tavily_api_key: str = Field(default="", env="TAVILY_API_KEY")
    serp_api_key: str = Field(default="", env="SERP_API_KEY")
    bing_api_key: str = Field(default="", env="BING_API_KEY")
    max_results: int = 5
    timeout: int = 10  # 秒

    model_config = {
        "env_file": os.path.join(ROOT_DIR, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 忽略额外的环境变量
    }


class FileProcessorSettings(BaseSettings):
    """文件处理配置"""
    upload_dir: str = os.path.join(ROOT_DIR, "data", "uploads")
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: List[str] = [
        # 文档
        ".pdf", ".docx", ".txt",
        # 表格
        ".csv", ".xlsx", ".xls",
        # 地理数据
        ".geojson", ".shp", ".kml", ".kmz",
        # 图像
        ".tif", ".tiff", ".jp2",
        # 配置文件
        ".json", ".yaml", ".yml"
    ]
    temp_dir: str = os.path.join(ROOT_DIR, "data", "temp")

    model_config = {
        "env_file": os.path.join(ROOT_DIR, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 忽略额外的环境变量
    }


class APISettings(BaseSettings):
    """API配置"""
    host: str = "127.0.0.1"
    port: int = 2025
    # debug: bool = True
    debug: Union[bool, str] = True
    allowed_origins: List[str] = ["*"]
    # 在生产环境中，应该设置为特定域名
    # allowed_origins: List[str] = ["https://yourdomain.com"]

    model_config = {
        "env_file": os.path.join(ROOT_DIR, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 忽略额外的环境变量
    }


class AgentSettings(BaseSettings):
    """智能体配置"""
    max_thinking_steps: int = 10
    planning_timeout: int = 30  # 秒
    dialogue_history_limit: int = 20  # 保留的对话轮数
    requirements_fields: List[str] = [
        "area_of_interest",  # 感兴趣区域
        "time_range",  # 时间范围
        "spatial_resolution",  # 空间分辨率
        "spectral_bands",  # 光谱波段
        "revisit_frequency",  # 重访频率
        "data_quality",  # 数据质量
        "priority_factor",  # 优先考虑因素
        "application_scenario"  # 应用场景
    ]

    model_config = {
        "env_file": os.path.join(ROOT_DIR, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 忽略额外的环境变量
    }


class SatelliteApiSettings(BaseSettings):
    """卫星数据API配置"""
    # 这里可以配置各种卫星数据提供商的API信息
    providers: Dict[str, Dict[str, Any]] = {
        "provider1": {
            "api_key": Field(default="", env="SATELLITE_PROVIDER1_API_KEY"),
            "base_url": "https://api.provider1.com/v1",
            "timeout": 30
        },
        "provider2": {
            "api_key": Field(default="", env="SATELLITE_PROVIDER2_API_KEY"),
            "base_url": "https://api.provider2.com/v2",
            "timeout": 30
        }
    }

    model_config = {
        "env_file": os.path.join(ROOT_DIR, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 忽略额外的环境变量
    }


class Settings(BaseSettings):
    """应用全局配置"""
    app_name: str = "智慧虚拟星座助手"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", env="APP_ENV")
    log_level: str = "INFO"
    log_file: Optional[str] = os.path.join(ROOT_DIR, "logs", "app.log")

    # 子配置
    faiss: FaissSettings = FaissSettings()
    llm: LLMSettings = LLMSettings()
    search: SearchSettings = SearchSettings()
    file_processor: FileProcessorSettings = FileProcessorSettings()
    api: APISettings = APISettings()
    agent: AgentSettings = AgentSettings()
    satellite_api: SatelliteApiSettings = SatelliteApiSettings()

    # 路径配置
    root_dir: str = ROOT_DIR
    data_dir: str = os.path.join(ROOT_DIR, "data")
    knowledge_dir: str = os.path.join(ROOT_DIR, "data", "knowledge")

    # 在 pydantic-settings 中，使用 model_config 替代 Config 类
    model_config = {
        "env_file": os.path.join(ROOT_DIR, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 忽略额外的环境变量
    }


# 创建设置实例
settings = Settings()

# 确保必要的目录存在
for directory in [
    settings.file_processor.upload_dir,
    settings.file_processor.temp_dir,
    settings.faiss.index_directory,
    settings.data_dir,
    settings.knowledge_dir,
    os.path.dirname(settings.log_file) if settings.log_file else None
]:
    if directory:
        os.makedirs(directory, exist_ok=True)


def get_settings() -> Settings:
    """返回设置实例，用于依赖注入"""
    return settings