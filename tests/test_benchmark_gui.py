"""
test_benchmark_gui.py - Unit test tu dong cho Giao dien do hoa Benchmark GUI.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Bat buoc chay Qt o che do offscreen de test tren headless / CI
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication, QMessageBox

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from benchmark import common, gui


class TestBenchmarkGUI(unittest.TestCase):
    """Kiem tra khoi tao va cac ham logic cua BenchmarkWindow."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def setUp(self):
        self.window = gui.BenchmarkWindow()

    def tearDown(self):
        self.window.close()

    def test_window_initialization(self):
        """Kiem tra khoi tao cua so va cac tab."""
        self.assertIn("Benchmark", self.window.windowTitle())
        self.assertEqual(self.window.tabs.count(), 3)
        self.assertEqual(self.window.tabs.tabText(0), "🕹️ Thực thi Benchmark")
        self.assertEqual(self.window.tabs.tabText(1), "📊 Xem 8 Biểu đồ")
        self.assertEqual(self.window.tabs.tabText(2), "📋 Bảng Thống kê & Báo cáo")

    def test_mode_switching(self):
        """Kiem tra chuyen doi ca 3 che do: Local, Sender Server va Receiver Server."""
        # 1. Mac dinh la Local
        self.assertTrue(self.window.radio_local.isChecked())
        self.assertEqual(self.window.edit_host.text(), "127.0.0.1")
        self.assertFalse(self.window.edit_host.isEnabled())
        self.assertFalse(self.window.btn_ping.isEnabled())
        self.assertTrue(self.window.scenario_group.isEnabled())
        self.assertIn("LOCAL", self.window.btn_start.text())

        # 2. Chuyen sang Sender Server
        self.window.radio_sender.setChecked(True)
        self.window._on_mode_changed(2)
        self.assertTrue(self.window.edit_host.isEnabled())
        self.assertTrue(self.window.btn_ping.isEnabled())
        self.assertTrue(self.window.scenario_group.isEnabled())
        self.assertIn("SENDER SERVER", self.window.btn_start.text())

        # 3. Chuyen sang Receiver Server
        self.assertTrue(hasattr(self.window, "radio_server"))
        self.window.radio_server.setChecked(True)
        self.window._on_mode_changed(3)
        self.assertEqual(self.window.edit_host.text(), "0.0.0.0")
        self.assertFalse(self.window.edit_host.isEnabled())
        self.assertFalse(self.window.btn_ping.isEnabled())
        self.assertFalse(self.window.scenario_group.isEnabled())
        self.assertIn("RECEIVER SERVER", self.window.btn_start.text())

        # 4. Chuyen lai ve Local
        self.window.radio_local.setChecked(True)
        self.window._on_mode_changed(1)
        self.assertEqual(self.window.edit_host.text(), "127.0.0.1")
        self.assertFalse(self.window.edit_host.isEnabled())
        self.assertFalse(self.window.btn_ping.isEnabled())
        self.assertTrue(self.window.scenario_group.isEnabled())

    def test_start_and_stop_server_mode(self):
        """Kiem tra khoi dong va dung Receiver Server trong GUI."""
        self.window._start_server_mode("127.0.0.1", 5098)
        self.assertTrue(self.window._server_worker.isRunning())
        self.assertFalse(self.window.btn_start.isEnabled())
        self.assertTrue(self.window.btn_stop.isEnabled())
        self.assertIn("DỪNG RECEIVER SERVER", self.window.btn_stop.text())

        self.window._on_stop_clicked()
        self.window._server_worker.wait(2000)
        QApplication.processEvents()
        self.assertFalse(self.window._server_worker.isRunning())
        self.assertTrue(self.window.btn_start.isEnabled())

    def test_client_progress_updates_table_and_cards(self):
        """Kiem tra cap nhat tien trinh va chen dong vao bang live."""
        sample_progress = {
            "is_warmup": False,
            "current_run": 1,
            "total_runs": 10,
            "combo_idx": 1,
            "total_combos": 1,
            "algo": "AES-128-CBC",
            "size_bytes": 1024,
            "row": {
                "run_id": 1,
                "algorithm": "AES-128-CBC",
                "size_bytes": 1024,
                "ciphertext_size_bytes": 1040,
                "packet_size_bytes": 1056,
                "encryption_ms": 0.05,
                "decrypt_ms": 0.04,
                "verify_ms": 0.01,
                "rtt_ms": 0.12,
                "total_ms": 0.17,
                "throughput_kbps": 6023.5,
                "enc_cpu_pct": 0.0,
                "dec_cpu_pct": 0.0,
                "enc_ram_mb": 105.0,
                "dec_ram_mb": 105.0,
                "enc_ram_delta_kb": 0.0,
                "dec_ram_delta_kb": 0.0,
                "success": True,
            }
        }
        self.window._on_client_progress(sample_progress)

        self.assertEqual(self.window.table_live.rowCount(), 1)
        self.assertEqual(self.window.table_live.item(0, 0).text(), "#001")
        self.assertEqual(self.window.table_live.item(0, 1).text(), "AES-128-CBC")
        self.assertEqual(self.window.table_live.item(0, 12).text(), "PASS")
        self.assertIn("1 / 10", self.window.lbl_card_progress.text())

    def test_chart_viewer_navigation(self):
        """Kiem tra dieu huong bieu do tren Tab 2."""
        self.assertEqual(self.window.combo_charts.count(), 8)
        self.window.combo_charts.setCurrentIndex(0)
        self.window._on_next_chart()
        self.assertEqual(self.window.combo_charts.currentIndex(), 1)
        self.window._on_prev_chart()
        self.assertEqual(self.window.combo_charts.currentIndex(), 0)

    def test_stats_table_loads(self):
        """Kiem tra doc bang thong ke neu co san file detailed_statistics.csv."""
        stat_csv = os.path.join(self.window.results_dir, "detailed_statistics.csv")
        if os.path.exists(stat_csv):
            self.window._load_stats_table()
            self.assertGreater(self.window.table_stats.rowCount(), 0)

    def test_worker_live_execution(self):
        """Kiem tra khoi chay luong Server + Client thuc te o quy mo mini."""
        import tempfile
        import time

        test_port = 5099
        server_worker = gui.BenchmarkServerWorker("127.0.0.1", test_port)
        server_worker.start()
        time.sleep(0.3)

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_csv = os.path.join(tmpdir, "test.csv")
                client_worker = gui.BenchmarkClientWorker(
                    host="127.0.0.1",
                    port=test_port,
                    output_csv=tmp_csv,
                    seed=42,
                    algorithms=["None"],
                    sizes=[1024],
                    benchmark_runs=1,
                    warmup_runs=0,
                )
                progress_data = []
                client_worker.progress_signal.connect(lambda d: progress_data.append(d))
                client_worker.start()
                client_worker.wait(5000)
                QApplication.processEvents()

                self.assertTrue(os.path.exists(tmp_csv))
                self.assertEqual(len(progress_data), 1)
                self.assertEqual(progress_data[0]["row"]["algorithm"], "None")
        finally:
            server_worker.stop()
            server_worker.wait(2000)

    def test_clear_benchmark_results_function(self):
        """Kiem tra ham common.clear_benchmark_results xoa dung file du lieu va anh bieu do."""
        with tempfile.TemporaryDirectory() as tmpdir:
            charts_dir = os.path.join(tmpdir, "charts")
            os.makedirs(charts_dir, exist_ok=True)

            # Tao cac file du lieu gia lap
            csv_path = os.path.join(tmpdir, "benchmark_results.csv")
            stat_path = os.path.join(tmpdir, "detailed_statistics.csv")
            md_path = os.path.join(tmpdir, "summary_table.md")
            chart1_path = os.path.join(charts_dir, "01_encryption_time.png")
            chart2_path = os.path.join(charts_dir, "02_decryption_time.png")

            for path in (csv_path, stat_path, md_path, chart1_path, chart2_path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write("test_content")

            deleted, locked = common.clear_benchmark_results(tmpdir)
            self.assertEqual(len(deleted), 5)
            self.assertEqual(len(locked), 0)

            # Kiem tra file da bi xoa
            self.assertFalse(os.path.exists(csv_path))
            self.assertFalse(os.path.exists(stat_path))
            self.assertFalse(os.path.exists(md_path))
            self.assertFalse(os.path.exists(chart1_path))
            self.assertFalse(os.path.exists(chart2_path))

            # Thu muc charts van ton tai
            self.assertTrue(os.path.exists(charts_dir))

    def test_clear_buttons_exist_in_gui(self):
        """Kiem tra cac nut xoa ket qua cu co mat tren giao dien."""
        self.assertTrue(hasattr(self.window, "btn_clear"))
        self.assertTrue(hasattr(self.window, "btn_clear_header"))
        self.assertTrue(hasattr(self.window, "btn_stats_clear"))

        self.assertIn("XÓA KẾT QUẢ", self.window.btn_clear.text().upper())
        self.assertIn("XÓA KẾT QUẢ", self.window.btn_clear_header.text().upper())
        self.assertIn("XÓA KẾT QUẢ", self.window.btn_stats_clear.text().upper())

    def test_running_state_toggles_clear_buttons(self):
        """Kiem tra trang thai vo hieu hoa / kich hoat cac nut xoa khi he thong dang chay."""
        # Khi bat dau chay: nut xoa phai bi vo hieu hoa de tranh race condition
        self.window._set_running_state(True)
        self.assertFalse(self.window.btn_clear.isEnabled())
        self.assertFalse(self.window.btn_clear_header.isEnabled())
        self.assertFalse(self.window.btn_stats_clear.isEnabled())
        self.assertFalse(self.window.btn_start.isEnabled())
        self.assertTrue(self.window.btn_stop.isEnabled())

        # Khi dung chay: nut xoa duoc bat lai
        self.window._set_running_state(False)
        self.assertTrue(self.window.btn_clear.isEnabled())
        self.assertTrue(self.window.btn_clear_header.isEnabled())
        self.assertTrue(self.window.btn_stats_clear.isEnabled())
        self.assertTrue(self.window.btn_start.isEnabled())
        self.assertFalse(self.window.btn_stop.isEnabled())

    def test_on_clear_results_clicked_confirmation_yes(self):
        """Kiem tra nguoi dung bam Dong y tren hop thoai -> du lieu duoc xoa va GUI duoc reset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.window.results_dir = tmpdir
            self.window.charts_dir = os.path.join(tmpdir, "charts")
            os.makedirs(self.window.charts_dir, exist_ok=True)

            dummy_csv = os.path.join(tmpdir, "benchmark_results.csv")
            dummy_chart = os.path.join(self.window.charts_dir, "01_encryption_time.png")
            with open(dummy_csv, "w") as f:
                f.write("run_id,algorithm\n1,None\n")
            with open(dummy_chart, "w") as f:
                f.write("fake_png")

            # Gia lap co du lieu tren table live
            self.window.table_live.insertRow(0)
            self.window.table_stats.insertRow(0)
            self.window.progress_bar.setValue(50)
            self.window.lbl_card_progress.setText("5 / 10")

            with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes), \
                 patch.object(QMessageBox, "information"):
                self.window._on_clear_results_clicked()

            # Kiem tra file da bi xoa
            self.assertFalse(os.path.exists(dummy_csv))
            self.assertFalse(os.path.exists(dummy_chart))

            # Kiem tra GUI duoc reset
            self.assertEqual(self.window.table_live.rowCount(), 0)
            self.assertEqual(self.window.table_stats.rowCount(), 0)
            self.assertEqual(self.window.progress_bar.value(), 0)
            self.assertEqual(self.window.lbl_card_progress.text(), "--")
            self.assertIn("Chưa có biểu đồ", self.window.lbl_chart_img.text())

    def test_on_clear_results_clicked_confirmation_no(self):
        """Kiem tra nguoi dung bam Khong / Cancel -> khong xoa file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.window.results_dir = tmpdir
            dummy_csv = os.path.join(tmpdir, "benchmark_results.csv")
            with open(dummy_csv, "w") as f:
                f.write("keep_this_data")

            with patch.object(QMessageBox, "question", return_value=QMessageBox.No):
                self.window._on_clear_results_clicked()

            # File van phai con nguyen
            self.assertTrue(os.path.exists(dummy_csv))

    def test_on_clear_results_blocked_when_worker_running(self):
        """Kiem tra khong cho xoa khi dang co luong hoat dong."""
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = True
        self.window._client_worker = mock_worker

        with patch.object(QMessageBox, "warning") as mock_warn:
            self.window._on_clear_results_clicked()
            mock_warn.assert_called_once()


if __name__ == "__main__":
    unittest.main()
