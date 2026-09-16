"""
playfair.py - Trien khai thuat toan ma hoa / giai ma Playfair.

Quy uoc mat ma hoc & quy tac thuc thi:
- Bang chu cai 25 ky tu tieng Anh (A-Z, gop chu 'J' vao 'I').
- Ma tran khoa 5x5 duoc sinh tu khoa (keyword) do nguoi dung nhap.
- Chuan hoa plaintext: viet hoa, bo ky tu ngoai A-Z, thay toan bo 'J' bang 'I'.
- Chia cap (digraph): neu hai ky tu trong cap giong nhau thi chen 'X' vao giua,
  neu ky tu cuoi cung bi le thi them 'X' vao cuoi de du cap.
- Bien doi theo 3 quy tac hinh hoc: Cung hang (dich phai/trai), Cung cot (dich xuong/len),
  Khac hang khac cot (tao hinh chu nhat, hoan doi vi tri cot).
- Toi uu hoa: Xay dung bang tra cuu LUT 625 cap ky tu de dat toc do O(1) tren du lieu lon.
"""

from __future__ import annotations

# Import cac hang so tu config: ALPHABET (25 ky tu), FILLER ('X'), MATRIX_SIZE (5)
from config import ALPHABET, FILLER, MATRIX_SIZE


def normalize_text(text: str) -> str:
    """
    Chuan hoa van ban dau vao theo luat Playfair:
    1. Chuyen tat ca thanh chu in hoa (upper).
    2. Thay the ky tu 'J' thanh 'I' (vi bang chi co 25 o, gop J vao I).
    3. Loai bo toan bo ky tu khong thuoc bang 25 chu cai (so, dau cach, dau cau).
    """
    result = []
    # Duyet qua tung ky tu trong chuoi da viet hoa
    for ch in text.upper():
        if ch == "J":
            ch = "I"  # Quy uoc gop J vao I
        if ch in ALPHABET:
            result.append(ch)  # Chi giu lai cac chu cai hop le trong ALPHABET
    return "".join(result)


def build_matrix(key: str) -> list[list[str]]:
    """
    Tao ma tran Playfair 5x5 tu tu khoa nguoi dung nhap:
    - Cac ky tu trong khoa duoc dua vao ma tran truoc (loai bo ky tu trung lap).
    - Cac ky tu con lai trong bang ALPHABET duoc dien tiep vao cac o trong con lai.
    
    Tra ve:
        Danh sach 5 hang, moi hang gom 5 ky tu: list[list[str]]
    """
    # Chuan hoa tu khoa truoc khi dien vao ma tran
    normalized_key = normalize_text(key)
    seen: list[str] = []

    # Duyet qua tu khoa roi den toan bo bang ALPHABET 25 ky tu
    for ch in normalized_key + ALPHABET:
        if ch not in seen:
            seen.append(ch)  # Chi them ky tu chua tung xuat hien

    # Cat danh sach 25 ky tu thanh 5 hang, moi hang 5 ky tu (MATRIX_SIZE = 5)
    return [seen[i * MATRIX_SIZE:(i + 1) * MATRIX_SIZE] for i in range(MATRIX_SIZE)]


def matrix_to_string(matrix: list[list[str]]) -> str:
    """
    Chuyen ma tran 5x5 thanh chuoi van ban truc quan de hien thi len giao dien GUI.
    Moi phan tu cach nhau 2 dau cach, moi hang xuong dong.
    """
    return "\n".join("  ".join(row) for row in matrix)


def _position_map(matrix: list[list[str]]) -> dict[str, tuple[int, int]]:
    """
    Tao tu dien anh xa tu ky tu sang toa do (hang, cot) trong ma tran 5x5.
    Vi du: {'M': (0, 0), 'O': (0, 1), ...}
    Giup tim nhanh toa do cua bat ky chu cai nao ma khong can quet ma tran.
    """
    return {
        matrix[r][c]: (r, c)
        for r in range(MATRIX_SIZE)
        for c in range(MATRIX_SIZE)
    }


def make_digraphs(text: str) -> list[str]:
    """
    Chia van ban da chuan hoa thanh cac cap 2 ky tu (digraph) theo quy tac Playfair:
    - Neu gap hai chu cai giong nhau trong 1 cap (vi du: "LL"): chen 'X' vao giua -> "LX",
      sau do xet chu 'L' thu hai voi ky tu tiep theo.
    - Neu den cuoi van ban ma chi con 1 chu cai dung le: them 'X' vao cuoi.
    """
    digraphs: list[str] = []
    i = 0
    while i < len(text):
        a = text[i]
        # Lay ky tu thu hai neu con trong chuoi, nguoc lai de rong
        b = text[i + 1] if i + 1 < len(text) else ""

        if not b:
            # Truong hop 1: Ky tu cuoi cung bi le -> them FILLER ('X')
            digraphs.append(a + FILLER)
            i += 1
        elif a == b:
            # Truong hop 2: Hai chu cai giong nhau -> chen FILLER ('X') vao giua
            digraphs.append(a + FILLER)
            i += 1  # Chi nhay 1 buoc de ky tu 'b' duoc xet o cap tiep theo
        else:
            # Truong hop 3: Hai chu cai khac nhau hop le -> tao cap 'ab'
            digraphs.append(a + b)
            i += 2  # Nhay 2 buoc sang cap ke tiep
    return digraphs


def _shift_pair(matrix: list[list[str]], pair: str, direction: int) -> str:
    """
    Bien doi mot cap ky tu theo 3 luat hinh hoc cua Playfair.
    
    Tham so:
        direction: +1 cho ma hoa (dich phai / dich xuong)
                   -1 cho giai ma (dich trai / dich len)
    """
    # Lay toa do (hang, cot) cua 2 ky tu trong cap
    pos = _position_map(matrix)
    (r1, c1), (r2, c2) = pos[pair[0]], pos[pair[1]]

    if r1 == r2:
        # LUAT 1: Cung hang (r1 == r2) -> Dich chuyen cot theo direction (vong tron modulo 5)
        c1 = (c1 + direction) % MATRIX_SIZE
        c2 = (c2 + direction) % MATRIX_SIZE
    elif c1 == c2:
        # LUAT 2: Cung cot (c1 == c2) -> Dich chuyen hang theo direction (vong tron modulo 5)
        r1 = (r1 + direction) % MATRIX_SIZE
        r2 = (r2 + direction) % MATRIX_SIZE
    else:
        # LUAT 3: Hinh chu nhat (khac hang, khac cot) -> Hoan doi cot cho nhau (giu nguyen hang)
        c1, c2 = c2, c1

    # Tra ve cap ky tu moi tu toa do da bien doi
    return matrix[r1][c1] + matrix[r2][c2]


def _build_pair_lut(matrix: list[list[str]], direction: int) -> dict[str, str]:
    """
    KY THUAT TOI UU HOA:
    Tao bang tra cuu (Lookup Table - LUT) gom toan bo 25 x 25 = 625 cap ky tu co the xay ra.
    Moi cap duoc tinh san ket qua bien doi theo ma tran.
    
    Khi ma hoa tap tin lon (100 KB, 1 MB), ta chi can tra tu dien voi toc do O(1),
    khong can phai tinh toan lai toa do hang/cot cho tung cap ky tu nua.
    """
    pos = _position_map(matrix)
    lut: dict[str, str] = {}
    for ch1 in ALPHABET:
        for ch2 in ALPHABET:
            (r1, c1), (r2, c2) = pos[ch1], pos[ch2]
            if r1 == r2:
                # Cung hang
                nc1 = (c1 + direction) % MATRIX_SIZE
                nc2 = (c2 + direction) % MATRIX_SIZE
                lut[ch1 + ch2] = matrix[r1][nc1] + matrix[r2][nc2]
            elif c1 == c2:
                # Cung cot
                nr1 = (r1 + direction) % MATRIX_SIZE
                nr2 = (r2 + direction) % MATRIX_SIZE
                lut[ch1 + ch2] = matrix[nr1][c1] + matrix[nr2][c2]
            else:
                # Hinh chu nhat (hoan doi cot)
                lut[ch1 + ch2] = matrix[r1][c2] + matrix[r2][c1]
    return lut


def encrypt(plaintext: str, key: str) -> str:
    """
    Ma hoa plaintext bang khoa Playfair, tra ve chuoi ciphertext in hoa.
    
    Cac buoc:
    1. Tao ma tran 5x5 tu khoa.
    2. Chuan hoa plaintext (A-Z, J->I).
    3. Chia cap ky tu (digraphs) va chen 'X' neu can.
    4. Xay dung bang LUT ma hoa (+1).
    5. Tra cuu LUT de tao ciphertext.
    """
    matrix = build_matrix(key)
    normalized = normalize_text(plaintext)
    if not normalized:
        raise ValueError("Plaintext khong chua ky tu chu cai nao de ma hoa.")

    digraphs = make_digraphs(normalized)
    # Xay dung bang tra cuu chieu ma hoa (+1)
    lut = _build_pair_lut(matrix, +1)

    # Voi moi cap trong digraphs, tra cuu nhanh trong lut
    return "".join(lut.get(pair, _shift_pair(matrix, pair, +1)) for pair in digraphs)


def decrypt(ciphertext: str, key: str) -> str:
    """
    Giai ma ciphertext bang khoa Playfair, tra ve plaintext da duoc chuan hoa.
    
    Cac buoc:
    1. Tao ma tran 5x5 tu khoa.
    2. Chuan hoa ciphertext va kiem tra do dai chan (bat buoc).
    3. Xay dung bang LUT giai ma (-1).
    4. Tra cuu tung cap 2 ky tu de tao plaintext.
    """
    matrix = build_matrix(key)
    normalized = normalize_text(ciphertext)
    if not normalized:
        raise ValueError("Ciphertext rong hoac khong hop le.")
    if len(normalized) % 2 != 0:
        # Trong Playfair, ban ma luon duoc tao tu cac cap ky tu nen do dai bat buoc phai chan
        raise ValueError("Ciphertext Playfair phai co do dai chan.")

    # Xay dung bang tra cuu chieu giai ma (-1)
    lut = _build_pair_lut(matrix, -1)

    # Duyet tung buoc 2 ky tu mot va tra cuu trong lut
    return "".join(
        lut.get(normalized[i:i + 2], _shift_pair(matrix, normalized[i:i + 2], -1))
        for i in range(0, len(normalized), 2)
    )
