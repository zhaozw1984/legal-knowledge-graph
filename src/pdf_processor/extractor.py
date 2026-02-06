"""PDF 文本提取模块"""
import os
from typing import List, Optional
import fitz  # PyMuPDF
from config.settings import settings
from src.utils.logger import logger


class PDFExtractor:
    """PDF 文本提取器"""
    
    def __init__(self, input_dir: Optional[str] = None):
        """
        初始化 PDF 提取器
        
        Args:
            input_dir: PDF 文件目录，默认从配置读取
        """
        self.input_dir = input_dir or settings.input_dir
        logger.info(f"PDF 提取器初始化，输入目录: {self.input_dir}")
    
    def extract_from_file(self, pdf_path: str) -> dict:
        """
        从单个 PDF 文件提取文本
        
        Args:
            pdf_path: PDF 文件路径
            
        Returns:
            dict: 包含文件名、页数、提取文本等信息的字典
        """
        if not os.path.exists(pdf_path):
            logger.error(f"PDF 文件不存在: {pdf_path}")
            return {"error": f"文件不存在: {pdf_path}"}
        
        try:
            doc = fitz.open(pdf_path)
            text_list = []
            
            # 逐页提取文本
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                text_list.append(text)
            
            full_text = "\n\n".join(text_list)
            
            result = {
                "file_name": os.path.basename(pdf_path),
                "file_path": pdf_path,
                "page_count": len(doc),
                "full_text": full_text,
                "success": True,
            }
            
            logger.info(f"成功提取 PDF: {pdf_path}, 页数: {len(doc)}, 文本长度: {len(full_text)}")
            doc.close()
            return result
            
        except Exception as e:
            logger.error(f"提取 PDF 失败 {pdf_path}: {e}")
            return {
                "file_name": os.path.basename(pdf_path),
                "file_path": pdf_path,
                "error": str(e),
                "success": False,
            }
    
    def extract_from_directory(self) -> List[dict]:
        """
        从目录中提取所有 PDF 文本
        
        Returns:
            List[dict]: 所有 PDF 文件的提取结果列表
        """
        if not os.path.exists(self.input_dir):
            logger.error(f"输入目录不存在: {self.input_dir}")
            return []
        
        # 获取所有 PDF 文件
        pdf_files = [
            f for f in os.listdir(self.input_dir)
            if f.lower().endswith('.pdf')
        ]
        
        if not pdf_files:
            logger.warning(f"未找到 PDF 文件: {self.input_dir}")
            return []
        
        logger.info(f"找到 {len(pdf_files)} 个 PDF 文件")
        
        results = []
        for pdf_file in sorted(pdf_files):
            pdf_path = os.path.join(self.input_dir, pdf_file)
            result = self.extract_from_file(pdf_path)
            results.append(result)
        
        return results
    
    def save_extracted_text(self, result: dict, output_dir: Optional[str] = None) -> Optional[str]:
        """
        保存提取的文本到文件
        
        Args:
            result: PDF 提取结果
            output_dir: 输出目录
            
        Returns:
            保存的文本文件路径，失败返回 None
        """
        if not result.get("success"):
            logger.error(f"无法保存失败的提取结果: {result.get('file_name')}")
            return None
        
        output_dir = output_dir or settings.output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件名
        base_name = os.path.splitext(result["file_name"])[0]
        txt_path = os.path.join(output_dir, f"{base_name}.txt")
        
        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(result["full_text"])
            logger.info(f"文本已保存: {txt_path}")
            return txt_path
        except Exception as e:
            logger.error(f"保存文本失败 {txt_path}: {e}")
            return None


def main():
    """测试 PDF 提取功能"""
    extractor = PDFExtractor()
    results = extractor.extract_from_directory()
    
    for result in results:
        if result["success"]:
            print(f"\n文件: {result['file_name']}")
            print(f"页数: {result['page_count']}")
            print(f"文本长度: {len(result['full_text'])} 字符")
            print(f"文本预览: {result['full_text'][:200]}...")
            
            # 保存提取的文本
            txt_path = extractor.save_extracted_text(result)
            if txt_path:
                print(f"已保存到: {txt_path}")


if __name__ == "__main__":
    main()
