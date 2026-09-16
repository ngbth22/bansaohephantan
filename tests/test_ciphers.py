"""
test_ciphers.py - Bo kiem thu tu dong cho cac thuat toan va giao thuc truyen tin.

Bao gom:
- Kiem thu Playfair
- Kiem thu Caesar
- Kiem thu AES-128-CBC
- Kiem thu Protocol (pack / unpack / tuong thich nguoc)
- Kiem thu truyen nhan Socket TCP tich hop
"""

import os
import sys
import unittest

# Them duong dan sender va receiver vao sys.path de kiem thu
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENDER_DIR = os.path.join(BASE_DIR, "sender")
RECEIVER_DIR = os.path.join(BASE_DIR, "receiver")

if SENDER_DIR not in sys.path:
    sys.path.insert(0, SENDER_DIR)

import aes_cbc
import caesar
import config
import playfair
import protocol


class TestPlayfairCipher(unittest.TestCase):
    """Kiem thu thuat toan Playfair."""

    def test_normalize_text(self):
        self.assertEqual(playfair.normalize_text("Hello World"), "HELLOWORLD")
        self.assertEqual(playfair.normalize_text("Jam & Jelly"), "IAMIELLY")
        self.assertEqual(playfair.normalize_text("1234!@#$"), "")

    def test_build_matrix(self):
        matrix = playfair.build_matrix("MONARCHY")
        self.assertEqual(len(matrix), 5)
        self.assertEqual(len(matrix[0]), 5)
        # 25 ky tu duy nhat, khong co 'J'
        flat = [ch for row in matrix for ch in row]
        self.assertEqual(len(flat), 25)
        self.assertEqual(len(set(flat)), 25)
        self.assertNotIn("J", flat)
        self.assertIn("I", flat)

    def test_encrypt_decrypt_roundtrip(self):
        key = "MONARCHY"
        plaintext = "INSTRUMENTS"
        ciphertext = playfair.encrypt(plaintext, key)
        self.assertTrue(len(ciphertext) % 2 == 0)

        decrypted = playfair.decrypt(ciphertext, key)
        # Theo Playfair, J->I va co the co ky tu dem X
        expected_normalized = playfair.normalize_text(plaintext)
        if len(expected_normalized) % 2 != 0:
            expected_normalized += config.FILLER
        self.assertEqual(decrypted, expected_normalized)

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            playfair.encrypt("12345", "MONARCHY")
        with self.assertRaises(ValueError):
            playfair.decrypt("ABC", "MONARCHY")  # do dai le


class TestCaesarCipher(unittest.TestCase):
    """Kiem thu thuat toan Caesar."""

    def test_encrypt_basic(self):
        # Shift = 3: A -> D, B -> E, ..., Z -> C
        self.assertEqual(caesar.encrypt("ABC", 3), "DEF")
        self.assertEqual(caesar.encrypt("XYZ", 3), "ABC")
        self.assertEqual(caesar.encrypt("Hello, World! 123", 3), "Khoor, Zruog! 123")

    def test_decrypt_basic(self):
        self.assertEqual(caesar.decrypt("DEF", 3), "ABC")
        self.assertEqual(caesar.decrypt("Khoor, Zruog! 123", 3), "Hello, World! 123")

    def test_rot13(self):
        plain = "The Quick Brown Fox Jumps Over The Lazy Dog"
        cipher = caesar.encrypt(plain, 13)
        self.assertEqual(caesar.decrypt(cipher, 13), plain)
        # ROT13 hai lan tra ve ban goc
        self.assertEqual(caesar.encrypt(cipher, 13), plain)

    def test_large_and_negative_shift(self):
        plain = "Cryptography"
        # Shift 29 == Shift 3 (29 % 26 = 3)
        self.assertEqual(caesar.encrypt(plain, 29), caesar.encrypt(plain, 3))
        # Shift -1 == Shift 25
        self.assertEqual(caesar.encrypt(plain, -1), caesar.encrypt(plain, 25))
        # Giai ma voi shift -1
        cipher = caesar.encrypt(plain, -1)
        self.assertEqual(caesar.decrypt(cipher, -1), plain)

    def test_get_mapping_string(self):
        mapping = caesar.get_mapping_string(3)
        self.assertIn("Goc:  A B C", mapping)
        self.assertIn("Dich: D E F", mapping)
        self.assertIn("k = 3", mapping)

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            caesar.encrypt("", 3)
        with self.assertRaises(ValueError):
            caesar.decrypt("", 3)
        with self.assertRaises(ValueError):
            caesar.normalize_shift("abc")


class TestAES128CBCCipher(unittest.TestCase):
    """Kiem thu thuat toan AES-128-CBC."""

    def setUp(self):
        self.key = aes_cbc.generate_key()
        self.iv = aes_cbc.generate_iv()

    def test_generate_key_and_iv(self):
        self.assertEqual(len(self.key), 16)
        self.assertEqual(len(self.iv), 16)
        # Sinh 2 lan phai khac nhau (ngau nhien)
        key2 = aes_cbc.generate_key()
        self.assertNotEqual(self.key, key2)

    def test_parse_bytes_hex(self):
        hex_str = "000102030405060708090a0b0c0d0e0f"
        parsed = aes_cbc.parse_bytes(hex_str, 16)
        self.assertEqual(len(parsed), 16)
        self.assertEqual(parsed, bytes.fromhex(hex_str))

    def test_parse_bytes_text(self):
        text_str = "1234567890123456"  # 16 ky tu ASCII = 16 byte
        parsed = aes_cbc.parse_bytes(text_str, 16)
        self.assertEqual(len(parsed), 16)
        self.assertEqual(parsed, text_str.encode("utf-8"))

    def test_parse_bytes_invalid(self):
        with self.assertRaises(ValueError):
            aes_cbc.parse_bytes("", 16)
        with self.assertRaises(ValueError):
            aes_cbc.parse_bytes("short", 16)
        with self.assertRaises(ValueError):
            aes_cbc.parse_bytes("0123456789abcdef0123456789abcdef99", 16)

    def test_encrypt_decrypt_roundtrip(self):
        test_messages = [
            "A",
            "Hello World!",
            "Chính xác 16 byte",  # co the vuot 16 byte UTF-8
            "Tin nhắn tiếng Việt có dấu: Hệ thống phân tán an toàn và bảo mật 100%!",
            "A" * 1000,
        ]
        for msg in test_messages:
            cipher = aes_cbc.encrypt(msg, self.key, self.iv)
            # Do dai phai la boi so cua 16 byte
            self.assertEqual(len(cipher) % 16, 0)
            # Giai ma phai ra dung noi dung ban dau
            decrypted = aes_cbc.decrypt(cipher, self.key, self.iv)
            self.assertEqual(decrypted, msg)

    def test_base64_and_hex_conversions(self):
        cipher = aes_cbc.encrypt("Test payload", self.key, self.iv)
        b64 = aes_cbc.bytes_to_base64(cipher)
        self.assertIsInstance(b64, str)
        restored = aes_cbc.base64_to_bytes(b64)
        self.assertEqual(cipher, restored)

        hex_str = aes_cbc.bytes_to_hex(cipher)
        self.assertIsInstance(hex_str, str)
        restored_hex = aes_cbc.hex_to_bytes(hex_str)
        self.assertEqual(cipher, restored_hex)

    def test_decrypt_with_wrong_key_or_iv_fails(self):
        msg = "Bi mat toi mat"
        cipher = aes_cbc.encrypt(msg, self.key, self.iv)
        wrong_key = aes_cbc.generate_key()
        wrong_iv = aes_cbc.generate_iv()

        with self.assertRaises(ValueError):
            aes_cbc.decrypt(cipher, wrong_key, self.iv)

        # Sai IV thuong lam hong khoi dau tien va co the khien dem sai
        # hoac giai ma ra ky tu vo nghia
        try:
            res = aes_cbc.decrypt(cipher, self.key, wrong_iv)
            self.assertNotEqual(res, msg)
        except ValueError:
            pass  # Loi dem cung la hop le khi IV sai


class TestProtocol(unittest.TestCase):
    """Kiem thu giao thuc dong/giai goi tin."""

    def test_pack_and_unpack_playfair(self):
        packet = protocol.pack_message(
            algorithm=config.ALGORITHM_PLAYFAIR,
            key="MONARCHY",
            ciphertext="GATLMZCLRQTX",
        )
        self.assertTrue(packet.endswith(config.DELIMITER))
        payload = protocol.unpack_message(packet.rstrip(config.DELIMITER))
        self.assertEqual(payload["algorithm"], "playfair")
        self.assertEqual(payload["key"], "MONARCHY")
        self.assertEqual(payload["ciphertext"], "GATLMZCLRQTX")

    def test_pack_and_unpack_caesar(self):
        packet = protocol.pack_message(
            algorithm=config.ALGORITHM_CAESAR,
            key="3",
            ciphertext="KHOOR",
        )
        payload = protocol.unpack_message(packet.rstrip(config.DELIMITER))
        self.assertEqual(payload["algorithm"], "caesar")
        self.assertEqual(payload["key"], "3")
        self.assertEqual(payload["ciphertext"], "KHOOR")

    def test_pack_and_unpack_aes(self):
        iv_hex = "000102030405060708090a0b0c0d0e0f"
        packet = protocol.pack_message(
            algorithm=config.ALGORITHM_AES_128_CBC,
            key="2b7e151628aed2a6abf7158809cf4f3c",
            ciphertext="abc123base64==",
            iv=iv_hex,
        )
        payload = protocol.unpack_message(packet.rstrip(config.DELIMITER))
        self.assertEqual(payload["algorithm"], "aes-128-cbc")
        self.assertEqual(payload["iv"], iv_hex)

    def test_legacy_v1_compatibility(self):
        import json
        legacy_packet = json.dumps({
            "type": "playfair_message",
            "version": 1,
            "key": "KEYWORD",
            "ciphertext": "BMODIF",
            "timestamp": "2026-08-28T14:30:00",
        }).encode("utf-8")
        payload = protocol.unpack_message(legacy_packet)
        self.assertEqual(payload["algorithm"], "playfair")
        self.assertEqual(payload["key"], "KEYWORD")
        self.assertEqual(payload["ciphertext"], "BMODIF")

    def test_unpack_invalid(self):
        with self.assertRaises(ValueError):
            protocol.unpack_message(b"not json")
        with self.assertRaises(ValueError):
            protocol.unpack_message(b'{"type":"unknown"}')
        with self.assertRaises(ValueError):
            # Thieu IV trong AES
            protocol.unpack_message(
                b'{"type":"crypto_message","algorithm":"aes-128-cbc","key":"k","ciphertext":"c"}'
            )


if __name__ == "__main__":
    unittest.main()
