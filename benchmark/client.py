"""
client.py - Sender Benchmark Client.

Chay tren Sender (VM1):
python benchmark/client.py --host 192.168.1.2 --port 5000 --output benchmark/results/benchmark_results.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import socket
import sys
import time

import psutil

proc = psutil.Process()

from common import (
    AES_KEY,
    ALGO_AES_128_CBC,
    ALGO_CAESAR,
    ALGO_NONE,
    ALGO_PLAYFAIR,
    ALGORITHMS,
    BENCHMARK_RUNS,
    CAESAR_SHIFT,
    PLAYFAIR_KEY,
    SIZES,
    WARMUP_RUNS,
    generate_plaintext,
    recv_ack,
    send_frame,
)
import aes_cbc
import caesar
import playfair


def run_benchmark(
    host: str = "127.0.0.1",
    port: int = 5000,
    output_csv: str = "benchmark/results/benchmark_results.csv",
    seed: int | None = 42,
    algorithms: list[str] | None = None,
    sizes: list[int] | None = None,
    benchmark_runs: int = BENCHMARK_RUNS,
    warmup_runs: int = WARMUP_RUNS,
    progress_callback: any = None,
    stop_requested: any = None,
) -> str:
    """
    Thực hiện toàn bộ kịch bản đo kiểm (benchmark):
    - Sinh danh sách các tổ hợp (thuật toán, kích thước payload).
    - Trộn ngẫu nhiên (shuffle) thứ tự tổ hợp 1 lần duy nhất để tránh sai số đo lường (systematic bias).
    - Với mỗi tổ hợp: chạy warm-up (khởi động) + các lượt đo chính thức.
    - Đo đạc thời gian mã hóa, giải mã, kiểm tra toàn vẹn, RTT mạng, CPU%, RAM (RSS).
    - Ghi dữ liệu chi tiết ra file CSV.
    """
    # Đảm bảo thư mục cha chứa file CSV kết quả đã tồn tại trên đĩa
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)

    # Nếu không truyền danh sách thuật toán/kích thước tùy chọn, dùng danh sách mặc định trong common.py
    active_algos = algorithms if algorithms is not None else ALGORITHMS
    active_sizes = sizes if sizes is not None else SIZES

    # 1. Tạo danh sách tất cả các cặp tổ hợp (Algorithm, Size) bằng list comprehension
    combinations = [(algo, sz) for algo in active_algos for sz in active_sizes]
    
    # Thiết lập seed ngẫu nhiên cố định để kết quả xáo trộn có tính tái lập (reproducible)
    if seed is not None:
        random.seed(seed)
    # Shuffle thứ tự kiểm thử để tránh hiện tượng đo tuần tự gây thiên lệch nhiệt độ CPU hoặc đệm mạng
    random.shuffle(combinations)

    # Tính toán tổng số lượt chạy (bao gồm cả khởi động warm-up và đo chính)
    total_executions = len(combinations) * (warmup_runs + benchmark_runs)
    total_analysis_samples = len(combinations) * benchmark_runs

    print("============================================================")
    print("  KHOI DONG BENCHMARK MA HOA MANG SENDER -> RECEIVER")
    print(f"  Dich den: {host}:{port}")
    print(f"  Tong to hop: {len(combinations)} | Warm-up/to hop: {warmup_runs} | Mau/to hop: {benchmark_runs}")
    print(f"  Tong thuc thi: {total_executions} luot")
    print(f"  Mau phan tich: {total_analysis_samples} mau")
    print("============================================================")
    print("Thu tu chay cac to hop sau khi shuffle:")
    for idx, (algo, sz) in enumerate(combinations, 1):
        print(f"  {idx:02d}. {algo:12s} - {sz // 1024:4d} KB ({sz} B)")
    print("------------------------------------------------------------")

    # 2. Khởi tạo socket TCP/IP và kết nối tới máy chủ Receiver
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    # Bật cờ TCP_NODELAY: tắt thuật toán Nagle để gói tin nhỏ được gửi đi ngay lập tức,
    # tránh độ trễ tích lũy 40ms giả tạo khi đo đạc RTT mạng
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    csv_rows = []           # Danh sách lưu kết quả của từng lượt đo chính để ghi vào CSV
    run_id_counter = 1      # Mã định danh tăng dần cho từng lượt đo chính
    executed_counter = 0    # Đếm tổng số lượt chạy (cả warmup lẫn test chính) cho thanh tiến độ

    try:
        total_combo = len(combinations)
        for c_idx, (algo, size_bytes) in enumerate(combinations, 1):
            # Kiểm tra nếu người dùng bấm nút Hủy / Dừng trên giao diện GUI
            if stop_requested and stop_requested():
                print("[*] Nhan tin hieu dung tu nguoi dung.")
                break

            print(f"\n>>> [To hop {c_idx:02d}/{total_combo:02d}] {algo} - {size_bytes} Byte")

            # A. Warm-up run (Lượt chạy khởi động):
            # Mục đích: Làm nóng cache CPU, nạp module/thư viện vào RAM, và ổn định socket TCP.
            # Dữ liệu của các lượt warm-up này hoàn toàn KHÔNG được đưa vào thống kê phân tích.
            for w_idx in range(warmup_runs):
                if stop_requested and stop_requested():
                    break
                plain = generate_plaintext(size_bytes)
                if algo == ALGO_NONE:
                    cipher_bytes = plain.encode("utf-8")
                    packet_bytes = cipher_bytes
                elif algo == ALGO_CAESAR:
                    cipher_str = caesar.encrypt(plain, CAESAR_SHIFT)
                    cipher_bytes = cipher_str.encode("utf-8")
                    packet_bytes = cipher_bytes
                elif algo == ALGO_PLAYFAIR:
                    cipher_str = playfair.encrypt(plain, PLAYFAIR_KEY)
                    cipher_bytes = cipher_str.encode("utf-8")
                    packet_bytes = cipher_bytes
                elif algo == ALGO_AES_128_CBC:
                    iv = os.urandom(16)
                    cipher_bytes = aes_cbc.encrypt(plain, AES_KEY, iv)
                    # Gói tin AES gửi kèm IV (16 bytes) ở đầu để Receiver dùng giải mã
                    packet_bytes = iv + cipher_bytes

                # Gửi frame với cờ is_warmup=True để Receiver biết và bỏ qua thống kê
                send_frame(sock, algo, size_bytes, 0, True, packet_bytes)
                recv_ack(sock)
                executed_counter += 1
                if progress_callback:
                    progress_callback({
                        "is_warmup": True,
                        "current_run": executed_counter,
                        "total_runs": total_executions,
                        "combo_idx": c_idx,
                        "total_combos": total_combo,
                        "algo": algo,
                        "size_bytes": size_bytes,
                        "row": None,
                    })
                print(f"    [Warm-up OK] Da chay xong 1 luot khoi dong cho {algo} {size_bytes}B")

            # B. Các lượt đo lường chính thức (Benchmark runs):
            # Dữ liệu thu thập từ các lượt này sẽ được lưu vào file CSV để phân tích thống kê.
            for m_idx in range(1, benchmark_runs + 1):
                if stop_requested and stop_requested():
                    break
                # Sinh dữ liệu chuỗi giả lập tuần tự xác định theo kích thước (đảm bảo tính nhất quán)
                plain = generate_plaintext(size_bytes)

                # 1. Đo lường thời gian mã hóa (encryption_ms), mức chiếm dụng CPU và RAM
                # Lấy dung lượng RAM hiện tại (RSS - Resident Set Size) trước khi mã hóa
                m_before = proc.memory_info().rss
                # Đo thời gian CPU thực tế (chỉ tính chu kỳ CPU tiêu tốn cho tiến trình này)
                p_enc_start = time.process_time()
                # Đo thời gian đồng hồ vật lý (wall-clock) độ phân giải nano giây
                t_enc_start = time.perf_counter()

                if algo == ALGO_NONE:
                    # Không mã hóa: chỉ chuyển chuỗi văn bản thành mảng byte UTF-8
                    cipher_bytes = plain.encode("utf-8")
                    packet_bytes = cipher_bytes
                elif algo == ALGO_CAESAR:
                    # Mã hóa Caesar cổ điển theo bước dịch CAESAR_SHIFT
                    cipher_str = caesar.encrypt(plain, CAESAR_SHIFT)
                    cipher_bytes = cipher_str.encode("utf-8")
                    packet_bytes = cipher_bytes
                elif algo == ALGO_PLAYFAIR:
                    # Mã hóa ma trận Playfair 5x5
                    cipher_str = playfair.encrypt(plain, PLAYFAIR_KEY)
                    cipher_bytes = cipher_str.encode("utf-8")
                    packet_bytes = cipher_bytes
                elif algo == ALGO_AES_128_CBC:
                    # Mã hóa hiện đại AES-128 ở chế độ CBC với IV ngẫu nhiên 16 bytes
                    iv = os.urandom(16)
                    cipher_bytes = aes_cbc.encrypt(plain, AES_KEY, iv)
                    # Gói tin truyền mạng bao gồm: 16 bytes IV + ciphertext đã mã hóa
                    packet_bytes = iv + cipher_bytes
                else:
                    raise ValueError(f"Thuat toan khong hop le: {algo}")

                t_enc_end = time.perf_counter()
                p_enc_end = time.process_time()
                m_after = proc.memory_info().rss

                # Tính toán thời gian mã hóa (đổi sang mili-giây ms)
                encryption_ms = (t_enc_end - t_enc_start) * 1000.0
                cpu_time_ms = (p_enc_end - p_enc_start) * 1000.0
                # Tỷ lệ % CPU sử dụng = (thời gian CPU / thời gian thực tế) * 100%
                enc_cpu_pct = round(min(100.0, (cpu_time_ms / encryption_ms * 100.0)), 1) if encryption_ms > 0 else 0.0
                # Dung lượng RAM tiến trình (MB) và mức tăng thêm (Delta KB)
                enc_ram_mb = round(m_after / (1024.0 * 1024.0), 2)
                enc_ram_delta_kb = round(max(0.0, (m_after - m_before) / 1024.0), 1)

                ciphertext_size_bytes = len(cipher_bytes)
                packet_size_bytes = len(packet_bytes)

                # 2. Gửi packet qua mạng TCP và chờ nhận gói ACK phản hồi từ Receiver
                # Đo Round-Trip Time (RTT): từ lúc bắt đầu gửi gói tin cho tới khi nhận trọn vẹn ACK
                t_send = time.perf_counter()
                send_frame(sock, algo, size_bytes, run_id_counter, False, packet_bytes)
                (
                    decrypt_ms,
                    verify_ms,
                    success,
                    dec_cpu_pct,
                    dec_ram_mb,
                    dec_ram_delta_kb,
                ) = recv_ack(sock)
                t_ack = time.perf_counter()

                # Thời gian khứ hồi mạng (RTT) bao gồm cả thời gian truyền gói + xử lý trên receiver + gửi ACK về
                rtt_ms = (t_ack - t_send) * 1000.0

                # 3. Tính toán tổng thời gian hoàn tất:
                # ĐẶC BIỆT LƯU Ý KHI THUYẾT TRÌNH:
                # total_ms = encryption_ms + rtt_ms
                # Lý do: Trong thời gian rtt_ms, Receiver đã thực hiện decrypt_ms và verify_ms.
                # Do đó, decrypt_ms là một phần thời gian nằm BÊN TRONG rtt_ms.
                # Không được cộng dồn decrypt_ms vào total_ms vì sẽ bị tính trùng lặp 2 lần (double-counting).
                total_ms = encryption_ms + rtt_ms
                
                # Thông lượng (Throughput) tính bằng KB/giây
                throughput_kbps = (size_bytes / 1024.0) / (total_ms / 1000.0) if total_ms > 0 else 0.0

                # Lưu toàn bộ 18 chỉ số đo lường vào từ điển hàng CSV
                row = {
                    "run_id": run_id_counter,
                    "algorithm": algo,
                    "size_bytes": size_bytes,
                    "ciphertext_size_bytes": ciphertext_size_bytes,
                    "packet_size_bytes": packet_size_bytes,
                    "encryption_ms": round(encryption_ms, 4),
                    "decrypt_ms": round(decrypt_ms, 4),
                    "verify_ms": round(verify_ms, 4),
                    "rtt_ms": round(rtt_ms, 4),
                    "total_ms": round(total_ms, 4),
                    "throughput_kbps": round(throughput_kbps, 2),
                    "enc_cpu_pct": enc_cpu_pct,
                    "dec_cpu_pct": round(dec_cpu_pct, 1),
                    "enc_ram_mb": enc_ram_mb,
                    "dec_ram_mb": round(dec_ram_mb, 2),
                    "enc_ram_delta_kb": enc_ram_delta_kb,
                    "dec_ram_delta_kb": round(dec_ram_delta_kb, 1),
                    "success": success,
                }
                csv_rows.append(row)
                executed_counter += 1
                if progress_callback:
                    progress_callback({
                        "is_warmup": False,
                        "current_run": executed_counter,
                        "total_runs": total_executions,
                        "combo_idx": c_idx,
                        "total_combos": total_combo,
                        "algo": algo,
                        "size_bytes": size_bytes,
                        "row": row,
                    })

                # In ra terminal log định kỳ mỗi 10 lượt đo hoặc ở lượt cuối cùng
                if m_idx % 10 == 0 or m_idx == benchmark_runs:
                    print(
                        f"    Run {m_idx:02d}/{benchmark_runs} (ID:{run_id_counter:03d}) | "
                        f"Enc: {encryption_ms:6.2f}ms | Dec: {decrypt_ms:6.2f}ms | "
                        f"RTT: {rtt_ms:6.2f}ms | Tot: {total_ms:6.2f}ms | "
                        f"CPU: {enc_cpu_pct:4.1f}%/{dec_cpu_pct:4.1f}% | "
                        f"RAM: {enc_ram_mb:4.1f}M/{dec_ram_mb:4.1f}M | "
                        f"TP: {throughput_kbps:8.1f} KB/s | Success: {success}"
                    )

                run_id_counter += 1

    finally:
        # Luôn luôn đóng socket kết nối TCP giải phóng tài nguyên mạng ngay cả khi gặp lỗi
        sock.close()

    # 3. Ghi dữ liệu kết quả đo vào file CSV theo đúng chuẩn 18 cột
    fieldnames = [
        "run_id",                 # Mã số lượt đo
        "algorithm",              # Tên thuật toán: None, Caesar, Playfair, AES-128-CBC
        "size_bytes",             # Kích thước payload gốc (Bytes)
        "ciphertext_size_bytes",  # Kích thước ciphertext sau mã hóa
        "packet_size_bytes",      # Kích thước gói tin truyền mạng (bao gồm IV nếu có)
        "encryption_ms",          # Thời gian mã hóa (ms)
        "decrypt_ms",             # Thời gian giải mã tại Receiver (ms)
        "verify_ms",              # Thời gian kiểm tra toàn vẹn chuỗi tại Receiver (ms)
        "rtt_ms",                 # Round-Trip Time mạng (ms)
        "total_ms",               # Tổng thời gian: encryption_ms + rtt_ms (ms)
        "throughput_kbps",        # Thông lượng hệ thống (KB/s)
        "enc_cpu_pct",            # % CPU tiêu tốn khi mã hóa trên Sender
        "dec_cpu_pct",            # % CPU tiêu tốn khi giải mã trên Receiver
        "enc_ram_mb",             # Dung lượng RAM tiến trình Sender (MB)
        "dec_ram_mb",             # Dung lượng RAM tiến trình Receiver (MB)
        "enc_ram_delta_kb",       # Mức tăng RAM tức thời khi mã hóa (KB)
        "dec_ram_delta_kb",       # Mức tăng RAM tức thời khi giải mã (KB)
        "success",                # Kết quả xác minh khớp dữ liệu (True/False)
    ]
    if len(csv_rows) > 0:
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print("------------------------------------------------------------")
        print(f"[+] Hoan tat benchmark! Da luu {len(csv_rows)} mau vao: {output_csv}")
    return output_csv


if __name__ == "__main__":
    # Cấu hình đối số dòng lệnh khi chạy độc lập qua terminal
    parser = argparse.ArgumentParser(description="Sender Benchmark Client")
    parser.add_argument("--host", default="127.0.0.1", help="Dia chi IP cua Receiver (mac dinh: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Cong TCP cua Receiver (mac dinh: 5000)")
    parser.add_argument(
        "--output",
        default="benchmark/results/benchmark_results.csv",
        help="Duong dan file CSV xuat ket qua",
    )
    parser.add_argument("--seed", type=int, default=42, help="Seed ngau nhien cho shuffle (mac dinh: 42)")
    args = parser.parse_args()

    # Bắt đầu chạy benchmark bằng tham số dòng lệnh
    run_benchmark(args.host, args.port, args.output, args.seed)
