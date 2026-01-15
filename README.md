# Sora Automation Tool v1.57

Tool tự động hóa tương tác với Sora (sora.com) để tạo video/hình ảnh từ prompt.

## Tính năng

- ✅ Đọc prompts từ file Excel
- ✅ Tự động nhập prompt và tạo nội dung
- ✅ Hỗ trợ tạo video và hình ảnh
- ✅ Tùy chỉnh tỉ lệ khung hình, thời lượng, độ phân giải
- ✅ Lưu profile đăng nhập
- ✅ Chế độ Headless (chạy ẩn)
- ✅ Cập nhật trạng thái vào Excel

## Cài đặt

1. Cài Python 3.9+
2. Cài dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Chạy tool:
   ```bash
   python main.py
   ```

## Sử dụng

1. Click "Tạo Template" để tạo file Excel mẫu
2. Điền prompts vào file Excel
3. Click "Duyệt" để chọn file Excel
4. Click "Load Tasks" để đọc danh sách tasks
5. Click "Bắt đầu" để chạy

## Cấu trúc file Excel

| Cột | Mô tả |
|-----|-------|
| Prompt | Nội dung prompt để tạo |
| Type | `video` hoặc `image` |
| AspectRatio | `16:9`, `9:16`, `1:1` |
| Duration | `5s`, `10s`, `15s`, `20s` (cho video) |
| Resolution | `480p`, `720p`, `1080p` |
| Variations | Số lượng biến thể |
| OutputPath | Đường dẫn lưu file (tùy chọn) |
| Status | Trạng thái xử lý |
| Result | Kết quả |

## Build thành .exe

```bash
pip install pyinstaller
python build.py
```

Output sẽ nằm trong thư mục `dist/Sora157/`

## Cấu trúc thư mục

```
Sora157_source/
├── main.py              # Entry point
├── build.py             # Script đóng gói
├── requirements.txt     # Dependencies
├── README.md           
├── config/
│   ├── __init__.py
│   └── settings.py      # Cấu hình
├── core/
│   ├── __init__.py
│   ├── browser.py       # Quản lý browser
│   ├── excel_handler.py # Xử lý Excel
│   └── sora_automation.py # Tự động hóa Sora
├── gui/
│   ├── __init__.py
│   └── main_window.py   # Giao diện PyQt5
└── data/
    ├── profiles/        # Lưu profile browser
    └── output/          # Output mặc định
```

## Lưu ý

- Lần đầu chạy cần đăng nhập thủ công vào Sora
- Profile sẽ được lưu để không cần đăng nhập lại
- Nên để delay giữa các task để tránh bị chặn
# new-sora
