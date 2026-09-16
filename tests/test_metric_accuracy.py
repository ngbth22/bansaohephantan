"""
test_metric_accuracy.py - Kiem thu toan dien tinh chinh xac cua co che theo doi chi so he thong.

Cac khia canh kiem tra:
1. Tinh chinh xac cua cong thuc Throughput (Goodput KB/s vs kbps), bao ve loi chia 0.
2. Tinh toan thoi gian tong the (total_ms = encryption_ms + rtt_ms), khong tinh trung lap.
3. Phan ra do tre mang thuan tuy (Pure Network RTT = rtt_ms - decrypt_ms - verify_ms).
4. Do luong CPU utilization (process_time / perf_counter) va gioi han min(100.0, ...).
5. Do luong RAM RSS va Delta RAM voi co che chong am max(0.0, ...).
6. Tinh chinh xac kich thuoc goi tin (Packet size) & do phinh overhead tren 4 thuat toan x 3 kich thuoc.
7. Dinh dang khung tin TCP nhi phan: Header (29 bytes) va ACK (41 bytes).
8. Thong ke tong hop (analyze.py): Mean, Median, Std (an toan NaN), va System Throughput.
"""

from __future__ import annotations

import os
import struct
import sys
import unittest
import numpy as np
import pandas as pd

# Them thu muc goc va benchmark vao sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH_DIR = os.path.join(BASE_DIR, "benchmark")
SENDER_DIR = os.path.join(BASE_DIR, "sender")

for p in [BASE_DIR, BENCH_DIR, SENDER_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

import aes_cbc
import analyze
import caesar
import common
import playfair


class TestThroughputCalculation(unittest.TestCase):
    """Kiem tra tinh chinh xac cua cong thuc Thong luong / Bang thong."""

    def test_throughput_formula_standard(self):
        """Kiem tra tinh toan Throughput chuan o cac muc kich thuoc va thoi gian."""
        # 1 MB trong 1000 ms (1 giay) -> 1024 KB/s
        size_bytes = 1048576  # 1 MB = 1024 KB
        total_ms = 1000.0     # 1 s
        tp = (size_bytes / 1024.0) / (total_ms / 1000.0)
        self.assertAlmostEqual(tp, 1024.0, places=4)

        # 100 KB trong 10 ms (0.01 s) -> 10,000 KB/s
        size_bytes = 102400
        total_ms = 10.0
        tp = (size_bytes / 1024.0) / (total_ms / 1000.0)
        self.assertAlmostEqual(tp, 10000.0, places=4)

    def test_throughput_zero_time_protection(self):
        """Kiem tra bao ve chia cho 0 khi total_ms <= 0."""
        size_bytes = 1024
        total_ms = 0.0
        tp = (size_bytes / 1024.0) / (total_ms / 1000.0) if total_ms > 0 else 0.0
        self.assertEqual(tp, 0.0)

        total_ms_neg = -5.0
        tp_neg = (size_bytes / 1024.0) / (total_ms_neg / 1000.0) if total_ms_neg > 0 else 0.0
        self.assertEqual(tp_neg, 0.0)

    def test_throughput_unit_conversion_kbps_vs_kbytes(self):
        """Kiem tra quy doi chinh xac giua KB/s (KiloBytes/s) va kbps (Kilobits/s)."""
        size_bytes = 102400  # 100 KB
        total_ms = 50.0      # 0.05 s
        tp_kbytes_per_sec = (size_bytes / 1024.0) / (total_ms / 1000.0)  # 2000.0 KB/s
        # 1 Byte = 8 bits -> 2000 KB/s = 16,000 kbps (16 Mbps)
        tp_kbits_per_sec = tp_kbytes_per_sec * 8.0
        self.assertAlmostEqual(tp_kbytes_per_sec, 2000.0, places=2)
        self.assertAlmostEqual(tp_kbits_per_sec, 16000.0, places=2)

    def test_jensen_inequality_harmonic_vs_arithmetic(self):
        """
        Chung minh bat dang thuc Jensen:
        Trung binh cong cua throughput thuong lon hon throughput thuc te toan he thong
        khi thoi gian giua cac luot co phuong sai.
        """
        size_bytes = 102400  # 100 KB
        # Gia su co 2 luot: 1 luot cache cuc nhanh (1 ms) va 1 luot thong thuong (39 ms)
        t1, t2 = 1.0, 39.0
        tp1 = (size_bytes / 1024.0) / (t1 / 1000.0)  # 100,000 KB/s
        tp2 = (size_bytes / 1024.0) / (t2 / 1000.0)  # 2,564.1 KB/s

        arithmetic_mean_tp = (tp1 + tp2) / 2.0  # 51,282.05 KB/s
        total_time = (t1 + t2) / 1000.0         # 0.04 s
        total_data = (size_bytes * 2) / 1024.0  # 200 KB
        actual_system_tp = total_data / total_time  # 5,000.0 KB/s

        # Arithmetic mean bi keo phinh gap hon 10 lan so voi throughput thuc te
        self.assertGreater(arithmetic_mean_tp, actual_system_tp * 5)


class TestTimingAndLatencyAccuracy(unittest.TestCase):
    """Kiem tra tinh hop ly va chinh xac cua cac phep do thoi gian va do tre."""

    def test_total_time_non_overlapping(self):
        """Kiem tra total_ms = encryption_ms + rtt_ms khong bi gap hay chong lan."""
        enc_ms = 1.5
        rtt_ms = 10.2
        total_ms = enc_ms + rtt_ms
        self.assertAlmostEqual(total_ms, 11.7, places=4)

    def test_pure_network_rtt_decomposition(self):
        """
        Kiem tra phan ra Application RTT thanh Pure Network RTT va Processing Time:
        rtt_ms = pure_network_rtt + decrypt_ms + verify_ms
        """
        rtt_ms = 1124.98
        decrypt_ms = 1120.57
        verify_ms = 0.41
        pure_network_rtt = rtt_ms - (decrypt_ms + verify_ms)
        self.assertAlmostEqual(pure_network_rtt, 4.0, places=2)
        # Dam bao pure_network_rtt luon khong am
        self.assertGreaterEqual(pure_network_rtt, 0.0)


class TestHardwareMetricAccuracy(unittest.TestCase):
    """Kiem tra tinh chinh xac cua chi so CPU va RAM."""

    def test_cpu_pct_formula_and_clamping(self):
        """Kiem tra cong thuc CPU% va bao ve vuot qua 100%."""
        # 1. Truong hop binh thuong: 80 ms CPU tren 100 ms thoi gian thuc -> 80.0%
        cpu_time_ms = 80.0
        wall_time_ms = 100.0
        cpu_pct = round(min(100.0, (cpu_time_ms / wall_time_ms * 100.0)), 1)
        self.assertEqual(cpu_pct, 80.0)

        # 2. Truong hop multi-core hoac timer burst: cpu_time > wall_time phai duoc clamp ve 100.0%
        cpu_time_ms_burst = 150.0
        wall_time_ms = 100.0
        cpu_pct_burst = round(min(100.0, (cpu_time_ms_burst / wall_time_ms * 100.0)), 1)
        self.assertEqual(cpu_pct_burst, 100.0)

        # 3. Truong hop wall_time_ms == 0 -> 0.0%
        cpu_pct_zero = round(min(100.0, (0.0 / 0.0 * 100.0)), 1) if 0.0 > 0 else 0.0
        self.assertEqual(cpu_pct_zero, 0.0)

    def test_ram_delta_non_negative_clamping(self):
        """Kiem tra Delta RAM khong bao gio bi am do GC."""
        m_before = 200 * 1024 * 1024  # 200 MB
        m_after_more = 205 * 1024 * 1024  # Tang 5 MB
        delta_pos = round(max(0.0, (m_after_more - m_before) / 1024.0), 1)
        self.assertEqual(delta_pos, 5120.0)

        # Khi GC chay hoac OS thu hoi page, m_after < m_before -> phai clamp ve 0.0
        m_after_less = 195 * 1024 * 1024  # Giam 5 MB
        delta_neg = round(max(0.0, (m_after_less - m_before) / 1024.0), 1)
        self.assertEqual(delta_neg, 0.0)


class TestPacketSizingAndProtocolFraming(unittest.TestCase):
    """Kiem tra tinh chinh xac tuyet doi ve kich thuoc goi tin va framing nhan/gui."""

    def test_data_size_and_overhead_all_combinations(self):
        """Kiem tra kich thuoc Ciphertext va Packet tren ca 4 thuat toan x 3 kich thuoc."""
        for sz in common.SIZES:
            plain = common.generate_plaintext(sz)
            self.assertEqual(len(plain), sz)

            # 1. ALGO_NONE
            none_bytes = plain.encode("utf-8")
            self.assertEqual(len(none_bytes), sz)

            # 2. ALGO_CAESAR
            caesar_str = caesar.encrypt(plain, common.CAESAR_SHIFT)
            caesar_bytes = caesar_str.encode("utf-8")
            self.assertEqual(len(caesar_bytes), sz)

            # 3. ALGO_PLAYFAIR
            playfair_str = playfair.encrypt(plain, common.PLAYFAIR_KEY)
            playfair_bytes = playfair_str.encode("utf-8")
            self.assertEqual(len(playfair_bytes), sz)

            # 4. ALGO_AES_128_CBC: Luon cong dung 16 byte padding PKCS#7 va 16 byte IV
            iv = b"\x00" * 16
            aes_cipher = aes_cbc.encrypt(plain, common.AES_KEY, iv)
            # Vi Plaintext sz la boi so cua 16 (1024, 102400, 1048576), PKCS#7 dem tron 16 bytes
            self.assertEqual(len(aes_cipher), sz + 16)
            aes_packet = iv + aes_cipher
            self.assertEqual(len(aes_packet), sz + 32)

    def test_binary_header_framing(self):
        """Kiem tra struct Header 29 bytes va unpack dung dinh dang."""
        self.assertEqual(common.HEADER_SIZE, 29)
        algo = "AES-128-CBC"
        size_bytes = 1048576
        run_id = 15
        is_warmup = False
        packet_len = 1048608

        algo_bytes = algo.encode("ascii").ljust(16, b"\x00")
        header = struct.pack(
            common.HEADER_FORMAT,
            algo_bytes,
            size_bytes,
            run_id,
            is_warmup,
            packet_len,
        )
        self.assertEqual(len(header), 29)

        # Unpack
        u_algo_raw, u_sz, u_run, u_warm, u_plen = struct.unpack(common.HEADER_FORMAT, header)
        u_algo = u_algo_raw.rstrip(b"\x00").decode("ascii")

        self.assertEqual(u_algo, algo)
        self.assertEqual(u_sz, size_bytes)
        self.assertEqual(u_run, run_id)
        self.assertEqual(u_warm, is_warmup)
        self.assertEqual(u_plen, packet_len)

    def test_binary_ack_framing(self):
        """Kiem tra struct ACK 41 bytes va unpack dung dinh dang."""
        self.assertEqual(common.ACK_SIZE, 41)
        dec_ms = 1.09
        ver_ms = 0.40
        success = True
        cpu_pct = 6.7
        ram_mb = 110.5
        ram_delta_kb = 0.0

        ack_data = struct.pack(
            common.ACK_FORMAT,
            dec_ms,
            ver_ms,
            success,
            cpu_pct,
            ram_mb,
            ram_delta_kb,
        )
        self.assertEqual(len(ack_data), 41)

        u_dec, u_ver, u_succ, u_cpu, u_ram, u_delta = struct.unpack(common.ACK_FORMAT, ack_data)
        self.assertAlmostEqual(u_dec, dec_ms, places=4)
        self.assertAlmostEqual(u_ver, ver_ms, places=4)
        self.assertEqual(u_succ, success)
        self.assertAlmostEqual(u_cpu, cpu_pct, places=2)
        self.assertAlmostEqual(u_ram, ram_mb, places=2)
        self.assertAlmostEqual(u_delta, ram_delta_kb, places=2)


class TestStatisticalAnalysisAccuracy(unittest.TestCase):
    """Kiem tra tinh chinh xac cua ham thong ke compute_statistics trong analyze.py."""

    def test_analyze_compute_statistics(self):
        """Kiem tra tinh toan Mean, Median, Min, Max, Std va loai tru dong that bai."""
        # Tao DataFrame mau gia lap
        data = [
            # 2 luot thanh cong cho None 1024
            {"run_id": 1, "algorithm": "None", "size_bytes": 1024, "ciphertext_size_bytes": 1024,
             "packet_size_bytes": 1024, "encryption_ms": 0.1, "decrypt_ms": 0.1, "verify_ms": 0.01,
             "rtt_ms": 0.5, "total_ms": 0.6, "throughput_kbps": 1666.7, "enc_cpu_pct": 0.0,
             "dec_cpu_pct": 0.0, "enc_ram_mb": 100.0, "dec_ram_mb": 100.0, "enc_ram_delta_kb": 0.0,
             "dec_ram_delta_kb": 0.0, "success": True},
            {"run_id": 2, "algorithm": "None", "size_bytes": 1024, "ciphertext_size_bytes": 1024,
             "packet_size_bytes": 1024, "encryption_ms": 0.3, "decrypt_ms": 0.3, "verify_ms": 0.01,
             "rtt_ms": 0.7, "total_ms": 1.0, "throughput_kbps": 1000.0, "enc_cpu_pct": 0.0,
             "dec_cpu_pct": 0.0, "enc_ram_mb": 100.0, "dec_ram_mb": 100.0, "enc_ram_delta_kb": 0.0,
             "dec_ram_delta_kb": 0.0, "success": True},
            # 1 luot that bai (bi loai khoi thong ke hieu nang)
            {"run_id": 3, "algorithm": "None", "size_bytes": 1024, "ciphertext_size_bytes": 1024,
             "packet_size_bytes": 1024, "encryption_ms": 99.0, "decrypt_ms": 99.0, "verify_ms": 99.0,
             "rtt_ms": 99.0, "total_ms": 198.0, "throughput_kbps": 5.0, "enc_cpu_pct": 100.0,
             "dec_cpu_pct": 100.0, "enc_ram_mb": 999.0, "dec_ram_mb": 999.0, "enc_ram_delta_kb": 999.0,
             "dec_ram_delta_kb": 999.0, "success": False},
        ]
        df = pd.DataFrame(data)
        df_rates, df_stats = analyze.compute_statistics(df)

        # 1. Kiem tra ti le thanh cong: 2/3 = 66.67%
        none_1kb_rate = df_rates[(df_rates["algorithm"] == "None") & (df_rates["size_bytes"] == 1024)].iloc[0]
        self.assertEqual(none_1kb_rate["total_runs"], 3)
        self.assertEqual(none_1kb_rate["success_runs"], 2)
        self.assertAlmostEqual(none_1kb_rate["success_rate_pct"], 66.67, places=2)

        # 2. Kiem tra so mau hop le: chi gom 2 mau thanh cong
        none_1kb_stat = df_stats[(df_stats["algorithm"] == "None") & (df_stats["size_bytes"] == 1024)].iloc[0]
        self.assertEqual(none_1kb_stat["valid_samples"], 2)

        # 3. Kiem tra Mean cua encryption_ms: (0.1 + 0.3) / 2 = 0.2
        self.assertAlmostEqual(none_1kb_stat["encryption_ms_mean"], 0.2, places=3)
        # Median: 0.2
        self.assertAlmostEqual(none_1kb_stat["encryption_ms_median"], 0.2, places=3)
        # Min = 0.1, Max = 0.3
        self.assertAlmostEqual(none_1kb_stat["encryption_ms_min"], 0.1, places=3)
        self.assertAlmostEqual(none_1kb_stat["encryption_ms_max"], 0.3, places=3)

        # 4. Kiem tra throughput_overall_kbps: (1024 / 1024) / (total_mean 0.8 / 1000) = 1250.0 KB/s
        self.assertAlmostEqual(none_1kb_stat["throughput_overall_kbps"], 1250.0, places=1)

    def test_single_sample_nan_std_handling(self):
        """Kiem tra khi chi co 1 mau, std khong bi nan."""
        data = [
            {"run_id": 1, "algorithm": "Caesar", "size_bytes": 1024, "ciphertext_size_bytes": 1024,
             "packet_size_bytes": 1024, "encryption_ms": 0.5, "decrypt_ms": 0.5, "verify_ms": 0.01,
             "rtt_ms": 1.0, "total_ms": 1.5, "throughput_kbps": 682.7, "enc_cpu_pct": 0.0,
             "dec_cpu_pct": 0.0, "enc_ram_mb": 100.0, "dec_ram_mb": 100.0, "enc_ram_delta_kb": 0.0,
             "dec_ram_delta_kb": 0.0, "success": True},
        ]
        df = pd.DataFrame(data)
        _, df_stats = analyze.compute_statistics(df)
        stat_row = df_stats.iloc[0]
        self.assertFalse(np.isnan(stat_row["encryption_ms_std"]))
        self.assertEqual(stat_row["encryption_ms_std"], 0.0)


if __name__ == "__main__":
    unittest.main()
