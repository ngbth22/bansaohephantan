"""
test_integration.py - Kiem thu tich hop truyen nhan qua mang TCP thuc te.
"""

import socket
import sys
import threading
import time
import unittest

sys.path.insert(0, "receiver")
sys.path.insert(0, "sender")

import aes_cbc
import caesar
import config
import playfair
import protocol


class TestTCPIntegration(unittest.TestCase):
    """Kiem thu truyen nhan qua TCP Socket voi ca 3 thuat toan."""

    @classmethod
    def setUpClass(cls):
        # Mo mot socket lang nghe tren localhost cong ngau nhien
        cls.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cls.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        cls.server_sock.bind(("127.0.0.1", 0))
        cls.host, cls.port = cls.server_sock.getsockname()
        cls.server_sock.listen(5)
        cls.running = True
        cls.received_messages = []

        def server_loop():
            cls.server_sock.settimeout(0.5)
            while cls.running:
                try:
                    conn, _ = cls.server_sock.accept()
                except socket.timeout:
                    continue
                with conn:
                    conn.settimeout(2.0)
                    buffer = b""
                    while cls.running:
                        try:
                            chunk = conn.recv(1024)
                        except socket.timeout:
                            break
                        if not chunk:
                            break
                        buffer += chunk
                        while config.DELIMITER in buffer:
                            line, buffer = buffer.split(config.DELIMITER, 1)
                            if line.strip():
                                cls.received_messages.append(line)

        cls.thread = threading.Thread(target=server_loop, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.running = False
        cls.thread.join(timeout=2.0)
        cls.server_sock.close()

    def _send_packet(self, packet: bytes):
        with socket.create_connection((self.host, self.port), timeout=2.0) as sock:
            sock.sendall(packet)
        time.sleep(0.1)

    def test_e2e_playfair(self):
        key = "SECURITY"
        plain = "DISTRIBUTEDSYSTEMS"
        cipher = playfair.encrypt(plain, key)
        packet = protocol.pack_message(config.ALGORITHM_PLAYFAIR, key, cipher)
        
        self._send_packet(packet)
        self.assertTrue(len(self.received_messages) > 0)
        raw = self.received_messages.pop(0)

        payload = protocol.unpack_message(raw)
        self.assertEqual(payload["algorithm"], "playfair")
        decrypted = playfair.decrypt(payload["ciphertext"], payload["key"])
        self.assertEqual(decrypted, playfair.normalize_text(plain))

    def test_e2e_caesar(self):
        shift = 7
        plain = "Hello Distributed World 2026!"
        cipher = caesar.encrypt(plain, shift)
        packet = protocol.pack_message(config.ALGORITHM_CAESAR, str(shift), cipher)

        self._send_packet(packet)
        self.assertTrue(len(self.received_messages) > 0)
        raw = self.received_messages.pop(0)

        payload = protocol.unpack_message(raw)
        self.assertEqual(payload["algorithm"], "caesar")
        decrypted = caesar.decrypt(payload["ciphertext"], int(payload["key"]))
        self.assertEqual(decrypted, plain)

    def test_e2e_aes_128_cbc(self):
        key = aes_cbc.generate_key()
        iv = aes_cbc.generate_iv()
        plain = "Mã hóa bảo mật cao bằng AES-128-CBC qua mạng TCP!"
        cipher_bytes = aes_cbc.encrypt(plain, key, iv)
        b64_cipher = aes_cbc.bytes_to_base64(cipher_bytes)
        iv_hex = aes_cbc.bytes_to_hex(iv)
        key_hex = aes_cbc.bytes_to_hex(key)

        packet = protocol.pack_message(
            config.ALGORITHM_AES_128_CBC,
            key_hex,
            b64_cipher,
            iv=iv_hex,
        )

        self._send_packet(packet)
        self.assertTrue(len(self.received_messages) > 0)
        raw = self.received_messages.pop(0)

        payload = protocol.unpack_message(raw)
        self.assertEqual(payload["algorithm"], "aes-128-cbc")

        # Giai ma tai may nhan
        rec_key = aes_cbc.parse_bytes(payload["key"], 16)
        rec_iv = aes_cbc.parse_bytes(payload["iv"], 16)
        rec_cipher = aes_cbc.base64_to_bytes(payload["ciphertext"])
        decrypted = aes_cbc.decrypt(rec_cipher, rec_key, rec_iv)
        self.assertEqual(decrypted, plain)


if __name__ == "__main__":
    unittest.main()
