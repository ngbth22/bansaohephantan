"""
protocol.py - Dinh dang du lieu truyen giua VM1 (Sender) va VM2 (Receiver).

Format goi tin: JSON UTF-8, ket thuc bang ky tu xuong dong '\\n'
(Newline-Delimited JSON) de tach cac goi tin tren luong byte TCP lien tuc.

Ho tro 3 thuat toan: Playfair, Caesar, AES-128-CBC.

Cau truc goi tin phien ban 2 (JSON Object):
{
    "type": "crypto_message",
    "version": 2,
    "algorithm": "playfair" | "caesar" | "aes-128-cbc",
    "key": "<khoa hoac do dich>",
    "iv": "<vector IV 16 byte (hex) neu dung AES-128-CBC>",
    "ciphertext": "<ban ma van ban hoac Base64>",
    "timestamp": "<thoi diem gui, ISO 8601 YYYY-MM-DDTHH:MM:SS>"
}
"""

from __future__ import annotations

import json
from datetime import datetime

# Import cac hang so cau hinh giao thuc tu config.py
from config import (
    ALGORITHM_AES_128_CBC,
    ALGORITHM_PLAYFAIR,
    DELIMITER,
    ENCODING,
    LEGACY_MESSAGE_TYPE,
    MESSAGE_TYPE,
    PROTOCOL_VERSION,
    SUPPORTED_ALGORITHMS,
)


def pack_message(
    algorithm: str,
    key: str,
    ciphertext: str,
    iv: str = "",
) -> bytes:
    """
    Dong goi thong tin ma hoa thanh goi tin JSON san sang gui qua mang TCP.

    Quy trinh:
    1. Kiem tra thuat toan co nam trong danh muc duoc ho tro khong.
    2. Xay dung Dictionary chua cac truong bat buoc: type, version, algorithm, key, ciphertext, timestamp.
    3. Neu la AES-128-CBC thi bo sung them truong 'iv'.
    4. Chuyen Dictionary sang chuoi JSON UTF-8 (ensure_ascii=False de giu ky tu tieng Viet).
    5. Gan them byte phan tach '\\n' (DELIMITER) vao cuoi goi tin.

    Args:
        algorithm: 'playfair', 'caesar' hoac 'aes-128-cbc'.
        key: Chuoi khoa Playfair, do dich Caesar, hoac khoa AES (dang hex/text).
        ciphertext: Ban ma da ma hoa.
        iv: Vector khoi tao (bat buoc doi voi aes-128-cbc).

    Returns:
        Mang byte JSON UTF-8 ket thuc bang ky tu phan tach b'\\n'.
    """
    # 1. Kiem tra tinh hop le cua ten thuat toan
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"Thuat toan '{algorithm}' khong duoc ho tro. Ho tro: {SUPPORTED_ALGORITHMS}")

    # 2. Xay dung payload chua thong tin goi tin
    payload: dict = {
        "type": MESSAGE_TYPE,                                       # Dinh danh loai goi tin Version 2
        "version": PROTOCOL_VERSION,                               # So hieu phien ban giao thuc (2)
        "algorithm": algorithm,                                     # Thuat toan su dung
        "key": str(key),                                            # Khoa / do dich
        "ciphertext": ciphertext,                                   # Ban ma
        "timestamp": datetime.now().isoformat(timespec="seconds"),  # Moc thoi gian gui
    }

    # 3. Neu co tham so IV truyen vao (dung cho AES), them vao payload
    if iv:
        payload["iv"] = iv

    # 4. Serialize sang chuoi JSON, encode sang UTF-8 va noi them byte delimiter b'\n'
    # ensure_ascii=False giup giu nguyen chuoi unicode ma khong bi escape sang dang \uXXXX
    return json.dumps(payload, ensure_ascii=False).encode(ENCODING) + DELIMITER


def unpack_message(raw: bytes) -> dict:
    """
    Giai ma va kiem tra tinh hop le cua goi tin JSON nhan duoc tu TCP Socket.

    Quy trinh:
    1. Giai ma mang byte raw sang chuoi UTF-8 va parse JSON thanh Dictionary.
    2. Kiem tra tinh tuong thich nguoc:
       - Neu goi tin la phien ban 1 ('playfair_message') -> Tu dong gan algorithm = 'playfair'.
       - Neu khong dung 'crypto_message' -> Bao loi khong dung giao thuc.
    3. Kiem tra cac truong bat buoc: 'key', 'ciphertext'.
    4. Kiem tra dac thu cua AES-128-CBC: bat buoc phai co truong 'iv'.

    Args:
        raw: Mang byte cua mot dong JSON hoan chinh (da duoc bo delimiter '\\n').

    Returns:
        Dictionary chua day du thong tin goi tin de ben nhan thuc hien giai ma.
    """
    # 1. Thu decode UTF-8 va parse JSON
    try:
        payload = json.loads(raw.decode(ENCODING))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Goi tin khong phai JSON hop le: {exc}") from exc

    # Kiem tra doi tuong parse duoc phai la mot JSON Object (dict)
    if not isinstance(payload, dict):
        raise ValueError("Goi tin phai la mot JSON object.")

    # 2. Kiem tra loai goi tin va ho tro TUONG THICH NGUOC (Backward Compatibility)
    msg_type = payload.get("type")
    if msg_type == LEGACY_MESSAGE_TYPE:
        # Neu la goi tin cu cua Version 1 (chi co Playfair) -> Tu dong map sang "playfair"
        payload["algorithm"] = ALGORITHM_PLAYFAIR
    elif msg_type != MESSAGE_TYPE:
        # Neu loai goi tin hoan toan la, tu choi xu ly de bao ve he thong
        raise ValueError(
            f"Goi tin khong dung loai cho phep (nhan '{msg_type}', mong muon '{MESSAGE_TYPE}' hoac '{LEGACY_MESSAGE_TYPE}')."
        )

    # 3. Kiem tra danh muc thuat toan duoc ho tro
    algorithm = payload.get("algorithm", ALGORITHM_PLAYFAIR)
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"Thuat toan '{algorithm}' khong nam trong danh muc ho tro: {SUPPORTED_ALGORITHMS}")
    payload["algorithm"] = algorithm

    # 4. Kiem tra su hien dien cua cac truong bat buoc
    if "key" not in payload:
        raise ValueError("Goi tin thieu truong 'key'.")
    if "ciphertext" not in payload:
        raise ValueError("Goi tin thieu truong 'ciphertext'.")

    # 5. Kiem tra rieng doi voi thuat toan AES-128-CBC: bat buoc phai co vector IV
    if algorithm == ALGORITHM_AES_128_CBC:
        if not payload.get("iv"):
            raise ValueError("Goi tin AES-128-CBC thieu truong 'iv'.")

    return payload
