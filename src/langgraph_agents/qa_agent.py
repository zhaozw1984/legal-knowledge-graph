"""质量检查智能体模块"""
import json
from typing import Dict, Any, List
from src.langgraph_agents.base_agent import BaseAgent
from config.settings import settings
from src.utils.logger import logger


class QualityCheckAgent(BaseAgent):
    """质量检查智能体"""
    
    def __init__(self, llm=None):
        """初始化质量检查智能体"""
        super().__init__("QualityCheckAgent", llm)
        self.quality_threshold = settings.quality_threshold
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建质量检查提示词
        
        Args:
            context: 包含 raw_text, normalized_entities, relations 的上下文
            
        Returns:
            提示词
        """
        text = context.get("raw_text", "")
        entities = context.get("normalized_entities", [])
        relations = context.get("relations", [])
        
        # 构建摘要
        entity_summary = self._create_entity_summary(entities)
        relation_summary = self._create_relation_summary(relations)
        
        prompt = f"""你是一个知识图谱质量检查专家。请评估以下抽取结果的质量。

原文摘要：
{text[:1000]}...

抽取结果摘要：
{entity_summary}

{relation_summary}

检查维度：
1. 实体完整性：是否遗漏重要实体
2. 实体准确性：实体类型、属性是否正确
3. 关系合理性：关系是否符合法律逻辑
4. 一致性：实体和关系是否自洽
5. 置信度：低置信度的结果是否需要改进

输出格式（JSON）：
{{
    "quality_score": 0.85,
    "entity_count": 15,
    "relation_count": 20,
    "issues": [
        "问题1：具体描述",
        "问题2：具体描述"
    ],
    "recommendations": [
        "建议1：具体改进措施",
        "建议2：具体改进措施"
    ],
    "backtrack_stage": "建议回溯的阶段（ner/corf/normalization/relation）"
}}

注意：
1. quality_score 范围为 0-1
2. 如果 quality_score < 0.8，建议回溯
3. backtrack_stage 只选择一个最需要回溯的阶段
4. 只输出 JSON

开始评估："""
        return prompt
    
    def _create_entity_summary(self, entities: List[Dict[str, Any]]) -> str:
        """创建实体摘要"""
        if not entities:
            return "未识别到实体"
        
        summary = ["实体列表（按类型）："]
        from collections import defaultdict
        by_type = defaultdict(list)
        for e in entities:
            by_type[e["type"]].append(e)
        
        for etype, ents in sorted(by_type.items()):
            summary.append(f"\n{etype} ({len(ents)}个):")
            for e in ents[:5]:  # 最多显示5个
                summary.append(f"  - {e['id']}: {e['text']}")
            if len(ents) > 5:
                summary.append(f"  ... 还有 {len(ents) - 5} 个")
        
        return "\n".join(summary)
    
    def _create_relation_summary(self, relations: List[Dict[str, Any]]) -> str:
        """创建关系摘要"""
        if not relations:
            return "未识别到关系"
        
        summary = ["关系列表："]
        for rel in relations[:10]:  # 最多显示10个
            summary.append(f"  - {rel['subject']} -[{rel['predicate']}]-> {rel['object']} (置信度: {rel['confidence']})")
        
        if len(relations) > 10:
            summary.append(f"  ... 还有 {len(relations) - 10} 个关系")
        
        return "\n".join(summary)
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行质量检查
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        logger.info(f"[{self.name}] 开始执行质量检查...")
        
        # 构建 prompt 并调用 LLM
        prompt = self.build_prompt(state)
        try:
            response = self.invoke_llm(prompt)
            quality_report = self._parse_response(response)
            
            # 检查是否需要回溯
            needs_backtrack = quality_report["quality_score"] < self.quality_threshold
            
            if needs_backtrack:
                state["backtrack_needed"] = True
                state["backtrack_stage"] = quality_report["backtrack_stage"]
                state["backtrack_count"] += 1
                logger.warning(f"[{self.name}] 质量不达标（{quality_report['quality_score']:.2f}），建议回溯到 {quality_report['backtrack_stage']}")
                
                # 检查是否超过最大回溯次数
                if state["backtrack_count"] > settings.max_backtrack_attempts:
                    logger.error(f"[{self.name}] 超过最大回溯次数（{settings.max_backtrack_attempts}），停止回溯")
                    state["backtrack_needed"] = False
            else:
                state["backtrack_needed"] = False
                logger.info(f"[{self.name}] 质量检查通过（{quality_report['quality_score']:.2f}）")
            
            state["quality_report"] = quality_report
            state["current_stage"] = "qa_completed"
            
        except Exception as e:
            logger.error(f"[{self.name}] 质量检查失败: {e}")
            state["error_messages"].append(f"质量检查失败: {str(e)}")
            # 如果检查失败，默认不回溯
            state["backtrack_needed"] = False
            state["quality_report"] = {
                "quality_score": 0.5,
                "entity_count": len(state.get("normalized_entities", [])),
                "relation_count": len(state.get("relations", [])),
                "issues": ["质量检查失败"],
                "recommendations": [],
            }
            raise
        
        return state
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析质量检查响应
        
        Args:
            response: LLM 响应
            
        Returns:
            质量报告字典
        """
        try:
            # 清理响应
            response = response.strip()
            
            # 检查响应是否为空
            if not response:
                logger.warning("质量检查响应为空")
                return self._get_default_report("响应为空")
            
            # 尝试解析 JSON
            data = json.loads(response)
            
            return {
                "quality_score": data.get("quality_score", 0.5),
                "entity_count": data.get("entity_count", 0),
                "relation_count": data.get("relation_count", 0),
                "issues": data.get("issues", []),
                "recommendations": data.get("recommendations", []),
                "backtrack_stage": data.get("backtrack_stage", None),
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}, 响应内容: {response[:500]}")
            return self._get_default_report(f"JSON 解析失败: {str(e)}")
        except Exception as e:
            logger.error(f"解析质量检查响应失败: {e}")
            return self._get_default_report(f"解析失败: {str(e)}")
    
    def _get_default_report(self, reason: str) -> Dict[str, Any]:
        """获取默认质量报告"""
        return {
            "quality_score": 0.5,
            "entity_count": 0,
            "relation_count": 0,
            "issues": [reason],
            "recommendations": [],
            "backtrack_stage": None,
        }
