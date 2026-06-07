import json
import os

class MutationRefinerAgent:
    def __init__(self, mutation_json_path):
        # Nạp đường dẫn động từ Pipeline
        self.mutation_json_path = os.path.abspath(mutation_json_path)

    def get_mutation_context(self, source_path, test_path):
        """
        Tool dành cho AutoGen: Đọc file report của Stryker để tìm các Mutant còn sống
        và CHỈ trả về danh sách text (Tránh duplicate source code gây nổ token).
        """
        if not os.path.exists(self.mutation_json_path):
            print(f"[ERROR] Không tìm thấy file JSON báo cáo Mutation: {self.mutation_json_path}")
            return ""

        with open(self.mutation_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        target_file_name = os.path.basename(source_path)
        survived_list = []
        
        # Bóc tách JSON của Stryker
        for file_path, file_data in data.get('files', {}).items():
            if target_file_name in file_path:
                for mutant in file_data.get('mutants', []):
                    if mutant['status'] in ['Survived', 'NoCoverage']:
                        line = mutant['location']['start']['line']
                        mutator = mutant['mutatorName']
                        replacement = mutant.get('replacement', 'N/A')
                        survived_list.append(f"- Dòng {line} | Loại lỗi: {mutator} | Code bị đột biến thành: '{replacement}'")
        
        # Nếu đã diệt sạch Mutant, trả về rỗng để Pipeline kết thúc sớm
        if not survived_list:
            return ""
            
        # CHỈ trả về danh sách Mutant, tuyệt đối không nối thêm Source Code
        return "\n".join(survived_list)