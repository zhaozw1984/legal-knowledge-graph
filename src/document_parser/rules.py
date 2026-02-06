"""
法律文书章节识别规则

定义法律文书常见章节的识别模式（正则表达式）和块类型常量。
"""

from typing import Dict, List, Pattern
import re

# 文档块类型枚举
BLOCK_TYPES = {
    "CASE_INFO": "案件基本信息",      # 案号、法院、当事人等基本信息
    "CLAIM": "诉讼请求",              # 原告的诉讼请求
    "FACT": "案件事实",               # 案件事实陈述
    "DEFENSE": "被告答辩",            # 被告的答辩意见
    "EVIDENCE": "证据",               # 证据列举和说明
    "REASONING": "判决理由",          # 法院的判决理由
    "JUDGMENT": "判决结果",           # 最终判决结果
    "PROCEDURE": "审理经过",          # 案件审理过程
    "COST": "诉讼费用",               # 诉讼费用承担
    "OTHER": "其他"                   # 其他内容
}

# 法律文书章节标题正则表达式模式
LEGAL_SECTION_PATTERNS: Dict[str, Pattern] = {
    # 案件信息相关
    "CASE_INFO": re.compile(
        r'^【?(案件|法院|当事人|审理|案号).*?】?$', 
        re.MULTILINE | re.IGNORECASE
    ),
    
    # 诉讼请求
    "CLAIM": re.compile(
        r'^【?(诉讼请求|原告诉称|诉讼请求内容).*?】?$', 
        re.MULTILINE | re.IGNORECASE
    ),
    
    # 案件事实
    "FACT": re.compile(
        r'^【?(案件事实|事实经过|查明事实|经审理查明).*?】?$', 
        re.MULTILINE | re.IGNORECASE
    ),
    
    # 被告答辩
    "DEFENSE": re.compile(
        r'^【?(被告答辩|被告辩称|答辩意见).*?】?$', 
        re.MULTILINE | re.IGNORECASE
    ),
    
    # 证据
    "EVIDENCE": re.compile(
        r'^【?(证据|证据认定|证据分析).*?】?$', 
        re.MULTILINE | re.IGNORECASE
    ),
    
    # 判决理由
    "REASONING": re.compile(
        r'^【?(判决理由|本院认为|理由).*?】?$', 
        re.MULTILINE | re.IGNORECASE
    ),
    
    # 判决结果
    "JUDGMENT": re.compile(
        r'^【?(判决结果|判决如下|裁判结果|判决).*?】?$', 
        re.MULTILINE | re.IGNORECASE
    ),
    
    # 审理经过
    "PROCEDURE": re.compile(
        r'^【?(审理经过|审理过程|诉讼过程).*?】?$', 
        re.MULTILINE | re.IGNORECASE
    ),
    
    # 诉讼费用
    "COST": re.compile(
        r'^【?(诉讼费用|费用承担).*?】?$', 
        re.MULTILINE | re.IGNORECASE
    )
}

# 层级编号模式（用于识别嵌套结构）
HIERARCHY_PATTERNS = [
    re.compile(r'^([一二三四五六七八九十]+)、(.+)$'),           # 一、标题
    re.compile(r'^(\（[一二三四五六七八九十]+\）)、(.+)$'),      # （一）标题
    re.compile(r'^([1-9]\d*)[.、](.+)$'),                       # 1. 标题
    re.compile(r'^\([1-9]\d*\)(.+)$'),                         # (1) 标题
]


def get_section_pattern(block_type: str) -> Pattern:
    """
    获取指定块类型的章节识别模式
    
    Args:
        block_type: 块类型，如 'FACT', 'REASONING' 等
        
    Returns:
        正则表达式模式对象
        
    Raises:
        KeyError: 当 block_type 不存在时
    """
    return LEGAL_SECTION_PATTERNS[block_type]


def is_legal_section(text: str) -> tuple[bool, str]:
    """
    判断文本是否为法律文书章节标题
    
    Args:
        text: 待判断的文本
        
    Returns:
        (是否为章节标题, 匹配的块类型)
    """
    text = text.strip()
    
    # 检查是否匹配任一章节模式
    for block_type, pattern in LEGAL_SECTION_PATTERNS.items():
        if pattern.match(text):
            return True, block_type
    
    return False, "OTHER"


def identify_hierarchy_level(text: str) -> int:
    """
    识别文本的层级级别
    
    Args:
        text: 待识别的文本
        
    Returns:
        层级级别（0表示非层级标题）
    """
    for i, pattern in enumerate(HIERARCHY_PATTERNS):
        if pattern.match(text.strip()):
            return i + 1
    
    return 0


def normalize_block_type(raw_type: str) -> str:
    """
    标准化块类型
    
    Args:
        raw_type: 原始块类型（可能来自不同来源）
        
    Returns:
        标准化的块类型
    """
    # 如果已经在 BLOCK_TYPES 中，直接返回
    if raw_type in BLOCK_TYPES:
        return raw_type
    
    # 尝试通过别名映射
    aliases = {
        "案件信息": "CASE_INFO",
        "案情": "FACT",
        "事实": "FACT",
        "理由": "REASONING",
        "判决": "JUDGMENT",
        "结果": "JUDGMENT"
    }
    
    return aliases.get(raw_type, "OTHER")
