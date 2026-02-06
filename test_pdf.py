"""测试 PDF 提取功能"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pdf_processor.extractor import PDFExtractor

def main():
    print("开始测试 PDF 提取功能...")
    extractor = PDFExtractor()
    results = extractor.extract_from_directory()
    
    print(f"\n找到 {len(results)} 个 PDF 文件")
    for result in results:
        if result["success"]:
            print(f"✓ {result['file_name']}")
            print(f"  页数: {result['page_count']}")
            print(f"  文本长度: {len(result['full_text'])} 字符")
            print(f"  预览: {result['full_text'][:150]}...")
            
            # 保存文本
            txt_path = extractor.save_extracted_text(result)
            if txt_path:
                print(f"  已保存到: {txt_path}")
        else:
            print(f"✗ {result['file_name']}: {result.get('error', '未知错误')}")

if __name__ == "__main__":
    main()
