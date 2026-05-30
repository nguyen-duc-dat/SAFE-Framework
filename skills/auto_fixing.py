import os
from file_utils import read_js_file, save_test_file

class AutoFixingAgent:
    def __init__(self):
        # Đã loại bỏ genai.GenerativeModel và API Key
        pass

    def clean_code_output(self, raw_text):
        """Hàm dọn dẹp: Cắt bỏ các dấu tick (```javascript) nếu AI lỡ viết vào"""
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.split('\n')
            if len(lines) > 0 and lines[0].startswith("```"):
                lines = lines[1:]
            if len(lines) > 0 and lines[-1].startswith("```"):
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return text

    def get_error_context(self, source_code_path, test_code_path, error_log_path):
        """
        Tool 1 (AutoGen): Đọc file hiện trường và đóng gói thành 1 thông điệp hoàn chỉnh.
        """
        source_code = read_js_file(source_code_path)
        test_code = read_js_file(test_code_path)

        try:
            with open(error_log_path, 'r', encoding='utf-8') as f:
                error_log = f.read()
        except Exception as e:
            return f"[ERROR] Khong the doc file log: {e}"

        # --- TỰ ĐỘNG NHẬN DIỆN LỖI REQUIRE (Giữ nguyên logic tuyệt vời của cậu) ---
        extra_info = ""
        if "require is not defined" in error_log:
            extra_info = "\n[LUU Y QUAN TRONG TU HE THONG]: Loi 'require is not defined' do chay ESM. Hay dat tat ca lenh jest.mock() len tren cung file, TRUOC KHI import module can test.\n"

        context = (
            f"{extra_info}\n"
            f"--- MA NGUON ---\n{source_code}\n\n"
            f"--- TEST LOI HIEN TAI ---\n{test_code}\n\n"
            f"--- LOG LOI TU JEST ---\n{error_log}"
        )
        return context

    def process_and_save_fix(self, raw_ai_code, test_code_path, error_log_path):
        """
        Tool 2 (AutoGen): Dọn dẹp code, lưu đè file test và dọn dẹp file log.
        """
        clean_code = self.clean_code_output(raw_ai_code)
        
        if not clean_code:
            return "[ERROR] Code AI sinh ra trong rong."

        if save_test_file(clean_code, test_code_path):
            print(f"[SUCCESS] Da luu ban va loi tai: {test_code_path}")
            
            # Xóa file log cũ vì đã sửa xong (Giữ nguyên logic dọn dẹp của cậu)
            if os.path.exists(error_log_path):
                os.remove(error_log_path)
                print(f"[INFO] Da don dep file log cu: {error_log_path}")
                
            return "Sửa lỗi và lưu file thành công."
        else:
            return "[ERROR] Khong the luu file test do loi he thong."
