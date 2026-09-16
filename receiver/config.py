"""
config.py - Tap trung toan bo tham so cau hinh cua ung dung.

Moi hang so cau hinh (thuat toan, giao thuc, mang, giao dien) deu duoc
dinh nghia tai day de cac module khac import, tranh rai rac "magic number"
(cac con so/chuoi cung trong code kho bao tri).
"""

# ============================== Danh muc Thuat toan ==============================
# Ten dinh danh (ID chuoi) cua tung thuat toan duoc ho tro trong he thong
ALGORITHM_PLAYFAIR = "playfair"        # Thuat toan co dien ma hoa ma tran 5x5 Playfair
ALGORITHM_CAESAR = "caesar"            # Thuat toan co dien dich chuyen ky tu Caesar
ALGORITHM_AES_128_CBC = "aes-128-cbc"  # Chuan ma hoa khoi hien dai AES 128-bit che do CBC

# Danh sach tap hop cac thuat toan duoc phep su dung de kiem tra tinh hop le
SUPPORTED_ALGORITHMS = [
    ALGORITHM_PLAYFAIR,
    ALGORITHM_CAESAR,
    ALGORITHM_AES_128_CBC,
]

# Thuat toan mac dinh duoc chon khi khoi dong ung dung giao dien
DEFAULT_ALGORITHM = ALGORITHM_PLAYFAIR

# ============================== Thuat toan Playfair ==============================
# Bang chu cai 25 ky tu tieng Anh viet hoa: chu 'J' duoc gop chung vao chu 'I'
ALPHABET = "ABCDEFGHIKLMNOPQRSTUVWXYZ"

# Ky tu dem (padding) dung de chen vao giua hai chu cai giong nhau trong mot cap,
# hoac chen vao cuoi chuoi neu tong so ky tu la so le
FILLER = "X"

# Kich thuoc ma tran khoa vuong cua Playfair la 5 hang x 5 cot = 25 o
MATRIX_SIZE = 5

# ============================== Thuat toan Caesar ================================
# Do dich chuyen mac dinh theo chuan mat ma Caesar co dien cua La Ma (dich 3 vi tri)
DEFAULT_CAESAR_SHIFT = 3

# ============================== Thuat toan AES-128-CBC ===========================
# Kich thuoc khoa doi xung: 128 bit = 16 byte (tuong ung voi 32 ky tu he Hex)
AES_KEY_SIZE = 16

# Kich thuoc khoi du lieu (Block size) cua chuan AES: 128 bit = 16 byte
AES_BLOCK_SIZE = 16

# ============================== Giao thuc truyen tin =============================
# Dinh danh loai thong diep cho giao thuc Version 2 (ho tro da thuat toan)
MESSAGE_TYPE = "crypto_message"

# Dinh danh loai thong diep cua Version 1 (dung de kiem tra va giu tuong thich nguoc)
LEGACY_MESSAGE_TYPE = "playfair_message"

# Phien ban giao thuc hien tai cua he thong
PROTOCOL_VERSION = 2

# Bang ma hoa ky tu dung khi chuyen doi giua chuoi JSON va mang byte nhi phan
ENCODING = "utf-8"

# Ky tu phan tach khung tin (Delimiter) tren luong byte TCP: ky tu xuong dong '\n'
# Giup ben nhan biet duoc ranh gioi ket thuc cua mot goi tin JSON
DELIMITER = b"\n"

# ============================== Cau hinh mang ====================================
# Cong (Port) TCP mac dinh ma Receiver lang nghe va Sender ket noi toi
DEFAULT_PORT = 5000

# Dia chi IP mac dinh cua may nhan (Receiver - VM2) trong mang may ao
DEFAULT_RECEIVER_HOST = "192.168.1.2"

# Dia chi IP lang nghe mac dinh: "0.0.0.0" nghia la lang nghe tren tat ca card mang
DEFAULT_LISTEN_HOST = "0.0.0.0"

# Gioi han cong TCP hop le theo chuan mang Internet (tu 1 den 65535)
PORT_MIN = 1
PORT_MAX = 65535

# Thoi gian cho toi da (giay) khi may gui thiet lap ket noi TCP toi may nhan
CONNECT_TIMEOUT = 5.0

# Chu ky thoi gian (giay) ma Server kiem tra co dung (stop flag) trong vong lap accept
ACCEPT_TIMEOUT = 0.5

# Thoi gian cho toi da (giay) khi doc du lieu tu mot client truoc khi ngat ket noi
CLIENT_RECV_TIMEOUT = 10.0

# Kich thuoc bo dem (bytes) cho moi lan goi ham socket.recv() doc du lieu tu card mang
RECV_BUFFER = 4096

# So luong ket noi toi da duoc phep cho trong hang doi ket noi cua Server (Backlog)
LISTEN_BACKLOG = 5

# Thoi gian toi da (mili-giay) cho luong Server dung han truoc khi dong giao dien
SERVER_STOP_WAIT_MS = 2000

# ============================== Giao dien do hoa (GUI) ============================
# Kich thuoc mac dinh cua cua so may gui Sender: (chieu rong = 820px, chieu cao = 720px)
SENDER_WINDOW_SIZE = (820, 720)

# Kich thuoc mac dinh cua cua so may nhan Receiver: (chieu rong = 820px, chieu cao = 740px)
RECEIVER_WINDOW_SIZE = (820, 740)

# Phong chu don cach (Monospace) dung de hien thi ma tran 5x5 va nhat ky (log) cho thang hang
MONO_FONT_FAMILY = "Consolas"
MONO_FONT_SIZE = 11
