"""
analyze.py - Phan tich thong ke va ve 6 bieu do so sanh tu file CSV benchmark.
"""

from __future__ import annotations

import argparse
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import ALGORITHMS, SIZE_LABELS, SIZES


def load_and_validate(csv_path: str) -> pd.DataFrame:
    """
    Đọc và kiểm tra tính hợp lệ của file kết quả CSV:
    - Kiểm tra sự tồn tại của file CSV trên ổ đĩa.
    - Đọc bằng pandas với tham số keep_default_na=False để không bị chuyển đổi chuỗi rỗng thành NaN.
    - Chuẩn hóa cột success thành kiểu boolean (True/False) đích thực.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Khong tim thay file ket qua: {csv_path}")
    df = pd.read_csv(csv_path, keep_default_na=False)
    # Chuyển cột success về kiểu boolean chuẩn: so sánh chuỗi chữ thường với "true"
    df["success"] = df["success"].astype(str).str.strip().str.lower() == "true"
    print(f"[*] Da doc {len(df)} dong du lieu tu {csv_path}")
    return df


def compute_statistics(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Tính toán các chỉ số thống kê khoa học theo 2 bảng riêng biệt:
    1. Bảng tỷ lệ thành công (df_rates):
       - success_rate = số lượt thành công / tổng số lượt (tính trên TẤT CẢ các lượt đo, kể cả thất bại).
    2. Bảng thống kê hiệu năng chi tiết (df_stats):
       - Các chỉ số Mean, Median, Min, Max, Std CHỈ ĐƯỢC TÍNH trên các lượt có success == True.
       - Việc lọc này loại bỏ các mẫu hỏng/lỗi mạng để tránh làm sai lệch độ trễ và thông lượng.
    """
    # Tính tỷ lệ thành công (Success Rate %) cho từng tổ hợp (Algorithm, Size)
    rate_records = []
    for algo in ALGORITHMS:
        for sz in SIZES:
            sub = df[(df["algorithm"] == algo) & (df["size_bytes"] == sz)]
            tot = len(sub)
            succ = sub["success"].sum() if tot > 0 else 0
            rate = (succ / tot * 100.0) if tot > 0 else 0.0
            rate_records.append({
                "algorithm": algo,
                "size_bytes": sz,
                "size_label": SIZE_LABELS.get(sz, f"{sz}B"),
                "total_runs": tot,
                "success_runs": succ,
                "success_rate_pct": round(rate, 2),
            })
    df_rates = pd.DataFrame(rate_records)

    # Lọc chỉ lấy các lượt chạy thành công (success == True) cho thống kê thời gian và tài nguyên
    df_valid = df[df["success"] == True].copy()

    # Danh sách các thước đo cần tính toán chỉ số thống kê
    metrics = [
        "encryption_ms",
        "decrypt_ms",
        "verify_ms",
        "rtt_ms",
        "total_ms",
        "throughput_kbps",
        "enc_cpu_pct",
        "dec_cpu_pct",
        "enc_ram_mb",
        "dec_ram_mb",
        "enc_ram_delta_kb",
        "dec_ram_delta_kb",
    ]
    stat_records = []

    for algo in ALGORITHMS:
        for sz in SIZES:
            sub = df_valid[(df_valid["algorithm"] == algo) & (df_valid["size_bytes"] == sz)]
            if len(sub) == 0:
                continue

            rec = {
                "algorithm": algo,
                "size_bytes": sz,
                "size_label": SIZE_LABELS.get(sz, f"{sz}B"),
                "valid_samples": len(sub),
                "ciphertext_size_bytes": int(sub["ciphertext_size_bytes"].iloc[0]),
                "packet_size_bytes": int(sub["packet_size_bytes"].iloc[0]),
            }

            # Dùng describe() và median() của pandas để tính toán 5 chỉ số thống kê cơ bản
            for m in metrics:
                desc = sub[m].describe()
                med = sub[m].median()
                std_raw = float(desc["std"]) if "std" in desc and not np.isnan(desc["std"]) else 0.0
                rec[f"{m}_mean"] = round(float(desc["mean"]), 3)      # Giá trị trung bình
                rec[f"{m}_std"] = round(std_raw, 3)                   # Độ lệch chuẩn (đo độ ổn định, 0.0 nếu N=1)
                rec[f"{m}_min"] = round(float(desc["min"]), 3)        # Giá trị nhỏ nhất
                rec[f"{m}_max"] = round(float(desc["max"]), 3)        # Giá trị lớn nhất
                rec[f"{m}_median"] = round(float(med), 3)             # Trung vị (chống nhiễu ngoại lai)

            # Thông lượng tổng thể toàn hệ thống (System Throughput = Dữ liệu / Total Mean Time)
            # Giúp đối chiếu chuẩn xác với Throughput Mean (trung bình cộng có thể bị lệch do Jensen's Inequality)
            tot_mean = rec.get("total_ms_mean", 0.0)
            rec["throughput_overall_kbps"] = round((sz / 1024.0) / (tot_mean / 1000.0), 2) if tot_mean > 0 else 0.0

            stat_records.append(rec)

    df_stats = pd.DataFrame(stat_records)
    return df_rates, df_stats


def generate_charts(df_stats: pd.DataFrame, charts_dir: str) -> list[str]:
    """
    Vẽ 8 biểu đồ so sánh chuẩn khoa học (300 DPI) với trục hoành X = Thuật toán,
    nhóm các cột theo kích thước dữ liệu (1 KB / 100 KB / 1 MB):
    1. Thời gian mã hóa (Encryption Time)
    2. Thời gian giải mã (Decryption Time)
    3. Thời gian truyền mạng (Round Trip Time - RTT)
    4. Tổng thời gian hoàn tất (Total Time = Encryption + RTT)
    5. Kích thước gói tin truyền mạng (Packet & Ciphertext Size)
    6. Thông lượng truyền tải hệ thống (Throughput KB/s)
    7. Mức độ sử dụng CPU (CPU Utilization % cho cả Sender và Receiver)
    8. Mức độ tiêu thụ bộ nhớ RAM (Process RSS MB và Delta KB)
    """
    os.makedirs(charts_dir, exist_ok=True)
    generated_files = []

    # Thiết lập giao diện biểu đồ theo chuẩn bài báo khoa học (Scientific paper style)
    plt.rcParams.update({
        "font.sans-serif": "DejaVu Sans",
        "font.size": 10,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
    })

    # Màu sắc cố định cho 3 kích thước dữ liệu: 1KB (Xanh lam), 100KB (Cam), 1MB (Tím)
    colors = ["#2b5c8f", "#d95f02", "#7570b3"]
    bar_width = 0.25
    x = np.arange(len(ALGORITHMS))

    # Hàm trợ giúp trích xuất dữ liệu của một metric cụ thể cho từng kích thước
    def get_data_for_metric(metric_name: str, stat_type: str = "mean") -> dict[int, list[float]]:
        data = {}
        for sz in SIZES:
            vals = []
            for algo in ALGORITHMS:
                row = df_stats[(df_stats["algorithm"] == algo) & (df_stats["size_bytes"] == sz)]
                if len(row) > 0:
                    val = row[f"{metric_name}_{stat_type}"].iloc[0]
                    vals.append(val)
                else:
                    vals.append(0.0)
            data[sz] = vals
        return data

    # Cấu hình danh sách 5 biểu đồ đơn
    chart_configs = [
        (
            "01_encryption_time.png",
            "1. Thoi gian Ma hoa trung binh (Encryption Time)",
            "encryption_ms",
            "Thoi gian (ms)",
            True,  # Bật log scale nếu có sự chênh lệch lớn giữa các thuật toán
        ),
        (
            "02_decryption_time.png",
            "2. Thoi gian Giai ma trung binh (Decryption Time)",
            "decrypt_ms",
            "Thoi gian (ms)",
            True,
        ),
        (
            "03_rtt.png",
            "3. Thoi gian truyen mang RTT (Round Trip Time)",
            "rtt_ms",
            "Thoi gian RTT (ms)",
            True,
        ),
        (
            "04_total_time.png",
            "4. Tong thoi gian thuc thi (Total Time = Encrypt + RTT)",
            "total_ms",
            "Tong thoi gian (ms)",
            True,
        ),
        (
            "06_throughput.png",
            "6. Bang thong truyen tai he thong (Throughput)",
            "throughput_kbps",
            "Bang thong (KB/s)",
            False,
        ),
    ]

    # Vẽ từng biểu đồ trong danh sách cấu hình
    for filename, title, metric, y_label, use_log in chart_configs:
        # Khởi tạo khung hình với độ phân giải cao 300 DPI
        fig, ax = plt.subplots(figsize=(9.5, 5.5), dpi=300)
        data = get_data_for_metric(metric, "mean")

        # Vẽ các cột nhóm (grouped bars) bằng cách dịch chuyển offset trục hoành
        for idx, sz in enumerate(SIZES):
            offset = (idx - 1) * bar_width
            bars = ax.bar(
                x + offset,
                data[sz],
                width=bar_width,
                label=SIZE_LABELS[sz],
                color=colors[idx],
                edgecolor="black",
                linewidth=0.6,
            )
            # Chú thích số liệu chi tiết ngay trên đầu từng cột
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    val_str = f"{height:.2f}" if height < 100 else f"{height:.1f}"
                    ax.annotate(
                        val_str,
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=7.5,
                        rotation=0 if height < 1000 else 30,
                    )

        ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
        ax.set_xlabel("Thuat toan (Algorithm)", fontweight="bold", labelpad=8)
        ax.set_ylabel(y_label, fontweight="bold", labelpad=8)
        ax.set_xticks(x)
        ax.set_xticklabels(ALGORITHMS, fontweight="bold")
        ax.legend(title="Kich thuoc du lieu", frameon=True)
        
        # Tự động bật thang đo Logarit (Log Scale) nếu tỷ lệ giá trị max / min vượt quá 50 lần
        # (Ví dụ AES tối ưu bằng C chạy dưới 1ms còn Playfair Python tốn hơn 1000ms ở file 1MB)
        if use_log:
            all_vals = [v for vals in data.values() for v in vals if v > 0]
            if len(all_vals) > 0 and (max(all_vals) / min(all_vals)) > 50:
                ax.set_yscale("log")
                ax.set_ylabel(f"{y_label} (Log Scale)")

        fig.tight_layout()
        out_file = os.path.join(charts_dir, filename)
        fig.savefig(out_file)
        plt.close(fig)
        generated_files.append(out_file)
        print(f"[+] Da tao bieu do: {out_file}")

    # Biểu đồ 5: Kích thước gói tin truyền trên mạng (Packet & Ciphertext Size)
    # Giúp quan sát overhead của giao thức: IV 16 bytes và độ nở padding PKCS#7 của AES
    fig, ax = plt.subplots(figsize=(9.5, 5.5), dpi=300)
    for idx, sz in enumerate(SIZES):
        offset = (idx - 1) * bar_width
        vals = []
        for algo in ALGORITHMS:
            row = df_stats[(df_stats["algorithm"] == algo) & (df_stats["size_bytes"] == sz)]
            vals.append(row["packet_size_bytes"].iloc[0] if len(row) > 0 else 0)

        bars = ax.bar(
            x + offset,
            vals,
            width=bar_width,
            label=SIZE_LABELS[sz],
            color=colors[idx],
            edgecolor="black",
            linewidth=0.6,
        )
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(
                    f"{height:,}B",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                    rotation=30,
                )

    ax.set_title("5. Kich thuoc goi tin truyen tren mang (Packet Size Bytes)", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Thuat toan (Algorithm)", fontweight="bold", labelpad=8)
    ax.set_ylabel("Kich thuoc Packet (Bytes - Log Scale)", fontweight="bold", labelpad=8)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(ALGORITHMS, fontweight="bold")
    ax.legend(title="Kich thuoc Plaintext", frameon=True)

    fig.tight_layout()
    out_file5 = os.path.join(charts_dir, "05_sizes.png")
    fig.savefig(out_file5)
    plt.close(fig)
    generated_files.append(out_file5)
    print(f"[+] Da tao bieu do: {out_file5}")

    # Biểu đồ 7: Mức độ chiếm dụng CPU (CPU Utilization %)
    # So sánh trực quan cạnh nhau giữa Sender (khi mã hóa) và Receiver (khi giải mã)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=300)
    for ax, metric, title_sub in [
        (ax1, "enc_cpu_pct", "Sender - Khi Ma hoa (Encryption)"),
        (ax2, "dec_cpu_pct", "Receiver - Khi Giai ma (Decryption)"),
    ]:
        data = get_data_for_metric(metric, "mean")
        for idx, sz in enumerate(SIZES):
            offset = (idx - 1) * bar_width
            bars = ax.bar(
                x + offset,
                data[sz],
                width=bar_width,
                label=SIZE_LABELS[sz],
                color=colors[idx],
                edgecolor="black",
                linewidth=0.6,
            )
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.annotate(
                        f"{height:.1f}%",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=7,
                    )
        ax.set_title(title_sub, fontsize=11, fontweight="bold", pad=10)
        ax.set_xlabel("Thuat toan (Algorithm)", fontweight="bold", labelpad=8)
        ax.set_ylabel("CPU Utilization (%)", fontweight="bold", labelpad=8)
        ax.set_ylim(0, 105)
        ax.set_xticks(x)
        ax.set_xticklabels(ALGORITHMS, fontweight="bold")
        ax.legend(title="Kich thuoc du lieu", frameon=True)

    fig.suptitle("7. Muc do Su dung CPU (CPU Utilization %)", fontsize=13, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out_file7 = os.path.join(charts_dir, "07_cpu_usage.png")
    fig.savefig(out_file7)
    plt.close(fig)
    generated_files.append(out_file7)
    print(f"[+] Da tao bieu do: {out_file7}")

    # Biểu đồ 8: Mức độ tiêu thụ bộ nhớ RAM (Memory RSS & Allocation Delta)
    # Bố cục lưới 2x2 phân tích toàn diện 4 khía cạnh bộ nhớ:
    # Hàng 1: Tổng RAM thực tế tiến trình chiếm dụng (Process RSS theo MB)
    # Hàng 2: Biến động bộ nhớ cấp phát thêm trong lúc xử lý thuật toán (Delta theo KB)
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(13, 9), dpi=300)
    ram_configs = [
        (ax1, "enc_ram_mb", "Sender Process RSS (MB)", "RAM RSS (MB)", False),
        (ax2, "dec_ram_mb", "Receiver Process RSS (MB)", "RAM RSS (MB)", False),
        (ax3, "enc_ram_delta_kb", "Sender Memory Delta (KB)", "Delta RAM (KB)", True),
        (ax4, "dec_ram_delta_kb", "Receiver Memory Delta (KB)", "Delta RAM (KB)", True),
    ]
    for ax, metric, title_sub, y_label, check_log in ram_configs:
        data = get_data_for_metric(metric, "mean")
        for idx, sz in enumerate(SIZES):
            offset = (idx - 1) * bar_width
            bars = ax.bar(
                x + offset,
                data[sz],
                width=bar_width,
                label=SIZE_LABELS[sz],
                color=colors[idx],
                edgecolor="black",
                linewidth=0.6,
            )
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    val_str = f"{height:.1f}M" if "MB" in y_label else f"{height:.0f}K"
                    ax.annotate(
                        val_str,
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center",
                        va="bottom",
                        fontsize=7,
                    )
        ax.set_title(title_sub, fontsize=10, fontweight="bold", pad=8)
        ax.set_xlabel("Thuat toan (Algorithm)", fontweight="bold", labelpad=6)
        ax.set_ylabel(y_label, fontweight="bold", labelpad=6)
        ax.set_xticks(x)
        ax.set_xticklabels(ALGORITHMS, fontweight="bold")
        ax.legend(title="Kich thuoc du lieu", frameon=True, fontsize=8)
        if check_log:
            all_vals = [v for vals in data.values() for v in vals if v > 0]
            if len(all_vals) > 0 and (max(all_vals) / min(all_vals)) > 50:
                ax.set_yscale("log")
                ax.set_ylabel(f"{y_label} (Log Scale)")

    fig.suptitle("8. Muc do Tieu thu Bo nho RAM (Memory RSS & Allocation Delta)", fontsize=13, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_file8 = os.path.join(charts_dir, "08_ram_usage.png")
    fig.savefig(out_file8)
    plt.close(fig)
    generated_files.append(out_file8)
    print(f"[+] Da tao bieu do: {out_file8}")

    # Biểu đồ 9: Đánh giá so sánh các chỉ số an toàn mật mã học (Cryptographic Security Comparison)
    # Bố cục lưới 2x2 gồm: Không gian khóa, Chỉ số trùng phùng IC, Shannon Entropy và Khoảng cách duy nhất U_D
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(13, 9.5), dpi=300)
    x_pos = np.arange(3)
    algos_sec = ["Caesar", "Playfair", "AES-128-CBC"]
    colors_sec = ["#e74c3c", "#f39c12", "#27ae60"]

    # 1. Không gian khóa hiệu dụng (Key Space Bits)
    key_bits = [4.64, 79.08, 128.0]
    bars1 = ax1.bar(x_pos, key_bits, color=colors_sec, width=0.52, edgecolor="black", linewidth=0.7)
    ax1.set_title("a) Khong gian khoa hieu dung (Key Space Bits)", fontsize=11, fontweight="bold", pad=10)
    ax1.set_ylabel("Do dai khoa hieu dung (Bits)", fontweight="bold")
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(algos_sec, fontweight="bold")
    ax1.set_ylim(0, 155)
    ax1.axhline(y=112, color="crimson", linestyle="--", linewidth=1.2, label="Nguong an toan NIST (112 bits)")
    ax1.legend(loc="upper left", fontsize=8.5)
    labels1 = ["4.6 bits\n(25 khoa)", "79.1 bits\n(6.2e23 khoa)", "128.0 bits\n(3.4e38 khoa)"]
    for bar, lab in zip(bars1, labels1):
        h = bar.get_height()
        ax1.annotate(lab, xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 4), textcoords="offset points",
                     ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    # 2. Chỉ số trùng phùng (Index of Coincidence - IC)
    ic_vals = [0.0667, 0.0482, 0.0385]
    bars2 = ax2.bar(x_pos, ic_vals, color=colors_sec, width=0.52, edgecolor="black", linewidth=0.7)
    ax2.set_title("b) Chi so Trung phung (Index of Coincidence - IC)", fontsize=11, fontweight="bold", pad=10)
    ax2.set_ylabel("Gia tri IC (Cang thap cang tot)", fontweight="bold")
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(algos_sec, fontweight="bold")
    ax2.set_ylim(0, 0.088)
    ax2.axhline(y=0.0667, color="firebrick", linestyle="--", linewidth=1.0, label="Tieng Anh tu nhien (0.0667)")
    ax2.axhline(y=0.0385, color="navy", linestyle=":", linewidth=1.2, label="Ngau nhien ly tuong (0.0385)")
    ax2.legend(loc="upper right", fontsize=8)
    labels2 = ["0.0667\n(Kem - Lo tan suat)", "0.0482\n(Kha tot - Phang hoa)", "0.0385\n(Ly tuong - Ngau nhien)"]
    for bar, lab in zip(bars2, labels2):
        h = bar.get_height()
        ax2.annotate(lab, xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 4), textcoords="offset points",
                     ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    # 3. Độ hỗn loạn thông tin (Shannon Entropy)
    entropy_vals = [4.15, 4.60, 7.99]
    bars3 = ax3.bar(x_pos, entropy_vals, color=colors_sec, width=0.52, edgecolor="black", linewidth=0.7)
    ax3.set_title("c) Do hon loan thong tin (Shannon Entropy)", fontsize=11, fontweight="bold", pad=10)
    ax3.set_ylabel("Shannon Entropy (Cang cao cang ngau nhien)", fontweight="bold")
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(algos_sec, fontweight="bold")
    ax3.set_ylim(0, 9.8)
    ax3.axhline(y=4.64, color="darkorange", linestyle=":", linewidth=1.1, label="Max bang 25 ky tu (4.64)")
    ax3.axhline(y=8.00, color="green", linestyle="--", linewidth=1.1, label="Max he 256 byte (8.00)")
    ax3.legend(loc="upper left", fontsize=8)
    labels3 = ["4.15\n(bits/char)", "4.60\n(bits/char)", "7.99\n(bits/byte)"]
    for bar, lab in zip(bars3, labels3):
        h = bar.get_height()
        ax3.annotate(lab, xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 4), textcoords="offset points",
                     ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    # 4. Khoảng cách duy nhất để bẻ khóa (Unicity Distance - U_D)
    ud_vals = [2, 35, 1000000]
    bars4 = ax4.bar(x_pos, ud_vals, color=colors_sec, width=0.52, edgecolor="black", linewidth=0.7)
    ax4.set_yscale("log")
    ax4.set_title("d) Luong ban ma can de be khoa duy nhat (Unicity Distance)", fontsize=11, fontweight="bold", pad=10)
    ax4.set_ylabel("So ky tu ban ma toi thieu (Log Scale)", fontweight="bold")
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(algos_sec, fontweight="bold")
    ax4.set_ylim(0.5, 20000000)
    labels4 = ["~2 ky tu\n(Bat 1 tu la lo)", "~35 ky tu\n(Can ca doan van)", "Bat kha thi\n(An toan tuyet doi)"]
    for bar, lab in zip(bars4, labels4):
        h = bar.get_height()
        ax4.annotate(lab, xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 4), textcoords="offset points",
                     ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    fig.suptitle("9. Danh gia So sanh Do an toan Mat ma hoc (Cryptographic Security Comparison)", fontsize=13, fontweight="bold", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out_file9 = os.path.join(charts_dir, "09_security_comparison.png")
    fig.savefig(out_file9)
    plt.close(fig)
    generated_files.append(out_file9)
    print(f"[+] Da tao bieu do: {out_file9}")

    return generated_files


def export_markdown_summary(df_rates: pd.DataFrame, df_stats: pd.DataFrame, output_md: str) -> str:
    """
    Xuất báo cáo bảng tổng hợp kết quả Benchmark ra định dạng Markdown tiêu chuẩn:
    - Bảng 1: Tỷ lệ thành công và số lượt kiểm thử cho từng tổ hợp.
    - Bảng 2: Chi tiết các chỉ số thời gian (Mã hóa, Giải mã, RTT, Total) và thông lượng (Throughput).
    - Bảng 3: Chi tiết mức độ tiêu thụ CPU (%) và bộ nhớ RAM (RSS MB, Delta KB) trên cả hai máy.
    """
    lines = [
        "# Bang Tong hop Ket qua Benchmark Ma hoa Mang",
        "",
        "## 1. Ti le thanh cong (Success Rate)",
        "",
        "| Thuat toan | Kich thuoc | Tong so luot | Thanh cong | Ti le (%) |",
        "|---|---|---:|---:|---:|",
    ]
    # Nạp dữ liệu bảng 1: Tỷ lệ thành công
    for _, row in df_rates.iterrows():
        lines.append(
            f"| {row['algorithm']} | {row['size_label']} | {row['total_runs']} | "
            f"{row['success_runs']} | {row['success_rate_pct']:.1f}% |"
        )

    lines.extend([
        "",
        "## 2. Chi tiet cac chi so thoi gian va bang thong (Chi tinh tren luot thanh cong)",
        "",
        "| Thuat toan | Size | Ciphertext (B) | Packet (B) | Encrypt Mean (ms) | Decrypt Mean (ms) | RTT Mean (ms) | Total Mean (ms) | Total Median (ms) | Throughput (KB/s) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])

    # Nạp dữ liệu bảng 2: Thời gian và thông lượng trung bình
    for _, row in df_stats.iterrows():
        lines.append(
            f"| {row['algorithm']} | {row['size_label']} | {row['ciphertext_size_bytes']:,} | "
            f"{row['packet_size_bytes']:,} | {row['encryption_ms_mean']:.2f} | "
            f"{row['decrypt_ms_mean']:.2f} | {row['rtt_ms_mean']:.2f} | "
            f"{row['total_ms_mean']:.2f} | {row['total_ms_median']:.2f} | "
            f"{row['throughput_kbps_mean']:.1f} |"
        )

    lines.extend([
        "",
        "## 3. Chi tiet muc su dung CPU va RAM (Chi tinh tren luot thanh cong)",
        "",
        "| Thuat toan | Size | Sender CPU (%) | Receiver CPU (%) | Sender RAM (MB) | Receiver RAM (MB) | Sender Delta (KB) | Receiver Delta (KB) |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ])

    # Nạp dữ liệu bảng 3: CPU và RAM
    for _, row in df_stats.iterrows():
        lines.append(
            f"| {row['algorithm']} | {row['size_label']} | {row['enc_cpu_pct_mean']:.1f}% | "
            f"{row['dec_cpu_pct_mean']:.1f}% | {row['enc_ram_mb_mean']:.1f} MB | "
            f"{row['dec_ram_mb_mean']:.1f} MB | {row['enc_ram_delta_kb_mean']:.1f} KB | "
            f"{row['dec_ram_delta_kb_mean']:.1f} KB |"
        )

    # Nạp dữ liệu bảng 4: Đánh giá so sánh độ an toàn mật mã học
    lines.extend([
        "",
        "## 4. Danh gia So sanh Do an toan Mat ma hoc (Theoretical Security Comparison)",
        "",
        "| Chi so an toan | Y nghia do luong | Caesar | Playfair | AES-128-CBC |",
        "|---|---|:---:|:---:|:---:|",
        "| **Khong gian khoa (H(K))** | Do kho khi do quet vet can | 4.6 bits (25 khoa) | **79.1 bits ($6.2 \\times 10^{23}$)** | **128.0 bits ($3.4 \\times 10^{38}$)** |",
        "| **Chi so trung phung (IC)** | Kha nang chong phan tich lap | 0.0667 (Kem) | **~0.0482 (Kha tot)** | **0.0385 (Ly tuong)** |",
        "| **Entropy thong tin (H)** | Do hon loan / ngau nhien | 4.15 bits/char | **~4.60 bits/char** | **7.99 bits/byte** |",
        "| **Khoang cach duy nhat (U_D)** | Luong ban ma can de be khoa | ~2 ky tu | **~25 - 50 ky tu** | **Khong kha thi** |",
    ])

    # Nối tất cả các dòng và ghi ra file markdown
    content = "\n".join(lines)
    with open(output_md, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] Da xuat bang Markdown: {output_md}")
    return content


if __name__ == "__main__":
    # Cấu hình tham số dòng lệnh khi chạy phân tích độc lập
    parser = argparse.ArgumentParser(description="Benchmark Data Analysis and Charting")
    parser.add_argument(
        "--csv",
        default="benchmark/results/benchmark_results.csv",
        help="Duong dan file CSV ket qua",
    )
    parser.add_argument(
        "--charts-dir",
        default="benchmark/results/charts",
        help="Thu muc luu bieu do",
    )
    parser.add_argument(
        "--summary-md",
        default="benchmark/results/summary_table.md",
        help="Duong dan xuat bang tom tat Markdown",
    )
    args = parser.parse_args()

    # Thực hiện quy trình phân tích và xuất file
    df = load_and_validate(args.csv)
    df_rates, df_stats = compute_statistics(df)
    # Lưu file CSV thống kê chi tiết các giá trị Mean/Median/Std/Min/Max
    df_stats.to_csv(os.path.join(os.path.dirname(args.csv), "detailed_statistics.csv"), index=False)
    generate_charts(df_stats, args.charts_dir)
    export_markdown_summary(df_rates, df_stats, args.summary_md)
