"""
gui.py (VM1 - Sender) - Giao dien PySide6 cho may gui.

Ho tro 3 thuat toan: Playfair, Caesar, AES-128-CBC.
Hien thi: Lua chon thuat toan, Khoa/IV tuong ung, Plaintext,
truc quan hoa (ma tran 5x5 / bang dich / thong so khoi AES),
Ciphertext, cau hinh mang va nhat ky truyen tin.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import aes_cbc
import caesar
import config
import playfair
import protocol
from network import SenderThread, validate_endpoint


class SenderWindow(QMainWindow):
    """Cua so chinh cua ung dung Sender (VM1)."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VM1 - Cryptography Sender (Playfair / Caesar / AES-128-CBC)")
        self.resize(*config.SENDER_WINDOW_SIZE)
        self._sender_thread: SenderThread | None = None
        self._current_iv_hex: str = ""
        self._build_ui()

    # ------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        mono = QFont(config.MONO_FONT_FAMILY, config.MONO_FONT_SIZE)

        # --- Nhom nhap lieu ---
        input_group = QGroupBox("Cấu hình mã hóa & Dữ liệu đầu vào")
        input_layout = QVBoxLayout(input_group)

        # Chon thuat toan
        algo_row = QHBoxLayout()
        algo_row.addWidget(QLabel("Thuật toán mã hóa:"))
        self.algo_combo = QComboBox()
        self.algo_combo.addItem("Playfair (Ma trận 5×5)", config.ALGORITHM_PLAYFAIR)
        self.algo_combo.addItem("Caesar (Dịch chuyển ký tự)", config.ALGORITHM_CAESAR)
        self.algo_combo.addItem("AES-128-CBC (Mã hóa khối 128-bit)", config.ALGORITHM_AES_128_CBC)
        self.algo_combo.currentIndexChanged.connect(self._on_algo_changed)
        algo_row.addWidget(self.algo_combo, stretch=1)

        self.btn_open_benchmark = QPushButton("🚀 Mở Benchmark GUI")
        self.btn_open_benchmark.setStyleSheet(
            "background-color: #0284c7; color: white; font-weight: bold; padding: 4px 10px; border-radius: 4px;"
        )
        self.btn_open_benchmark.clicked.connect(self._on_open_benchmark_gui)
        algo_row.addWidget(self.btn_open_benchmark)

        input_layout.addLayout(algo_row)

        # Stacked widget cho phan nhap khoa / tham so rieng
        self.key_stack = QStackedWidget()

        # Trang 0: Playfair Key
        playfair_page = QWidget()
        pf_layout = QHBoxLayout(playfair_page)
        pf_layout.setContentsMargins(0, 0, 0, 0)
        pf_layout.addWidget(QLabel("Khóa Playfair:"))
        self.playfair_key_edit = QLineEdit()
        self.playfair_key_edit.setPlaceholderText("Ví dụ: MONARCHY (các chữ cái A-Z)")
        pf_layout.addWidget(self.playfair_key_edit, stretch=1)
        self.key_stack.addWidget(playfair_page)

        # Trang 1: Caesar Shift
        caesar_page = QWidget()
        cs_layout = QHBoxLayout(caesar_page)
        cs_layout.setContentsMargins(0, 0, 0, 0)
        cs_layout.addWidget(QLabel("Độ dịch (Shift k):"))
        self.caesar_shift_spin = QSpinBox()
        self.caesar_shift_spin.setRange(-1000, 1000)
        self.caesar_shift_spin.setValue(config.DEFAULT_CAESAR_SHIFT)
        cs_layout.addWidget(self.caesar_shift_spin)

        btn_rot3 = QPushButton("k = 3 (Caesar)")
        btn_rot3.clicked.connect(lambda: self.caesar_shift_spin.setValue(3))
        cs_layout.addWidget(btn_rot3)

        btn_rot13 = QPushButton("k = 13 (ROT13)")
        btn_rot13.clicked.connect(lambda: self.caesar_shift_spin.setValue(13))
        cs_layout.addWidget(btn_rot13)
        cs_layout.addStretch(1)
        self.key_stack.addWidget(caesar_page)

        # Trang 2: AES-128-CBC
        aes_page = QWidget()
        aes_layout = QGridLayout(aes_page)
        aes_layout.setContentsMargins(0, 0, 0, 0)

        aes_layout.addWidget(QLabel("Khóa AES (16B / 32 hex):"), 0, 0)
        self.aes_key_edit = QLineEdit()
        self.aes_key_edit.setPlaceholderText("Nhập 16 ký tự văn bản hoặc 32 ký tự Hex")
        aes_layout.addWidget(self.aes_key_edit, 0, 1)

        self.btn_gen_aes_key = QPushButton("Tạo khóa ngẫu nhiên")
        self.btn_gen_aes_key.clicked.connect(self._on_generate_aes_key)
        aes_layout.addWidget(self.btn_gen_aes_key, 0, 2)

        aes_layout.addWidget(QLabel("Vector IV (16B / 32 hex):"), 1, 0)
        self.aes_iv_edit = QLineEdit()
        self.aes_iv_edit.setPlaceholderText("Vector khởi tạo IV 16 byte (Hex)")
        aes_layout.addWidget(self.aes_iv_edit, 1, 1)

        self.btn_gen_aes_iv = QPushButton("Tạo IV ngẫu nhiên")
        self.btn_gen_aes_iv.clicked.connect(self._on_generate_aes_iv)
        aes_layout.addWidget(self.btn_gen_aes_iv, 1, 2)

        self.key_stack.addWidget(aes_page)

        input_layout.addWidget(self.key_stack)

        # Plaintext
        pt_layout = QHBoxLayout()
        pt_layout.addWidget(QLabel("Plaintext:"), alignment=Qt.AlignTop)
        self.plaintext_edit = QPlainTextEdit()
        self.plaintext_edit.setPlaceholderText("Nhập nội dung tin nhắn cần mã hóa...")
        self.plaintext_edit.setFixedHeight(75)
        pt_layout.addWidget(self.plaintext_edit, stretch=1)
        input_layout.addLayout(pt_layout)

        # Nut ma hoa
        self.encrypt_button = QPushButton("Tạo ma trận & Mã hóa")
        self.encrypt_button.clicked.connect(self.on_encrypt)
        input_layout.addWidget(self.encrypt_button, alignment=Qt.AlignRight)

        root.addWidget(input_group)

        # --- Nhom ket qua ma hoa ---
        result_group = QGroupBox("Kết quả mã hóa & Trực quan hóa")
        result_layout = QGridLayout(result_group)

        self.visual_label = QLabel("Ma trận Playfair 5×5:")
        result_layout.addWidget(self.visual_label, 0, 0, Qt.AlignTop)
        self.visual_view = QPlainTextEdit()
        self.visual_view.setReadOnly(True)
        self.visual_view.setFont(mono)
        self.visual_view.setFixedHeight(95)
        result_layout.addWidget(self.visual_view, 0, 1)

        result_layout.addWidget(QLabel("Ciphertext:"), 1, 0, Qt.AlignTop)
        self.ciphertext_view = QPlainTextEdit()
        self.ciphertext_view.setReadOnly(True)
        self.ciphertext_view.setFont(mono)
        self.ciphertext_view.setFixedHeight(65)
        result_layout.addWidget(self.ciphertext_view, 1, 1)

        root.addWidget(result_group)

        # --- Nhom ket noi ---
        conn_group = QGroupBox("Kết nối tới Receiver (VM2)")
        conn_layout = QHBoxLayout(conn_group)

        conn_layout.addWidget(QLabel("IP Receiver:"))
        self.host_edit = QLineEdit(config.DEFAULT_RECEIVER_HOST)
        conn_layout.addWidget(self.host_edit)

        conn_layout.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(config.PORT_MIN, config.PORT_MAX)
        self.port_spin.setValue(config.DEFAULT_PORT)
        conn_layout.addWidget(self.port_spin)

        self.send_button = QPushButton("Gửi ciphertext")
        self.send_button.clicked.connect(self.on_send)
        conn_layout.addWidget(self.send_button)

        root.addWidget(conn_group)

        # --- Trang thai / log ---
        status_group = QGroupBox("Trạng thái gửi & Nhật ký")
        status_layout = QVBoxLayout(status_group)
        self.status_label = QLabel("Chưa gửi.")
        status_layout.addWidget(self.status_label)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(mono)
        status_layout.addWidget(self.log_view)
        root.addWidget(status_group, stretch=1)

        self.setCentralWidget(central)

        # Khoi tao khoa ngau nhien cho AES san sang
        self._on_generate_aes_key()
        self._on_generate_aes_iv()

    # -------------------------------------------------------- Handlers (Ham xu ly su kien)
    def _on_algo_changed(self, index: int) -> None:
        """
        Su kien chuyen doi thuat toan tren ComboBox:
        - Chuyen trang nhap lieu tuong ung tren QStackedWidget (Playfair / Caesar / AES).
        - Cap nhat nhan tieu de truc quan hoa va chu tren nut Bam ma hoa.
        """
        self.key_stack.setCurrentIndex(index)
        algo = self.algo_combo.currentData()

        if algo == config.ALGORITHM_PLAYFAIR:
            self.encrypt_button.setText("Tạo ma trận & Mã hóa")
            self.visual_label.setText("Ma trận Playfair 5×5:")
        elif algo == config.ALGORITHM_CAESAR:
            self.encrypt_button.setText("Mã hóa Caesar")
            self.visual_label.setText("Bảng quy tắc dịch Caesar:")
        elif algo == config.ALGORITHM_AES_128_CBC:
            self.encrypt_button.setText("Mã hóa AES-128-CBC")
            self.visual_label.setText("Thông số mã hóa AES-128-CBC:")

    def _on_generate_aes_key(self) -> None:
        """Sinh khoa AES-128 ngau nhien (16 byte hex = 32 ky tu) va dien vao o nhap."""
        key_bytes = aes_cbc.generate_key()
        self.aes_key_edit.setText(aes_cbc.bytes_to_hex(key_bytes))

    def _on_generate_aes_iv(self) -> None:
        """Sinh vector khoi tao IV ngau nhien (16 byte hex = 32 ky tu) va dien vao o nhap."""
        iv_bytes = aes_cbc.generate_iv()
        self.aes_iv_edit.setText(aes_cbc.bytes_to_hex(iv_bytes))

    def on_encrypt(self) -> None:
        """
        Ham dieu phoi khi nguoi dung bam nut 'Ma hoa':
        1. Kiem tra Plaintext khong duoc de trong.
        2. Kiem tra thuat toan dang chon va goi ham ma hoa tuong ung.
        """
        algo = self.algo_combo.currentData()
        plaintext = self.plaintext_edit.toPlainText()

        # Kiem tra nguoi dung da nhap van ban can ma hoa chua
        if not plaintext.strip():
            QMessageBox.warning(self, "Thiếu Plaintext", "Hãy nhập nội dung Plaintext cần mã hóa.")
            return

        # Dieu huong toi ham ma hoa cua tung thuat toan
        if algo == config.ALGORITHM_PLAYFAIR:
            self._encrypt_playfair(plaintext)
        elif algo == config.ALGORITHM_CAESAR:
            self._encrypt_caesar(plaintext)
        elif algo == config.ALGORITHM_AES_128_CBC:
            self._encrypt_aes(plaintext)

    def _encrypt_playfair(self, plaintext: str) -> None:
        key = self.playfair_key_edit.text().strip()
        if not playfair.normalize_text(key):
            QMessageBox.warning(self, "Thiếu khóa", "Khóa Playfair phải chứa ít nhất một chữ cái A-Z.")
            return

        try:
            matrix = playfair.build_matrix(key)
            normalized = playfair.normalize_text(plaintext)
            digraphs = playfair.make_digraphs(normalized)
            ciphertext = playfair.encrypt(plaintext, key)
        except ValueError as exc:
            QMessageBox.warning(self, "Không thể mã hóa", str(exc))
            return

        self.visual_view.setPlainText(playfair.matrix_to_string(matrix))
        self.ciphertext_view.setPlainText(ciphertext)
        self._log(f"[Playfair] Plaintext chuẩn hóa : {normalized}")
        self._log(f"[Playfair] Chia cặp ký tự      : {' '.join(digraphs)}")
        self._log(f"[Playfair] Ciphertext          : {ciphertext}")
        self.status_label.setText("Đã mã hóa Playfair xong, sẵn sàng gửi.")

    def _encrypt_caesar(self, plaintext: str) -> None:
        shift = self.caesar_shift_spin.value()
        try:
            ciphertext = caesar.encrypt(plaintext, shift)
            mapping_str = caesar.get_mapping_string(shift)
        except ValueError as exc:
            QMessageBox.warning(self, "Không thể mã hóa", str(exc))
            return

        self.visual_view.setPlainText(mapping_str)
        self.ciphertext_view.setPlainText(ciphertext)
        self._log(f"[Caesar] Độ dịch k = {shift % 26} (gốc: {shift})")
        self._log(f"[Caesar] Plaintext : {plaintext}")
        self._log(f"[Caesar] Ciphertext: {ciphertext}")
        self.status_label.setText(f"Đã mã hóa Caesar (k={shift % 26}) xong, sẵn sàng gửi.")

    def _encrypt_aes(self, plaintext: str) -> None:
        key_text = self.aes_key_edit.text().strip()
        iv_text = self.aes_iv_edit.text().strip()

        try:
            key_bytes = aes_cbc.parse_bytes(key_text, config.AES_KEY_SIZE, "Khóa AES")
        except ValueError as exc:
            QMessageBox.warning(self, "Khóa AES không hợp lệ", str(exc))
            return

        try:
            iv_bytes = aes_cbc.parse_bytes(iv_text, config.AES_BLOCK_SIZE, "Vector IV")
        except ValueError as exc:
            QMessageBox.warning(self, "Vector IV không hợp lệ", str(exc))
            return

        try:
            cipher_bytes = aes_cbc.encrypt(plaintext, key_bytes, iv_bytes)
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi mã hóa AES", str(exc))
            return

        b64_ciphertext = aes_cbc.bytes_to_base64(cipher_bytes)
        info_str = aes_cbc.get_aes_info_string(
            key_bytes,
            iv_bytes,
            len(plaintext.encode("utf-8")),
            len(cipher_bytes),
        )

        self._current_iv_hex = aes_cbc.bytes_to_hex(iv_bytes)
        self.visual_view.setPlainText(info_str)
        self.ciphertext_view.setPlainText(b64_ciphertext)
        self._log(f"[AES-128-CBC] Khóa (Hex): {aes_cbc.bytes_to_hex(key_bytes)}")
        self._log(f"[AES-128-CBC] IV   (Hex): {self._current_iv_hex}")
        self._log(f"[AES-128-CBC] Ciphertext (Base64, {len(cipher_bytes)}B): {b64_ciphertext}")
        self.status_label.setText("Đã mã hóa AES-128-CBC xong, sẵn sàng gửi.")

    def on_send(self) -> None:
        """
        Ham dieu phoi khi nguoi dung bam nut 'Gui ciphertext':
        1. Kiem tra xem da co ciphertext chua.
        2. Kiem tra tinh hop le cua IP va Port.
        3. Thu thap khoa / IV phu hop theo thuat toan dang chon.
        4. Dong goi tin JSON bang protocol.pack_message().
        5. Khoi dong SenderThread chay ngam de gui qua TCP.
        6. Ket noi cac Signal (log, succeeded, failed) ve cac ham phan hoi tren GUI.
        """
        algo = self.algo_combo.currentData()
        ciphertext = self.ciphertext_view.toPlainText().strip()
        host = self.host_edit.text().strip()
        port = self.port_spin.value()

        # Kiem tra da thuc hien ma hoa de co ciphertext chua
        if not ciphertext:
            QMessageBox.warning(self, "Chưa có ciphertext", "Hãy bấm nút mã hóa trước khi gửi.")
            return

        # Kiem tra tinh hop le cua dia chi IP va cong port
        try:
            validate_endpoint(host, port)
        except ValueError as exc:
            QMessageBox.warning(self, "Địa chỉ không hợp lệ", str(exc))
            return

        # Ngan chan nguoi dung spam nut gui khi luong gui truoc do van dang chay
        if self._sender_thread and self._sender_thread.isRunning():
            QMessageBox.information(self, "Đang gửi", "Đang có một phiên gửi, vui lòng đợi.")
            return

        # Thu thap khoa va IV phu hop theo thuat toan
        iv = ""
        if algo == config.ALGORITHM_PLAYFAIR:
            key = self.playfair_key_edit.text().strip()
        elif algo == config.ALGORITHM_CAESAR:
            key = str(self.caesar_shift_spin.value() % 26)
        elif algo == config.ALGORITHM_AES_128_CBC:
            key = self.aes_key_edit.text().strip()
            iv = self.aes_iv_edit.text().strip()
        else:
            QMessageBox.warning(self, "Lỗi", "Thuật toán không xác định.")
            return

        # Dong goi thong diep thanh chuoi byte JSON ket thuc bang '\n'
        try:
            packet = protocol.pack_message(algo, key, ciphertext, iv=iv)
        except ValueError as exc:
            QMessageBox.warning(self, "Lỗi đóng gói", str(exc))
            return

        self._log(f"Gói tin JSON ({algo}): {packet.decode('utf-8').strip()}")
        # Khoa nut Gui lai de tranh bam trung lap
        self.send_button.setEnabled(False)
        self.status_label.setText(f"Đang gửi [{algo}] tới {host}:{port} ...")

        # Khoi tao luong SenderThread (QThread) va ket noi cac Signal ve Slot
        self._sender_thread = SenderThread(host, port, packet, parent=self)
        self._sender_thread.log.connect(self._log)
        self._sender_thread.succeeded.connect(self._on_send_success)
        self._sender_thread.failed.connect(self._on_send_failure)
        # Khi thread ket thuc (du thanh cong hay that bai), mo lai nut Gui
        self._sender_thread.finished.connect(lambda: self.send_button.setEnabled(True))
        # start() se kich hoat ham run() chay tren thread rieng
        self._sender_thread.start()

    def _on_send_success(self, message: str) -> None:
        """Slot nhan tin hieu khi gui goi tin thanh cong."""
        self.status_label.setText(message)
        self._log(message)

    def _on_send_failure(self, message: str) -> None:
        """Slot nhan tin hieu khi gui goi tin that bai (hien hop thoai loi)."""
        self.status_label.setText(f"Lỗi: {message}")
        self._log(f"LỖI: {message}")
        QMessageBox.critical(self, "Gửi thất bại", message)

    def _log(self, line: str) -> None:
        self.log_view.appendPlainText(line)

    def _on_open_benchmark_gui(self) -> None:
        try:
            bench_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "benchmark")
            if bench_dir not in sys.path:
                sys.path.insert(0, bench_dir)
            import gui as bench_gui
            self._bench_win = bench_gui.BenchmarkWindow()
            self._bench_win.show()
        except Exception as exc:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở Benchmark GUI: {exc}")
