"""
测试7步新架构流水线

运行完整的知识图谱构建流程，验证所有步骤是否正常工作。
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.langgraph_agents.graph import LegalExtractionGraph
from src.utils.logger import logger


def test_7_step_pipeline():
    """测试7步流水线"""
    logger.info("=" * 80)
    logger.info("开始测试7步新架构流水线")
    logger.info("=" * 80)
    
    # 测试文本（包含法律文书典型结构）
    test_text = """
【案件基本信息】

案件编号：HCAL 123/2024
法院名称：香港高等法院上诉法庭
案件性质：民事诉讼

【诉讼请求】

原告张三请求法院判令：
1. 被告李四支付赔偿金港币10万元；
2. 被告承担本案诉讼费用。

【案件事实】

原告张三于2024年1月1日与被告李四签订合同，约定被告向原告提供货物。
被告未能按期交付货物，构成违约。
原告多次催告，被告仍不履行义务。

【证据】

1. 合同原件（编号：CT-2024-001）
2. 催告函三封
3. 邮件往来记录

【判决理由】

本院认为，双方签订的合同合法有效。
被告未能按期交付货物，已构成违约。
根据《香港合约法》相关规定，被告应承担违约责任。

【判决结果】

1. 被告败诉；
2. 被告应于判决书送达之日起30日内向原告支付赔偿金港币10万元；
3. 被告承担本案全部诉讼费用。

【诉讼费用】

本案诉讼费用由被告承担，共计港币5千元。
"""
    
    try:
        # 创建7步流水线实例
        logger.info("初始化7步流水线...")
        graph = LegalExtractionGraph()
        
        # 执行抽取
        logger.info("\n开始执行完整抽取流程...\n")
        result = graph.extract(test_text)
        
        # 验证结果
        logger.info("\n" + "=" * 80)
        logger.info("抽取结果汇总")
        logger.info("=" * 80)
        
        logger.info(f"\n✅ 流程状态: {'成功' if result['success'] else '失败'}")
        logger.info(f"📊 文档块数量: {len(result.get('document_blocks', []))}")
        logger.info(f"🔤 实体数量: {len(result.get('entities', []))}")
        logger.info(f"🔗 关系数量: {len(result.get('relations', []))}")
        
        if result['quality_report']:
            logger.info(f"⭐ 质量评分: {result['quality_report'].get('quality_score', 0):.2f}")
        
        logger.info(f"🔄 回溯次数: {result.get('backtrack_count', 0)}")
        
        # 打印文档块信息
        if result.get('document_blocks'):
            logger.info("\n📄 文档块详情:")
            for i, block in enumerate(result['document_blocks'], 1):
                block_type = block.get('block_type', '')
                title = block.get('title', '')
                content_preview = block.get('content', '')[:50]
                logger.info(f"  {i}. [{block_type}] {title}: {content_preview}...")
        
        # 打印实体详情
        if result.get('entities'):
            logger.info("\n🔤 实体详情（前10个）:")
            for i, entity in enumerate(result['entities'][:10], 1):
                entity_id = entity.get('entity_id', '')
                entity_type = entity.get('entity_type', '')
                canonical_name = entity.get('canonical_name', '')
                logger.info(f"  {i}. {entity_id} [{entity_type}] {canonical_name}")
        
        # 打印关系详情
        if result.get('relations'):
            logger.info("\n🔗 关系详情（前10个）:")
            for i, rel in enumerate(result['relations'][:10], 1):
                subject = rel.get('subject_entity_id', '')
                predicate = rel.get('predicate', '')
                object_id = rel.get('object_entity_id', '')
                validation = "✓" if rel.get('validation_passed', False) else "✗"
                logger.info(f"  {i}. {subject} -[{predicate}]-> {object_id} {validation}")
        
        # 打印错误信息
        if result.get('error_messages'):
            logger.warning("\n⚠️ 错误信息:")
            for error in result['error_messages']:
                logger.warning(f"  - {error}")
        
        logger.info("\n" + "=" * 80)
        logger.info("7步流水线测试完成")
        logger.info("=" * 80)
        
        return result
        
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    result = test_7_step_pipeline()
    
    if result and result['success']:
        logger.info("\n✅ 所有步骤测试通过！")
        sys.exit(0)
    else:
        logger.error("\n❌ 测试未通过")
        sys.exit(1)
