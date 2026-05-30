import os

def read_js_file(file_path):
    """Đọc file và trả về string để Agent phân tích (Bước 2)"""
    if not os.path.exists(file_path):
        msg = f" Lỗi: Không tìm thấy file tại: {file_path}"
        print(msg)
        return msg

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            print(f" Đã đọc file: {os.path.basename(file_path)}")
            return content
    except Exception as e:
        return f" Lỗi đọc file: {str(e)}"

def save_test_file(content, output_path):
    """Lưu code test (Bước 3/6/9/12). Quan trọng: Trả về string cho Agent."""
    directory = os.path.dirname(output_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        print(f" Đã tạo thư mục: {directory}")

    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(content)
        success_msg = f" Đã lưu file thành công tại: {output_path}"
        print(success_msg)
        return success_msg
    except Exception as e:
        return f" Lỗi lưu file: {str(e)}"