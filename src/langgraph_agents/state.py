"""LangGraph 状态定义模块"""
from typing import TypedDict, List, Optional, Dict, Any
from src.knowledge_base.schemas import QualityReport


class ExtractionState(TypedDict):
    """抽取状态"""
    # 输入
    raw_text: str
    pdf_path: Optional[str]
    
    # 文档块信息（新增）
    document_blocks: List[Dict[str, Any]]          # 文档块列表
    
    # 实体抽取结果
    entities: List[Dict[str, Any]]
    
    # 块级实体映射（新增）
    block_entities: Dict[str, List[Dict[str, Any]]]  # 块ID -> 实体列表
    
    # 指代消解后的实体
    resolved_entities: List[Dict[str, Any]]
    
    # 归一化后的实体
    normalized_entities: List[Dict[str, Any]]
    
    # 关系抽取结果
    relations: List[Dict[str, Any]]
    
    # 归一化后的关系（新增）
    normalized_relations: List[Dict[str, Any]]
    
    # 质量检查
    quality_report: Optional[QualityReport]
    
    # 流程控制
    current_stage: str
    backtrack_needed: bool
    backtrack_stage: Optional[str]
    backtrack_count: int
    
    # 错误信息
    error_messages: List[str]
    
    # 元数据
    metadata: Dict[str, Any]


def create_initial_state(text: str, pdf_path: Optional[str] = None) -> ExtractionState:
    """
    创建初始状态
    
    Args:
        text: 原始文本
        pdf_path: PDF 文件路径
        
    Returns:
        初始抽取状态
    """
    return ExtractionState(
        raw_text=text,
        pdf_path=pdf_path,
        document_blocks=[],
        entities=[],
        block_entities={},
        resolved_entities=[],
        normalized_entities=[],
        relations=[],
        normalized_relations=[],
        quality_report=None,
        current_stage="initial",
        backtrack_needed=False,
        backtrack_stage=None,
        backtrack_count=0,
        error_messages=[],
        metadata={},
    )


def update_state_stage(
    state: ExtractionState,
    stage: str,
    error_messages: Optional[List[str]] = None
) -> ExtractionState:
    """
    更新状态阶段
    
    Args:
        state: 当前状态
        stage: 新阶段名称
        error_messages: 错误消息列表
        
    Returns:
        更新后的状态
    """
    state["current_stage"] = stage
    if error_messages:
        state["error_messages"].extend(error_messages)
    return state
