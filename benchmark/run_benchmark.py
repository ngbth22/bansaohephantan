"""
run_benchmark.py - Trinh dieu phoi toan bo quy trinh Benchmark:
1. Kiem tra mang / ping test toi Receiver (neu la IP tu xa).
2. Khoi dong server ngam (neu chay che do local) hoac ket noi server VM2.
3. Chay 12 to hop x (1 warm-up + 30 do chinh) = 372 luot.
4. Luu 360 mau phan tich vao CSV.
5. Chay phan tich thong ke pandas va sinh 6 bieu do matplotlib.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time

# Them duong dan hien tai vao sys.path
BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BENCH_DIR)

import analyze
import client
import common
import server


def perform_ping_test(host: str, count: int = 4) -> bool:
    """
    Kiểm tra độ trễ mạng và tỷ lệ mất gói (packet loss) bằng lệnh ping của hệ điều hành.
    Tự động nhận diện hệ điều hành: Windows dùng cờ '-n', Linux/macOS dùng cờ '-c'.
    """
    import platform
    print(f"[*] Dang thuc hien Ping test toi {host} ({count} goi tin) ...", flush=True)
    try:
        flag = "-n" if platform.system().lower() == "windows" else "-c"
        cmd = ["ping", flag, str(count), host]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        lines = []
        for line in proc.stdout:
            print(line, end="", flush=True)
            lines.append(line)
        proc.wait(timeout=count * 3)
        out = "".join(lines).lower()
        if "0% loss" in out or "0% packet loss" in out or "0.0% packet loss" in out:
            print("[+] Ping test hoan hao: 0% mat goi.\n", flush=True)
            return True
        elif "100% loss" in out or "100% packet loss" in out or "unreachable" in out:
            print("[!] CANH BAO: Khong ping duoc toi host. Vui long kiem tra firewall hoac cau hinh mang!\n", flush=True)
            return False
        else:
            print("[!] CANH BAO: Co hien tuong mat goi. Kiem tra lai adapter mang Bridge/Host-Only.\n", flush=True)
            return True
    except Exception as exc:
        print(f"[!] Khong the thuc hien ping: {exc}\n", flush=True)
        return True


def run_full_pipeline(
    host: str = "127.0.0.1",
    port: int = 5000,
    results_dir: str = "benchmark/results",
    seed: int = 42,
    is_local: bool | None = None,
    clean: bool = False,
    no_ping: bool = False,
) -> None:
    """
    Hàm điều phối toàn diện quy trình đo kiểm và sinh báo cáo:
    1. Chuẩn hóa đường dẫn thư mục lưu trữ kết quả.
    2. Tự động nhận diện chế độ: Local (chạy Server ngầm) hoặc Remote (kết nối máy ảo VM2).
    3. Thực hiện benchmark đo lường toàn bộ các tổ hợp.
    4. Xử lý số liệu thống kê bằng thư viện pandas (Mean, Std, Median, Min, Max).
    5. Xuất 8 biểu đồ phân tích trực quan bằng matplotlib (300 DPI).
    6. Sinh báo cáo tổng hợp Markdown kèm bảng tỷ lệ cải thiện/chênh lệch.
    """
    # Chuẩn hóa results_dir: Nếu người dùng đang đứng trong thư mục benchmark và để mặc định "benchmark/results"
    # thì chuyển thành "results" để tránh tạo lồng "benchmark/benchmark/results".
    current_dir = os.path.abspath(os.getcwd())
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if results_dir == "benchmark/results" and current_dir == script_dir:
        results_dir = os.path.join(script_dir, "results")

    # Tạo thư mục đích nếu chưa có
    os.makedirs(results_dir, exist_ok=True)
    if clean:
        # Nếu bật cờ clean, xóa sạch toàn bộ file CSV, Markdown và ảnh biểu đồ cũ
        deleted, locked = common.clear_benchmark_results(results_dir)
        print(f"[*] Da xoa {len(deleted)} tep ket qua va anh bieu do cu trong {results_dir}")
        if locked:
            print(f"[!] Canh bao: {len(locked)} tep dang bi khoa khong the xoa: {', '.join(locked)}")

    # Xác định đường dẫn các file đầu ra
    csv_file = os.path.join(results_dir, "benchmark_results.csv")
    charts_dir = os.path.join(results_dir, "charts")
    summary_md = os.path.join(results_dir, "summary_table.md")

    # Tự động phát hiện chế độ hoạt động:
    # Nếu host là 127.0.0.1 / localhost -> chế độ Self-test (tự khởi động Server trong luồng nền)
    # Nếu host là IP mạng lan/VM khác -> chế độ Remote (kết nối trực tiếp tới Receiver)
    clean_host = host.strip() if host else "127.0.0.1"
    if is_local is None:
        is_local = clean_host.lower() in ("127.0.0.1", "localhost")

    server_thread = None
    stop_event = threading.Event()

    if is_local:
        print("[*] Che do SELF-TEST (LOCAL): Tu dong khoi dong Receiver Server noi bo tren luong nen ...")
        # Khởi chạy server Receiver trong một luồng daemon chạy ngầm
        def start_bg_server():
            server.run_server(host="127.0.0.1", port=port, stop_event=stop_event)

        server_thread = threading.Thread(target=start_bg_server, daemon=True)
        server_thread.start()
        time.sleep(0.5)  # Nghỉ 0.5s để socket server kịp bind và listen
    else:
        print(f"[*] Che do REMOTE: Ket noi toi Receiver tai {clean_host}:{port} (khong bat server noi bo) ...")
        # Chạy kiểm tra Ping trước khi bắt đầu đo đạc qua mạng thật
        if not no_ping:
            perform_ping_test(clean_host, count=4)

    # 1. Khởi chạy tiến trình Benchmark Client
    t_start = time.perf_counter()
    client.run_benchmark(
        host=clean_host,
        port=port,
        output_csv=csv_file,
        seed=seed,
    )
    total_duration = time.perf_counter() - t_start

    print(f"\n[+] Thoi gian thuc hien toan bo 372 luot benchmark: {total_duration:.2f} giay.")

    # 2. Phân tích dữ liệu thống kê và vẽ 8 biểu đồ khoa học
    print("\n[*] Dang phan tich du lieu bang pandas va tao bieu do matplotlib ...")
    # Đọc và xác thực cấu trúc file CSV
    df = analyze.load_and_validate(csv_file)
    # Tính toán các chỉ số thống kê (Mean, Median, Std, Min, Max)
    df_rates, df_stats = analyze.compute_statistics(df)
    # Xuất 8 biểu đồ chuẩn IEEE / Scientific (300 DPI)
    analyze.generate_charts(df_stats, charts_dir)
    # Xuất bảng tổng kết báo cáo định dạng Markdown
    analyze.export_markdown_summary(df_rates, df_stats, summary_md)

    print("\n============================================================")
    print("  HOAN TAT TOAN BO TIEN TRINH BENCHMARK!")
    print(f"  - File CSV:      {csv_file}")
    print(f"  - Bang ket qua:  {summary_md}")
    print(f"  - 8 Bieu do:     {charts_dir}")
    print("============================================================")


if __name__ == "__main__":
    # Cấu hình bộ phân tích tham số dòng lệnh CLI
    parser = argparse.ArgumentParser(description="Master Benchmark Orchestrator")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Dia chi IP cua Receiver (mac dinh: 127.0.0.1 -> tu chay self-test; neu la IP khac -> tu dong chuyen sang remote)",
    )
    parser.add_argument("--port", type=int, default=5000, help="Cong TCP (mac dinh: 5000)")
    parser.add_argument("--results-dir", default="benchmark/results", help="Thu muc luu ket qua")
    parser.add_argument("--seed", type=int, default=42, help="Seed ngau nhien")
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Cuong che che do remote (khong bat server noi bo du la 127.0.0.1)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Xoa toan bo ket qua cu (CSV, MD va anh bieu do) truoc khi chay lan moi",
    )
    parser.add_argument(
        "--no-ping",
        action="store_true",
        help="Bo qua buoc ping kiem tra mang truoc khi do",
    )
    parser.add_argument("--gui", action="store_true", help="Mo giao dien do hoa Benchmark GUI")
    args = parser.parse_args()

    # Nếu người dùng truyền cờ --gui, khởi chạy giao diện Benchmark Dashboard Qt
    if args.gui:
        import gui
        gui.main()
        sys.exit(0)

    # Nếu người dùng truyền flag --remote rõ ràng, cưỡng chế is_local=False, ngược lại để hàm tự xác định theo --host
    is_local_flag = False if args.remote else None

    # Khởi động toàn bộ pipeline
    run_full_pipeline(
        host=args.host,
        port=args.port,
        results_dir=args.results_dir,
        seed=args.seed,
        is_local=is_local_flag,
        clean=args.clean,
        no_ping=args.no_ping,
    )
