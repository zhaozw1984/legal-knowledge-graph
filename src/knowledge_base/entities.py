"""实体类型定义模块"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class LegalEntity(BaseModel):
    """法律实体基类"""
    id: str = Field(..., description="实体唯一标识")
    type: str = Field(..., description="实体类型")
    text: str = Field(..., description="实体在文本中的原始表述")
    start_pos: Optional[int] = Field(None, description="在文本中的起始位置")
    end_pos: Optional[int] = Field(None, description="在文本中的结束位置")
    confidence: float = Field(default=1.0, description="识别置信度")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="实体属性")
    
    class Config:
        use_enum_values = True


class CaseEntity(LegalEntity):
    """案件实体"""
    type: str = "Case"
    attributes: Dict[str, Any] = Field(default_factory=lambda: {
        "case_id": "",
        "title": "",
        "date": "",
        "citation": "",
        "court": "",
    })


class CourtEntity(LegalEntity):
    """法院实体"""
    type: str = "Court"
    attributes: Dict[str, Any] = Field(default_factory=lambda: {
        "name": "",
        "level": "",
        "jurisdiction": "",
    })


class JudgeEntity(LegalEntity):
    """法官实体"""
    type: str = "Judge"
    attributes: Dict[str, Any] = Field(default_factory=lambda: {
        "name": "",
        "title": "",
    })


class PartyEntity(LegalEntity):
    """当事人实体"""
    type: str = "Party"
    attributes: Dict[str, Any] = Field(default_factory=lambda: {
        "name": "",
        "party_type": "",  # plaintiff/defendant
        "role": "",
    })


class LawEntity(LegalEntity):
    """法律条文实体"""
    type: str = "Law"
    attributes: Dict[str, Any] = Field(default_factory=lambda: {
        "name": "",
        "law_type": "",  # ordinance/regulation/common law
        "provision": "",
        "chapter": "",
    })


class EvidenceEntity(LegalEntity):
    """证据实体"""
    type: str = "Evidence"
    attributes: Dict[str, Any] = Field(default_factory=lambda: {
        "type": "",
        "description": "",
    })


class LegalTermEntity(LegalEntity):
    """法律术语实体"""
    type: str = "LegalTerm"
    attributes: Dict[str, Any] = Field(default_factory=lambda: {
        "term": "",
        "definition": "",
    })


class DateEntity(LegalEntity):
    """日期实体"""
    type: str = "Date"
    attributes: Dict[str, Any] = Field(default_factory=lambda: {
        "date": "",
        "date_type": "",  # filing/hearing/judgment
    })


class AmountEntity(LegalEntity):
    """金额实体"""
    type: str = "Amount"
    attributes: Dict[str, Any] = Field(default_factory=lambda: {
        "amount": "",
        "currency": "HKD",
    })


# 实体类型映射
ENTITY_TYPES = {
    "Case": CaseEntity,
    "Court": CourtEntity,
    "Judge": JudgeEntity,
    "Party": PartyEntity,
    "Law": LawEntity,
    "Evidence": EvidenceEntity,
    "LegalTerm": LegalTermEntity,
    "Date": DateEntity,
    "Amount": AmountEntity,
}


def create_entity(entity_type: str, **kwargs) -> LegalEntity:
    """根据类型创建实体"""
    entity_class = ENTITY_TYPES.get(entity_type, LegalEntity)
    return entity_class(**kwargs)


def normalize_entity_type(entity_type: str) -> str:
    """归一化实体类型"""
    type_mapping = {
        "案件": "Case",
        "法院": "Court",
        "法官": "Judge",
        "当事人": "Party",
        "法律": "Law",
        "证据": "Evidence",
        "法律术语": "LegalTerm",
        "日期": "Date",
        "金额": "Amount",
        "plaintiff": "Party",
        "defendant": "Party",
    }
    return type_mapping.get(entity_type, entity_type)
