"""智能体基类模块"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from src.llm.client import get_llm, call_llm_sync
from src.utils.logger import logger


class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, name: str, llm=None):
        """
        初始化智能体
        
        Args:
            name: 智能体名称
            llm: LLM 实例（可选）
        """
        self.name = name
        self.llm = llm or get_llm()
        logger.info(f"智能体 {self.name} 初始化完成")
    
    @abstractmethod
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理状态
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        pass
    
    @abstractmethod
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建 LLM 提示词
        
        Args:
            context: 上下文信息
            
        Returns:
            提示词字符串
        """
        pass
    
    def invoke_llm(self, prompt: str) -> str:
        """
        调用 LLM
        
        Args:
            prompt: 提示词
            
        Returns:
            LLM 响应
        """
        try:
            response = call_llm_sync(prompt, self.llm)
            # 清理响应，移除可能的 markdown 标记
            response = response.strip()
            if response.startswith('```'):
                response = response.split('```')[1]
                if response.startswith('json'):
                    response = response[4:]
            if response.endswith('```'):
                response = response[:-3]
            return response.strip()
        except Exception as e:
            logger.error(f"[{self.name}] LLM 调用失败: {e}")
            raise
