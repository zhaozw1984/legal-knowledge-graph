"""主程序入口"""
import os
import sys
import asyncio
from typing import List, Dict, Any, Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pdf_processor.extractor import PDFExtractor
from src.langgraph_agents.graph import LegalExtractionGraph
from src.neo4j.storage import KnowledgeGraphStorage
from src.utils.logger import logger
from config.settings import settings


class LegalKnowledgeGraphPipeline:
    """法律知识图谱构建流水线"""
    
    def __init__(self, use_neo4j: bool = True):
        """
        初始化流水线
        
        Args:
            use_neo4j: 是否使用 Neo4j 存储结果
        """
        self.use_neo4j = use_neo4j
        self.pdf_extractor = PDFExtractor()
        self.extraction_graph = None
        self.storage = None
        
        logger.info("法律知识图谱流水线初始化完成")
    
    def initialize(self):
        """初始化组件"""
        logger.info("初始化流水线组件...")
        
        # 初始化抽取图
        self.extraction_graph = LegalExtractionGraph()
        
        # 初始化 Neo4j 存储
        if self.use_neo4j:
            self.storage = KnowledgeGraphStorage()
            if not self.storage.connect():
                logger.error("无法连接到 Neo4j 数据库")
                self.use_neo4j = False
        
        logger.info("流水线初始化完成")
    
    def process_single_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        处理单个 PDF 文件
        
        Args:
            pdf_path: PDF 文件路径
            
        Returns:
            处理结果
        """
        logger.info(f"开始处理 PDF: {pdf_path}")
        
        # 提取文本
        extraction_result = self.pdf_extractor.extract_from_file(pdf_path)
        
        if not extraction_result.get("success"):
            logger.error(f"PDF 提取失败: {extraction_result.get('error')}")
            return {
                "pdf_path": pdf_path,
                "success": False,
                "error": extraction_result.get("error"),
            }
        
        # 执行知识抽取
        extraction_data = self.extraction_graph.extract(
            text=extraction_result["full_text"],
            pdf_path=pdf_path
        )
        
        # 保存到 Neo4j
        if self.use_neo4j and extraction_data.get("success"):
            try:
                stats = self.storage.save_extraction_result(extraction_data)
                extraction_data["neo4j_stats"] = stats
                logger.info(f"已保存到 Neo4j: {stats}")
            except Exception as e:
                logger.error(f"保存到 Neo4j 失败: {e}")
                extraction_data["neo4j_error"] = str(e)
        
        return extraction_data
    
    def process_directory(self, directory: str = None) -> List[Dict[str, Any]]:
        """
        批量处理目录中的所有 PDF 文件
        
        Args:
            directory: PDF 文件目录，默认使用配置中的目录
            
        Returns:
            所有文件的处理结果列表
        """
        directory = directory or settings.input_dir
        
        logger.info(f"开始批量处理目录: {directory}")
        
        # 提取所有 PDF
        pdf_results = self.pdf_extractor.extract_from_directory()
        
        if not pdf_results:
            logger.warning("未找到 PDF 文件")
            return []
        
        logger.info(f"找到 {len(pdf_results)} 个 PDF 文件")
        
        # 批量处理
        results = []
        for i, pdf_result in enumerate(pdf_results):
            if not pdf_result.get("success"):
                logger.warning(f"跳过无效的 PDF: {pdf_result['file_name']}")
                continue
            
            logger.info(f"处理进度: {i+1}/{len(pdf_results)}")
            result = self.process_single_pdf(pdf_result["file_path"])
            results.append(result)
        
        # 统计
        success_count = sum(1 for r in results if r.get("success"))
        logger.info(f"批量处理完成: 成功 {success_count}/{len(results)}")
        
        return results
    
    def run(self, input_path: str = None) -> List[Dict[str, Any]]:
        """
        运行流水线
        
        Args:
            input_path: 输入路径（文件或目录）
            
        Returns:
            处理结果列表
        """
        try:
            # 初始化
            self.initialize()
            
            if input_path:
                if os.path.isfile(input_path):
                    # 处理单个文件
                    result = self.process_single_pdf(input_path)
                    return [result]
                elif os.path.isdir(input_path):
                    # 处理目录
                    return self.process_directory(input_path)
                else:
                    logger.error(f"无效的输入路径: {input_path}")
                    return []
            else:
                # 处理默认目录
                return self.process_directory()
                
        except Exception as e:
            logger.error(f"流水线运行失败: {e}", exc_info=True)
            return []
        finally:
            # 清理资源
            if self.storage:
                self.storage.close()


def main():
    """主函数"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="香港法律文书知识图谱构建工具")
    parser.add_argument("--input", "-i", help="输入文件或目录路径")
    parser.add_argument("--no-neo4j", action="store_true", help="不使用 Neo4j 存储")
    parser.add_argument("--export", "-e", help="导出知识图谱到 JSON 文件")
    args = parser.parse_args()
    
    # 创建流水线
    pipeline = LegalKnowledgeGraphPipeline(use_neo4j=not args.no_neo4j)
    
    # 运行流水线
    results = pipeline.run(args.input)
    
    # 输出结果摘要
    if results:
        print("\n" + "="*60)
        print("处理结果摘要")
        print("="*60)
        
        success_count = 0
        total_entities = 0
        total_relations = 0
        
        for i, result in enumerate(results):
            print(f"\n文件 {i+1}: {result.get('pdf_path', '未知')}")
            print(f"  状态: {'成功' if result.get('success') else '失败'}")
            
            if result.get('success'):
                entities = result.get('entities', [])
                relations = result.get('relations', [])
                print(f"  实体数: {len(entities)}")
                print(f"  关系数: {len(relations)}")

                # 打印实体详情
                if entities:
                    print("\n  === 实体列表 ===")
                    for j, entity in enumerate(entities, 1):
                        print(f"  {j}. {entity}")

                # 打印关系详情
                if relations:
                    print("\n  === 关系列表 ===")
                    for j, relation in enumerate(relations, 1):
                        print(f"  {j}. {relation}")

                if result.get('quality_report'):
                    print(f"\n  质量评分: {result['quality_report'].get('quality_score', 0):.2f}")
                success_count += 1
                total_entities += len(entities)
                total_relations += len(relations)
            else:
                print(f"  错误: {result.get('error', '未知错误')}")
        
        print("\n" + "-"*60)
        print(f"总计: 成功 {success_count}/{len(results)}")
        print(f"总实体数: {total_entities}")
        print(f"总关系数: {total_relations}")
        print("="*60)
        
        # 导出知识图谱
        if args.export and pipeline.storage and pipeline.storage.connected:
            pipeline.storage.export_to_json(args.export)
    else:
        print("没有处理任何文件")


if __name__ == "__main__":
    main()
