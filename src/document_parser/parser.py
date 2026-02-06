"""
文档结构解析器

基于规则+模板匹配方法，从PDF文本中识别法律文书章节结构，
提取文档块（DocumentBlock），并支持层级结构解析。
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import re
from loguru import logger

from .rules import (
    BLOCK_TYPES,
    is_legal_section,
    identify_hierarchy_level,
    normalize_block_type
)


@dataclass
class DocumentBlock:
    """文档块数据结构"""
    block_id: str                    # 块唯一标识
    block_type: str                  # 块类型（fact/reason/judgment等）
    title: str                       # 章节标题
    content: str                     # 块内容
    start_pos: int                   # 起始位置
    end_pos: int                     # 结束位置
    level: int = 0                   # 层级级别
    parent_id: Optional[str] = None  # 父块ID
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


class DocumentParser:
    """文档结构解析器"""
    
    def __init__(self):
        """初始化解析器"""
        self.blocks: List[DocumentBlock] = []
        self._block_counter = 0
    
    def parse(self, text: str) -> List[DocumentBlock]:
        """
        解析文档结构，提取文档块
        
        Args:
            text: PDF提取的完整文本
            
        Returns:
            文档块列表
        """
        logger.info(f"开始文档结构解析，文本长度: {len(text)} 字符")
        
        # 清理文本
        cleaned_text = self._clean_text(text)
        
        # 识别章节标题
        sections = self._identify_sections(cleaned_text)
        
        # 构建文档块
        self.blocks = self._build_blocks(sections, cleaned_text)
        
        # 建立层级关系
        self._build_hierarchy()
        
        logger.info(f"文档结构解析完成，识别到 {len(self.blocks)} 个文档块")
        
        return self.blocks
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本，移除多余空行和空白字符
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        # 移除连续空行（保留一个换行符）
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 移除行首行尾多余空白
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _identify_sections(self, text: str) -> List[Tuple[int, str, str]]:
        """
        识别章节标题位置
        
        Args:
            text: 清理后的文本
            
        Returns:
            [(位置, 标题, 块类型), ...]
        """
        sections = []
        lines = text.split('\n')
        current_pos = 0
        
        for line in lines:
            if not line.strip():
                current_pos += len(line) + 1
                continue
            
            is_section, block_type = is_legal_section(line)
            
            if is_section:
                sections.append((current_pos, line.strip(), block_type))
                logger.debug(f"识别到章节: {line.strip()} ({block_type})")
            
            current_pos += len(line) + 1
        
        return sections
    
    def _build_blocks(
        self, 
        sections: List[Tuple[int, str, str]], 
        text: str
    ) -> List[DocumentBlock]:
        """
        根据章节位置构建文档块
        
        Args:
            sections: 章节位置列表
            text: 完整文本
            
        Returns:
            文档块列表
        """
        blocks = []
        
        # 添加文档开头的"其他"块
        if sections:
            first_pos = sections[0][0]
            if first_pos > 0:
                prelude = text[:first_pos].strip()
                if prelude:
                    block = DocumentBlock(
                        block_id=self._generate_block_id(),
                        block_type="OTHER",
                        title="文档开头",
                        content=prelude,
                        start_pos=0,
                        end_pos=first_pos
                    )
                    blocks.append(block)
        
        # 为每个章节构建块
        for i, (pos, title, block_type) in enumerate(sections):
            # 确定块的结束位置
            if i + 1 < len(sections):
                next_pos = sections[i + 1][0]
                content = text[pos + len(title):next_pos].strip()
                end_pos = next_pos
            else:
                content = text[pos + len(title):].strip()
                end_pos = len(text)
            
            block = DocumentBlock(
                block_id=self._generate_block_id(),
                block_type=block_type,
                title=title,
                content=content,
                start_pos=pos,
                end_pos=end_pos,
                level=identify_hierarchy_level(title)
            )
            
            blocks.append(block)
            logger.debug(f"构建块: {block.block_id} - {title} ({block_type})")
        
        return blocks
    
    def _build_hierarchy(self):
        """建立文档块的层级关系"""
        # 按层级级别排序
        sorted_blocks = sorted(
            [b for b in self.blocks if b.level > 0],
            key=lambda x: x.start_pos
        )
        
        stack = []  # (block_id, level)
        
        for block in sorted_blocks:
            # 弹出层级更高或相同的块
            while stack and stack[-1][1] >= block.level:
                stack.pop()
            
            # 设置父块
            if stack:
                block.parent_id = stack[-1][0]
            
            # 压入当前块
            stack.append((block.block_id, block.level))
        
        logger.debug(f"层级关系构建完成，共 {len([b for b in self.blocks if b.parent_id])} 个子块")
    
    def _generate_block_id(self) -> str:
        """生成唯一的块ID"""
        self._block_counter += 1
        return f"block_{self._block_counter:04d}"
    
    def get_blocks_by_type(self, block_type: str) -> List[DocumentBlock]:
        """
        获取指定类型的所有文档块
        
        Args:
            block_type: 块类型
            
        Returns:
            匹配的文档块列表
        """
        return [b for b in self.blocks if b.block_type == block_type]
    
    def get_block_content(self, block_type: str, join_with: str = "\n") -> str:
        """
        获取指定类型块的合并内容
        
        Args:
            block_type: 块类型
            join_with: 连接符
            
        Returns:
            合并后的内容字符串
        """
        blocks = self.get_blocks_by_type(block_type)
        return join_with.join([b.content for b in blocks])
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取解析统计信息
        
        Returns:
            统计信息字典
        """
        type_counts = {}
        for block in self.blocks:
            type_counts[block.block_type] = type_counts.get(block.block_type, 0) + 1
        
        hierarchy_counts = {}
        for block in self.blocks:
            hierarchy_counts[block.level] = hierarchy_counts.get(block.level, 0) + 1
        
        return {
            "total_blocks": len(self.blocks),
            "type_distribution": type_counts,
            "hierarchy_distribution": hierarchy_counts,
            "blocks_with_parent": len([b for b in self.blocks if b.parent_id])
        }
