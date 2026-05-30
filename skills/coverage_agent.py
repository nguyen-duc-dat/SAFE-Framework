import json
import os

class CoverageAgent:
    def __init__(self, coverage_json_path):
        self.coverage_json_path = os.path.abspath(coverage_json_path)

    def _get_missing_analysis(self, target_file_name):
        """Đọc JSON, tính điểm SonarQube và tìm nhánh thiếu"""
        if not os.path.exists(self.coverage_json_path):
            return None
        
        with open(self.coverage_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        target_data = next((v for k, v in data.items() if target_file_name in k), None)
        if not target_data: return None

        # 1. Tính toán Dòng thực thi (Lines/Statements)
        s_data = target_data.get('s', {})
        total_lines = len(s_data)
        covered_lines = sum(1 for count in s_data.values() if count > 0)

        # 2. Tính toán Nhánh (Branches)
        b_data = target_data.get('b', {})
        total_branches = 0
        covered_branches = 0
        missing_logic = []

        # Istanbul JSON chia nhánh thành các mảng (paths), tương đương (2 * B) trong SonarQube
        for idx, counts in b_data.items():
            total_branches += len(counts)
            for i, count in enumerate(counts):
                if count > 0:
                    covered_branches += 1
                else:
                    line = target_data['branchMap'][idx]['line']
                    missing_logic.append(f"- Dòng {line}: Nhánh điều kiện số {i+1} (True/False) chưa được thực thi.")

        # 3. Áp dụng Công thức SonarQube: Coverage = (Covered Branches + Covered Lines) / (Total Branches + Total Lines)
        denominator = total_branches + total_lines
        sonar_score = (covered_branches + covered_lines) / denominator if denominator > 0 else 1.0
        
        # Nếu đạt Quality Gate 80%, trả về cờ để bỏ qua
        if sonar_score >= 0.8:
            return "COVERAGE_PASSED"

        # Nếu < 80%, lập báo cáo để ép AI tập trung diệt Branch
        score_percent = round(sonar_score * 100, 2)
        report = f"[SONARQUBE QUALITY GATE] Điểm Coverage tổng hợp: {score_percent}% (Ngưỡng yêu cầu: 80%).\n"
        report += f"Chi tiết: Phủ {covered_lines}/{total_lines} dòng (LC/EL) | Phủ {covered_branches}/{total_branches} nhánh (CT+CF / 2B).\n"
        report += "BẮT BUỘC bổ sung test case cho các nhánh logic sau để tăng gấp đôi trọng số điểm:\n"
        report += "\n".join(missing_logic)
        
        return report

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

    def get_coverage_context(self, source_path, test_path):
        """Tool 1 (AutoGen): Đọc coverage, nếu thiếu thì trả về context để AI viết bù."""
        file_name = os.path.basename(source_path)
        missing_logic = self._get_missing_analysis(file_name)

        if not missing_logic:
            return f"COVERAGE_100: File {file_name} không tìm thấy thông tin thiếu."
            
        if missing_logic == "COVERAGE_PASSED":
            return f"COVERAGE_100: File {file_name} đã vượt ngưỡng SonarQube Quality Gate (>= 80%)."

        print(f"[INFO] Phat hien chua dat SonarQube Quality Gate:\n{missing_logic}")

        try:
            with open(source_path, 'r', encoding='utf-8') as f: source_code = f.read()
            with open(test_path, 'r', encoding='utf-8') as f: test_code = f.read()
        except Exception as e:
            return f"[ERROR] Loi doc file source/test: {e}"

        context = (
            f"--- MA NGUON GOC ---\n{source_code}\n\n"
            f"--- FILE TEST HIEN TAI ---\n{test_code}\n\n"
            f"--- YÊU CẦU NÂNG CẤP (SONARQUBE) ---\n{missing_logic}"
        )
        return context
    
    def append_test_cases(self, raw_ai_code, test_path):
        """
        Tool 2 (AutoGen): Chèn đoạn code test bổ sung vào file test hiện tại.
        """
        new_test_code = self.clean_code_output(raw_ai_code)
        
        if not new_test_code:
            return "[ERROR] Code AI sinh ra trong rong."

        try:
            with open(test_path, 'r', encoding='utf-8') as f:
                original_test = f.read()

            # THỰC HIỆN CHÈN (APPEND) VÀO FILE TEST
            # Tìm dấu ngoặc đóng cuối cùng của describe block (thường là '});')
            last_bracket = original_test.rfind('});')
            
            if last_bracket != -1:
                updated_test = (
                    original_test[:last_bracket] + 
                    "\n  // --- AI ADDED FOR COVERAGE ---\n" + 
                    new_test_code + 
                    "\n" + 
                    original_test[last_bracket:]
                )
                with open(test_path, 'w', encoding='utf-8') as f:
                    f.write(updated_test)
                
                print(f"[SUCCESS] Da chen them test case moi vao: {test_path}")
                return "Đã chèn test case bổ sung thành công."
            else:
                return "[ERROR] Khong tim thay cau truc describe block '});' de chen code."
        except Exception as e:
            return f"[ERROR] Loi khi chen file: {e}"

