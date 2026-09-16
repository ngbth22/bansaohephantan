"""
common.py - Cac tham so, ham sinh du lieu tat dinh va giao thuc truyen tin benchmark.
"""

from __future__ import annotations

import os
import socket
import struct
import sys

# Them thu muc goc vao sys.path de import cac module thuat toan
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENDER_DIR = os.path.join(BASE_DIR, "sender")
RECEIVER_DIR = os.path.join(BASE_DIR, "receiver")

if SENDER_DIR not in sys.path:
    sys.path.insert(0, SENDER_DIR)

import aes_cbc
import caesar
import config
import playfair

# 4 thuat toan danh gia hieu nang
ALGO_NONE = "None"                # Truyen tin thuan tuy khong ma hoa (Baseline kiem chung)
ALGO_CAESAR = "Caesar"            # Ma hoa dich chuyen co dien (k=3)
ALGO_PLAYFAIR = "Playfair"        # Ma hoa ma tran 5x5 co dien (khoa 'MONARCHY')
ALGO_AES_128_CBC = "AES-128-CBC"  # Chuan ma hoa khoi doi xung hien dai 128-bit che do CBC
ALGORITHMS = [ALGO_NONE, ALGO_CAESAR, ALGO_PLAYFAIR, ALGO_AES_128_CBC]

# 3 kich thuoc du lieu thuc nghiem: 1 KB, 100 KB, 1 MB
SIZE_1KB = 1024
SIZE_100KB = 102400
SIZE_1MB = 1048576
SIZES = [SIZE_1KB, SIZE_100KB, SIZE_1MB]

SIZE_LABELS = {
    SIZE_1KB: "1 KB",
    SIZE_100KB: "100 KB",
    SIZE_1MB: "1 MB",
}

# Tham so ma hoa co dinh trong suot qua trinh benchmark de dam bao tinh nhat quan
CAESAR_SHIFT = 3
PLAYFAIR_KEY = "MONARCHY"
AES_KEY = b"0123456789abcdef"  # 16 byte khoa doi xung co dinh cho benchmark

# So luot chay thuc nghiem theo chuan khoa hoc
WARMUP_RUNS = 1                                         # 1 luot khoi dong loai bo nhiễu cache/socket
BENCHMARK_RUNS = 30                                     # 30 lan do chinh thuc de lay gia tri thong ke
TOTAL_PER_COMBO = WARMUP_RUNS + BENCHMARK_RUNS          # 31 luot cho moi to hop
TOTAL_COMBINATIONS = len(ALGORITHMS) * len(SIZES)      # 4 thuat toan x 3 kich thuoc = 12 to hop
TOTAL_EXECUTIONS = TOTAL_COMBINATIONS * TOTAL_PER_COMBO  # 12 x 31 = 372 luot thuc thi
TOTAL_SAMPLES = TOTAL_COMBINATIONS * BENCHMARK_RUNS      # 12 x 30 = 360 mau du lieu phan tich

# Dinh dang khung tin TCP nhi phan (Binary Framing) bang struct:
# Header dinh dang Big-Endian (!):
# - 16s: ten thuat toan (16 byte chuoi ASCII)
# - I: size_bytes (unsigned int 4 byte)
# - I: run_id (unsigned int 4 byte)
# - ?: is_warmup (bool 1 byte)
# - I: packet_len (unsigned int 4 byte - do dai du lieu phia sau)
HEADER_FORMAT = "!16sII?I"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # Tong kich thuoc Header dung 29 bytes

# ACK tra ve tu Receiver ve Sender:
# - d: decrypt_ms (double float 8 byte - thoi gian giai ma)
# - d: verify_ms (double float 8 byte - thoi gian kiem dinh tinh dung dan)
# - ?: success (bool 1 byte - ket qua giai ma dung hay sai)
# - d: dec_cpu_pct (double float 8 byte - phan tram CPU tai Receiver)
# - d: dec_ram_mb (double float 8 byte - RAM RSS tai Receiver)
# - d: dec_ram_delta_kb (double float 8 byte - RAM Delta tai Receiver)
ACK_FORMAT = "!dd?ddd"
ACK_SIZE = struct.calcsize(ACK_FORMAT)  # Tong kich thuoc ACK dung 41 bytes


def generate_plaintext(size_bytes: int) -> str:
    """
    Sinh chuoi plaintext tat dinh chi gom cac chu cai in hoa A-Z.
    Su dung bang chu cai 25 ky tu (A-Z, loai tru J de dam bao Playfair khong bi lech ky tu).
    Dam bao khong co hai ky tu giong nhau lien tiep de Playfair khong can chen X.
    Nho do, moi thuat toan deu giai ma ra chinh xac 100% tung byte voi ban goc de chay kiem tra verify.
    """
    pattern = config.ALPHABET  # "ABCDEFGHIKLMNOPQRSTUVWXYZ" (25 ky tu)
    repeat_count = (size_bytes // len(pattern)) + 1
    full_str = pattern * repeat_count
    return full_str[:size_bytes]


def send_all(sock: socket.socket, data: bytes) -> None:
    """Gui toan bo mang byte qua socket TCP (lap den khi het)."""
    sock.sendall(data)


def recv_all(sock: socket.socket, num_bytes: int) -> bytes:
    """
    Doc chinh xac du num_bytes tu socket TCP.
    Lap lien tuc den khi bo dem dat du num_bytes, khac phuc triet de van de vỡ goi tin tren TCP.
    """
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = sock.recv(num_bytes - len(buf))
        if not chunk:
            raise ConnectionError(f"Socket bi dong dot ngot, con thieu {num_bytes - len(buf)} byte.")
        buf.extend(chunk)
    return bytes(buf)


def send_frame(
    sock: socket.socket,
    algo: str,
    size_bytes: int,
    run_id: int,
    is_warmup: bool,
    packet_data: bytes,
) -> None:
    """
    Dong goi va gui mot khung du lieu tu Sender den Receiver:
    - Chuyen algo thanh chuoi 16 byte ASCII (dem them byte 0x00 neu ngan hon 16).
    - Dong goi Header 29 byte va noi packet_data phia sau.
    - Gui qua socket.
    """
    algo_bytes = algo.encode("ascii").ljust(16, b"\x00")
    header = struct.pack(
        HEADER_FORMAT,
        algo_bytes,
        size_bytes,
        run_id,
        is_warmup,
        len(packet_data),
    )
    send_all(sock, header + packet_data)


def recv_frame(sock: socket.socket) -> tuple[str, int, int, bool, bytes]:
    """
    Nhan mot khung du lieu phia Receiver:
    1. Doc dung 29 bytes Header (HEADER_SIZE).
    2. Unpack de lay ten thuat toan, kich thuoc, so thu tu, co warmup va do dai packet_len.
    3. Doc tiep dung packet_len bytes du lieu payload.
    """
    header_raw = recv_all(sock, HEADER_SIZE)
    algo_raw, size_bytes, run_id, is_warmup, packet_len = struct.unpack(HEADER_FORMAT, header_raw)
    algo = algo_raw.rstrip(b"\x00").decode("ascii")
    packet_data = recv_all(sock, packet_len)
    return algo, size_bytes, run_id, is_warmup, packet_data


def send_ack(
    sock: socket.socket,
    decrypt_ms: float,
    verify_ms: float,
    success: bool,
    dec_cpu_pct: float = 0.0,
    dec_ram_mb: float = 0.0,
    dec_ram_delta_kb: float = 0.0,
) -> None:
    """Gui goi tin ACK 41 bytes tu Receiver ve Sender (bao gom ca thoi gian, CPU va RAM cua Receiver)."""
    ack_data = struct.pack(
        ACK_FORMAT,
        decrypt_ms,
        verify_ms,
        success,
        dec_cpu_pct,
        dec_ram_mb,
        dec_ram_delta_kb,
    )
    send_all(sock, ack_data)


def recv_ack(sock: socket.socket) -> tuple[float, float, bool, float, float, float]:
    """Nhan goi tin ACK tai Sender (tra ve decrypt_ms, verify_ms, success, dec_cpu_pct, dec_ram_mb, dec_ram_delta_kb)."""
    ack_raw = recv_all(sock, ACK_SIZE)
    decrypt_ms, verify_ms, success, dec_cpu_pct, dec_ram_mb, dec_ram_delta_kb = struct.unpack(
        ACK_FORMAT, ack_raw
    )
    return decrypt_ms, verify_ms, success, dec_cpu_pct, dec_ram_mb, dec_ram_delta_kb


def clear_benchmark_results(results_dir: str) -> tuple[list[str], list[str]]:
    """
    Xóa toàn bộ kết quả benchmark cũ bao gồm:
    - Các file dữ liệu CSV, file báo cáo Markdown trong results_dir.
    - Toàn bộ file ảnh biểu đồ (*.png) trong thư mục con charts/.

    Trả về tuple: (danh_sach_file_da_xoa, danh_sach_file_loi_bi_khoa)
    """
    deleted_files: list[str] = []
    locked_files: list[str] = []

    charts_dir = os.path.join(results_dir, "charts")
    if os.path.exists(charts_dir):
        for fname in os.listdir(charts_dir):
            fpath = os.path.join(charts_dir, fname)
            if os.path.isfile(fpath):
                try:
                    os.remove(fpath)
                    deleted_files.append(os.path.join("charts", fname))
                except Exception as exc:
                    locked_files.append(f"{os.path.join('charts', fname)} ({exc})")

    if os.path.exists(results_dir):
        for fname in os.listdir(results_dir):
            fpath = os.path.join(results_dir, fname)
            if os.path.isfile(fpath):
                try:
                    os.remove(fpath)
                    deleted_files.append(fname)
                except Exception as exc:
                    locked_files.append(f"{fname} ({exc})")

    # Đảm bảo thư mục charts vẫn tồn tại sẵn sàng cho lần sinh biểu đồ mới
    os.makedirs(charts_dir, exist_ok=True)

    return deleted_files, locked_files
