import os
import sys
import autogen
import shutil
import time
import argparse
import json 
from datetime import datetime
from dotenv import load_dotenv

# --- [PHẦN 0] SETUP PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
project_root = os.path.abspath(os.path.join(parent_dir, ".."))

for path in [parent_dir, os.path.join(parent_dir, "skills")]:
    if path not in sys.path:
        sys.path.append(path)


from skills.context_analyzer import ContextAnalyzerAgent
from skills.test_generation import TestGenerationAgent
from skills.test_execution import TestExecutionAgent
from skills.auto_fixing import AutoFixingAgent
from skills.coverage_agent import CoverageAgent
from skills.mutation_execution import MutationExecutionAgent
from skills.mutation_refiner import MutationRefinerAgent

# --- [PHẦN 1] LOAD ENV & CONFIG ---
load_dotenv(dotenv_path=os.path.join(parent_dir, ".env"))
api_keys = [ os.getenv("GEMINI_API_KEY_1"),
            os.getenv("GEMINI_API_KEY_2"),
            os.getenv("GEMINI_API_KEY_3"),
            os.getenv("GEMINI_API_KEY_4"),
            os.getenv("GEMINI_API_KEY_5"),
            os.getenv("GEMINI_API_KEY_6"),
            os.getenv("GEMINI_API_KEY_7"),
            os.getenv("GEMINI_API_KEY_8")
             ]
# Lọc bỏ những giá trị None nếu khai báo thiếu
valid_keys = [key for key in api_keys if key]

# Tạo config_list chứa nhiều cấu hình
config_list = []
for key in valid_keys:
    config_list.append({
        "model": "gemini-2.5-flash", 
        "api_key": key,
        "api_type": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/"
    })

llm_config = {
    "config_list": config_list,
    "temperature": 0.1,
    "cache_seed": None,
    "max_retries": 7, # tự động retry khi hết token
}

# ==TRỘN PROMPT ===
def get_rule(file_name, frontend_dir=None):
    rule_path = os.path.join(parent_dir, "rules", file_name)
    with open(rule_path, 'r', encoding='utf-8') as f:
        prompt_content = f.read()

    if not frontend_dir:
        return prompt_content

    config_path = os.path.join(frontend_dir, "autef.config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as cf:
                user_config = json.load(cf)

            for key, value in user_config.items():
                placeholder = f"{{{key}}}"
                if placeholder in prompt_content:
                    if isinstance(value, list):
                        value = "- " + "\n- ".join(value)
                    prompt_content = prompt_content.replace(placeholder, str(value))
        except Exception as e:
            print(f"[CẢNH BÁO] Lỗi đọc file autef.config.json: {e}")

    return prompt_content
# =========================================================================

def log_time(msg):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")

# HÀM GỌI API 
def fast_chat(agent, message):
    try:
        log_time(f" Gửi request tới {agent.name}...")
        user_proxy.initiate_chat(agent, message=message, max_turns=1, summary_method="last_msg", silent=True)
        time.sleep(30) 
        return user_proxy.last_message(agent)["content"]
    except Exception as e:
        print(f"\n LỖI TRÍ MẠNG KHI GỌI API: {str(e)}")
        print("=> HƯỚNG GIẢI QUYẾT: API Key đã hết Quota hoặc mất mạng. Hãy thay API Key mới vào file .env rồi chạy lại!")
        sys.exit(1)

# [PHẦN 2 INIT AGENTS CHUYỂN XUỐNG CUỐI FILE]

# --- [PHẦN 3] PIPELINE 13 BƯỚC ---
def run_full_pipeline(source_file):
    source_file = source_file.replace("\\", "/")
    file_name = os.path.basename(source_file)
    file_base = file_name.split('.')[0]
    base_path, ext = os.path.splitext(source_file)
    test_path = f"{base_path}.test{ext}"

    rel_test_path = os.path.relpath(test_path, FRONTEND_DIR).replace("\\", "/")

    print(f"\n{'='*20} [STEP 1: INPUT] BẮT ĐẦU XỬ LÝ {file_name} {'='*20}")

    # --- BƯỚC 2: ANALYST ---
    plan_path = os.path.join(OUTPUT_DIR, "test_plans", f"{file_base}_plan.md") 
    if os.path.exists(plan_path):
        log_time(" Dùng file Plan Cache (Bỏ qua Analyst).")
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_content = f.read()
    else:
        source_code = ctx_tool.get_source_code(source_file)
        plan_content = fast_chat(analyst, f"Phân tích mã nguồn và trả về Kế hoạch kiểm thử:\n\n{source_code}")
        
        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(plan_content)
        log_time(" Đã lưu Kế hoạch kiểm thử vào kho Artifacts.")

    # --- BƯỚC 3: CODER ---
    log_time("Đang sinh Test Code...")
    source_code = ctx_tool.get_source_code(source_file) 
    
    coder_input = f"""
    TÊN FILE GỐC: {file_name}
    TEST PLAN:
    {plan_content}
    SOURCE CODE:
    {source_code}
    """
    test_code = fast_chat(coder, coder_input)
    gen_tool.process_and_save(test_code, test_path)
    log_time(" Đã lưu file Test.")

    # --- BƯỚC 4-7: EXECUTION & AUTO-FIXING ---
    is_pass = False
    max_fixes = 90

    for i in range(max_fixes + 1):
        log_time(f" Chạy Jest lần {i+1}...")
        is_pass, jest_output = exe_tool.execute(rel_test_path)

        log_status = "PASS" if is_pass else "FAIL"
        current_log_path = os.path.join(OUTPUT_DIR, "execution_logs", f"{file_base}_Jest_{log_status}_Lan_{i+1}.log")
        
        with open(current_log_path, "w", encoding="utf-8") as f:
            f.write(str(jest_output) if jest_output else "[HỆ THỐNG] Không nhận được Log từ Terminal.")
        
        if is_pass:
            log_time(" [STEP 7] TEST PASS 100%!")
            break 
            
        if i < max_fixes:
            log_time(f"Test Fail. Chuyển Fixer sửa (Lần {i+1})...")
            error_context = fix_tool.get_error_context(source_file, test_path, current_log_path)
            fixer_prompt = f"Tên file gốc: '{file_name}'. CẤM ĐỔI ĐUÔI FILE IMPORT. Sửa test dựa trên log (Chỉ trả code):\n\n{error_context}"
            fixed_code = fast_chat(fixer, fixer_prompt)            
            fix_tool.process_and_save_fix(fixed_code, test_path, current_log_path)
        else:
            log_time(" Đã dùng hết quyền trợ giúp từ Fixer nhưng test vẫn FAIL.")

    if not is_pass:
        log_time(" [CẢNH BÁO] Test vẫn FAIL. Dừng pipeline!")
        return

    # --- BƯỚC 8-9: COVERAGE ENHANCEMENT (SONARQUBE) & SELF-HEALING ---
    log_time(" Kiểm tra mức độ phủ code theo chuẩn SonarQube (Quality Gate >= 80%)...")
    coverage_context = cov_tool.get_coverage_context(source_file, test_path)
    
    if not coverage_context or "COVERAGE_100" in coverage_context:
        log_time(" Quality Gate Passed (Coverage >= 80%). Bỏ qua CovExpert.")
    elif len(coverage_context) > 50:
        log_time(" Điểm Coverage chưa đạt ngưỡng 80%. Nhờ CovExpert đánh mạnh vào các nhánh (Branch)...")
        
        with open(test_path, 'r', encoding='utf-8') as f:
            backup_test_code = f.read()

        cov_prompt = f"Phân tích báo cáo SonarQube sau và viết thêm các khối it() để phủ các nhánh (Branch) còn thiếu. CHỈ TRẢ VỀ CODE CỦA KHỐI it(), TUYỆT ĐỐI KHÔNG GIẢI THÍCH, KHÔNG BỌC MARKDOWN:\n\n{coverage_context}"
        cov_code = fast_chat(cov_expert, cov_prompt)
        
        append_status = cov_tool.append_test_cases(cov_code, test_path)
        
        if "[ERROR]" in append_status:
            log_time(f" [LỖI] Không thể chèn code Coverage: {append_status}")
        else:
            log_time(" Đã chèn kịch bản Coverage mới! ĐANG CHẠY JEST ĐỂ KIỂM DUYỆT...")

            is_verify_pass, verify_log = exe_tool.execute(rel_test_path)
            
            if not is_verify_pass:
                log_time(" [CẢNH BÁO] CovExpert viết code lỗi! Kích hoạt Fixer để cứu viện...")
                
                max_rescue = 2
                for r in range(max_rescue):
                    log_time(f" Fixer đang xử lý lỗi Coverage (Lần {r+1}/{max_rescue})...")
                    
                    rescue_log_path = os.path.join(OUTPUT_DIR, "execution_logs", f"{file_base}_Cov_Rescue_Lần_{r+1}.log")
                    with open(rescue_log_path, "w", encoding="utf-8") as f:
                        f.write(verify_log)
                    
                    error_context = fix_tool.get_error_context(source_file, test_path, rescue_log_path)
                    fixer_prompt = f"Tên file: {file_name}. Code test bị lỗi sau khi thêm nhánh Coverage. Sửa test dựa trên log (Chỉ trả code hoàn chỉnh):\n\n{error_context}"
                    fixed_code = fast_chat(fixer, fixer_prompt)
                    
                    fix_tool.process_and_save_fix(fixed_code, test_path, rescue_log_path)
                    
                    is_verify_pass, verify_log = exe_tool.execute(rel_test_path)
                    if is_verify_pass:
                        log_time(" Fixer đã cứu viện thành công! Bộ test lại XANH mượt.")
                        break 
                
                if not is_verify_pass:
                    log_time(" [THẤT BẠI] Fixer bất lực. Kích hoạt Rollback bảo vệ file gốc.")
                    with open(test_path, 'w', encoding='utf-8') as f:
                        f.write(backup_test_code)
            else:
                log_time(" Xác thực Jest thành công ngay lần đầu! Mức độ phủ (SonarQube) đã tăng lên đáng kể.")
    else:
        log_time(" Báo cáo thiếu không hợp lệ. Bỏ qua.")

    # --- BƯỚC 10-12: MUTATION TESTING ---
    log_time(" Đang khởi tạo cấu hình Stryker động (Dynamic Isolation Config)...")
    
    rel_source_path = os.path.relpath(source_file, FRONTEND_DIR).replace("\\", "/")
    
    stryker_config_path = os.path.join(FRONTEND_DIR, "stryker.conf.json")
    dynamic_stryker_config = {
        "mutate": [rel_source_path],
        "testRunner": "jest",
        "jest": {
            "projectType": "custom",
            "configFile": "jest.config.cjs",
            "enableFindRelatedTests": False,
            "config": {
                "testMatch": [f"<rootDir>/{rel_test_path}"] 
            }
        },
        "reporters": ["progress", "clear-text", "json", "html"],
        "concurrency": 1,
        "ignoreStatic": True,
        "testRunnerNodeArgs": ["--experimental-vm-modules", "--max-old-space-size=4096", "--no-warnings"]
    }
    
    with open(stryker_config_path, "w", encoding="utf-8") as f:
        json.dump(dynamic_stryker_config, f, indent=2)
        
    log_time(" Đã cấu hình xong Stryker. Bắt đầu chiến dịch tiêu diệt Mutant!")
    
    max_mutation_loops = 2
    for mut_loop in range(max_mutation_loops):
        log_time(f" Chạy Stryker Mutation Testing (Lần {mut_loop + 1})...")
        stryker_status = mut_exe_tool.execute_stryker(source_file)
        
        if "[FAILED]" in stryker_status:
            log_time(" [LỖI] Stryker không thể khởi động! Dừng vòng lặp Mutation.")
            break 
            
        mutation_context = mut_ref_tool.get_mutation_context(source_file, test_path)
        
        if not mutation_context or len(mutation_context) < 50:
            log_time(" Đã tiêu diệt hết Mutant hoặc không có lỗi đột biến.")
            break
            
        if mut_loop == max_mutation_loops - 1:
            log_time(" Đã chạy hết giới hạn vòng lặp Mutation. Chuyển sang Report.")
            break

        log_time(" Nhờ MutHunter tiêu diệt Mutant còn sống...")
        
        source_code = ctx_tool.get_source_code(source_file)
        with open(test_path, 'r', encoding='utf-8') as f:
            current_test_code = f.read()
            backup_test_code = current_test_code 
            
        raw_mut_prompt = get_rule("prompt_mutation.txt", FRONTEND_DIR) # [ĐÃ SỬA] Nạp config
        mut_prompt = raw_mut_prompt.replace("{file_name}", file_name) \
                                   .replace("{source_code}", source_code) \
                                   .replace("{current_test_code}", current_test_code) \
                                   .replace("{mutation_context}", mutation_context)
                                   
        mut_code = fast_chat(mut_hunter, mut_prompt)
        mut_code = mut_code.replace("```javascript", "").replace("```jsx", "").replace("```js", "").replace("```", "").strip()

        log_time(" Đang tiến hành chèn kịch bản mới vào file test...")
        last_closing_index = current_test_code.rfind('});') 
        
        if last_closing_index != -1:
            new_test_code = current_test_code[:last_closing_index] + "\n\n" + mut_code + "\n" + current_test_code[last_closing_index:]
            with open(test_path, 'w', encoding='utf-8') as f:
                f.write(new_test_code)
            log_time(" Đã chèn code thành công! ĐANG CHẠY JEST ĐỂ KIỂM DUYỆT...")
        else:
            log_time(" [CẢNH BÁO] Không tìm thấy dấu đóng khối describe. Bỏ qua việc chèn code.")
            break 

        is_verify_pass, verify_log = exe_tool.execute(rel_test_path)
        
        if not is_verify_pass:
            log_time(" [CẢNH BÁO] MutHunter viết code lỗi! Kích hoạt Fixer để cấp cứu...")
            
            max_rescue = 2
            for r in range(max_rescue):
                log_time(f"Fixer đang cố gắng sửa lỗi (Lần {r+1}/{max_rescue})...")
                
                rescue_log_path = os.path.join(OUTPUT_DIR, "execution_logs", f"{file_base}_Mut_Rescue_{r+1}.log")
                with open(rescue_log_path, "w", encoding="utf-8") as f:
                    f.write(verify_log)
                
                error_context = fix_tool.get_error_context(source_file, test_path, rescue_log_path)
                fixer_prompt = f"Tên file: {file_name}. Code test bị lỗi sau khi bổ sung kịch bản Mutation. Hãy sửa test dựa trên log (Chỉ trả code hoàn chỉnh):\n\n{error_context}"
                fixed_code = fast_chat(fixer, fixer_prompt)
                
                fix_tool.process_and_save_fix(fixed_code, test_path, rescue_log_path)
                
                is_verify_pass, verify_log = exe_tool.execute(rel_test_path)
                if is_verify_pass:
                    log_time(" Fixer đã cấp cứu thành công! Bộ test lại XANH mượt.")
                    break 
            
            if not is_verify_pass:
                log_time(" [THẤT BẠI] Fixer bất lực. Bắt buộc Rollback để bảo vệ Stryker.")
                with open(test_path, 'w', encoding='utf-8') as f:
                    f.write(backup_test_code)
                break 
        else:
            log_time(" Xác thực Jest thành công ngay lần đầu! Sẵn sàng cho Stryker Lần 2.")

    # --- BƯỚC 13: REPORT & BACKUP ARTIFACTS ---
    print(f"\n [STEP 13] FINAL REPORT: Đang đóng gói Artifacts cho {file_name}...")

    file_report_dir = os.path.join(OUTPUT_DIR, "reports", file_base)
    os.makedirs(file_report_dir, exist_ok=True)

    if os.path.exists(test_path):
        dest_test_path = os.path.join(OUTPUT_DIR, "test_scripts", f"{file_base}.test{ext}")
        shutil.copy2(test_path, dest_test_path)
        log_time(f" Đã sao chép file kiểm thử: {dest_test_path}")

    source_coverage = os.path.join(FRONTEND_DIR, "coverage")
    if os.path.exists(source_coverage):
        shutil.copytree(source_coverage, os.path.join(file_report_dir, "coverage"), dirs_exist_ok=True)
        log_time(" Đã sao lưu Báo cáo Coverage.")

    source_mutation = os.path.join(FRONTEND_DIR, "reports", "mutation")
    if os.path.exists(source_mutation):
        shutil.copytree(source_mutation, os.path.join(file_report_dir, "mutation"), dirs_exist_ok=True)
        log_time(" Đã sao lưu Báo cáo Mutation.")

    print(f"\n{'='*20} HOÀN TẤT AUTEF PIPELINE {'='*20}")
    print(f"Toàn bộ kết quả (Logs, Code, Reports) đã được lưu trữ an toàn tại:\n📁 {OUTPUT_DIR}")

# --- [PHẦN CUỐI] GIAO DIỆN DÒNG LỆNH (CLI)---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AUTEF - Hệ thống Kiểm thử Tự động hóa bằng LLM (Phiên bản Đa Dự Án)",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument("-p", "--project", type=str, required=True, help="[BẮT BUỘC] Đường dẫn tuyệt đối đến thư mục gốc của dự án frontend cần test")
    parser.add_argument("-f", "--files", nargs='+', type=str, help="Đường dẫn TƯƠNG ĐỐI đến 1 hoặc nhiều file")
    parser.add_argument("-d", "--dir", type=str, help="Quét toàn bộ một thư mục con")
    parser.add_argument("--all", action="store_true", help="Kích hoạt test toàn bộ dự án")
    
    args = parser.parse_args()

    # ================= 1. KHỞI TẠO MÔI TRƯỜNG ĐỘNG =================
    FRONTEND_DIR = os.path.abspath(args.project)

    if not os.path.exists(FRONTEND_DIR):
        print(f"[LỖI TRÍ MẠNG] Không tìm thấy thư mục dự án: {FRONTEND_DIR}")
        sys.exit(1)

    print(f"[MÔI TRƯỜNG] Đã nạp dự án mục tiêu: {FRONTEND_DIR}")

    # SAU KHI BIẾT FRONTEND_DIR, MỚI BẮT ĐẦU TẠO OUTPUT_DIR VÀ FOLDERS BÊN TRONG
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR = os.path.join(os.path.dirname(FRONTEND_DIR), "autef_outputs_global", f"run_{timestamp}")

    os.makedirs(os.path.join(OUTPUT_DIR, "test_plans"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "execution_logs"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "test_scripts"), exist_ok=True)

    # ================= 1.5. KHỞI TẠO ĐỘI NGŨ AI (Đã nạp Config người dùng) =================
    global user_proxy, analyst, coder, fixer, cov_expert, mut_hunter
    
    user_proxy = autogen.UserProxyAgent(
        name="Admin", human_input_mode="NEVER", code_execution_config=False, llm_config=False
    )

    analyst = autogen.AssistantAgent("Analyst", system_message=get_rule("prompt_analyzer.txt", FRONTEND_DIR), llm_config=llm_config)
    coder = autogen.AssistantAgent("Coder", system_message=get_rule("prompt_coder.txt", FRONTEND_DIR), llm_config=llm_config)
    fixer = autogen.AssistantAgent("Fixer", system_message=get_rule("prompt_fixer.txt", FRONTEND_DIR), llm_config=llm_config)
    cov_expert = autogen.AssistantAgent("CovExpert", system_message=get_rule("prompt_coverage.txt", FRONTEND_DIR), llm_config=llm_config)
    mut_hunter = autogen.AssistantAgent("MutHunter", system_message=get_rule("prompt_mutation.txt", FRONTEND_DIR), llm_config=llm_config)

    # ================= 2. KHỞI TẠO CÁC TOOL VỚI ĐƯỜNG DẪN MỚI =================
    ctx_tool = ContextAnalyzerAgent()
    gen_tool = TestGenerationAgent()
    exe_tool = TestExecutionAgent(FRONTEND_DIR)
    fix_tool = AutoFixingAgent()
    cov_tool = CoverageAgent(os.path.join(FRONTEND_DIR, "coverage", "coverage-final.json"))
    mut_exe_tool = MutationExecutionAgent(FRONTEND_DIR)
    mut_ref_tool = MutationRefinerAgent(os.path.join(FRONTEND_DIR, "reports", "mutation", "mutation.json"))

    # ================= 3. QUÉT VÀ THU THẬP FILE =================
    files_to_process = []

    if args.files:
        for rel_path in args.files:
            target = os.path.join(FRONTEND_DIR, rel_path)
            if os.path.exists(target):
                files_to_process.append(target)
            else:
                print(f"[LỖI] Không tìm thấy file: {target}")

    elif args.dir or args.all:
        folder_to_scan = "src" if args.all else args.dir
        target_dir = os.path.join(FRONTEND_DIR, folder_to_scan)
        
        if os.path.exists(target_dir):
            print(f"Đang quét thư mục: {folder_to_scan}...")
            for root, _, files in os.walk(target_dir):
                for file in files:
                    if (file.endswith('.js') or file.endswith('.jsx')) and not file.endswith('.test.js') and not file.endswith('.test.jsx'):
                        files_to_process.append(os.path.join(root, file))
        else:
            print(f"[LỖI] Không tìm thấy thư mục: {target_dir}")
    else:
        parser.print_help()
        sys.exit(0)

    # ================= 4. KHỞI ĐỘNG =================
    if not files_to_process:
        print("Không tìm thấy file mã nguồn nào hợp lệ để kiểm thử.")
    else:
        print(f"\n🚀 [HỆ THỐNG ĐÃ KHỞI ĐỘNG] TÌM THẤY {len(files_to_process)} FILE CẦN XỬ LÝ!")
        
        for index, file_path in enumerate(files_to_process, 1):
            print(f"\n{'='*50}")
            print(f"TIẾN TRÌNH TỔNG: Đang xử lý file {index}/{len(files_to_process)}")
            print(f"TARGET: {os.path.basename(file_path)}")
            print(f"{'='*50}")
            
            run_full_pipeline(file_path)
            
        print("\n🎉🎉🎉 ĐÃ HOÀN TẤT KIỂM THỬ TẤT CẢ FILE CỦA DỰ ÁN! 🎉🎉🎉")