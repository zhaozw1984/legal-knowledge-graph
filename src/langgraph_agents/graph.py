"""LangGraph 状态机模块（7步新架构）"""
import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from src.langgraph_agents.state import ExtractionState, create_initial_state
from src.langgraph_agents.ner_agent import NERAgent
from src.langgraph_agents.coref_agent import CorefAgent
from src.langgraph_agents.relation_agent import RelationAgent
from src.langgraph_agents.qa_agent import QualityCheckAgent
from src.langgraph_agents.relation_norm_agent import RelationNormalizationAgent
from src.normalization.normalizer import EntityNormalizer
from src.document_parser.parser import DocumentParser
from src.utils.logger import logger
from config.settings import settings


class LegalExtractionGraph:
    """法律文书抽取状态机（7步新架构）"""
    
    def __init__(self):
        """初始化状态机"""
        # 初始化智能体和处理器
        self.document_parser = DocumentParser()
        self.ner_agent = NERAgent()
        self.entity_normalizer = EntityNormalizer()
        self.relation_agent = RelationAgent()
        self.relation_norm_agent = RelationNormalizationAgent()
        self.coref_agent = CorefAgent()
        self.qa_agent = QualityCheckAgent()
        
        # 创建状态图
        self.graph = self._build_graph()
        logger.info("LangGraph 状态机构建完成（7步架构）")
    
    def _build_graph(self) -> StateGraph:
        """
        构建7步状态机
        
        流程：文档解析 → 块级NER → 规则标准化 → 循环关系抽取 → 关系归一 → 关系引导消解 → QA
        
        Returns:
            StateGraph 实例
        """
        # 创建状态图
        workflow = StateGraph(ExtractionState)
        
        # 添加节点（7步新架构）
        workflow.add_node("document_parser", self._document_parser_node)
        workflow.add_node("ner", self._ner_node)
        workflow.add_node("normalization", self._normalization_node)
        workflow.add_node("relation", self._relation_node)
        workflow.add_node("relation_norm", self._relation_norm_node)
        workflow.add_node("coref", self._coref_node)
        workflow.add_node("qa", self._qa_node)
        
        # 设置入口点
        workflow.set_entry_point("document_parser")
        
        # 添加边（7步线性流程）
        workflow.add_edge("document_parser", "ner")
        workflow.add_edge("ner", "normalization")
        workflow.add_edge("normalization", "relation")
        workflow.add_edge("relation", "relation_norm")
        workflow.add_edge("relation_norm", "coref")
        workflow.add_edge("coref", "qa")
        
        # 添加条件边（回溯逻辑）
        workflow.add_conditional_edges(
            "qa",
            self._should_backtrack,
            {
                "end": END,
                "backtrack_document_parser": "document_parser",
                "backtrack_ner": "ner",
                "backtrack_normalization": "normalization",
                "backtrack_relation": "relation",
                "backtrack_relation_norm": "relation_norm",
                "backtrack_coref": "coref",
            }
        )
        
        # 编译状态图
        return workflow.compile()
    
    def _document_parser_node(self, state: ExtractionState) -> ExtractionState:
        """文档结构解析节点（新增）"""
        logger.info(">>> 进入文档结构解析节点")
        
        try:
            # 解析文档结构
            raw_text = state.get("raw_text", "")
            document_blocks = self.document_parser.parse(raw_text)
            
            # 转换为字典格式并更新状态
            state["document_blocks"] = [block.to_dict() for block in document_blocks]
            state["current_stage"] = "document_parser_completed"
            
            # 打印统计信息
            stats = self.document_parser.get_statistics()
            logger.info(f"文档解析完成，共识别 {stats['total_blocks']} 个文档块")
            logger.info(f"  类型分布: {stats['type_distribution']}")
            
        except Exception as e:
            logger.error(f"文档结构解析失败: {e}")
            state["error_messages"].append(f"文档解析失败: {str(e)}")
            raise
        
        return state
    
    def _ner_node(self, state: ExtractionState) -> ExtractionState:
        """块级实体识别节点"""
        logger.info(">>> 进入块级NER节点")
        return self.ner_agent.process(state)
    
    def _normalization_node(self, state: ExtractionState) -> ExtractionState:
        """规则实体标准化节点（新逻辑）"""
        logger.info(">>> 进入规则实体标准化节点")
        
        try:
            # 获取原始实体
            raw_entities = state.get("entities", [])
            
            if not raw_entities:
                logger.warning("没有实体需要标准化")
                state["normalized_entities"] = []
                return state
            
            # 执行规则标准化
            normalized_entities = self.entity_normalizer.normalize(raw_entities)
            
            # 转换为字典格式
            state["normalized_entities"] = [
                {
                    "entity_id": e.entity_id,
                    "canonical_name": e.canonical_name,
                    "aliases": e.aliases,
                    "entity_type": e.entity_type,
                    "original_names": e.original_names,
                    "block_type": e.block_type,
                    "confidence": e.confidence,
                    "source_block_ids": e.source_block_ids
                }
                for e in normalized_entities
            ]
            
            state["current_stage"] = "normalization_completed"
            
            # 打印统计信息
            logger.info(
                f"规则标准化完成，"
                f"合并前: {len(raw_entities)} 个实体，"
                f"合并后: {len(normalized_entities)} 个实体"
            )
            
        except Exception as e:
            logger.error(f"实体标准化失败: {e}")
            state["error_messages"].append(f"实体标准化失败: {str(e)}")
            raise
        
        return state
    
    def _relation_node(self, state: ExtractionState) -> ExtractionState:
        """循环关系抽取节点"""
        logger.info(">>> 进入循环关系抽取节点")
        return self.relation_agent.process(state)
    
    def _relation_norm_node(self, state: ExtractionState) -> ExtractionState:
        """关系归一化节点（新增）"""
        logger.info(">>> 进入关系归一化节点")
        return self.relation_norm_agent.normalize(state)
    
    def _coref_node(self, state: ExtractionState) -> ExtractionState:
        """Relation-guided指代消解节点（新逻辑）"""
        logger.info(">>> 进入关系引导指代消解节点")
        return self.coref_agent.process(state)
    
    def _qa_node(self, state: ExtractionState) -> ExtractionState:
        """质量检查节点（适配7步）"""
        logger.info(">>> 进入质量检查节点")
        return self.qa_agent.process(state)
    
    def _should_backtrack(
        self, 
        state: ExtractionState
    ) -> Literal[
        "end", 
        "backtrack_document_parser",
        "backtrack_ner", 
        "backtrack_normalization", 
        "backtrack_relation",
        "backtrack_relation_norm",
        "backtrack_coref"
    ]:
        """
        决定是否回溯以及回溯到哪个阶段（适配7步架构）
        
        Args:
            state: 当前状态
            
        Returns:
            下一个节点的名称
        """
        # 检查是否需要回溯
        if not state.get("backtrack_needed", False):
            logger.info("质量检查通过，流程结束")
            return "end"
        
        # 检查是否超过最大回溯次数
        if state.get("backtrack_count", 0) >= settings.max_backtrack_attempts:
            logger.warning(f"已达到最大回溯次数（{settings.max_backtrack_attempts}），停止回溯")
            return "end"
        
        # 根据回溯阶段决定回溯目标
        backtrack_stage = state.get("backtrack_stage", "")
        logger.info(f"质量检查未通过，回溯到 {backtrack_stage} 阶段")
        
        # 7步回溯阶段映射
        stage_mapping = {
            "document_parser": "backtrack_document_parser",
            "ner": "backtrack_ner",
            "normalization": "backtrack_normalization",
            "relation": "backtrack_relation",
            "relation_norm": "backtrack_relation_norm",
            "coref": "backtrack_coref",
        }
        
        return stage_mapping.get(backtrack_stage, "end")
    
    def extract(self, text: str, pdf_path: str = None) -> Dict[str, Any]:
        """
        执行完整的7步抽取流程
        
        Args:
            text: 原始文本
            pdf_path: PDF 文件路径（可选）
            
        Returns:
            抽取结果
        """
        logger.info(f"开始7步抽取流程，文本长度: {len(text)} 字符")
        
        # 创建初始状态
        state = create_initial_state(text, pdf_path)
        
        try:
            # 运行状态机
            final_state = self.graph.invoke(state)
            
            logger.info("7步抽取流程完成")
            logger.info(f"  文档块: {len(final_state.get('document_blocks', []))}")
            logger.info(f"  识别实体: {len(final_state.get('normalized_entities', []))}")
            logger.info(f"  归一化关系: {len(final_state.get('normalized_relations', []))}")
            logger.info(f"  质量评分: {final_state.get('quality_report', {}).get('quality_score', 0):.2f}")
            logger.info(f"  回溯次数: {final_state.get('backtrack_count', 0)}")
            
            return {
                "text": final_state["raw_text"],
                "pdf_path": final_state.get("pdf_path"),
                "document_blocks": final_state.get("document_blocks", []),
                "entities": final_state.get("normalized_entities", []),
                "relations": final_state.get("normalized_relations", []),
                "quality_report": final_state.get("quality_report"),
                "backtrack_count": final_state.get("backtrack_count", 0),
                "error_messages": final_state.get("error_messages", []),
                "success": True,
            }
            
        except Exception as e:
            logger.error(f"抽取流程失败: {e}", exc_info=True)
            return {
                "text": text,
                "pdf_path": pdf_path,
                "document_blocks": [],
                "entities": [],
                "relations": [],
                "quality_report": None,
                "backtrack_count": 0,
                "error_messages": [str(e)],
                "success": False,
            }
    
    def visualize_graph(self, output_path: str = None):
        """
        可视化状态机

        Args:
            output_path: 输出路径（可选）
        """
        try:
            # 尝试生成 Mermaid PNG 图片
            img = self.graph.get_graph().draw_mermaid_png()

            # 默认保存到 output 目录
            if output_path is None:
                output_path = os.path.join(project_root, "output", "graph.png")

            # 确保目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(img)
            logger.info(f"状态机图已保存到: {output_path}")
        except Exception as e:
            logger.warning(f"无法生成 PNG 图片: {e}")
            # 打印 Mermaid 文本表示
            try:
                mermaid_code = self.graph.get_graph().draw_mermaid()
                print("\n=== 状态机 Mermaid 图形 ===")
                print(mermaid_code)
                print("=== 结束 ===\n")
            except Exception as e2:
                logger.warning(f"无法生成 Mermaid 文本: {e2}")


def main():
    """测试状态机"""

    # 创建抽取图
    extraction_graph = LegalExtractionGraph()

    # 测试文本
    test_text = """
    本案由香港高等法院上诉法庭审理。
    原告为张三，被告为李四。
    法官王五于2024年1月15日作出判决。
    根据《香港条例》第123章，法院裁定被告败诉。
    原告获得赔偿金10万港币。
    """

    # 执行抽取
    result = extraction_graph.extract(test_text)
    print("抽取结果:")
    print(f"  实体数量: {len(result['entities'])}")
    print(f"  关系数数量: {len(result['relations'])}")
    print(f"  质量评分: {result['quality_report']['quality_score'] if result['quality_report'] else 'N/A'}")

    # 打印实体详情
    if result['entities']:
        print("\n=== 实体列表 ===")
        for i, entity in enumerate(result['entities'], 1):
            print(f"{i}. {entity}")
    else:
        print("\n未识别到实体")

    # 打印关系详情
    if result['relations']:
        print("\n=== 关系列表 ===")
        for i, relation in enumerate(result['relations'], 1):
            print(f"{i}. {relation}")
    else:
        print("\n未识别到关系")
    
    # 可视化状态机
    extraction_graph.visualize_graph()


if __name__ == "__main__":
    main()
