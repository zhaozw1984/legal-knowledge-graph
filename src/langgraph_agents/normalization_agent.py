"""实体归一化智能体模块"""
import json
from typing import Dict, Any, List, Set
from src.langgraph_agents.base_agent import BaseAgent
from src.utils.logger import logger


class NormalizationAgent(BaseAgent):
    """实体归一化智能体"""
    
    def __init__(self, llm=None):
        """初始化归一化智能体"""
        super().__init__("NormalizationAgent", llm)
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建实体归一化提示词

        Args:
            context: 包含 resolved_entities 的上下文

        Returns:
            提示词
        """
        entities = context.get("resolved_entities", [])
        qa_report = context.get("quality_report", {})
        issues = qa_report.get("issues", [])
        recommendations = qa_report.get("recommendations", [])
        backtrack_count = context.get("backtrack_count", 0)

        # 按类型分组
        entities_by_type = {}
        for entity in entities:
            etype = entity["type"]
            if etype not in entities_by_type:
                entities_by_type[etype] = []
            entities_by_type[etype].append(entity)

        # 构建类型分组描述
        type_descriptions = []
        for etype, ents in entities_by_type.items():
            type_descriptions.append(f"\n{etype} 实体：")
            type_descriptions.extend([
                f"  - {e['id']}: {e['text']}"
                for e in ents
            ])

        # 如果有QA反馈且正在回溯，添加指导
        qa_guidance = ""
        if (issues or recommendations) and backtrack_count > 0:
            qa_guidance = "\n\n=== 质量检查反馈 ===\n"
            if issues:
                qa_guidance += "上一次归一化的问题：\n"
                qa_guidance += "\n".join(f"- {issue}" for issue in issues)
                qa_guidance += "\n\n"
            if recommendations:
                qa_guidance += "改进建议：\n"
                qa_guidance += "\n".join(f"- {rec}" for rec in recommendations)
                qa_guidance += "\n\n"
            qa_guidance += "请根据以上反馈，针对性地改进本次归一化操作。\n"

        prompt = f"""你是一个实体归一化专家。请将相似的实体合并，确保知识图谱的一致性。

实体列表：
{"".join(type_descriptions)}

任务：
1. 识别相同或相似的实体（同一人、同一案件、同一法律等）
2. 将它们合并为一个规范实体
3. 保留最完整的信息作为主实体

重要规则：
- **normalized_entities 列表只包含发生了合并操作的主实体**
- **未发生合并的实体（独立的实体）不需要在输出中列出，系统会自动保留**
- 每个 normalized_entity 必须包含 merged_ids 字段，列出所有被合并到主实体的ID
- 如果某个实体没有与其他实体相似，则不要在输出中列出它

输出格式（JSON）：
{{
    "normalized_entities": [
        {{
            "id": "保留的主实体ID",
            "type": "实体类型",
            "text": "规范化文本表述",
            "attributes": {{"合并后的属性": "值"}},
            "merged_ids": ["被合并的实体ID1", "被合并的实体ID2"],
            "confidence": "归一化置信度"
        }}
    ]
}}

注意：
1. 只合并确认为同一实体的记录
2. 保留最详细的属性信息
3. 保持实体类型的准确性
4. 只输出 JSON
5. merged_ids 必须包含所有被合并的实体ID（至少要有2个ID，因为发生了合并）
6. 如果没有需要合并的实体，返回空列表：{{"normalized_entities": []}}
{qa_guidance}
开始归一化："""
        return prompt
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行实体归一化
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        logger.info(f"[{self.name}] 开始执行实体归一化...")

        #跳过当前agent
        #state["normalized_entities"] = state.get("resolved_entities", [])
        #return state
        
        if not state.get("resolved_entities"):
            logger.warning(f"[{self.name}] 没有实体需要归一化")
            state["normalized_entities"] = state.get("resolved_entities", [])
            return state
        
        # 构建 prompt 并调用 LLM
        prompt = self.build_prompt(state)
        try:
            response = self.invoke_llm(prompt)
            normalized_entities = self._parse_response(response, state["resolved_entities"])
            
            state["normalized_entities"] = normalized_entities
            state["current_stage"] = "normalization_completed"
            logger.info(f"[{self.name}] 归一化完成，{len(state['resolved_entities'])} -> {len(normalized_entities)} 个实体")
            
        except Exception as e:
            logger.error(f"[{self.name}] 实体归一化失败: {e}")
            state["error_messages"].append(f"归一化失败: {str(e)}")
            # 如果归一化失败，使用消解后的实体
            state["normalized_entities"] = state.get("resolved_entities", [])
            raise
        
        return state
    
    def _parse_response(self, response: str, original_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析归一化响应
        
        Args:
            response: LLM 响应
            original_entities: 原始实体列表
            
        Returns:
            归一化后的实体列表
        """
        try:
            # 清理响应
            response = response.strip()
            
            # 检查响应是否为空
            if not response:
                logger.warning("归一化响应为空")
                return original_entities
            
            # 尝试解析 JSON
            data = json.loads(response)
            normalized_list = data.get("normalized_entities", [])
            
            if not normalized_list:
                # 如果没有需要归一化的，返回原始实体
                return original_entities
            
            # 收集被合并的实体 ID
            merged_ids: Set[str] = set()
            for norm_entity in normalized_list:
                merged_ids.update(norm_entity.get("merged_ids", []))
            
            # 添加未合并的实体
            result = normalized_list.copy()
            for entity in original_entities:
                if entity["id"] not in merged_ids:
                    result.append(entity)
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}, 响应内容: {response[:500]}")
            return original_entities
        except Exception as e:
            logger.error(f"解析归一化响应失败: {e}")
            return original_entities
