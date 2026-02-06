"""知识图谱存储集成模块"""
import os
from typing import Dict, Any, List, Optional
from src.neo4j.client import Neo4jClient
from src.neo4j.models import KnowledgeGraphBuilder
from src.utils.logger import logger
from config.settings import settings


class KnowledgeGraphStorage:
    """知识图谱存储管理器"""
    
    def __init__(self, neo4j_client: Optional[Neo4jClient] = None):
        """
        初始化存储管理器
        
        Args:
            neo4j_client: Neo4j 客户端（可选）
        """
        self.client = neo4j_client or Neo4jClient()
        self.builder = KnowledgeGraphBuilder(self.client)
        self.connected = False
    
    def connect(self) -> bool:
        """
        连接到 Neo4j 数据库
        
        Returns:
            是否连接成功
        """
        if self.connected:
            return True
        
        self.connected = self.client.connect()
        if self.connected:
            # 创建约束
            self.client.create_constraints()
            logger.info("Neo4j 数据库连接成功")
        return self.connected
    
    def close(self):
        """关闭数据库连接"""
        if self.connected:
            self.client.close()
            self.connected = False
    
    def save_extraction_result(self, result: Dict[str, Any]) -> Dict[str, int]:
        """
        保存抽取结果到知识图谱
        
        Args:
            result: 抽取结果
            
        Returns:
            统计信息（实体数、关系数等）
        """
        if not self.connected:
            raise RuntimeError("未连接到 Neo4j 数据库")
        
        logger.info(f"保存抽取结果: {result.get('pdf_path', '未知文件')}")
        
        # 构建知识图谱
        stats = self.builder.build_from_extraction(result)
        
        logger.info(f"知识图谱构建完成: {stats}")
        return stats
    
    def batch_save_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量保存抽取结果
        
        Args:
            results: 抽取结果列表
            
        Returns:
            总体统计信息
        """
        if not self.connected:
            raise RuntimeError("未连接到 Neo4j 数据库")
        
        total_stats = {}
        success_count = 0
        error_count = 0
        
        for i, result in enumerate(results):
            try:
                logger.info(f"保存第 {i+1}/{len(results)} 个结果...")
                stats = self.save_extraction_result(result)
                
                # 累计统计
                for key, value in stats.items():
                    if key not in total_stats:
                        total_stats[key] = 0
                    total_stats[key] += value
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"保存结果 {i+1} 失败: {e}")
                error_count += 1
        
        total_stats["success_count"] = success_count
        total_stats["error_count"] = error_count
        total_stats["total_count"] = len(results)
        
        logger.info(f"批量保存完成: 成功 {success_count}, 失败 {error_count}")
        return total_stats
    
    def export_to_json(self, output_path: str) -> bool:
        """
        导出知识图谱为 JSON
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            import json
            from datetime import datetime
            
            # 获取所有节点
            with self.client.driver.session() as session:
                nodes_result = session.run("""
                    MATCH (n)
                    RETURN {id: n.id, labels: labels(n), properties: properties(n)} as node
                """)
                nodes = [record["node"] for record in nodes_result]
                
                # 获取所有关系
                rels_result = session.run("""
                    MATCH (a)-[r]->(b)
                    RETURN {
                        source: a.id,
                        target: b.id,
                        type: type(r),
                        properties: properties(r)
                    } as relation
                """)
                relations = [record["relation"] for record in rels_result]
            
            # 构建导出数据
            export_data = {
                "export_time": datetime.now().isoformat(),
                "stats": self.client.get_stats(),
                "nodes": nodes,
                "relationships": relations,
            }
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"知识图谱已导出到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出知识图谱失败: {e}")
            return False
    
    def clear_database(self):
        """清空数据库"""
        if self.connected:
            self.client.clear_all()
            logger.warning("数据库已清空")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        if self.connected:
            return self.client.get_stats()
        return {}


def main():
    """测试存储功能"""
    # 创建存储管理器
    storage = KnowledgeGraphStorage()
    
    # 连接数据库
    if storage.connect():
        # 测试数据
        test_result = {
            "text": "测试文本",
            "entities": [
                {"id": "court_000", "type": "Court", "name": "香港高等法院", "level": "High Court"},
                {"id": "case_000", "type": "Case", "case_id": "HCMP001/2024", "title": "测试案件"},
                {"id": "party_000", "type": "Party", "name": "张三", "party_type": "plaintiff"},
            ],
            "relations": [
                {"subject": "case_000", "predicate": "case_in_court", "object": "court_000"},
                {"subject": "case_000", "predicate": "case_involved_party", "object": "party_000"},
            ],
        }
        
        # 保存结果
        stats = storage.save_extraction_result(test_result)
        print("统计:", stats)
        
        # 获取统计
        final_stats = storage.get_database_stats()
        print("最终统计:", final_stats)
        
        # 关闭连接
        storage.close()


if __name__ == "__main__":
    main()
