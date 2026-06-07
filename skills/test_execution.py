import subprocess
import os

class TestExecutionAgent:
    def __init__(self, frontend_dir):
        # Lưu đường dẫn tuyệt đối tới thư mục chứa code React (nơi có file package.json)
        self.frontend_dir = os.path.abspath(frontend_dir)

    def execute(self, test_file_relative_path):
        """
        Tool dành cho AutoGen: Chạy file test và xuất báo cáo Coverage dạng JSON.
        TRẢ VỀ KẾT QUẢ VÀ LOG CHO PIPELINE XỬ LÝ, KHÔNG TỰ LƯU FILE.
        """
        print(f"[INFO] Bat dau chay file test: {test_file_relative_path}...")
        
        command_str = (
            f"node --no-warnings --experimental-vm-modules node_modules/jest/bin/jest.js "
            f"{test_file_relative_path} --color=false --watchAll=false "
            f"--coverage --json --outputFile=coverage_report.json"
        )

        try:
            result = subprocess.run(
                command_str,
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                shell=True,
                encoding='utf-8',
                errors='replace' 
            )

            stdout_clean = result.stdout if result.stdout else ""
            stderr_clean = result.stderr if result.stderr else ""
            output = stdout_clean + "\n" + stderr_clean

            if result.returncode == 0:
                print("[SUCCESS] TUYET VOI! Bai test da PASS 100%!")
                # Chỉ trả về kết quả
                return True, output
            else:
                print("[FAILED] CANH BAO! Bai test co loi (FAIL)!")
                return False, output

        except Exception as e:
            print(f"[ERROR] Loi he thong khi chay Terminal: {e}")
            return False, str(e)
