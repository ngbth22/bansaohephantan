"""
server.py - Receiver Benchmark Server.

Chay tren Receiver (VM2):
python benchmark/server.py --host 0.0.0.0 --port 5000
"""

from __future__ import annotations

import argparse
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
    CAESAR_SHIFT,
    PLAYFAIR_KEY,
    generate_plaintext,
    recv_frame,
    send_ack,
)
import aes_cbc
import caesar
import playfair


def handle_client(client_sock: socket.socket, addr: tuple[str, int]) -> None:
    """
    Xử lý một phiên kết nối benchmark nhận dữ liệu từ Sender:
    - Lặp nhận từng khung tin (frame) qua giao thức nhị phân chuẩn hóa.
    - Đo đạc thời gian giải mã (decrypt_ms), mức CPU% và RAM RSS tiêu tốn.
    - So sánh đối chiếu chuỗi giải mã với dữ liệu mẫu gốc (verify_ms) để kiểm tra toàn vẹn.
    - Đóng gói gửi ACK phản hồi chứa toàn bộ thông số về cho Sender.
    """
    print(f"[*] Ket noi benchmark moi tu {addr[0]}:{addr[1]}")
    # Bật TCP_NODELAY trên socket chấp nhận để gói tin ACK 41 bytes được gửi đi tức thì,
    # loại bỏ hoàn toàn hiện tượng Nagle / Delayed-ACK deadlock làm sai lệch RTT
    try:
        client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except OSError:
        pass
    count = 0
    try:
        while True:
            # Nhận frame từ socket client. Nếu socket bị ngắt hoặc kết thúc thì thoát vòng lặp
            try:
                algo, size_bytes, run_id, is_warmup, packet_data = recv_frame(client_sock)
            except (ConnectionError, EOFError, OSError):
                break

            # 1. Đo lường thời gian giải mã, CPU tiêu tốn và biến động bộ nhớ RAM
            m_before = proc.memory_info().rss
            p_dec_start = time.process_time()
            t_dec_start = time.perf_counter()
            decryption_success = True
            plain = ""
            try:
                if algo == ALGO_NONE:
                    # Không mã hóa: giải mã chuỗi UTF-8 nguyên bản
                    plain = packet_data.decode("utf-8")
                elif algo == ALGO_CAESAR:
                    # Giải mã Caesar với bước dịch CAESAR_SHIFT
                    plain = caesar.decrypt(packet_data.decode("utf-8"), CAESAR_SHIFT)
                elif algo == ALGO_PLAYFAIR:
                    # Giải mã Playfair qua ma trận 5x5
                    plain = playfair.decrypt(packet_data.decode("utf-8"), PLAYFAIR_KEY)
                elif algo == ALGO_AES_128_CBC:
                    # AES-128-CBC: Tách 16 bytes đầu tiên làm IV (Vector khởi tạo)
                    iv = packet_data[:16]
                    # Phần byte còn lại là Ciphertext đã qua padding PKCS#7
                    cipher_bytes = packet_data[16:]
                    plain = aes_cbc.decrypt(cipher_bytes, AES_KEY, iv)
                else:
                    decryption_success = False
            except Exception as exc:
                decryption_success = False
                print(f"[!] Loi giai ma {algo} run {run_id}: {exc}")
            
            t_dec_end = time.perf_counter()
            p_dec_end = time.process_time()
            m_after = proc.memory_info().rss

            # Thời gian giải mã thực tế (ms)
            decrypt_ms = (t_dec_end - t_dec_start) * 1000.0
            cpu_time_ms = (p_dec_end - p_dec_start) * 1000.0
            # % CPU = (thời gian CPU tiến trình / thời gian thực tế) * 100%
            dec_cpu_pct = round(min(100.0, (cpu_time_ms / decrypt_ms * 100.0)), 1) if decrypt_ms > 0 else 0.0
            # RAM hiện tại (MB) và mức RAM tăng thêm (Delta KB)
            dec_ram_mb = round(m_after / (1024.0 * 1024.0), 2)
            dec_ram_delta_kb = round(max(0.0, (m_after - m_before) / 1024.0), 1)

            # 2. Đo thời gian kiểm tra toàn vẹn (verify_ms):
            # Tái sinh chuỗi mẫu chuẩn (ground-truth) và so sánh từng ký tự để đảm bảo dữ liệu giải mã chính xác 100%
            t_ver_start = time.perf_counter()
            verify_success = False
            if decryption_success:
                expected_plain = generate_plaintext(size_bytes)
                verify_success = (plain == expected_plain)
            verify_ms = (time.perf_counter() - t_ver_start) * 1000.0

            total_success = decryption_success and verify_success

            # 3. Gửi gói tin ACK về Sender chứa toàn bộ thông số phía Receiver
            send_ack(
                client_sock,
                decrypt_ms,
                verify_ms,
                total_success,
                dec_cpu_pct=dec_cpu_pct,
                dec_ram_mb=dec_ram_mb,
                dec_ram_delta_kb=dec_ram_delta_kb,
            )
            count += 1

            label = "WARMUP" if is_warmup else f"RUN {run_id:03d}"
            status = "OK" if total_success else "FAIL"
            if count % 10 == 0 or is_warmup:
                print(
                    f"[{label}] {algo:12s} | {size_bytes:7d}B | "
                    f"Dec: {decrypt_ms:6.2f}ms | CPU: {dec_cpu_pct:4.1f}% | RAM: {dec_ram_mb:4.1f}MB | {status}"
                )
    finally:
        client_sock.close()
        print(f"[*] Dong ket noi voi {addr[0]}:{addr[1]}. Da phuc vu {count} luot.")


def run_server(
    host: str = "0.0.0.0",
    port: int = 5000,
    stop_event: any = None,
    log_callback: any = None,
) -> None:
    """
    Khởi chạy TCP Server lắng nghe các lượt benchmark:
    - Gán socket vào địa chỉ host:port (mặc định 0.0.0.0:5000 lắng nghe tất cả các card mạng).
    - Hỗ trợ cờ SO_REUSEADDR để khởi động lại nhanh mà không bị lỗi cổng bận (Address already in use).
    - Sử dụng timeout 0.5s trên accept() để có thể nhận tín hiệu dừng (stop_event) từ UI luồng chính một cách mượt mà.
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # SO_REUSEADDR cho phép tái sử dụng cổng TCP ngay lập tức sau khi dừng server (bỏ qua trạng thái TIME_WAIT)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(5)
    # Đặt timeout cho accept() để vòng lặp không bị chặn vĩnh viễn, kiểm tra stop_event định kỳ 500ms
    server_sock.settimeout(0.5)

    msg = f"RECEIVER BENCHMARK SERVER DANG CHAY TAI {host}:{port}"
    print("============================================================")
    print(f"  {msg}")
    print("============================================================")
    if log_callback:
        log_callback(f"[+] {msg}")

    try:
        while True:
            # Kiểm tra xem giao diện GUI có yêu cầu dừng server hay không
            if stop_event and stop_event.is_set():
                break
            try:
                client_sock, addr = server_sock.accept()
            except socket.timeout:
                # Hết 0.5s chưa có kết nối thì lặp lại để kiểm tra cờ stop_event
                continue
            except OSError:
                break

            if log_callback:
                log_callback(f"[*] Ket noi benchmark moi tu {addr[0]}:{addr[1]}")
            # Xử lý kết nối benchmark của client
            handle_client(client_sock, addr)
    except KeyboardInterrupt:
        print("\n[*] Nguoi dung yeu cau dung server.")
    finally:
        # Giải phóng socket lắng nghe của server
        server_sock.close()
        if log_callback:
            log_callback("[*] Server da dung lang nghe.")


if __name__ == "__main__":
    # Phân tích đối số dòng lệnh khi chạy server độc lập
    parser = argparse.ArgumentParser(description="Receiver Benchmark Server")
    parser.add_argument("--host", default="0.0.0.0", help="Dia chi IP lang nghe (mac dinh: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Cong TCP (mac dinh: 5000)")
    args = parser.parse_args()

    # Bắt đầu vòng lặp phục vụ benchmark
    run_server(args.host, args.port)
