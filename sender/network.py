"""
network.py (VM1 - Sender) - TCP Client gui goi tin sang VM2 tren luong rieng.

Kien truc & nguyen ly hoat dong:
- Su dung QThread cua PySide6 de thuc hien ket noi mang bat dong bo,
  tranh viec ham blocking socket.connect() lam treo giao dien nguoi dung.
- Ket qua truyen tin (thanh cong / that bai / nhat ky) duoc ban ve GUI
  thong qua he thong Signal / Slot an toan da luong (Thread-safe).
- Xu ly ngoai le toan dien: kiem tra tinh hop le cua dia chi IP (ipaddress)
  va bat rieng tung ma loi mang pho bien (timeout, tu choi ket noi, sai DNS).
"""

from __future__ import annotations

import ipaddress
import socket

# Import QThread va Signal tu PySide6 de xay dung luong chay nen
from PySide6.QtCore import QThread, Signal

# Import cac hang so cau hinh tu config.py
from config import CONNECT_TIMEOUT, PORT_MAX, PORT_MIN


def validate_endpoint(host: str, port: int) -> None:
    """
    Kiem tra tinh hop le cua dia chi IP va cong dich truoc khi thuc hien ket noi socket.

    Quy tac kiem tra:
    1. Host khong duoc rong hoac chi chua khoang trang.
    2. Host phai la mot dia chi IPv4 chuan hop le (vi du: "192.168.1.2").
    3. Port phai la so nguyen nam trong khoang cho phep [1, 65535].

    Raises:
        ValueError: Kem theo thong bao loi chi tiet de hien thi len hop thoai GUI.
    """
    # Kiem tra neu chuoi IP bi de trong
    if not host or not host.strip():
        raise ValueError("Dia chi IP cua Receiver khong duoc de trong.")

    # Su dung thu vien chuan ipaddress de parse va kiem tra dia chi IPv4
    try:
        ipaddress.IPv4Address(host.strip())
    except ipaddress.AddressValueError as exc:
        raise ValueError(
            f"'{host}' khong phai la dia chi IPv4 hop le "
            "(vi du dung: 192.168.1.2)."
        ) from exc

    # Kiem tra cong port co nam trong dai hop le 1 - 65535 hay khong
    if not (PORT_MIN <= port <= PORT_MAX):
        raise ValueError(
            f"Cong {port} khong hop le, phai nam trong "
            f"khoang {PORT_MIN}-{PORT_MAX}."
        )


class SenderThread(QThread):
    """
    Luong chay ngam (Worker Thread) thuc hien ket noi TCP va gui goi tin.
    Ke thua tu QThread cua Qt.
    """

    # Cac tin hieu (Signal) de giao tiep tu luong Worker ve Main GUI Thread:
    log = Signal(str)         # Gui chuoi nhat ky (log) de hien thi len o text
    succeeded = Signal(str)   # Phat tin hieu khi gui goi tin thanh cong
    failed = Signal(str)      # Phat tin hieu kem thong bao loi khi gui that bai

    def __init__(self, host: str, port: int, packet: bytes, parent=None):
        """
        Khoi tao luong SenderThread voi cac tham so:
        - host: Dia chi IP may nhan.
        - port: Cong TCP may nhan.
        - packet: Mảng byte du lieu JSON da dong goi san sang gui.
        """
        super().__init__(parent)
        self._host = host
        self._port = port
        self._packet = packet

    def run(self) -> None:
        """
        Noi dung thuc thi cua luong (chay tren thread rieng cua he dieu hanh).
        Tu dong duoc goi khi ta goi lenh .start() tu GUI.
        """
        try:
            # Thong bao trang thai bat dau ket noi
            self.log.emit(f"Dang ket noi toi {self._host}:{self._port} ...")

            # socket.create_connection tu dong tao socket TCP va thuc hien bat tay 3 buoc SYN -> SYN-ACK -> ACK
            # timeout=CONNECT_TIMEOUT (5.0s) de khong bi treo vo han neu may kia tat
            with socket.create_connection(
                (self._host, self._port), timeout=CONNECT_TIMEOUT
            ) as sock:
                self.log.emit("Ket noi TCP thanh cong.")

                # sendall() lap lien tuc cho den khi toan bo mang byte duoc gui het qua card mang
                sock.sendall(self._packet)
                self.log.emit(f"Da gui {len(self._packet)} byte.")

            # Phat tin hieu thanh cong ve GUI khi da dong socket an toan
            self.succeeded.emit(
                f"Gui thanh cong toi {self._host}:{self._port}"
            )

        # Xu ly cac truong hop ngoai le mang pho bien de thong bao ro cho nguoi dung:
        except socket.timeout:
            # Truong hop 1: Qua 5 giay khong ket noi duoc (thuong do sai IP hoac bi Firewall chan)
            self.failed.emit(
                f"Het thoi gian cho ({CONNECT_TIMEOUT}s) khi ket noi toi "
                f"{self._host}:{self._port}. Kiem tra IP, ket noi mang "
                "hoac firewall cua Receiver."
            )
        except ConnectionRefusedError:
            # Truong hop 2: Server ben kia tu choi ket noi (chua bat Server hoac sai Port)
            self.failed.emit(
                f"{self._host}:{self._port} tu choi ket noi. "
                "Receiver chua khoi dong server hoac sai cong."
            )
        except socket.gaierror as exc:
            # Truong hop 3: Loi phan giai ten mien / dia chi IP
            self.failed.emit(
                f"Khong phan giai duoc dia chi '{self._host}': {exc}"
            )
        except OSError as exc:
            # Truong hop 4: Cac loi he dieu hanh khac ve socket mang
            self.failed.emit(f"Loi mang: {exc}")
