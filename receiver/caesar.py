"""
caesar.py - Trien khai thuat toan ma hoa / giai ma Caesar (dich chuyen ky tu).

Quy uoc toan hoc & ky thuat:
- Khoa la mot so nguyen shift k (vi du k = 3 cho Caesar co dien, k = 13 cho ROT13).
- Phep bien doi duoc thuc hien theo modulo 26 tren cac ky tu chu cai A-Z va a-z.
- Cac ky tu khong phai chu cai (khoang trang, chu so, dau cau, tieng Viet co dau ngoai ASCII)
  duoc giu nguyen khong bien doi.
- Su dung bang anh xa str.maketrans() o tang C cua Python de toi uu hoa toc do ma hoa.
"""

from __future__ import annotations

# Dinh nghia 26 chu cai tieng Anh viet hoa thu tu tu A den Z
UPPERCASE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Dinh nghia 26 chu cai tieng Anh viet thuong thu tu tu a den z
LOWERCASE_ALPHABET = "abcdefghijklmnopqrstuvwxyz"

# So luong chu cai trong bang chu cai tieng Anh (dung cho phep chia lay du modulo)
ALPHABET_SIZE = 26


def normalize_shift(shift: int | str) -> int:
    """
    Chuan hoa do dich k ve so nguyen hop le trong khoang tu 0 den 25.
    
    Tham so:
        shift: Do dich nguoi dung truyen vao (co the la int hoac chuoi so str, vi du "3", "-1", "29").
        
    Tra ve:
        Gia tri so nguyen trong khoang [0, 25].
        
    Ngoai le:
        ValueError: Neu gia tri truyen vao khong the ep kieu sang so nguyen.
    """
    try:
        # Ep kieu tham so sang so nguyen (int)
        val = int(shift)
    except (ValueError, TypeError) as exc:
        # Neu nguoi dung truyen chuoi khong phai so (vi du "abc"), bao loi ro rang
        raise ValueError(f"Do dich Caesar phai la so nguyen, nhan duoc '{shift}'.") from exc

    # Phep toan modulo 26:
    # - Neu k = 29 -> 29 % 26 = 3 (dich 29 vi tri tuong duong dich 3 vi tri)
    # - Neu k = -1 -> -1 % 26 = 25 trong Python (dich lui 1 vi tri tuong duong dich tien 25 vi tri)
    return val % ALPHABET_SIZE


def encrypt(plaintext: str, shift: int | str) -> str:
    """
    Ma hoa chuoi plaintext bang thuat toan Caesar voi do dich shift k.
    
    Cong thuc toan hoc: c = (p + k) mod 26
    
    Tham so:
        plaintext: Van ban goc can ma hoa.
        shift: Do dich chuyen k.
        
    Tra ve:
        Ciphertext da duoc dich chuyen cac chu cai.
    """
    # Kiem tra neu plaintext rong thi bao loi khong hop le
    if not plaintext:
        raise ValueError("Plaintext khong duoc de trong.")

    # 1. Chuan hoa do dich ve khoang 0-25
    k = normalize_shift(shift)

    # 2. Tao bang chu cai da bi dich chuyen k vi tri bang cach cat va ghep chuoi (slicing)
    # Vi du k = 3:
    # UPPERCASE_ALPHABET[3:] la "DEFGHIJKLMNOPQRSTUVWXYZ"
    # UPPERCASE_ALPHABET[:3] la "ABC"
    # -> upper_shifted se la "DEFGHIJKLMNOPQRSTUVWXYZABC"
    upper_shifted = UPPERCASE_ALPHABET[k:] + UPPERCASE_ALPHABET[:k]
    lower_shifted = LOWERCASE_ALPHABET[k:] + LOWERCASE_ALPHABET[:k]

    # 3. Tao bang anh xa ky tu 1-1 (Translation Table) cho ca chu hoa va chu thuong
    trans_table = str.maketrans(
        UPPERCASE_ALPHABET + LOWERCASE_ALPHABET,
        upper_shifted + lower_shifted,
    )

    # 4. Ap dung bang anh xa de thay the toan bo ky tu trong plaintext
    # Phuong thuc translate() duoc viet bang ma C trong Python nen chay cuc nhanh
    return plaintext.translate(trans_table)


def decrypt(ciphertext: str, shift: int | str) -> str:
    """
    Giai ma ciphertext Caesar bang cach dich nguoc lai dung do dich shift k ban dau.
    
    Cong thuc toan hoc: p = (c - k) mod 26
    
    Tham so:
        ciphertext: Van ban ma hoa can giai ma.
        shift: Do dich k da dung khi ma hoa.
        
    Tra ve:
        Plaintext ban dau.
    """
    # Kiem tra neu ciphertext rong thi bao loi
    if not ciphertext:
        raise ValueError("Ciphertext khong duoc de trong.")

    # Chuan hoa do dich k
    k = normalize_shift(shift)

    # Giai ma thuc chat la ma hoa lai voi do dich am (-k)
    # Vi du: ma hoa dich +3 thi giai ma dich -3 (tuong duong +23 modulo 26)
    return encrypt(ciphertext, -k)


def get_mapping_string(shift: int | str) -> str:
    """
    Tao chuoi truc quan hoa bang anh xa dich chuyen chu cai de hien thi len giao dien GUI.
    Giup giang vien va nguoi xem de dang quan sat quy tac bien doi ky tu.
    """
    k = normalize_shift(shift)
    # Danh sach cac chu cai ban dau cach nhau 1 dau cach
    plain_chars = " ".join(UPPERCASE_ALPHABET)
    # Danh sach cac chu cai sau khi dich k vi tri
    cipher_chars = " ".join(UPPERCASE_ALPHABET[k:] + UPPERCASE_ALPHABET[:k])

    # Tra ve chuoi 2 dong de trinh chieu tren giao dien
    return (
        f"Goc:  {plain_chars}\n"
        f"Dich: {cipher_chars}  (k = {k})"
    )
