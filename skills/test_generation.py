import os
# Chỉ cần import hàm lưu file vì không cần đọc source code ở đây nữa (AutoGen đã đọc ở bước Context)
from file_utils import save_test_file

class TestGenerationAgent:
    def __init__(self):
        pass

    def clean_code_output(self, raw_text):
        """Hàm dọn dẹp: Cắt bỏ các dấu tick (```javascript) nếu AI lỡ viết vào"""
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split('\n')
            if len(lines) > 0 and lines[0].startswith("```"):
                lines = lines[1:] # Bỏ dòng đầu
            if len(lines) > 0 and lines[-1].startswith("```"):
                lines = lines[:-1] # Bỏ dòng cuối
            return "\n".join(lines).strip()
        return text

    def process_and_save(self, raw_ai_code, output_test_path):
        """
        Tool dành cho AutoGen: Nhận chuỗi code do LLM sinh ra, dọn dẹp và lưu vào ổ cứng.
        """
        print(f"[INFO] Dang don dep va luu code test vao: {output_test_path}...")

        # 1. Dọn dẹp code thô từ AutoGen
        clean_code = self.clean_code_output(raw_ai_code)
        
        if not clean_code:
            print("[ERROR] Code thô trống rỗng, không thể lưu.")
            return "Lưu thất bại: Code AI trả về trống."

        # 2. Gọi hàm tiện ích để lưu file
        is_saved = save_test_file(clean_code, output_test_path)
        
        if is_saved:
            print(f"[SUCCESS] Da luu file test tai: {output_test_path}")
            return f"Lưu thành công tại {output_test_path}"
        else:
            return "Lưu thất bại do lỗi hệ thống (File IO)."
