"""
测试模块导入是否正常
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("开始测试模块导入...")

try:
    print("\n1. 导入文档解析器...")
    from src.document_parser.parser import DocumentParser
    print("   ✅ 成功")
except Exception as e:
    print(f"   ❌ 失败: {e}")

try:
    print("\n2. 导入实体标准化器...")
    from src.normalization.normalizer import EntityNormalizer
    print("   ✅ 成功")
except Exception as e:
    print(f"   ❌ 失败: {e}")

try:
    print("\n3. 导入关系归一化智能体...")
    from src.langgraph_agents.relation_norm_agent import RelationNormalizationAgent
    print("   ✅ 成功")
except Exception as e:
    print(f"   ❌ 失败: {e}")

try:
    print("\n4. 导入7步流水线图...")
    from src.langgraph_agents.graph import LegalExtractionGraph
    print("   ✅ 成功")
except Exception as e:
    print(f"   ❌ 失败: {e}")

try:
    print("\n5. 初始化流水线实例...")
    graph = LegalExtractionGraph()
    print("   ✅ 成功")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n" + "=" * 60)
print("模块导入测试完成")
print("=" * 60)
