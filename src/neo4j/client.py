"""Neo4j 客户端模块"""
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from config.settings import settings
from src.utils.logger import logger


class Neo4jClient:
    """Neo4j 数据库客户端"""
    
    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        """
        初始化 Neo4j 客户端
        
        Args:
            uri: Neo4j URI
            user: 用户名
            password: 密码
        """
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self.driver = None
        logger.info(f"Neo4j 客户端初始化: {self.uri}")
    
    def connect(self):
        """连接到 Neo4j 数据库"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # 验证连接
            self.driver.verify_connectivity()
            logger.info("成功连接到 Neo4j 数据库")
            return True
        except Exception as e:
            logger.error(f"连接 Neo4j 失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j 连接已关闭")
    
    def create_constraints(self):
        """创建约束和索引"""
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Case) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Court) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (j:Judge) REQUIRE j.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Party) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (l:Law) REQUIRE l.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Evidence) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (t:LegalTerm) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Date) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Amount) REQUIRE a.id IS UNIQUE",
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"创建约束成功: {constraint}")
                except Exception as e:
                    logger.warning(f"创建约束失败（可能已存在）: {e}")
    
    def create_entity(self, entity_type: str, entity: Dict[str, Any]) -> str:
        """
        创建实体节点
        
        Args:
            entity_type: 实体类型
            entity: 实体属性字典
            
        Returns:
            实体 ID
        """
        cypher = f"""
        MERGE (n:{entity_type} {{id: $id}})
        SET n = $properties
        RETURN n.id as id
        """
        
        with self.driver.session() as session:
            result = session.run(
                cypher,
                id=entity.get("id"),
                properties=entity
            )
            record = result.single()
            if record:
                logger.debug(f"创建/更新实体: {entity_type} {entity.get('id')}")
                return record["id"]
        return entity.get("id")
    
    def batch_create_entities(self, entities: List[Dict[str, Any]]) -> int:
        """
        批量创建实体节点
        
        Args:
            entities: 实体列表，每个实体包含 type 和属性
            
        Returns:
            成功创建的实体数量
        """
        count = 0
        for entity in entities:
            entity_type = entity.pop("type")
            self.create_entity(entity_type, entity)
            entity["type"] = entity_type  # 恢复 type
            count += 1
        
        logger.info(f"批量创建实体完成: {count} 个")
        return count
    
    def create_relation(self, subject_id: str, predicate: str, object_id: str, **attributes):
        """
        创建关系
        
        Args:
            subject_id: 主语实体 ID
            predicate: 关系类型
            object_id: 宾语实体 ID
            **attributes: 关系属性
        """
        cypher = f"""
        MATCH (a {{id: $subject_id}})
        MATCH (b {{id: $object_id}})
        MERGE (a)-[r:{predicate}]->(b)
        SET r = $attributes
        """
        
        with self.driver.session() as session:
            session.run(
                cypher,
                subject_id=subject_id,
                object_id=object_id,
                attributes=attributes
            )
            logger.debug(f"创建关系: {subject_id} -[{predicate}]-> {object_id}")
    
    def batch_create_relations(self, relations: List[Dict[str, Any]]) -> int:
        """
        批量创建关系
        
        Args:
            relations: 关系列表，每个关系包含 subject, predicate, object
            
        Returns:
            成功创建的关系数量
        """
        count = 0
        for relation in relations:
            self.create_relation(
                subject_id=relation["subject"],
                predicate=relation["predicate"],
                object_id=relation["object"],
                **{k: v for k, v in relation.items() 
                   if k not in ["subject", "predicate", "object"]}
            )
            count += 1
        
        logger.info(f"批量创建关系完成: {count} 个")
        return count
    
    def clear_all(self):
        """清空数据库（慎用）"""
        cypher = "MATCH (n) DETACH DELETE n"
        with self.driver.session() as session:
            session.run(cypher)
            logger.warning("数据库已清空")
    
    def get_stats(self) -> Dict[str, int]:
        """获取数据库统计信息"""
        stats = {}
        cypher = "MATCH (n) RETURN labels(n) as label, count(n) as count"
        
        with self.driver.session() as session:
            result = session.run(cypher)
            for record in result:
                label = record["label"][0] if record["label"] else "Unknown"
                stats[label] = record["count"]
        
        # 关系统计
        relation_cypher = "MATCH ()-[r]->() RETURN type(r) as relation, count(r) as count"
        with self.driver.session() as session:
            result = session.run(relation_cypher)
            for record in result:
                relation = record["relation"]
                stats[f"relation_{relation}"] = record["count"]
        
        return stats


def main():
    """测试 Neo4j 连接"""
    client = Neo4jClient()
    if client.connect():
        client.create_constraints()
        
        # 测试创建实体
        client.create_entity("Court", {
            "id": "HKCA_001",
            "name": "香港高等法院上诉法庭",
            "level": "High Court",
            "jurisdiction": "Hong Kong"
        })
        
        stats = client.get_stats()
        print("数据库统计:", stats)
        
        client.close()


if __name__ == "__main__":
    main()
