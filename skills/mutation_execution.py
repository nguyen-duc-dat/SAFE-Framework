import subprocess
import os

class MutationExecutionAgent:
    def __init__(self, frontend_dir):
        self.frontend_dir = os.path.abspath(frontend_dir)

    def execute_stryker(self, source_file):
        """
        Tool dành cho AutoGen: Kích hoạt Stryker chỉ cho đúng file đang test.
        """
        rel_source_path = os.path.relpath(source_file, self.frontend_dir).replace("\\", "/")
        
        print(f"[INFO] Bat dau kich hoat Stryker cho file: {rel_source_path}...")
        print(f"[INFO] Qua trinh nay co the mat 1-2 phut de Stryker tao va chay cac Mutant.")
        
        # --- XÓA FILE BÁO CÁO CŨ ĐỂ TRÁNH ĐỌC NHẦM RÁC ---
        report_path = os.path.join(self.frontend_dir, "reports", "mutation", "mutation.json")
        if os.path.exists(report_path):
            try:
                os.remove(report_path)
            except Exception as e:
                print(f"[WARNING] Khong the xoa file report cu: {e}")
        

        # test_file_path = rel_source_path.replace('.jsx', '.test.jsx').replace('.js', '.test.js') 
        command_str = f'npx stryker run stryker.conf.json --mutate "{rel_source_path}" --concurrency 1'
        
        try:
            result = subprocess.run(
                command_str,
                cwd=self.frontend_dir,
                capture_output=True,
                text=True,
                shell=True,
                env=os.environ,
                encoding='utf-8',
                errors='replace'
            )

            # Lấy cả 2 luồng: stdout và stderr
            stdout = result.stdout if result.stdout else ""
            stderr = result.stderr if result.stderr else ""
            
            # Kiểm tra xem Stryker có thực sự tạo ra file JSON mới hay không
            if os.path.exists(report_path):
                print("\n[SUCCESS] Stryker da chay xong!")
                print(f"[INFO] Da sinh ra file bao cao tai: {report_path}")
                
                lines = stdout.split('\n')
                score_log = '\n'.join(lines[-15:])
                print("\n--- KET QUA STRYKER ---")
                print(score_log)
                
                return f"[SUCCESS] Đã chạy Stryker xong. Báo cáo được tạo tại: {report_path}\nKết quả Score:\n{score_log}"
            else:
                print("\n[FAILED] Stryker chay loi, khong the tao file mutation.json!")
                print("\n--- CHI TIET LOI ---")
                full_log = stdout + "\n--- LỖI (STDERR) ---\n" + stderr
                error_log = full_log[-1500:] if len(full_log) > 1500 else full_log
                print(error_log) 
                return f"[FAILED] Lỗi khi chạy Stryker.\nLog:\n{error_log}"

        except Exception as e:
            error_msg = f"[ERROR] Loi he thong khi chay Terminal: {e}"
            print(error_msg)
            return f"[FAILED] {error_msg}"