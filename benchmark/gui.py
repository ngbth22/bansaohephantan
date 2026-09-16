"""
gui.py - Giao dien do hoa PySide6 cho He thong Benchmark Ma hoa Mang.

Ho tro:
- 2 che do van hanh: Local All-in-One, Remote Sender
- Cau hinh linh hoat thuat toan, kich thuoc payload, so luot do
- Tien trinh thoi gian thuc, bang ket qua live, metric cards
- Trinh duyet tich hop 8 bieu do phan giai cao (300 DPI)
- Trinh duyet bang thong ke chi tiet & xuat CSV / bao cao
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import threading
import time

from PySide6.QtCore import QObject, QSize, Qt, QThread, Signal, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Them thu muc hien tai vao sys.path de import cac module benchmark
BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
if BENCH_DIR not in sys.path:
    sys.path.insert(0, BENCH_DIR)

import analyze
import client
import common
import server


# ==============================================================================
# WORKER THREADS (BẤT ĐỒNG BỘ ĐỂ KHÔNG TREO GIAO DIỆN)
# ==============================================================================

class BenchmarkClientWorker(QThread):
    """
    Luồng chạy tiến trình Benchmark Client độc lập:
    - Kế thừa QThread để chạy ngầm dưới nền, tránh làm đơ/treo (freeze) giao diện Qt chính.
    - Phát các tín hiệu (Signals) an toàn về luồng UI:
        + progress_signal: Cập nhật thanh tiến độ và số liệu từng lượt chạy.
        + log_signal: Gửi dòng text ghi log lên màn hình.
        + finished_signal: Báo hiệu khi hoàn thành hoặc có lỗi phát sinh.
    """

    progress_signal = Signal(dict)
    log_signal = Signal(str)
    finished_signal = Signal(bool, str, str)  # (thành_công, thông_điệp, đường_dẫn_csv)

    def __init__(
        self,
        host: str,
        port: int,
        output_csv: str,
        seed: int,
        algorithms: list[str],
        sizes: list[int],
        benchmark_runs: int,
        warmup_runs: int,
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.output_csv = output_csv
        self.seed = seed
        self.algorithms = algorithms
        self.sizes = sizes
        self.benchmark_runs = benchmark_runs
        self.warmup_runs = warmup_runs
        self._is_stopped = False

    def stop(self) -> None:
        """Đặt cờ dừng để ngắt vòng lặp benchmark an toàn."""
        self._is_stopped = True

    def _is_stop_requested(self) -> bool:
        """Kiểm tra xem người dùng đã bấm nút Dừng hay chưa."""
        return self._is_stopped

    def run(self) -> None:
        """Thực thi mã benchmark trong luồng riêng biệt."""
        try:
            self.log_signal.emit(f"[*] Bat dau benchmark toi {self.host}:{self.port} ...")
            
            # Hàm callback chuyển tiếp dữ liệu tiến độ từ client.py thành tín hiệu Qt Signal
            def on_progress(data: dict):
                self.progress_signal.emit(data)

            # Khởi động hàm benchmark đo kiểm chính
            csv_path = client.run_benchmark(
                host=self.host,
                port=self.port,
                output_csv=self.output_csv,
                seed=self.seed,
                algorithms=self.algorithms,
                sizes=self.sizes,
                benchmark_runs=self.benchmark_runs,
                warmup_runs=self.warmup_runs,
                progress_callback=on_progress,
                stop_requested=self._is_stop_requested,
            )
            if self._is_stopped:
                self.finished_signal.emit(False, "Benchmark da bi dung boi nguoi dung.", csv_path)
            else:
                self.finished_signal.emit(True, "Benchmark hoan tat thanh cong!", csv_path)
        except Exception as exc:
            self.finished_signal.emit(False, f"Loi thuc thi benchmark: {exc}", "")


class BenchmarkServerWorker(QThread):
    """
    Luồng chạy Receiver TCP Server ngầm:
    - Lắng nghe kết nối TCP từ máy Sender trên luồng riêng.
    - Hỗ trợ sự kiện stop_event (threading.Event) để dừng server nhanh chóng.
    """

    log_signal = Signal(str)
    started_signal = Signal()
    stopped_signal = Signal()

    def __init__(self, host: str, port: int):
        super().__init__()
        self.host = host
        self.port = port
        self.stop_event = threading.Event()

    def stop(self) -> None:
        """Bật cờ dừng stop_event giải phóng socket server."""
        self.stop_event.set()

    def run(self) -> None:
        """Vòng lặp chạy server giải mã và gửi gói ACK."""
        try:
            self.started_signal.emit()
            server.run_server(
                host=self.host,
                port=self.port,
                stop_event=self.stop_event,
                log_callback=lambda msg: self.log_signal.emit(msg),
            )
        except Exception as exc:
            self.log_signal.emit(f"[!] Loi Server: {exc}")
        finally:
            self.stopped_signal.emit()


class PingWorker(QThread):
    """
    Luồng chạy Ping kiểm tra kết nối mạng không đồng bộ:
    - Tránh đóng băng giao diện khi lệnh ping đang chờ phản hồi ICMP (thường mất 2-5 giây).
    - Tự động nhận diện cú pháp lệnh ping theo hệ điều hành (Windows '-n' vs Linux '-c').
    - Phát tín hiệu finished_signal(kết_quả_thành_công, văn_bản_kết_quả).
    """

    finished_signal = Signal(bool, str)

    def __init__(self, host: str, count: int = 4):
        super().__init__()
        self.host = host
        self.count = count

    def run(self) -> None:
        """Thực thi lệnh ping mạng và phân tích tỷ lệ mất gói."""
        try:
            flag = "-n" if platform.system().lower() == "windows" else "-c"
            cmd = ["ping", flag, str(self.count), self.host]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            out = res.stdout.lower()
            # Kiểm tra xem có đạt 0% mất gói tin hay không
            success = ("0% loss" in out or "0% packet loss" in out or "0.0% packet loss" in out)
            self.finished_signal.emit(success, res.stdout)
        except Exception as exc:
            self.finished_signal.emit(False, f"Loi Ping: {exc}")


class AnalyzeWorker(QThread):
    """
    Luồng chạy phân tích thống kê và vẽ 8 biểu đồ ngầm:
    - Xử lý các phép tính toán ma trận với pandas và vẽ 8 biểu đồ độ phân giải 300 DPI bằng matplotlib.
    - Quá trình này tiêu tốn 1-3 giây CPU, do đó cần đặt trong QThread riêng để thanh tiến độ và giao diện không bị giật lag.
    """

    finished_signal = Signal(bool, str, list)  # (thành_công, thông_điệp, danh_sách_ảnh_biểu_đồ)

    def __init__(self, csv_path: str, charts_dir: str, summary_md: str):
        super().__init__()
        self.csv_path = csv_path
        self.charts_dir = charts_dir
        self.summary_md = summary_md

    def run(self) -> None:
        """Thực hiện chuỗi xử lý thống kê dữ liệu."""
        try:
            # 1. Đọc và kiểm tra cấu trúc dữ liệu CSV
            df = analyze.load_and_validate(self.csv_path)
            # 2. Tính toán các chỉ số Mean, Median, Min, Max, Std
            df_rates, df_stats = analyze.compute_statistics(df)
            # 3. Xuất file CSV thống kê chi tiết
            stat_csv = os.path.join(os.path.dirname(self.csv_path), "detailed_statistics.csv")
            df_stats.to_csv(stat_csv, index=False)
            # 4. Tạo 8 file ảnh biểu đồ PNG 300 DPI
            charts = analyze.generate_charts(df_stats, self.charts_dir)
            # 5. Xuất báo cáo tổng kết ra định dạng Markdown
            analyze.export_markdown_summary(df_rates, df_stats, self.summary_md)
            self.finished_signal.emit(True, "Phan tich va tao 8 bieu do thanh cong!", charts)
        except Exception as exc:
            self.finished_signal.emit(False, f"Loi phan tich: {exc}", [])


# ==============================================================================
# MAIN BENCHMARK GUI WINDOW
# ==============================================================================

class BenchmarkWindow(QMainWindow):
    """Cua so giao dien do hoa dieu khien Benchmark."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hệ thống Benchmark Mã hóa & Truyền tin Mạng Phân tán")
        self.resize(1180, 820)
        self.setMinimumSize(960, 680)

        # Duong dan mac dinh
        self.results_dir = os.path.join(BENCH_DIR, "results")
        os.makedirs(self.results_dir, exist_ok=True)
        self.csv_path = os.path.join(self.results_dir, "benchmark_results.csv")
        self.charts_dir = os.path.join(self.results_dir, "charts")
        self.summary_md = os.path.join(self.results_dir, "summary_table.md")

        # Worker threads
        self._client_worker: BenchmarkClientWorker | None = None
        self._server_worker: BenchmarkServerWorker | None = None
        self._ping_worker: PingWorker | None = None
        self._analyze_worker: AnalyzeWorker | None = None

        self._chart_files: list[str] = []
        self._current_chart_idx: int = 0

        self._build_ui()
        self._load_existing_results_if_any()

    # ------------------------------------------------------------- XAY DUNG UI
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # 1. Header Banner
        header = QFrame()
        header.setFrameShape(QFrame.StyledPanel)
        header.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 6px;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 8, 16, 8)

        title_label = QLabel("🚀 BENCHMARK MÃ HÓA & TRUYỀN TIN MẠNG PHÂN TÁN")
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: #38bdf8;")

        sub_label = QLabel("None | Caesar | Playfair | AES-128-CBC • 1 KB | 100 KB | 1 MB • Windows & Linux")
        sub_label.setFont(QFont("Arial", 9))
        sub_label.setStyleSheet("color: #94a3b8;")

        t_col = QVBoxLayout()
        t_col.addWidget(title_label)
        t_col.addWidget(sub_label)
        h_layout.addLayout(t_col)
        h_layout.addStretch()

        self.btn_clear_header = QPushButton("🗑️ Xóa kết quả cũ")
        self.btn_clear_header.setStyleSheet(
            "background-color: #c2410c; color: white; padding: 6px 12px; font-weight: bold; border-radius: 4px;"
        )
        self.btn_clear_header.setToolTip("Xóa toàn bộ dữ liệu CSV, bảng thống kê và 8 ảnh biểu đồ cũ")
        self.btn_clear_header.clicked.connect(self._on_clear_results_clicked)
        h_layout.addWidget(self.btn_clear_header)

        self.btn_open_folder = QPushButton("📁 Thư mục kết quả")
        self.btn_open_folder.setStyleSheet("padding: 6px 12px; font-weight: bold;")
        self.btn_open_folder.clicked.connect(self._on_open_results_folder)
        h_layout.addWidget(self.btn_open_folder)

        root_layout.addWidget(header)

        # 2. Tabs
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Arial", 10, QFont.Bold))

        self.tab_exec = QWidget()
        self.tab_charts = QWidget()
        self.tab_stats = QWidget()

        self.tabs.addTab(self.tab_exec, "🕹️ Thực thi Benchmark")
        self.tabs.addTab(self.tab_charts, "📊 Xem 8 Biểu đồ")
        self.tabs.addTab(self.tab_stats, "📋 Bảng Thống kê & Báo cáo")

        root_layout.addWidget(self.tabs, stretch=1)

        # Xay dung noi dung tung Tab
        self._build_tab_execution()
        self._build_tab_charts()
        self._build_tab_stats()

    # ------------------------------------------------------------- TAB 1: EXECUTION
    def _build_tab_execution(self) -> None:
        layout = QVBoxLayout(self.tab_exec)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Hang tren: Cau hinh Che do + Ket noi + Kich ban
        top_grid = QGridLayout()
        top_grid.setSpacing(10)

        # Group 1: Che do van hanh
        self.mode_group = QGroupBox("1. Chế độ Vận hành (Execution Mode)")
        mode_layout = QVBoxLayout(self.mode_group)
        mode_layout.setSpacing(6)

        self.radio_local = QRadioButton("Tự động toàn bộ (Local All-in-One)")
        self.radio_local.setChecked(True)
        self.radio_sender = QRadioButton("Sender Server (Đo đạc từ xa -> VM2 Receiver)")
        self.radio_server = QRadioButton("Receiver Server (Lắng nghe đo đạc từ máy Sender)")

        self.mode_btn_group = QButtonGroup(self)
        self.mode_btn_group.addButton(self.radio_local, 1)
        self.mode_btn_group.addButton(self.radio_sender, 2)
        self.mode_btn_group.addButton(self.radio_server, 3)
        self.mode_btn_group.idClicked.connect(self._on_mode_changed)

        mode_layout.addWidget(self.radio_local)
        mode_layout.addWidget(self.radio_sender)
        mode_layout.addWidget(self.radio_server)

        self.lbl_mode_hint = QLabel("💡 Tự động chạy Server ngầm + Client đo đạc trên máy (127.0.0.1).")
        self.lbl_mode_hint.setStyleSheet("color: #94a3b8; font-size: 11px; font-style: italic;")
        self.lbl_mode_hint.setWordWrap(True)
        mode_layout.addWidget(self.lbl_mode_hint)
        mode_layout.addStretch()

        top_grid.addWidget(self.mode_group, 0, 0)

        # Group 2: Dia chi mang & Ping
        net_group = QGroupBox("2. Cấu hình Mạng TCP (Target Host & Port)")
        net_layout = QGridLayout(net_group)

        net_layout.addWidget(QLabel("Địa chỉ IP:"), 0, 0)
        self.edit_host = QLineEdit("127.0.0.1")
        net_layout.addWidget(self.edit_host, 0, 1)

        net_layout.addWidget(QLabel("Cổng TCP:"), 1, 0)
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setValue(5000)
        net_layout.addWidget(self.spin_port, 1, 1)

        self.btn_ping = QPushButton("📡 Kiểm tra Ping")
        self.btn_ping.clicked.connect(self._on_ping_test)
        net_layout.addWidget(self.btn_ping, 2, 0, 1, 2)
        top_grid.addWidget(net_group, 0, 1)

        # Group 3: Kich ban do dac
        self.scenario_group = QGroupBox("3. Kịch bản Đo đạc (Algorithms & Sizes)")
        sc_layout = QGridLayout(self.scenario_group)

        # Chon thuat toan
        sc_layout.addWidget(QLabel("<b>Thuật toán:</b>"), 0, 0)
        self.cb_none = QCheckBox("None")
        self.cb_caesar = QCheckBox("Caesar")
        self.cb_playfair = QCheckBox("Playfair")
        self.cb_aes = QCheckBox("AES-128-CBC")
        for cb in (self.cb_none, self.cb_caesar, self.cb_playfair, self.cb_aes):
            cb.setChecked(True)

        algo_h = QHBoxLayout()
        algo_h.addWidget(self.cb_none)
        algo_h.addWidget(self.cb_caesar)
        algo_h.addWidget(self.cb_playfair)
        algo_h.addWidget(self.cb_aes)
        sc_layout.addLayout(algo_h, 0, 1)

        # Chon size
        sc_layout.addWidget(QLabel("<b>Kích thước:</b>"), 1, 0)
        self.cb_1kb = QCheckBox("1 KB")
        self.cb_100kb = QCheckBox("100 KB")
        self.cb_1mb = QCheckBox("1 MB")
        for cb in (self.cb_1kb, self.cb_100kb, self.cb_1mb):
            cb.setChecked(True)

        size_h = QHBoxLayout()
        size_h.addWidget(self.cb_1kb)
        size_h.addWidget(self.cb_100kb)
        size_h.addWidget(self.cb_1mb)
        sc_layout.addLayout(size_h, 1, 1)

        # So lan do
        sc_layout.addWidget(QLabel("<b>Số lần đo chính:</b>"), 2, 0)
        self.spin_runs = QSpinBox()
        self.spin_runs.setRange(1, 100)
        self.spin_runs.setValue(30)
        sc_layout.addWidget(self.spin_runs, 2, 1)

        top_grid.addWidget(self.scenario_group, 0, 2)
        layout.addLayout(top_grid)

        # Hang 2: Action Buttons + Progress Bar
        action_row = QHBoxLayout()
        self.btn_start = QPushButton("▶ BẮT ĐẦU BENCHMARK")
        self.btn_start.setFont(QFont("Arial", 11, QFont.Bold))
        self.btn_start.setStyleSheet(
            "background-color: #15803d; color: white; padding: 10px 20px; border-radius: 6px;"
        )
        self.btn_start.clicked.connect(self._on_start_clicked)

        self.btn_stop = QPushButton("⏹ DỪNG LẠI")
        self.btn_stop.setFont(QFont("Arial", 11, QFont.Bold))
        self.btn_stop.setStyleSheet(
            "background-color: #b91c1c; color: white; padding: 10px 20px; border-radius: 6px;"
        )
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_clicked)

        self.btn_clear = QPushButton("🗑️ XÓA KẾT QUẢ CŨ")
        self.btn_clear.setFont(QFont("Arial", 11, QFont.Bold))
        self.btn_clear.setStyleSheet(
            "background-color: #c2410c; color: white; padding: 10px 18px; border-radius: 6px;"
        )
        self.btn_clear.setToolTip("Xóa toàn bộ file kết quả CSV, bảng thống kê và 8 ảnh biểu đồ cũ để chuẩn bị lần chạy mới")
        self.btn_clear.clicked.connect(self._on_clear_results_clicked)

        self.btn_reanalyze = QPushButton("🔄 Phân tích lại CSV & Sinh 8 Biểu đồ")
        self.btn_reanalyze.setStyleSheet("padding: 8px 14px; font-weight: bold;")
        self.btn_reanalyze.clicked.connect(self._on_reanalyze_clicked)

        action_row.addWidget(self.btn_start, stretch=2)
        action_row.addWidget(self.btn_stop, stretch=1)
        action_row.addWidget(self.btn_clear, stretch=1)
        action_row.addWidget(self.btn_reanalyze, stretch=1)
        layout.addLayout(action_row)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Sẵn sàng khởi chạy ...")
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setStyleSheet(
            "QProgressBar { height: 26px; font-size: 11px; font-weight: bold; border-radius: 4px; text-align: center; } "
            "QProgressBar::chunk { background-color: #0284c7; }"
        )
        layout.addWidget(self.progress_bar)

        # Metric Cards
        card_row = QHBoxLayout()
        card_row.setSpacing(8)

        def make_card(title: str):
            f = QFrame()
            f.setFrameShape(QFrame.StyledPanel)
            f.setStyleSheet("background-color: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 4px;")
            l = QVBoxLayout(f)
            l.setContentsMargins(6, 4, 6, 4)
            t = QLabel(title)
            t.setFont(QFont("Arial", 8, QFont.Bold))
            t.setStyleSheet("color: #94a3b8;")
            v = QLabel("--")
            v.setFont(QFont("Arial", 12, QFont.Bold))
            v.setStyleSheet("color: #38bdf8;")
            l.addWidget(t)
            l.addWidget(v)
            return f, v

        self.card_progress_frame, self.lbl_card_progress = make_card("TIẾN ĐỘ THỰC HIỆN")
        self.card_latest_frame, self.lbl_card_latest = make_card("LƯỢT VỪA XONG")
        self.card_time_frame, self.lbl_card_time = make_card("THỜI GIAN (ENC / DEC / RTT)")
        self.card_res_frame, self.lbl_card_res = make_card("TÀI NGUYÊN (CPU / RAM)")

        card_row.addWidget(self.card_progress_frame)
        card_row.addWidget(self.card_latest_frame)
        card_row.addWidget(self.card_time_frame)
        card_row.addWidget(self.card_res_frame)
        layout.addLayout(card_row)

        # Splitter: Live Table + Log
        splitter = QSplitter(Qt.Vertical)

        # Live Table Widget
        self.table_live = QTableWidget()
        self.table_live.setColumnCount(13)
        self.table_live.setHorizontalHeaderLabels([
            "ID", "Thuật toán", "Payload", "Ciphertext", "Packet",
            "Mã hóa (ms)", "Giải mã (ms)", "RTT (ms)", "Tổng (ms)",
            "Thông lượng (KB/s)", "CPU Sender/Recv", "RAM Sender/Recv", "Trạng thái"
        ])
        self.table_live.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_live.horizontalHeader().setStretchLastSection(True)
        self.table_live.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_live.setAlternatingRowColors(True)
        splitter.addWidget(self.table_live)

        # Log Console
        self.txt_log = QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(150)
        self.txt_log.setFont(QFont("Consolas", 9))
        self.txt_log.setStyleSheet("background-color: #020617; color: #a5f3fc; border-radius: 4px;")
        splitter.addWidget(self.txt_log)

        splitter.setSizes([320, 110])
        layout.addWidget(splitter, stretch=1)
        self._on_mode_changed(1)

    # ------------------------------------------------------------- TAB 2: 8 CHARTS VIEWER
    def _build_tab_charts(self) -> None:
        layout = QVBoxLayout(self.tab_charts)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Controls bar
        ctrl_bar = QHBoxLayout()
        ctrl_bar.addWidget(QLabel("<b>Chọn biểu đồ để xem:</b>"))

        self.combo_charts = QComboBox()
        self.combo_charts.setMinimumWidth(400)
        self.combo_charts.addItems([
            "01_encryption_time.png - 1. Thời gian Mã hóa trung bình (Encryption Time)",
            "02_decryption_time.png - 2. Thời gian Giải mã trung bình (Decryption Time)",
            "03_rtt.png - 3. Độ trễ mạng hai chiều RTT (Round Trip Time)",
            "04_total_time.png - 4. Tổng thời gian thực thi (Total Time = Encrypt + RTT)",
            "05_sizes.png - 5. Kích thước gói tin truyền tải (Packet Size)",
            "06_throughput.png - 6. Băng thông truyền tải hệ thống (Throughput)",
            "07_cpu_usage.png - 7. Mức độ sử dụng CPU % (Sender vs Receiver)",
            "08_ram_usage.png - 8. Tiêu thụ Bộ nhớ RAM (Process RSS & Delta)",
            "09_security_comparison.png - 9. Đánh giá So sánh Độ an toàn Mật mã học (Security Comparison)",
        ])
        self.combo_charts.currentIndexChanged.connect(self._on_combo_chart_changed)
        ctrl_bar.addWidget(self.combo_charts)

        self.btn_prev_chart = QPushButton("◀ Trước")
        self.btn_prev_chart.clicked.connect(self._on_prev_chart)
        ctrl_bar.addWidget(self.btn_prev_chart)

        self.btn_next_chart = QPushButton("Sau ▶")
        self.btn_next_chart.clicked.connect(self._on_next_chart)
        ctrl_bar.addWidget(self.btn_next_chart)

        self.btn_reload_charts = QPushButton("🔄 Tải lại biểu đồ")
        self.btn_reload_charts.clicked.connect(self._load_charts_into_viewer)
        ctrl_bar.addWidget(self.btn_reload_charts)

        ctrl_bar.addStretch()
        layout.addLayout(ctrl_bar)

        # Scroll Area for Chart Image
        self.scroll_chart = QScrollArea()
        self.scroll_chart.setWidgetResizable(True)
        self.scroll_chart.setStyleSheet("background-color: #1e293b; border-radius: 6px;")

        self.lbl_chart_img = QLabel()
        self.lbl_chart_img.setAlignment(Qt.AlignCenter)
        self.lbl_chart_img.setText("Chưa có biểu đồ. Hãy chạy Benchmark hoặc bấm 'Phân tích lại CSV & Sinh 9 Biểu đồ'.")
        self.lbl_chart_img.setFont(QFont("Arial", 11))
        self.lbl_chart_img.setStyleSheet("color: #94a3b8;")
        self.scroll_chart.setWidget(self.lbl_chart_img)

        layout.addWidget(self.scroll_chart, stretch=1)

    # ------------------------------------------------------------- TAB 3: STATS & REPORT
    def _build_tab_stats(self) -> None:
        layout = QVBoxLayout(self.tab_stats)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        btn_row = QHBoxLayout()
        self.btn_open_csv = QPushButton("📊 Mở file dữ liệu CSV (benchmark_results.csv)")
        self.btn_open_csv.clicked.connect(self._on_open_csv)
        btn_row.addWidget(self.btn_open_csv)

        self.btn_open_report = QPushButton("📄 Mở Báo cáo Benchmark chi tiết (Markdown)")
        self.btn_open_report.clicked.connect(self._on_open_report)
        btn_row.addWidget(self.btn_open_report)

        self.btn_stats_clear = QPushButton("🗑️ Xóa kết quả & Biểu đồ cũ")
        self.btn_stats_clear.setStyleSheet("padding: 6px 12px; font-weight: bold; color: #f87171;")
        self.btn_stats_clear.setToolTip("Xóa toàn bộ kết quả để chạy lại lượt đo mới")
        self.btn_stats_clear.clicked.connect(self._on_clear_results_clicked)
        btn_row.addWidget(self.btn_stats_clear)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Bang Thong ke
        self.table_stats = QTableWidget()
        self.table_stats.setColumnCount(13)
        self.table_stats.setHorizontalHeaderLabels([
            "Thuật toán", "Kích thước", "Ciphertext (B)", "Packet (B)",
            "Encrypt Mean (ms)", "Decrypt Mean (ms)", "RTT Mean (ms)",
            "Total Mean (ms)", "Total Median (ms)", "Throughput (KB/s)",
            "Sender CPU (%)", "Sender RAM (MB)", "Receiver RAM (MB)"
        ])
        self.table_stats.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_stats.horizontalHeader().setStretchLastSection(True)
        self.table_stats.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_stats.setAlternatingRowColors(True)
        layout.addWidget(self.table_stats, stretch=1)

    # ------------------------------------------------------------- LOGGING & HELPERS
    # ------------------------------------------------------------- LOGGING & HELPERS
    def append_log(self, text: str) -> None:
        """Ghi dòng nhật ký kèm mốc thời gian (timestamp) vào ô văn bản phía dưới."""
        t_str = time.strftime("%H:%M:%S")
        self.txt_log.appendPlainText(f"[{t_str}] {text}")
        # Tự động cuộn xuống dòng cuối cùng để người dùng theo dõi log mới nhất
        self.txt_log.verticalScrollBar().setValue(self.txt_log.verticalScrollBar().maximum())

    # ------------------------------------------------------------- LOGIC CHUYỂN ĐỔI CHẾ ĐỘ
    def _on_mode_changed(self, mode_id: int) -> None:
        """
        Xử lý khi người dùng chọn 1 trong 3 chế độ vận hành:
        1: Tự động toàn bộ (Local All-in-One) -> Chạy cả Receiver ngầm và Client đo đạc trên 127.0.0.1.
        2: Sender Server -> Máy này đóng vai trò Client đo đạc, gửi gói tin tới Receiver VM2 từ xa.
        3: Receiver Server -> Máy này đóng vai trò Server lắng nghe trên 0.0.0.0, tự động giải mã và gửi ACK.
        """
        if mode_id == 1:  # Local All-in-One
            self.edit_host.setText("127.0.0.1")
            self.edit_host.setEnabled(False)
            self.spin_port.setEnabled(True)
            self.btn_ping.setEnabled(False)
            if hasattr(self, "scenario_group"):
                self.scenario_group.setEnabled(True)
            self.btn_start.setText("▶ BẮT ĐẦU BENCHMARK (LOCAL)")
            if hasattr(self, "lbl_mode_hint"):
                self.lbl_mode_hint.setText("💡 Tự động chạy Server ngầm + Client đo đạc trên máy (127.0.0.1).")
            self.append_log("Đã chuyển sang chế độ: Tự động toàn bộ (Local All-in-One).")
        elif mode_id == 2:  # Sender Server
            if self.edit_host.text() in ("127.0.0.1", "0.0.0.0") or not self.edit_host.text().strip():
                self.edit_host.setText("192.168.1.100")
            self.edit_host.setEnabled(True)
            self.spin_port.setEnabled(True)
            self.btn_ping.setEnabled(True)
            if hasattr(self, "scenario_group"):
                self.scenario_group.setEnabled(True)
            self.btn_start.setText("▶ BẮT ĐẦU BENCHMARK (SENDER SERVER)")
            if hasattr(self, "lbl_mode_hint"):
                self.lbl_mode_hint.setText("💡 Chế độ Sender Server: Kết nối tới máy chủ Receiver trên VM2 từ xa qua IP:Port.")
            self.append_log("Đã chuyển sang chế độ: Sender Server (Đo đạc từ xa -> VM2 Receiver).")
        elif mode_id == 3:  # Receiver Server
            self.edit_host.setText("0.0.0.0")
            self.edit_host.setEnabled(False)
            self.spin_port.setEnabled(True)
            self.btn_ping.setEnabled(False)
            if hasattr(self, "scenario_group"):
                self.scenario_group.setEnabled(False)
            self.btn_start.setText("▶ KHỞI ĐỘNG RECEIVER SERVER")
            if hasattr(self, "lbl_mode_hint"):
                self.lbl_mode_hint.setText("💡 Chế độ Receiver Server: Lắng nghe kết nối đo đạc từ máy Sender (0.0.0.0:Port). Tự động giải mã và gửi ACK.")
            self.append_log("Đã chuyển sang chế độ: Receiver Server (Lắng nghe đo đạc từ máy Sender).")

    # ------------------------------------------------------------- PING TEST
    def _on_ping_test(self) -> None:
        """Kích hoạt tiến trình Ping kiểm tra chất lượng kết nối tới máy Receiver từ xa."""
        host = self.edit_host.text().strip()
        if not host:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập IP máy đích cần ping!")
            return
        self.append_log(f"Đang thực hiện Ping test tới {host} ...")
        self.btn_ping.setEnabled(False)

        # Khởi chạy PingWorker trong luồng nền
        self._ping_worker = PingWorker(host, count=4)
        def on_ping_finished(success: bool, output: str):
            self.btn_ping.setEnabled(True)
            self.append_log(output)
            if success:
                QMessageBox.information(self, "Ping thành công", f"Kết nối mạng tới {host} hoàn hảo (0% mất gói)!")
            else:
                QMessageBox.warning(self, "Ping thất bại / Cảnh báo", f"Không thể ping tới {host} hoặc có hiện tượng mất gói!\nHãy kiểm tra Firewall hoặc Adapter mạng.")

        self._ping_worker.finished_signal.connect(on_ping_finished)
        self._ping_worker.start()

    # ------------------------------------------------------------- START / STOP BENCHMARK
    def _on_start_clicked(self) -> None:
        """Xử lý sự kiện khi người dùng bấm nút BẮT ĐẦU BENCHMARK."""
        mode_id = self.mode_btn_group.checkedId()
        port = self.spin_port.value()

        # Trường hợp 3: Chế độ Receiver Server (Máy chủ lắng nghe đo đạc từ máy Sender)
        if mode_id == 3:
            self._start_server_mode(host="0.0.0.0", port=port)
            return

        host = self.edit_host.text().strip()

        # Thu thập danh sách các thuật toán được tích chọn trên giao diện
        selected_algos = []
        if self.cb_none.isChecked():
            selected_algos.append(common.ALGO_NONE)
        if self.cb_caesar.isChecked():
            selected_algos.append(common.ALGO_CAESAR)
        if self.cb_playfair.isChecked():
            selected_algos.append(common.ALGO_PLAYFAIR)
        if self.cb_aes.isChecked():
            selected_algos.append(common.ALGO_AES_128_CBC)

        if not selected_algos:
            QMessageBox.warning(self, "Chưa chọn thuật toán", "Vui lòng chọn ít nhất 1 thuật toán để đo đạc!")
            return

        # Thu thập danh sách các kích thước payload được tích chọn
        selected_sizes = []
        if self.cb_1kb.isChecked():
            selected_sizes.append(1024)
        if self.cb_100kb.isChecked():
            selected_sizes.append(102400)
        if self.cb_1mb.isChecked():
            selected_sizes.append(1048576)

        if not selected_sizes:
            QMessageBox.warning(self, "Chưa chọn kích thước", "Vui lòng chọn ít nhất 1 kích thước dữ liệu!")
            return

        runs = self.spin_runs.value()
        warmup = 1

        # Trường hợp 1: Chế độ Local All-in-One (Tự khởi động Receiver ngầm rồi chạy Client)
        if mode_id == 1:
            self._start_local_mode(
                port=port,
                algorithms=selected_algos,
                sizes=selected_sizes,
                runs=runs,
                warmup=warmup,
            )
            return

        # Truong hop 2: Sender Server
        if mode_id == 2:
            self._start_client_mode(
                host=host,
                port=port,
                algorithms=selected_algos,
                sizes=selected_sizes,
                runs=runs,
                warmup=warmup,
            )

    def _set_running_state(self, running: bool) -> None:
        """Cập nhật trạng thái kích hoạt của các nút điều khiển khi tiến trình đang chạy/dừng."""
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        if hasattr(self, "mode_group"):
            self.mode_group.setEnabled(not running)
        if hasattr(self, "btn_clear"):
            self.btn_clear.setEnabled(not running)
        if hasattr(self, "btn_clear_header"):
            self.btn_clear_header.setEnabled(not running)
        if hasattr(self, "btn_stats_clear"):
            self.btn_stats_clear.setEnabled(not running)
        self.btn_reanalyze.setEnabled(not running)

    def _start_server_mode(self, host: str, port: int) -> None:
        """Khởi chạy máy chủ Receiver Benchmark độc lập trên luồng riêng."""
        self._set_running_state(True)
        self.btn_stop.setText("⏹ DỪNG RECEIVER SERVER")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(f"Receiver Server đang lắng nghe tại {host}:{port} ...")
        self.append_log(f"[*] Khởi động Receiver Server tại {host}:{port} (chờ kết nối từ máy Sender)...")

        # Khởi tạo BenchmarkServerWorker và gắn các tín hiệu kết nối
        self._server_worker = BenchmarkServerWorker(host, port)
        self._server_worker.log_signal.connect(self.append_log)
        def on_server_stopped():
            self._set_running_state(False)
            self.btn_stop.setText("⏹ DỪNG LẠI")
            self.progress_bar.setFormat("Receiver Server đã dừng.")
            self.append_log("[*] Receiver Server đã dừng lắng nghe.")
        self._server_worker.stopped_signal.connect(on_server_stopped)
        self._server_worker.start()

    def _start_local_mode(
        self,
        port: int,
        algorithms: list[str],
        sizes: list[int],
        runs: int,
        warmup: int,
    ) -> None:
        """
        Khởi chạy chế độ kiểm thử nội bộ tự động (Local All-in-One):
        - Bước 1: Khởi động Receiver Server ngầm tại 127.0.0.1.
        - Bước 2: Khởi động Client đo đạc kết nối tới Server vừa mở.
        """
        self._set_running_state(True)
        self.table_live.setRowCount(0)
        self.progress_bar.setValue(0)
        self.append_log("[1/2] Đang khởi động Server ngầm tại 127.0.0.1 ...")

        # Bước 1: Khởi động server ngầm
        self._server_worker = BenchmarkServerWorker("127.0.0.1", port)
        self._server_worker.log_signal.connect(self.append_log)
        self._server_worker.start()

        time.sleep(0.3)  # Chờ 300ms để server kịp bind cổng và bắt đầu listen

        # Bước 2: Khởi động tiến trình đo đạc của Client
        self.append_log("[2/2] Đang khởi động tiến trình Benchmark Client ...")
        self._start_client_worker(
            host="127.0.0.1",
            port=port,
            algorithms=algorithms,
            sizes=sizes,
            runs=runs,
            warmup=warmup,
        )

    def _start_client_mode(
        self,
        host: str,
        port: int,
        algorithms: list[str],
        sizes: list[int],
        runs: int,
        warmup: int,
    ) -> None:
        """Khởi chạy chế độ Sender đo đạc tới máy Receiver từ xa (qua mạng LAN/VM)."""
        self._set_running_state(True)
        self.table_live.setRowCount(0)
        self.progress_bar.setValue(0)
        self.append_log(f"Khởi động Benchmark Client kết nối tới {host}:{port} ...")

        self._start_client_worker(
            host=host,
            port=port,
            algorithms=algorithms,
            sizes=sizes,
            runs=runs,
            warmup=warmup,
        )

    def _start_client_worker(
        self,
        host: str,
        port: int,
        algorithms: list[str],
        sizes: list[int],
        runs: int,
        warmup: int,
    ) -> None:
        """Khởi tạo luồng BenchmarkClientWorker và gắn các hàm lắng nghe tín hiệu Qt."""
        self._client_worker = BenchmarkClientWorker(
            host=host,
            port=port,
            output_csv=self.csv_path,
            seed=42,
            algorithms=algorithms,
            sizes=sizes,
            benchmark_runs=runs,
            warmup_runs=warmup,
        )
        self._client_worker.progress_signal.connect(self._on_client_progress)
        self._client_worker.log_signal.connect(self.append_log)
        self._client_worker.finished_signal.connect(self._on_client_finished)
        self._client_worker.start()

    def _on_stop_clicked(self) -> None:
        """Xử lý khi người dùng nhấn nút DỪNG LẠI."""
        self.append_log("Đang yêu cầu dừng tiến trình ...")
        if self._client_worker and self._client_worker.isRunning():
            self._client_worker.stop()
        if self._server_worker and self._server_worker.isRunning():
            self._server_worker.stop()
        self.btn_stop.setEnabled(False)

    # ------------------------------------------------------------- CẬP NHẬT GIAO DIỆN REAL-TIME
    @Slot(dict)
    def _on_client_progress(self, data: dict) -> None:
        """
        Khe nhận tín hiệu (Slot) từ ClientWorker mỗi khi hoàn thành 1 lượt chạy:
        - Cập nhật % và trạng thái text trên thanh ProgressBar.
        - Cập nhật 4 thẻ chỉ số nhanh (Metric Cards): Tiến độ, Lượt vừa xong, Thời gian, Tài nguyên CPU/RAM.
        - Thêm một hàng dữ liệu mới vào bảng hiển thị trực tiếp (Live Table).
        """
        current_run = data.get("current_run", 0)
        total_runs = data.get("total_runs", 1)
        pct = int((current_run / total_runs) * 100) if total_runs > 0 else 0
        self.progress_bar.setValue(pct)

        algo = data.get("algo", "")
        sz = data.get("size_bytes", 0)
        sz_kb = sz // 1024 if sz >= 1024 else sz
        is_warmup = data.get("is_warmup", False)

        # Nếu là lượt warm-up khởi động: chỉ cập nhật thanh tiến độ, không thêm vào bảng kết quả chính
        if is_warmup:
            self.progress_bar.setFormat(f"[{pct}%] Warm-up: {algo} {sz_kb} KB ({current_run}/{total_runs})")
            self.lbl_card_latest.setText(f"{algo} - {sz_kb} KB (Warm-up)")
            return

        row = data.get("row")
        if not row:
            return

        # Cập nhật thông tin chi tiết của lượt đo chính thức
        self.progress_bar.setFormat(f"[{pct}%] Run {row['run_id']}: {algo} {sz_kb} KB ({current_run}/{total_runs})")
        self.lbl_card_progress.setText(f"{current_run} / {total_runs} ({pct}%)")
        self.lbl_card_latest.setText(f"Run #{row['run_id']:03d} • {algo} • {sz_kb} KB")
        self.lbl_card_time.setText(f"E:{row['encryption_ms']:.1f}ms | D:{row['decrypt_ms']:.1f}ms | RTT:{row['rtt_ms']:.1f}ms")
        self.lbl_card_res.setText(f"CPU: {row['enc_cpu_pct']:.0f}%/{row['dec_cpu_pct']:.0f}% | RAM: {row['enc_ram_mb']:.1f}M")

        # Chèn hàng dữ liệu mới vào Live Table
        r_idx = self.table_live.rowCount()
        self.table_live.insertRow(r_idx)

        items = [
            f"#{row['run_id']:03d}",
            str(row['algorithm']),
            f"{sz_kb} KB",
            f"{row['ciphertext_size_bytes']:,} B",
            f"{row['packet_size_bytes']:,} B",
            f"{row['encryption_ms']:.2f}",
            f"{row['decrypt_ms']:.2f}",
            f"{row['rtt_ms']:.2f}",
            f"{row['total_ms']:.2f}",
            f"{row['throughput_kbps']:,.1f}",
            f"{row['enc_cpu_pct']:.1f}% / {row['dec_cpu_pct']:.1f}%",
            f"{row['enc_ram_mb']:.1f}M / {row['dec_ram_mb']:.1f}M",
            "PASS" if row["success"] else "FAIL",
        ]
        for col, val in enumerate(items):
            it = QTableWidgetItem(val)
            it.setTextAlignment(Qt.AlignCenter)
            if col == 12:
                it.setForeground(QColor("#16a34a" if row["success"] else "#dc2626"))
                it.setFont(QFont("Arial", 9, QFont.Bold))
            self.table_live.setItem(r_idx, col, it)

        self.table_live.scrollToBottom()

    @Slot(bool, str, str)
    def _on_client_finished(self, success: bool, message: str, csv_path: str) -> None:
        self._set_running_state(False)

        # Dung server ngam neu dang chay local
        if self._server_worker and self._server_worker.isRunning():
            self._server_worker.stop()

        self.append_log(f"[+] {message}")
        if success and csv_path and os.path.exists(csv_path):
            self.append_log("Đang tự động chạy phân tích thống kê và vẽ 8 biểu đồ ...")
            self._run_analyze_process()
        else:
            QMessageBox.information(self, "Thông báo", message)

    # ------------------------------------------------------------- RE-ANALYZE & CHARTS
    def _on_reanalyze_clicked(self) -> None:
        if not os.path.exists(self.csv_path):
            QMessageBox.warning(self, "Không tìm thấy dữ liệu", f"Chưa có file kết quả: {self.csv_path}\nHãy chạy benchmark trước!")
            return
        self._run_analyze_process()

    def _run_analyze_process(self) -> None:
        self.append_log("[*] Khởi động luồng tính toán thống kê và vẽ 8 biểu đồ độ phân giải cao ...")
        self._set_running_state(True)

        self._analyze_worker = AnalyzeWorker(self.csv_path, self.charts_dir, self.summary_md)
        def on_analyze_finished(succ: bool, msg: str, charts: list):
            self._set_running_state(False)
            self.append_log(f"[+] {msg}")
            if succ:
                self._load_charts_into_viewer()
                self._load_stats_table()
                self.tabs.setCurrentIndex(1)  # Chuyen sang tab bieu do
                QMessageBox.information(self, "Hoàn tất", "Đã phân tích số liệu và tạo thành công 9 biểu đồ phân tích!")
            else:
                QMessageBox.critical(self, "Lỗi phân tích", msg)

        self._analyze_worker.finished_signal.connect(on_analyze_finished)
        self._analyze_worker.start()

    # ------------------------------------------------------------- CLEAR RESULTS
    def _on_clear_results_clicked(self) -> None:
        """Xóa toàn bộ kết quả cũ bao gồm các file dữ liệu và ảnh biểu đồ để chuẩn bị cho lần chạy mới."""
        if (self._client_worker and self._client_worker.isRunning()) or \
           (self._server_worker and self._server_worker.isRunning()) or \
           (self._analyze_worker and self._analyze_worker.isRunning()):
            QMessageBox.warning(
                self,
                "Tiến trình đang chạy",
                "Hệ thống đang thực hiện đo đạc hoặc phân tích dữ liệu.\n"
                "Vui lòng dừng tiến trình trước khi xóa kết quả cũ!",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa kết quả cũ",
            "Bạn có chắc chắn muốn xóa toàn bộ kết quả cũ để chuẩn bị cho lần chạy mới không?\n\n"
            "Các mục sẽ bị xóa:\n"
            "  • Dữ liệu đo thô: benchmark_results.csv\n"
            "  • Bảng thống kê chi tiết: detailed_statistics.csv\n"
            "  • Báo cáo tổng hợp: summary_table.md\n"
            "  • Toàn bộ 9 ảnh biểu đồ phân tích trong thư mục charts/\n\n"
            "Bảng dữ liệu và giao diện sẽ được làm mới hoàn toàn.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        deleted_files, locked_files = common.clear_benchmark_results(self.results_dir)

        # 1. Reset Tab 1: Live table, progress bar, metric cards
        self.table_live.setRowCount(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Sẵn sàng khởi chạy ...")
        self.lbl_card_progress.setText("--")
        self.lbl_card_latest.setText("--")
        self.lbl_card_time.setText("--")
        self.lbl_card_res.setText("--")

        # 2. Reset Tab 2: Trình xem biểu đồ
        self._chart_files = []
        self.lbl_chart_img.clear()
        self.lbl_chart_img.setText(
            "Chưa có biểu đồ. Dữ liệu và ảnh cũ đã được xóa sạch.\n"
            "Hãy nhấn 'BẮT ĐẦU BENCHMARK' để chạy lần đo mới hoặc bấm 'Phân tích lại CSV & Sinh 9 Biểu đồ'."
        )

        # 3. Reset Tab 3: Bảng thống kê
        self.table_stats.setRowCount(0)

        # 4. Ghi log và thông báo kết quả
        if locked_files:
            self.append_log(
                f"[!] Cảnh báo dọn dẹp: Đã xóa {len(deleted_files)} tệp, nhưng có {len(locked_files)} tệp bị khóa (ví dụ bởi Excel): {', '.join(locked_files)}"
            )
            QMessageBox.warning(
                self,
                "Cảnh báo tệp đang mở",
                f"Đã xóa {len(deleted_files)} tệp kết quả cũ.\n\n"
                f"Tuy nhiên, có {len(locked_files)} tệp không thể xóa vì đang được mở bởi ứng dụng khác:\n"
                + "\n".join(f"  • {f}" for f in locked_files)
                + "\n\nVui lòng đóng các tệp trên và thử lại nếu cần xóa sạch hoàn toàn.",
            )
        else:
            self.append_log(
                f"🗑️ [DỌN DẸP] Đã xóa thành công toàn bộ {len(deleted_files)} tệp kết quả cũ (dữ liệu CSV, bảng thống kê và 9 ảnh biểu đồ)."
            )
            self.append_log("[i] Hệ thống và giao diện đã được đặt lại trạng thái ban đầu, sẵn sàng cho lần chạy mới.")
            QMessageBox.information(
                self,
                "Đã xóa kết quả thành công",
                f"Đã xóa thành công toàn bộ {len(deleted_files)} tệp kết quả cũ (bao gồm ảnh biểu đồ và dữ liệu CSV/báo cáo)!\n\n"
                "Giao diện đã được làm mới hoàn toàn, sẵn sàng cho lần chạy đo đạc mới.",
            )

    # ------------------------------------------------------------- CHARTS VIEWER
    def _load_charts_into_viewer(self) -> None:
        self._chart_files = [
            os.path.join(self.charts_dir, "01_encryption_time.png"),
            os.path.join(self.charts_dir, "02_decryption_time.png"),
            os.path.join(self.charts_dir, "03_rtt.png"),
            os.path.join(self.charts_dir, "04_total_time.png"),
            os.path.join(self.charts_dir, "05_sizes.png"),
            os.path.join(self.charts_dir, "06_throughput.png"),
            os.path.join(self.charts_dir, "07_cpu_usage.png"),
            os.path.join(self.charts_dir, "08_ram_usage.png"),
            os.path.join(self.charts_dir, "09_security_comparison.png"),
        ]
        self._show_chart(self.combo_charts.currentIndex())

    def _on_combo_chart_changed(self, idx: int) -> None:
        self._show_chart(idx)

    def _on_prev_chart(self) -> None:
        idx = max(0, self.combo_charts.currentIndex() - 1)
        self.combo_charts.setCurrentIndex(idx)

    def _on_next_chart(self) -> None:
        idx = min(self.combo_charts.count() - 1, self.combo_charts.currentIndex() + 1)
        self.combo_charts.setCurrentIndex(idx)

    def _show_chart(self, idx: int) -> None:
        if not self._chart_files or idx < 0 or idx >= len(self._chart_files):
            self.lbl_chart_img.clear()
            self.lbl_chart_img.setText("Chưa có biểu đồ. Hãy chạy Benchmark hoặc bấm 'Phân tích lại CSV & Sinh 8 Biểu đồ'.")
            return
        fpath = self._chart_files[idx]
        if os.path.exists(fpath):
            pixmap = QPixmap(fpath)
            # Scale pixmap phu hop voi man hinh
            scaled = pixmap.scaled(
                QSize(1020, 600),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.lbl_chart_img.setPixmap(scaled)
        else:
            self.lbl_chart_img.clear()
            self.lbl_chart_img.setText(f"Chưa có tệp biểu đồ: {os.path.basename(fpath)}")

    # ------------------------------------------------------------- STATS VIEWER
    def _load_stats_table(self) -> None:
        stat_csv = os.path.join(self.results_dir, "detailed_statistics.csv")
        if not os.path.exists(stat_csv):
            return

        try:
            import pandas as pd
            df = pd.read_csv(stat_csv, keep_default_na=False)
            self.table_stats.setRowCount(0)
            for _, r in df.iterrows():
                row_idx = self.table_stats.rowCount()
                self.table_stats.insertRow(row_idx)
                items = [
                    str(r.get("algorithm", "")),
                    str(r.get("size_label", "")),
                    f"{int(r.get('ciphertext_size_bytes', 0)):,}",
                    f"{int(r.get('packet_size_bytes', 0)):,}",
                    f"{float(r.get('encryption_ms_mean', 0)):.2f}",
                    f"{float(r.get('decrypt_ms_mean', 0)):.2f}",
                    f"{float(r.get('rtt_ms_mean', 0)):.2f}",
                    f"{float(r.get('total_ms_mean', 0)):.2f}",
                    f"{float(r.get('total_ms_median', 0)):.2f}",
                    f"{float(r.get('throughput_kbps_mean', 0)):,.1f}",
                    f"{float(r.get('enc_cpu_pct_mean', 0)):.1f}%",
                    f"{float(r.get('enc_ram_mb_mean', 0)):.1f}M",
                    f"{float(r.get('dec_ram_mb_mean', 0)):.1f}M",
                ]
                for col, val in enumerate(items):
                    it = QTableWidgetItem(val)
                    it.setTextAlignment(Qt.AlignCenter)
                    self.table_stats.setItem(row_idx, col, it)
        except Exception as exc:
            self.append_log(f"[!] Loi doc bang thong ke: {exc}")

    # ------------------------------------------------------------- LOAD PREVIOUS RESULTS
    def _load_existing_results_if_any(self) -> None:
        if os.path.exists(self.charts_dir):
            self._load_charts_into_viewer()
        if os.path.exists(os.path.join(self.results_dir, "detailed_statistics.csv")):
            self._load_stats_table()

    # ------------------------------------------------------------- EXTERNAL FILE OPENERS
    def _on_open_results_folder(self) -> None:
        try:
            if platform.system().lower() == "windows":
                os.startfile(self.results_dir)
            else:
                subprocess.Popen(["xdg-open", self.results_dir])
        except Exception as exc:
            QMessageBox.information(self, "Đường dẫn", f"Thư mục kết quả:\n{self.results_dir}")

    def _on_open_csv(self) -> None:
        if not os.path.exists(self.csv_path):
            QMessageBox.warning(self, "Thông báo", f"Chưa có file CSV: {self.csv_path}")
            return
        try:
            if platform.system().lower() == "windows":
                os.startfile(self.csv_path)
            else:
                subprocess.Popen(["xdg-open", self.csv_path])
        except Exception as exc:
            QMessageBox.information(self, "Đường dẫn", f"File CSV:\n{self.csv_path}")

    def _on_open_report(self) -> None:
        report_path = os.path.join(os.path.dirname(BENCH_DIR), "docs", "bao-cao-benchmark.md")
        if not os.path.exists(report_path):
            report_path = self.summary_md
        try:
            if platform.system().lower() == "windows":
                os.startfile(report_path)
            else:
                subprocess.Popen(["xdg-open", report_path])
        except Exception as exc:
            QMessageBox.information(self, "Đường dẫn", f"Báo cáo Markdown:\n{report_path}")

    def closeEvent(self, event) -> None:
        """Xu ly don dep tai nguyen khi dong cua so."""
        if self._client_worker and self._client_worker.isRunning():
            self._client_worker.stop()
            self._client_worker.wait(1000)
        if self._server_worker and self._server_worker.isRunning():
            self._server_worker.stop()
            self._server_worker.wait(1000)
        event.accept()


def main() -> None:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = BenchmarkWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
