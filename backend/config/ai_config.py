import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class AIModelSettings(BaseSettings):
    """AI模型配置"""

    # 九州模型配置
    jiuzhou_model_path: str = Field(
        default="/root/autodl-tmp/virtual_constellation_assistant/backend/src/llm/JiuZhou-Instruct-v0.2",
        env="JIUZHOU_MODEL_PATH"
    )
    jiuzhou_enabled: bool = Field(default=True, env="JIUZHOU_ENABLED")
    jiuzhou_device: str = Field(default="auto", env="JIUZHOU_DEVICE")  # auto, cuda, cpu
    jiuzhou_max_tokens: int = Field(default=800, env="JIUZHOU_MAX_TOKENS")
    jiuzhou_temperature: float = Field(default=0.7, env="JIUZHOU_TEMPERATURE")
    jiuzhou_top_p: float = Field(default=0.9, env="JIUZHOU_TOP_P")

    # AI功能开关
    ai_parameter_extraction: bool = Field(default=True, env="AI_PARAMETER_EXTRACTION")
    ai_question_generation: bool = Field(default=True, env="AI_QUESTION_GENERATION")
    ai_response_parsing: bool = Field(default=True, env="AI_RESPONSE_PARSING")
    ai_fallback_to_rules: bool = Field(default=True, env="AI_FALLBACK_TO_RULES")

    # 性能配置
    ai_timeout_seconds: int = Field(default=30, env="AI_TIMEOUT_SECONDS")
    ai_cache_enabled: bool = Field(default=True, env="AI_CACHE_ENABLED")
    ai_cache_ttl: int = Field(default=3600, env="AI_CACHE_TTL")  # 缓存时间（秒）

    # 日志配置
    ai_debug_mode: bool = Field(default=False, env="AI_DEBUG_MODE")

    # 多模型API配置
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL")
    qwen_api_key: str = Field(default="", env="QWEN_API_KEY")  
    qwen_base_url: str = Field(default="https://dashscope.aliyuncs.com/api/v1", env="QWEN_BASE_URL")
    deepseek_api_key: str = Field(default="", env="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1", env="DEEPSEEK_BASE_URL")

    model_config = {
        "env_file": os.path.join(Path(__file__).parent.parent, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# 创建配置实例
ai_settings = AIModelSettings()