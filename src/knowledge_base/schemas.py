"""实体模式定义模块"""
from typing import List, Optional
from pydantic import BaseModel, Field


class RelationTriple(BaseModel):
    """关系三元组"""
    subject: str = Field(..., description="主语实体ID")
    predicate: str = Field(..., description="关系谓词")
    object: str = Field(..., description="宾语实体ID")
    confidence: float = Field(default=1.0, description="关系置信度")
    evidence: Optional[str] = Field(None, description="支持该关系的文本证据")


class QualityReport(BaseModel):
    """质量报告"""
    quality_score: float = Field(..., description="质量评分 0-1")
    entity_count: int = Field(default=0, description="实体数量")
    relation_count: int = Field(default=0, description="关系数量")
    issues: List[str] = Field(default_factory=list, description="发现的问题")
    recommendations: List[str] = Field(default_factory=list, description="改进建议")
    backtrack_stage: Optional[str] = Field(None, description="建议回溯的阶段")


class ExtractionResult(BaseModel):
    """抽取结果"""
    text: str = Field(..., description="原始文本")
    entities: List[dict] = Field(default_factory=list, description="实体列表")
    relations: List[dict] = Field(default_factory=list, description="关系列表")
    quality_report: Optional[QualityReport] = Field(None, description="质量报告")
    backtrack_attempts: int = Field(default=0, description="回溯尝试次数")


# 关系类型定义
RELATION_TYPES = {
    # Case 相关
    "case_in_court": "Case -> Court",
    "case_judged_by": "Case -> Judge",
    "case_involved_party": "Case -> Party",
    "case_applied_law": "Case -> Law",
    "case_evidence": "Case -> Evidence",
    
    # Party 相关
    "party_represented_by": "Party -> Party",  # e.g., Plaintiff represented by Lawyer
    "party_against_party": "Party -> Party",
    
    # Law 相关
    "law_cited_by_case": "Law -> Case",
    "law_interpreted_by_case": "Law -> Case",
    
    # 时间相关
    "case_filed_date": "Case -> Date",
    "case_hearing_date": "Case -> Date",
    "case_judgment_date": "Case -> Date",
    
    # 金额相关
    "case_amount": "Case -> Amount",
    "party_awarded_amount": "Party -> Amount",
}
