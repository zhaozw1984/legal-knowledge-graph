"""配置管理模块"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings(BaseSettings):
    """应用配置"""
    
    # DeepSeek API 配置
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "sk-590b0d025bad4f12a207f142fcdf49ed")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-v3.2")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "4000"))
    
    # API Base URL
    api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # Neo4j 配置
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")
    
    # 路径配置
    input_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
    output_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    
    # 日志配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "output/logs/app.log")
    
    # 质量检查阈值
    quality_threshold: float = 0.8
    
    # 最大回溯次数
    max_backtrack_attempts: int = 1
    
    # === 7步新架构配置 ===
    
    # 文档结构解析配置
    document_parser_enabled: bool = True  # 是否启用文档结构解析
    document_parser_min_block_length: int = 50  # 最小块长度
    document_parser_merge_short_blocks: bool = True  # 是否合并短块
    
    # 实体标准化配置
    entity_normalization_enabled: bool = True  # 是否启用规则实体标准化
    entity_similarity_threshold: float = 0.6  # 实体相似度阈值
    entity_min_cluster_size: int = 1  # 最小实体簇大小
    
    # 关系归一化配置
    relation_normalization_enabled: bool = True  # 是否启用关系归一化
    relation_validation_strict: bool = False  # 是否严格Schema验证
    
    # 指代消解配置
    coref_max_hops: int = 3  # 最大推理跳数
    coref_similarity_threshold: float = 0.5  # 指代消解相似度阈值
    
    # 块级处理配置
    block_parallel_processing: bool = False  # 是否并行处理块（预留）
    block_size_limit: int = 5000  # 单块最大字符数
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局配置实例
settings = Settings()


def get_llm_config() -> dict:
    """获取 LLM 配置"""
    return {
        "model": settings.llm_model,
        "api_key": settings.dashscope_api_key,
        "api_base": settings.api_base,
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }


def get_neo4j_config() -> dict:
    """获取 Neo4j 配置"""
    return {
        "uri": settings.neo4j_uri,
        "user": settings.neo4j_user,
        "password": settings.neo4j_password,
    }
