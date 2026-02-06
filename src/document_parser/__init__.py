"""
文档结构解析模块

用于识别和解析法律文书的章节结构（如'案件事实'、'判决理由'、'诉讼请求'等），
使用规则+模板匹配方法提取文档块。
"""

from .parser import DocumentParser
from .rules import (
    LEGAL_SECTION_PATTERNS,
    BLOCK_TYPES,
    get_section_pattern,
    is_legal_section
)

__all__ = [
    "DocumentParser",
    "LEGAL_SECTION_PATTERNS",
    "BLOCK_TYPES",
    "get_section_pattern",
    "is_legal_section"
]
