"""
aes_cbc.py - Trien khai thuat toan ma hoa / giai ma AES-128-CBC voi dem PKCS#7.

Quy uoc mat ma hoc & tieu chuan ap dung:
- Thuat toan: AES (Advanced Encryption Standard - Chuan ma hoa tien tien FIPS 197).
- Do dai khoa: 128 bit (dung 16 byte).
- Che do ma hoa: CBC (Cipher Block Chaining - Khoi sau moc xich voi khoi truoc).
- Vector khoi tao (IV): 128 bit (16 byte), bat buoc phai ngau nhien va duy nhat cho moi phien.
- Kieu dem: PKCS#7 (Public-Key Cryptography Standards #7, kich thuoc khoi 16 byte).
- Plaintext: chuoi UTF-8 tuy y (ho tro tieng Viet co dau, ky tu dac biet).
- Ciphertext: truyen duoi dang chuoi Base64 hoac Hex tren mang / JSON de tranh loi ky tu dieu khien.
- Su dung thu vien cryptography (chuan cong nghiep, goi OpenSSL tang C, co tap lenh AES-NI).
"""

from __future__ import annotations

import base64
import os

# Import cac module mat ma tu thu vien cryptography
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Hang so quy dinh kich thuoc khoa va kich thuoc khoi cua AES-128
AES_KEY_SIZE = 16    # 128 bit = 16 byte
AES_BLOCK_SIZE = 16  # Kich thuoc khoi AES luon la 128 bit = 16 byte


def generate_key() -> bytes:
    """
    Sinh khoa doi xung ngau nhien an toan co do dai 16 byte (128 bit).
    Su dung os.urandom() la bo sinh so ngau nhien an toan mat ma hoc (CSPRNG)
    lay entropy truc tiep tu he dieu hanh, khong the doan truoc.
    """
    return os.urandom(AES_KEY_SIZE)


def generate_iv() -> bytes:
    """
    Sinh vector khoi tao (IV - Initialization Vector) ngau nhien co do dai 16 byte (128 bit).
    IV giup hai ban tin giong nhau duoc ma hoa bang cung mot khoa se cho ra
    hai ban ma (ciphertext) hoan toan khac nhau, chong tan cong phan tich mau lap.
    """
    return os.urandom(AES_BLOCK_SIZE)


def parse_bytes(text: str, expected_len: int = 16, label: str = "Khóa") -> bytes:
    """
    Chuyen doi chuoi nhap lieu tu nguoi dung thanh mang byte nhi phan.
    
    Chap nhan 2 dinh dang linh hoat:
    1. Chuoi Hex: do dai gap doi expected_len (vi du: 32 ky tu hex cho 16 byte).
    2. Chuoi van ban UTF-8/ASCII: co do dai dung expected_len byte (vi du: 16 ky tu ASCII).
    
    Tham so:
        text: Chuoi do nguoi dung nhap tren giao dien GUI.
        expected_len: So byte mong muon (mac dinh la 16 byte).
        label: Nhan de hien thi trong thong bao loi (vi du: "Khóa AES" hoac "Vector IV").
    """
    clean_text = text.strip()
    if not clean_text:
        raise ValueError(f"{label} khong duoc de trong.")

    # Truong hop 1: Nguoi dung nhap chuoi Hex (vi du 32 ky tu bieu dien cho 16 byte)
    if len(clean_text) == expected_len * 2:
        try:
            return bytes.fromhex(clean_text)
        except ValueError:
            pass  # Neu khong phai chuoi hex hop le thi thu tiep cach ben duoi

    # Truong hop 2: Nguoi dung nhap chuoi van ban truc tiep (vi du "0123456789abcdef" gom 16 ky tu)
    raw_bytes = clean_text.encode("utf-8")
    if len(raw_bytes) == expected_len:
        return raw_bytes

    # Neu ca 2 truong hop deu khong thoa man do dai yeu cau -> Bao loi ro rang
    raise ValueError(
        f"{label} phai co do dai dung {expected_len} byte "
        f"({expected_len * 2} ky tu Hex hoac {expected_len} ky tu van ban ASCII/UTF-8). "
        f"Do dai hien tai: {len(raw_bytes)} byte."
    )


def bytes_to_hex(data: bytes) -> str:
    """Chuyen doi mang byte nhi phan sang chuoi bieu dien he Hex (16 byte -> 32 ky tu hex)."""
    return data.hex()


def hex_to_bytes(hex_str: str) -> bytes:
    """Chuyen doi chuoi Hex nguoc lai thanh mang byte nhi phan."""
    clean = hex_str.strip()
    return bytes.fromhex(clean)


def bytes_to_base64(data: bytes) -> str:
    """
    Chuyen doi mang byte nhi phan sang chuoi Base64 UTF-8 (an toan khi nhung vao JSON).
    Moi 3 byte nhi phan duoc ma hoa thanh 4 ky tu ASCII in duoc.
    """
    return base64.b64encode(data).decode("ascii")


def base64_to_bytes(b64_str: str) -> bytes:
    """Giai ma chuoi Base64 nguoc lai thanh mang byte nhi phan goc."""
    clean = b64_str.strip().encode("ascii")
    return base64.b64decode(clean)


def encrypt(plaintext: str | bytes, key: bytes, iv: bytes) -> bytes:
    """
    Ma hoa du lieu bang thuat toan AES-128 che do CBC voi dem PKCS#7.
    
    Quy trinh:
    1. Kiem tra tinh hop le cua do dai Khoa (16 byte) va IV (16 byte).
    2. Chuyen Plaintext sang dang byte UTF-8.
    3. Ap dung thuat toan dem PKCS#7 de du lieu co do dai la boi so cua 16 byte.
    4. Thuc hien ma hoa khoi AES-128-CBC.
    
    Tra ve:
        Mang byte nhi phan chua toan bo ciphertext sau khi ma hoa.
    """
    # 1. Kiem tra nghiem ngat do dai khoa va IV
    if len(key) != AES_KEY_SIZE:
        raise ValueError(f"Khoa AES-128 phai dung {AES_KEY_SIZE} byte, nhan duoc {len(key)} byte.")
    if len(iv) != AES_BLOCK_SIZE:
        raise ValueError(f"Vector IV phai dung {AES_BLOCK_SIZE} byte, nhan duoc {len(iv)} byte.")

    # 2. Chuyen plaintext thanh mảng byte neu dang la chuoi str
    if isinstance(plaintext, str):
        if not plaintext:
            raise ValueError("Plaintext khong duoc de trong.")
        raw_data = plaintext.encode("utf-8")
    else:
        if not plaintext:
            raise ValueError("Plaintext khong duoc de trong.")
        raw_data = plaintext

    # 3. Ap dung dem PKCS#7 (kich thuoc khoi la 128 bit = 16 byte)
    # Neu con thieu N byte (1 <= N <= 16) se them N byte mang gia tri N.
    # Neu vua khit boi so 16 se them 1 khoi 16 byte moi mang gia tri 0x10.
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(raw_data) + padder.finalize()

    # 4. Khoi tao doi tuong ma hoa AES che do CBC
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    # Ma hoa toan bo du lieu da duoc dem
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    return ciphertext


def decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> str:
    """
    Giai ma ciphertext AES-128-CBC va loai bo dem PKCS#7.
    
    Quy trinh:
    1. Kiem tra khoa, IV va do dai ciphertext (bat buoc chia het cho 16).
    2. Giai ma khoi AES-128-CBC de thu duoc du lieu co dem.
    3. Su dung PKCS#7 unpadder de loai bo byte dem an toan.
    4. Giai ma byte UTF-8 tro lai chuoi van ban ban dau.
    
    Tra ve:
        Chuoi plaintext UTF-8 ban dau (ho tro tieng Viet co dau).
    """
    # 1. Kiem tra tinh hop le cua cac tham so
    if len(key) != AES_KEY_SIZE:
        raise ValueError(f"Khoa AES-128 phai dung {AES_KEY_SIZE} byte, nhan duoc {len(key)} byte.")
    if len(iv) != AES_BLOCK_SIZE:
        raise ValueError(f"Vector IV phai dung {AES_BLOCK_SIZE} byte, nhan duoc {len(iv)} byte.")
    if not ciphertext:
        raise ValueError("Ciphertext khong duoc de trong.")
    if len(ciphertext) % AES_BLOCK_SIZE != 0:
        # Neu do dai ban ma khong chia het cho 16 byte thi chac chan goi tin bi loi tren duong truyen
        raise ValueError(
            f"Do dai ciphertext ({len(ciphertext)} byte) khong phai boi so cua "
            f"kich thuoc khoi AES ({AES_BLOCK_SIZE} byte)."
        )

    # 2. Thuc hien giai ma khoi AES-128-CBC
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    try:
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    except Exception as exc:
        raise ValueError(f"Loi giai ma AES: {exc}") from exc

    # 3. Loai bo dem PKCS#7 (unpadding)
    # Kiem tra cac byte cuoi cung: neu sai khoa hoac sai IV thi giai ma ra du lieu rac,
    # gia tri dem se khong hop le va unpadder se ban ra loi ValueError
    unpadder = padding.PKCS7(128).unpadder()
    try:
        raw_data = unpadder.update(padded_plaintext) + unpadder.finalize()
    except ValueError as exc:
        raise ValueError(
            "Loi giai ma: Dem PKCS#7 khong hop le (sai khoa hoac sai IV)."
        ) from exc

    # 4. Chuyen doi mảng byte tro lai chuoi van ban UTF-8
    try:
        return raw_data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Khong the giai ma UTF-8 cho plaintext sau giai ma.") from exc


def get_aes_info_string(key: bytes, iv: bytes, plaintext_len: int, ciphertext_len: int) -> str:
    """
    Tao chuoi thong tin truc quan ve cac tham so ma hoa AES-128-CBC de hien thi len GUI:
    - Khoa Hex 32 ky tu.
    - IV Hex 32 ky tu.
    - Do dai Plaintext goc va do dai sau khi dem PKCS#7 (so luong khoi).
    """
    num_blocks = ciphertext_len // AES_BLOCK_SIZE if ciphertext_len else 0
    return (
        f"Thuat toan       : AES-128-CBC (PKCS#7)\n"
        f"Khoa (Hex, 16B)  : {bytes_to_hex(key)}\n"
        f"IV   (Hex, 16B)  : {bytes_to_hex(iv)}\n"
        f"Do dai Plaintext : {plaintext_len} byte -> Sau dem: {ciphertext_len} byte ({num_blocks} khoi)"
    )
