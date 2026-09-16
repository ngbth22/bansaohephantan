"""
main.py (VM1 - Sender) - Diem khoi dong ung dung Cryptography Sender (VM1).

Vai tro:
- Khoi tao doi tuong QApplication cua framework PySide6.
- Khoi tao cua so giao dien SenderWindow.
- Bat dau vong lap xu ly su kien (Event Loop) cua Qt va thoat ung dung khi cua so dong.

Cach chay:
    python sender/main.py
"""

import sys

# Import lop quan ly vong lap su kien Qt
from PySide6.QtWidgets import QApplication

# Import cua so chinh SenderWindow tu module gui.py cung thu muc
from gui import SenderWindow


def main() -> int:
    """Ham main: khoi tao va dieu phoi vong doi cua ung dung Sender."""
    # 1. Khoi tao QApplication: bat buoc phai co cho moi ung dung PySide6/Qt
    # sys.argv cho phep truyen cac tham so dong lenh vao Qt neu can
    app = QApplication(sys.argv)

    # 2. Khoi tao doi tuong cua so chinh cua Sender
    window = SenderWindow()

    # 3. Hien thi cua so len man hinh
    window.show()

    # 4. app.exec() bat dau vong lap su kien (Event Loop) cho den khi dong ung dung,
    # tra ve ma thoat (exit code) 0 neu binh thuong
    return app.exec()


# Kiem tra neu file duoc chay truc tiep tu dong lenh (chu khong phai duoc import)
if __name__ == "__main__":
    # sys.exit nhan ma thoat tu main() de bao ve he dieu hanh
    sys.exit(main())
