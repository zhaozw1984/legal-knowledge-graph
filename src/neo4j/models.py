"""Neo4j 图数据库模型模块"""
from typing import Dict, Any, List, Optional
from src.knowledge_base.entities import LegalEntity, create_entity
from src.utils.logger import logger


class GraphModel:
    """图数据模型基类"""
    
    @staticmethod
    def entity_to_cypher_properties(entity: LegalEntity) -> Dict[str, Any]:
        """
        将实体转换为 Cypher 属性字典
        
        Args:
            entity: 法律实体对象
            
        Returns:
            Cypher 属性字典
        """
        properties = {
            "id": entity.id,
            "text": entity.text,
            "confidence": entity.confidence,
        }
        
        # 合并属性
        properties.update(entity.attributes)
        
        return properties
    
    @staticmethod
    def cypher_to_entity(node: Dict[str, Any], entity_type: str) -> LegalEntity:
        """
        从 Cypher 节点转换为实体对象
        
        Args:
            node: Cypher 节点数据
            entity_type: 实体类型
            
        Returns:
            法律实体对象
        """
        entity_data = {
            "id": node.get("id"),
            "type": entity_type,
            "text": node.get("text", ""),
            "confidence": node.get("confidence", 1.0),
            "attributes": {},
        }
        
        # 提取特定属性到 attributes 字段
        exclude_keys = {"id", "text", "confidence"}
        for key, value in node.items():
            if key not in exclude_keys:
                entity_data["attributes"][key] = value
        
        return create_entity(entity_type, **entity_data)


class KnowledgeGraphBuilder:
    """知识图谱构建器"""
    
    def __init__(self, neo4j_client):
        """
        初始化知识图谱构建器
        
        Args:
            neo4j_client: Neo4j 客户端实例
        """
        self.client = neo4j_client
        self.model = GraphModel()
        logger.info("知识图谱构建器初始化完成")
    
    def build_from_extraction(self, extraction_result: dict):
        """
        从抽取结果构建知识图谱

        Args:
            extraction_result: 包含 entities 和 relations 的抽取结果
        """
        # 创建实体
        entities = extraction_result.get("entities", [])
        if entities:
            logger.info(f"开始创建 {len(entities)} 个实体...")
            self.client.batch_create_entities(entities)
        
        # 创建关系
        relations = extraction_result.get("relations", [])
        if relations:
            logger.info(f"开始创建 {len(relations)} 个关系...")
            self.client.batch_create_relations(relations)
        
        # 获取统计信息
        stats = self.client.get_stats()
        logger.info(f"知识图谱构建完成，统计信息: {stats}")
        
        return stats
    
    def query_entity_by_id(self, entity_id: str) -> Dict[str, Any]:
        """
        根据 ID 查询实体
        
        Args:
            entity_id: 实体 ID
            
        Returns:
            实体数据字典
        """
        cypher = """
        MATCH (n {id: $id})
        RETURN n, labels(n) as labels
        """
        
        with self.client.driver.session() as session:
            result = session.run(cypher, id=entity_id)
            record = result.single()
            if record:
                node = record["n"]
                labels = record["labels"]
                entity_type = labels[0] if labels else "Unknown"
                return self.model.cypher_to_entity(node, entity_type)
        return None
    
    def query_relations(self, subject_id: str, relation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        查询实体相关的关系
        
        Args:
            subject_id: 主语实体 ID
            relation_type: 关系类型（可选）
            
        Returns:
            关系列表
        """
        if relation_type:
            cypher = f"""
            MATCH (a {{id: $id}})-[r:{relation_type}]->(b)
            RETURN r, b, labels(b) as labels
            """
        else:
            cypher = """
            MATCH (a {id: $id})-[r]->(b)
            RETURN r, b, labels(b) as labels
            """
        
        relations = []
        with self.client.driver.session() as session:
            result = session.run(cypher, id=subject_id)
            for record in result:
                relation = {
                    "subject": subject_id,
                    "predicate": record["r"].type,
                    "object": record["b"]["id"],
                    "attributes": dict(record["r"]),
                }
                relations.append(relation)
        
        return relations
