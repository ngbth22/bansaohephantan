"""
main.py (VM2 - Receiver) - Diem khoi dong ung dung Cryptography Receiver (CLI).

Vai tro:
- Khoi dong Server nhan tin tren cong chi dinh (mac dinh: 0.0.0.0:5000).
- Khong can giao dien do hoa (GUI / PySide6), chay truc tiep tren moi truong Console / Terminal / Linux headless.
- Ho tro tuong tac va truyen nhan qua lenh 'curl' (HTTP) va TCP Socket truyen thong tu VM1 (Sender).
- Tu dong giai ma va hien thi ket qua kem truc quan hoa ra Terminal.

Cach chay:
    python receiver/main.py
    python receiver/main.py --host 0.0.0.0 --port 5000
"""

from __future__ import annotations

import argparse
import os
import signal
import sys

# Dam bao thu muc receiver nam trong sys.path
receiver_dir = os.path.dirname(os.path.abspath(__file__))
if receiver_dir not in sys.path:
    sys.path.insert(0, receiver_dir)

import config
from network import ReceiverServer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cryptography Receiver Server (CLI) - Ho tro cURL va TCP Socket",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        type=str,
        default=config.DEFAULT_LISTEN_HOST,
        help="Dia chi IP lang nghe (dung 0.0.0.0 de nhan tren moi card mang)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config.DEFAULT_PORT,
        help=f"Cong TCP lang nghe ({config.PORT_MIN}-{config.PORT_MAX})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = ReceiverServer(host=args.host, port=args.port)

    # Dang ky xu ly tin hieu thoat Ctrl+C (SIGINT)
    def handle_signal(sig, frame):
        print("\n[*] Nhan tin hieu dung (Ctrl+C). Dang tat server...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)

    try:
        server.start(blocking=True)
    except KeyboardInterrupt:
        print("\n[*] Nhan Ctrl+C. Dang tat server...")
        server.stop()
    except Exception as exc:
        print(f"\n[!] LOI KHOI DONG SERVER: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
