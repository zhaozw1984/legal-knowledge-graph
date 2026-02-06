"""LLM 客户端模块"""
import os
from langchain_openai import ChatOpenAI
import httpx
from config.settings import settings
from src.utils.logger import logger


def get_llm():
    """
    初始化 LLM（使用用户提供的 DeepSeek 配置）
    
    Returns:
        ChatOpenAI 实例
    """
    api_key = settings.dashscope_api_key
    
    # 创建 httpx 客户端（禁用代理，增加超时）
    http_client = httpx.Client(timeout=120.0, trust_env=False)
    
    llm = ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=api_key,
        openai_api_base=settings.api_base,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        http_client=http_client,
        request_timeout=120.0,
        max_retries=2
    )
    
    logger.info(f"LLM 初始化成功: {settings.llm_model}")
    return llm


async def call_llm_with_prompt(prompt: str, llm=None) -> str:
    """
    使用 LLM 处理提示词
    
    Args:
        prompt: 提示词
        llm: LLM 实例（可选，如果不提供则使用默认配置）
        
    Returns:
        LLM 响应文本
    """
    if llm is None:
        llm = get_llm()
    
    try:
        response = await llm.ainvoke(prompt)
        return response.content
    except Exception as e:
        logger.error(f"LLM 调用失败: {e}")
        raise


def call_llm_sync(prompt: str, llm=None) -> str:
    """
    同步调用 LLM
    
    Args:
        prompt: 提示词
        llm: LLM 实例（可选）
        
    Returns:
        LLM 响应文本
    """
    if llm is None:
        llm = get_llm()
    
    try:
        logger.info(f"开始调用 LLM，prompt 长度: {len(prompt)} 字符")
        response = llm.invoke(prompt)
        logger.info(f"LLM 调用成功，响应长度: {len(response.content)} 字符")
        return response.content
    except Exception as e:
        logger.error(f"LLM 调用失败: {type(e).__name__}: {e}")
        raise
