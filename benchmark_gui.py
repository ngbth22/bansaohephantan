#!/usr/bin/env python3
"""
benchmark_gui.py - Trình khởi chạy nhanh Giao diện đồ họa Benchmark Mã hóa Mạng.

Cách chạy:
python benchmark_gui.py
"""

import os
import sys

# Đảm bảo đường dẫn gốc của project và thư mục benchmark luôn nằm ở đầu sys.path
# để Python có thể import đúng các module liên quan mà không phụ thuộc vào thư mục làm việc hiện tại
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
BENCH_DIR = os.path.join(ROOT_DIR, "benchmark")
if BENCH_DIR not in sys.path:
    sys.path.insert(0, BENCH_DIR)

if __name__ == "__main__":
    try:
        # Cố gắng import hàm main từ module benchmark.gui hoặc gui
        try:
            from benchmark.gui import main
        except ImportError:
            from gui import main
        # Khởi động ứng dụng giao diện Benchmark GUI
        main()
    except Exception as exc:
        import traceback
        err_msg = traceback.format_exc()
        
        # Ghi vết lỗi (traceback) ra file error_log.txt để người dùng tiện tra cứu khi gặp sự cố
        log_path = os.path.join(ROOT_DIR, "error_log.txt")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(err_msg)
        except Exception:
            pass

        # Hiển thị hộp thoại thông báo lỗi native trên Windows qua Win32 API
        # (rất hữu ích khi người dùng click đúp file .py mà không mở terminal)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Không thể khởi động Giao diện Benchmark!\n\nChi tiết lỗi:\n{err_msg}\n\nThông tin lỗi đã được lưu vào: error_log.txt",
                "Lỗi Khởi Động Benchmark GUI",
                0x10,  # MB_ICONERROR: Biểu tượng dấu X đỏ cảnh báo lỗi nghiêm trọng
            )
        except Exception:
            pass
        raise
