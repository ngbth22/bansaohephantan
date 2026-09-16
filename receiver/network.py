"""
network.py (VM2 - Receiver) - Server lang nghe va giai ma khong can GUI.

Ho tro:
1. Giao thuc HTTP (danh cho lenh 'curl' hoac REST API client).
   - GET /: Xem thong tin trang thai server va huong dan lenh curl mau.
   - POST / hoac POST /decrypt: Nhan payload JSON, giai ma va tra ve ket qua HTTP 200 JSON.
2. Giao thuc TCP Raw Socket (tuong thich nguoc voi VM1 Sender):
   - Nhan goi tin JSON ket thuc bang '\\n' (Newline-Delimited JSON), giai ma va in ra console.
"""

from __future__ import annotations

import errno
import ipaddress
import json
import os
import socket
import sys
import threading
from datetime import datetime

# Đảm bảo thư mục hiện tại nằm trong sys.path để import các module nghiệp vụ
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import aes_cbc
import caesar
import config
import playfair
import protocol

# Ma loi socket Winsock tuong ung tren he dieu hanh Windows
_WSAEADDRINUSE = 10048     # Loi cong da bi chiem dung
_WSAEADDRNOTAVAIL = 10049  # Loi dia chi IP khong ton tai


def validate_listen_endpoint(host: str, port: int) -> None:
    """Kiem tra tinh hop le cua IP lang nghe va cong truoc khi bind()."""
    if not host or not host.strip():
        raise ValueError("Dia chi IP lang nghe khong duoc de trong.")
    try:
        ipaddress.IPv4Address(host.strip())
    except ipaddress.AddressValueError as exc:
        raise ValueError(
            f"'{host}' khong phai la dia chi IPv4 hop le "
            "(dung 0.0.0.0 de lang nghe tren moi card mang)."
        ) from exc
    if not (config.PORT_MIN <= port <= config.PORT_MAX):
        raise ValueError(
            f"Cong {port} khong hop le, phai nam trong "
            f"khoang {config.PORT_MIN}-{config.PORT_MAX}."
        )


def _describe_bind_error(exc: OSError, host: str, port: int) -> str:
    """Dien giai ma loi bind thanh thong bao tieng Viet de hieu."""
    code = exc.errno
    if code in (errno.EADDRINUSE, _WSAEADDRINUSE):
        return (
            f"Cong {port} da bi chiem boi mot tien trinh khac. "
            "Hay dong tien trinh dang dung cong nay hoac chon cong khac."
        )
    if code in (errno.EADDRNOTAVAIL, _WSAEADDRNOTAVAIL):
        return (
            f"Dia chi IP {host} khong ton tai tren may nay. "
            "Kiem tra lai cau hinh mang hoac dung 0.0.0.0."
        )
    return f"Khong the mo server tai {host}:{port} - {exc}"


def decrypt_payload(payload: dict) -> tuple[str, str]:
    """
    Giai ma payload JSON tu goi tin nhan duoc.

    Args:
        payload: dict chua thong tin {algorithm, key, ciphertext, iv (neu AES)}.

    Returns:
        tuple (plaintext_giai_ma, chuoi_truc_quan_hoa)
    """
    algo = payload.get("algorithm", config.ALGORITHM_PLAYFAIR).lower()
    key = str(payload.get("key", ""))
    ciphertext = str(payload.get("ciphertext", ""))
    iv = str(payload.get("iv", ""))

    if algo == config.ALGORITHM_PLAYFAIR:
        matrix = playfair.build_matrix(key)
        plaintext = playfair.decrypt(ciphertext, key)
        visual = f"Ma tran Playfair 5x5:\n{playfair.matrix_to_string(matrix)}"
        return plaintext, visual

    elif algo == config.ALGORITHM_CAESAR:
        shift = caesar.normalize_shift(key)
        plaintext = caesar.decrypt(ciphertext, shift)
        visual = f"Bang quy tac dich Caesar (k={shift}):\n{caesar.get_mapping_string(shift)}"
        return plaintext, visual

    elif algo == config.ALGORITHM_AES_128_CBC:
        if not iv:
            raise ValueError("Thuat toan AES-128-CBC bat buoc phai co vector 'iv'.")
        key_bytes = aes_cbc.parse_bytes(key, config.AES_KEY_SIZE, "Khoa AES")
        iv_bytes = aes_cbc.parse_bytes(iv, config.AES_BLOCK_SIZE, "Vector IV")
        cipher_bytes = aes_cbc.base64_to_bytes(ciphertext)
        plaintext = aes_cbc.decrypt(cipher_bytes, key_bytes, iv_bytes)
        info_str = aes_cbc.get_aes_info_string(
            key_bytes,
            iv_bytes,
            len(plaintext.encode("utf-8")),
            len(cipher_bytes),
        )
        visual = f"Thong so giai ma AES-128-CBC:\n{info_str}"
        return plaintext, visual

    else:
        raise ValueError(f"Thuat toan '{algo}' khong duoc ho tro. Ho tro: {config.SUPPORTED_ALGORITHMS}")


if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _safe_print(*args, **kwargs) -> None:
    kwargs.setdefault("flush", True)
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(a) for a in args)
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        sanitized = text.encode(enc, errors="replace").decode(enc)
        print(sanitized, **kwargs)


def print_decryption_log(
    client_addr: tuple[str, int],
    protocol_type: str,
    payload: dict,
    plaintext: str,
    visual: str,
) -> None:
    """In thong tin giai ma ro rang, dep mat ra man hinh console."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    algo = payload.get("algorithm", "?").upper()
    key = payload.get("key", "")
    iv = payload.get("iv", "")
    ciphertext = payload.get("ciphertext", "")

    sep = "=" * 70
    sub_sep = "-" * 70
    _safe_print(f"\n{sep}")
    _safe_print(f"[{now_str}] NHAN GOI TIN TU {client_addr[0]}:{client_addr[1]} ({protocol_type})")
    _safe_print(f"Thuat toan:  {algo}")
    _safe_print(f"Khoa:        {key}")
    if iv:
        _safe_print(f"Vector IV:   {iv}")
    _safe_print(f"Ciphertext:  {ciphertext}")
    _safe_print(f"{sub_sep}")
    _safe_print(f"Truc quan hoa:\n{visual}")
    _safe_print(f"{sub_sep}")
    _safe_print(f"PLAINTEXT GIAI MA:\n>>> {plaintext} <<<")
    _safe_print(f"{sep}\n")


class ReceiverServer:
    """
    Dual-mode Server chay tren background thread hoac blocking:
    - Tu dong phat hien request HTTP (curl) hoac Raw TCP JSON (Sender).
    """

    def __init__(self, host: str = config.DEFAULT_LISTEN_HOST, port: int = config.DEFAULT_PORT):
        self.host = host
        self.port = port
        self._running = False
        self._server_sock: socket.socket | None = None
        self._thread: threading.Thread | None = None

    def start(self, blocking: bool = False) -> None:
        """Khoi dong server."""
        validate_listen_endpoint(self.host, self.port)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.host, self.port))
        except OSError as exc:
            sock.close()
            raise RuntimeError(_describe_bind_error(exc, self.host, self.port)) from exc

        sock.listen(config.LISTEN_BACKLOG)
        sock.settimeout(config.ACCEPT_TIMEOUT)
        self._server_sock = sock
        self._running = True

        print("=" * 70, flush=True)
        print(f"  CRYPTOGRAPHY RECEIVER SERVER (CLI) DANG HOAT DONG", flush=True)
        print(f"  Dia chi lang nghe: {self.host}:{self.port}", flush=True)
        print(f"  Ho tro: HTTP (cURL) & Raw TCP Socket (Sender)", flush=True)
        print("=" * 70, flush=True)
        print("Nhan Ctrl+C de dung server.\n", flush=True)

        if blocking:
            self._serve_loop()
        else:
            self._thread = threading.Thread(target=self._serve_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Yeu cau dung server."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._server_sock:
            try:
                self._server_sock.close()
            except OSError:
                pass
            self._server_sock = None
        print("[*] Receiver Server da dung.")

    def _serve_loop(self) -> None:
        while self._running and self._server_sock:
            try:
                client_sock, addr = self._server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            # Xu ly moi ket noi tren mot worker thread rieng de khong bi block
            client_thread = threading.Thread(
                target=self._handle_client,
                args=(client_sock, addr),
                daemon=True,
            )
            client_thread.start()

    def _handle_client(self, sock: socket.socket, addr: tuple[str, int]) -> None:
        sock.settimeout(config.CLIENT_RECV_TIMEOUT)
        try:
            # Doc chunk dau tien de xac dinh loai giao thuc (HTTP vs Raw TCP)
            initial_data = sock.recv(config.RECV_BUFFER)
            if not initial_data:
                sock.close()
                return

            # Kiem tra xem co phai request HTTP khong (GET, POST, OPTIONS, HEAD, PUT)
            is_http = any(
                initial_data.startswith(method)
                for method in (b"GET ", b"POST ", b"OPTIONS ", b"HEAD ", b"PUT ")
            )

            if is_http:
                self._handle_http_client(sock, addr, initial_data)
            else:
                self._handle_tcp_client(sock, addr, initial_data)

        except (OSError, Exception) as exc:
            print(f"[-] Loi xu ly ket noi tu {addr[0]}:{addr[1]}: {exc}")
        finally:
            try:
                sock.close()
            except OSError:
                pass

    # ------------------------------------------------------------- HTTP HANDLER (cURL)
    def _handle_http_client(
        self, sock: socket.socket, addr: tuple[str, int], initial_data: bytes
    ) -> None:
        buffer = initial_data
        # Doc het header HTTP (ket thuc bang b"\r\n\r\n" hoac b"\n\n")
        while b"\r\n\r\n" not in buffer and b"\n\n" not in buffer:
            chunk = sock.recv(config.RECV_BUFFER)
            if not chunk:
                break
            buffer += chunk

        # Tach header va body ban dau
        if b"\r\n\r\n" in buffer:
            header_bytes, body_prefix = buffer.split(b"\r\n\r\n", 1)
            sep = "\r\n"
        elif b"\n\n" in buffer:
            header_bytes, body_prefix = buffer.split(b"\n\n", 1)
            sep = "\n"
        else:
            self._send_http_response(sock, 400, {"status": "error", "message": "Header HTTP khong hop le."})
            return

        header_lines = header_bytes.decode("utf-8", errors="replace").split(sep)
        request_line = header_lines[0].strip() if header_lines else ""
        parts = request_line.split(" ")
        if len(parts) < 2:
            self._send_http_response(sock, 400, {"status": "error", "message": "Request line khong hop le."})
            return

        method, path = parts[0].upper(), parts[1]

        # Trich xuat cac header quan trong nhu Content-Length
        headers: dict[str, str] = {}
        for line in header_lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        # 1. Xu ly OPTIONS (CORS pre-flight)
        if method == "OPTIONS":
            self._send_http_response(sock, 200, {"status": "ok"})
            return

        # 2. Xu ly GET (Kiem tra status & huong dan mau curl)
        if method == "GET":
            info = {
                "status": "online",
                "message": f"Receiver Server dang chay tren port {self.port}",
                "supported_algorithms": config.SUPPORTED_ALGORITHMS,
                "curl_examples": {
                    "caesar": (
                        f"curl -X POST http://localhost:{self.port}/ "
                        "-H \"Content-Type: application/json\" "
                        "-d '{\"algorithm\": \"caesar\", \"key\": \"3\", \"ciphertext\": \"DEF\"}'"
                    ),
                    "playfair": (
                        f"curl -X POST http://localhost:{self.port}/ "
                        "-H \"Content-Type: application/json\" "
                        "-d '{\"algorithm\": \"playfair\", \"key\": \"MONARCHY\", \"ciphertext\": \"GATLMZCLRQTX\"}'"
                    ),
                    "aes_128_cbc": (
                        f"curl -X POST http://localhost:{self.port}/ "
                        "-H \"Content-Type: application/json\" "
                        "-d '{\"algorithm\": \"aes-128-cbc\", \"key\": \"000102030405060708090a0b0c0d0e0f\", "
                        "\"iv\": \"0f0e0d0c0b0a09080706050403020100\", \"ciphertext\": \"<base64>\"}'"
                    ),
                },
            }
            self._send_http_response(sock, 200, info)
            return

        # 3. Xu ly POST (Giai ma du lieu tu cURL)
        if method == "POST":
            content_length = int(headers.get("content-length", 0))
            body_bytes = body_prefix
            while len(body_bytes) < content_length:
                chunk = sock.recv(min(config.RECV_BUFFER, content_length - len(body_bytes)))
                if not chunk:
                    break
                body_bytes += chunk

            if not body_bytes.strip():
                self._send_http_response(sock, 400, {"status": "error", "message": "Body POST khong duoc de trong."})
                return

            try:
                payload = json.loads(body_bytes.decode("utf-8"))
            except Exception as exc:
                self._send_http_response(sock, 400, {"status": "error", "message": f"JSON khong hop le: {exc}"})
                return

            # Neu payload co wrap theo dang protocol Version 2 hoac json co ban
            if payload.get("type") == config.MESSAGE_TYPE or "ciphertext" in payload:
                pass
            else:
                self._send_http_response(
                    sock, 400, {"status": "error", "message": "Thieu truong 'ciphertext' hoac 'key' trong JSON."}
                )
                return

            try:
                plaintext, visual = decrypt_payload(payload)
                print_decryption_log(addr, f"HTTP POST {path}", payload, plaintext, visual)

                response_data = {
                    "status": "success",
                    "algorithm": payload.get("algorithm", config.DEFAULT_ALGORITHM),
                    "key": payload.get("key", ""),
                    "ciphertext": payload.get("ciphertext", ""),
                    "plaintext": plaintext,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
                self._send_http_response(sock, 200, response_data)
            except Exception as exc:
                print(f"[-] Loi giai ma HTTP tu {addr[0]}: {exc}")
                self._send_http_response(sock, 400, {"status": "error", "message": str(exc)})
            return

        self._send_http_response(sock, 405, {"status": "error", "message": f"Method {method} khong duoc ho tro."})

    def _send_http_response(self, sock: socket.socket, status_code: int, data: dict) -> None:
        status_text = {
            200: "OK",
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error",
        }.get(status_code, "OK")

        body_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        headers = [
            f"HTTP/1.1 {status_code} {status_text}",
            "Content-Type: application/json; charset=utf-8",
            f"Content-Length: {len(body_bytes)}",
            "Access-Control-Allow-Origin: *",
            "Access-Control-Allow-Methods: GET, POST, OPTIONS",
            "Access-Control-Allow-Headers: Content-Type",
            "Connection: close",
            "",
            "",
        ]
        response_bytes = "\r\n".join(headers).encode("utf-8") + body_bytes
        sock.sendall(response_bytes)

    # ------------------------------------------------------------- TCP HANDLER (Sender)
    def _handle_tcp_client(
        self, sock: socket.socket, addr: tuple[str, int], initial_data: bytes
    ) -> None:
        buffer = initial_data
        while config.DELIMITER not in buffer:
            chunk = sock.recv(config.RECV_BUFFER)
            if not chunk:
                break
            buffer += chunk

        while config.DELIMITER in buffer:
            line, buffer = buffer.split(config.DELIMITER, 1)
            line = line.strip()
            if not line:
                continue
            try:
                payload = protocol.unpack_message(line)
                plaintext, visual = decrypt_payload(payload)
                print_decryption_log(addr, "Raw TCP Socket", payload, plaintext, visual)

                # Gui phan hoi ACK ve cho sender neu ket noi van con mo
                ack_response = json.dumps(
                    {
                        "status": "success",
                        "algorithm": payload.get("algorithm"),
                        "plaintext": plaintext,
                    },
                    ensure_ascii=False,
                ).encode("utf-8") + config.DELIMITER
                try:
                    sock.sendall(ack_response)
                except OSError:
                    pass
            except Exception as exc:
                print(f"[-] Loi xu ly goi tin TCP tu {addr[0]}: {exc}")
