"""
test_receiver_cli.py - Kiem thu Receiver Server (CLI) ho tro ca HTTP (cURL) va TCP Socket.
"""

import json
import os
import socket
import sys
import time
import unittest
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECEIVER_DIR = os.path.join(BASE_DIR, "receiver")
if RECEIVER_DIR not in sys.path:
    sys.path.insert(0, RECEIVER_DIR)

import aes_cbc
import caesar
import config
from network import ReceiverServer, decrypt_payload, validate_listen_endpoint
import playfair
import protocol


class TestReceiverCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Tim 1 port trong ngau nhien
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            cls.test_port = s.getsockname()[1]

        cls.server = ReceiverServer(host="127.0.0.1", port=cls.test_port)
        cls.server.start(blocking=False)
        time.sleep(0.3)  # Cho server khoi dong

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_validate_listen_endpoint(self):
        validate_listen_endpoint("0.0.0.0", 5000)
        validate_listen_endpoint("127.0.0.1", 8080)
        with self.assertRaises(ValueError):
            validate_listen_endpoint("", 5000)
        with self.assertRaises(ValueError):
            validate_listen_endpoint("999.999.999.999", 5000)
        with self.assertRaises(ValueError):
            validate_listen_endpoint("127.0.0.1", 70000)

    def test_decrypt_payload_caesar(self):
        payload = {"algorithm": "caesar", "key": "3", "ciphertext": "DEF"}
        plain, visual = decrypt_payload(payload)
        self.assertEqual(plain, "ABC")
        self.assertIn("k=3", visual)

    def test_decrypt_payload_playfair(self):
        key = "MONARCHY"
        c = playfair.encrypt("HELLOPLAYFAIR", key)
        payload = {"algorithm": "playfair", "key": key, "ciphertext": c}
        plain, visual = decrypt_payload(payload)
        self.assertEqual(plain, "HELXLOPLAYFAIR")
        self.assertIn("M  O  N  A  R", visual)

    def test_decrypt_payload_aes(self):
        key = aes_cbc.generate_key()
        iv = aes_cbc.generate_iv()
        msg = "Secret Data 123"
        c_bytes = aes_cbc.encrypt(msg, key, iv)
        payload = {
            "algorithm": "aes-128-cbc",
            "key": aes_cbc.bytes_to_hex(key),
            "iv": aes_cbc.bytes_to_hex(iv),
            "ciphertext": aes_cbc.bytes_to_base64(c_bytes),
        }
        plain, visual = decrypt_payload(payload)
        self.assertEqual(plain, msg)
        self.assertIn("AES-128-CBC", visual)

    # ------------------ Kiem thu HTTP (Mo phong lenh cURL) ------------------
    def test_http_get_status(self):
        url = f"http://127.0.0.1:{self.test_port}/"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "online")
            self.assertIn("curl_examples", data)

    def test_http_curl_post_caesar(self):
        url = f"http://127.0.0.1:{self.test_port}/"
        body = json.dumps({"algorithm": "caesar", "key": "3", "ciphertext": "DEF"}).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["plaintext"], "ABC")

    def test_http_curl_post_playfair(self):
        url = f"http://127.0.0.1:{self.test_port}/decrypt"
        key = "KEYWORD"
        plain_input = "SECRET"
        cipher = playfair.encrypt(plain_input, key)
        body = json.dumps(
            {"algorithm": "playfair", "key": key, "ciphertext": cipher}
        ).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["plaintext"], plain_input)

    def test_http_curl_post_aes(self):
        url = f"http://127.0.0.1:{self.test_port}/"
        key = aes_cbc.generate_key()
        iv = aes_cbc.generate_iv()
        secret = "Thong diep bi mat cURL"
        c_bytes = aes_cbc.encrypt(secret, key, iv)

        body = json.dumps(
            {
                "algorithm": "aes-128-cbc",
                "key": aes_cbc.bytes_to_hex(key),
                "iv": aes_cbc.bytes_to_hex(iv),
                "ciphertext": aes_cbc.bytes_to_base64(c_bytes),
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["plaintext"], secret)

    def test_http_curl_post_error(self):
        url = f"http://127.0.0.1:{self.test_port}/"
        body = json.dumps({"algorithm": "invalid_algo", "key": "1", "ciphertext": "abc"}).encode(
            "utf-8"
        )
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)

    # ------------------ Kiem thu TCP Raw Socket (VM1 Sender) ------------------
    def test_tcp_raw_socket(self):
        pkt = protocol.pack_message(config.ALGORITHM_CAESAR, "5", "KLMN")
        with socket.create_connection(("127.0.0.1", self.test_port), timeout=2.0) as sock:
            sock.sendall(pkt)
            sock.settimeout(2.0)
            resp = sock.recv(1024)
            self.assertTrue(len(resp) > 0)
            ack = json.loads(resp.decode("utf-8").strip())
            self.assertEqual(ack["status"], "success")
            self.assertEqual(ack["plaintext"], "FGHI")


if __name__ == "__main__":
    unittest.main()
