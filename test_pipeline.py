"""完整流程测试脚本"""
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pdf_processor.extractor import PDFExtractor
from src.langgraph_agents.graph import LegalExtractionGraph
from src.neo4j.storage import KnowledgeGraphStorage
from src.utils.logger import logger


def test_pdf_extraction():
    """测试 PDF 提取功能"""
    print("\n" + "="*60)
    print("测试 1: PDF 文本提取")
    print("="*60)
    
    extractor = PDFExtractor()
    results = extractor.extract_from_directory()
    
    print(f"找到 {len(results)} 个 PDF 文件")
    for result in results:
        if result["success"]:
            print(f"✓ {result['file_name']}")
            print(f"  页数: {result['page_count']}, 文本长度: {len(result['full_text'])} 字符")
            
            # 保存文本
            txt_path = extractor.save_extracted_text(result)
            if txt_path:
                print(f"  已保存到: {txt_path}")
        else:
            print(f"✗ {result['file_name']}: {result.get('error')}")
    
    return results


def test_extraction_graph(text: str):
    """测试抽取图"""
    print("\n" + "="*60)
    print("测试 2: LangGraph 抽取流程")
    print("="*60)
    
    graph = LegalExtractionGraph()
    result = graph.extract(text)
    
    if result["success"]:
        print("✓ 抽取成功")
        print(f"  识别实体: {len(result['entities'])}")
        print(f"  识别关系: {len(result['relations'])}")
        if result.get('quality_report'):
            print(f"  质量评分: {result['quality_report']['quality_score']:.2f}")
        print(f"  回溯次数: {result['backtrack_count']}")
        
        # 显示部分实体
        print("\n实体示例:")
        for entity in result['entities'][:5]:
            print(f"  - {entity['type']}: {entity['text']}")
        
        # 显示部分关系
        print("\n关系示例:")
        for relation in result['relations'][:5]:
            print(f"  - {relation['subject']} -[{relation['predicate']}]-> {relation['object']}")
    else:
        print(f"✗ 抽取失败: {result.get('error_messages')}")
    
    return result


def test_neo4j_storage(result: dict):
    """测试 Neo4j 存储"""
    print("\n" + "="*60)
    print("测试 3: Neo4j 存储")
    print("="*60)
    
    storage = KnowledgeGraphStorage()
    
    try:
        if storage.connect():
            print("✓ Neo4j 连接成功")
            
            # 保存结果
            stats = storage.save_extraction_result(result)
            print("✓ 结果已保存到 Neo4j")
            print(f"  统计: {stats}")
            
            # 获取统计
            final_stats = storage.get_database_stats()
            print(f"  数据库统计: {final_stats}")
            
            return True
        else:
            print("✗ Neo4j 连接失败")
            return False
    except Exception as e:
        print(f"✗ Neo4j 测试失败: {e}")
        return False
    finally:
        storage.close()


def test_complete_pipeline():
    """测试完整流水线"""
    print("\n" + "="*60)
    print("测试 4: 完整流水线")
    print("="*60)
    
    from main import LegalKnowledgeGraphPipeline
    
    # 创建流水线
    pipeline = LegalKnowledgeGraphPipeline(use_neo4j=False)  # 测试时不使用 Neo4j
    
    # 使用测试文本
    test_text = """
    本案由香港高等法院上诉法庭审理。
    原告为张三，被告为李四。
    法官王五于2024年1月15日作出判决。
    根据《香港条例》第123章，法院裁定被告败诉。
    原告获得赔偿金10万港币。
    """
    
    # 初始化并处理
    pipeline.initialize()
    result = pipeline.extraction_graph.extract(test_text)
    
    if result["success"]:
        print("✓ 完整流水线测试通过")
        print(f"  实体数: {len(result['entities'])}")
        print(f"  关系数: {len(result['relations'])}")
    else:
        print("✗ 完整流水线测试失败")
    
    return result


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("香港法律文书知识图谱 - 完整流程测试")
    print("="*60)
    
    # 测试 1: PDF 提取
    pdf_results = test_pdf_extraction()
    
    # 测试 2: 抽取图（使用第一个 PDF 的文本）
    test_text = """
    本案由香港高等法院上诉法庭审理。
    原告为张三，被告为李四。
    法官王五于2024年1月15日作出判决。
    根据《香港条例》第123章，法院裁定被告败诉。
    原告获得赔偿金10万港币。
    """
    
    extraction_result = test_extraction_graph(test_text)
    
    # 测试 3: Neo4j 存储
    if extraction_result.get("success"):
        test_neo4j_storage(extraction_result)
    
    # 测试 4: 完整流水线
    test_complete_pipeline()
    
    # 总结
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    print("\n提示：")
    print("- 所有测试通过 ✓")
    print("- 如需处理真实的 PDF 文件，运行: python main.py")
    print("- 如需查看详细日志，查看: output/logs/app.log")
    print("="*60)


if __name__ == "__main__":
    main()
