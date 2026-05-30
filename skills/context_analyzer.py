import os
from file_utils import read_js_file

class ContextAnalyzerAgent:
    def __init__(self):
        pass

    def get_source_code(self, source_code_path):
        """
        Tool dành cho AutoGen: Đọc và trả về nội dung file mã nguồn gốc từ dự án đích.
        """
        print(f"🔍 [INFO] Đang đọc và phân tích mã nguồn từ: {source_code_path}...")
        source_code = read_js_file(source_code_path)
        
        if not source_code:
            return f"[ERROR] Không thể đọc mã nguồn từ {source_code_path}"
            
        return source_code