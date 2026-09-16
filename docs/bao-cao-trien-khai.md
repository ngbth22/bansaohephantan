# Tài liệu kỹ thuật hệ thống mã hóa và truyền tin đa thuật toán (Playfair, Caesar, AES-128-CBC)

**Biên soạn theo khung tài liệu ISO/IEC/IEEE 26514:2022 – Systems and software engineering — Design and development of information for users**

| Thuộc tính tài liệu | Giá trị |
|---|---|
| Tên hệ thống | Cryptography Sender/Receiver Demo (Playfair, Caesar, AES-128-CBC) |
| Phiên bản tài liệu | 3.0 |
| Ngày ban hành | 12/09/2026 |
| Kho mã nguồn | https://github.com/ngbth22/hephantan |

---

## 1. Phạm vi và mục đích tài liệu

Tài liệu này mô tả cấu hình, thiết kế triển khai và đặc tả tham chiếu (reference information) của hệ thống demo mã hóa – truyền tin – giải mã hỗ trợ đa thuật toán mật mã cổ điển và hiện đại giữa hai máy ảo Windows: **Playfair**, **Caesar**, và **AES-128-CBC**.

Theo yêu cầu của ISO/IEC/IEEE 26514:2022 về thông tin hướng đến người dùng và nhà phát triển, tài liệu cung cấp:
1. Thông tin khái quát về kiến trúc hệ thống và cấu hình tập trung.
2. Đặc tả từng hàm gồm mục đích, đầu vào, đầu ra, logic xử lý và ngoại lệ.
3. Cơ chế xử lý ngoại lệ toàn diện và thông báo hành động được.
4. Luồng dữ liệu chi tiết giữa Sender (VM1) và Receiver (VM2).
5. Hướng dẫn vận hành mạng và kiểm thử tự động.

## 2. Đối tượng sử dụng tài liệu

- **Người vận hành demo / Giảng viên / Sinh viên**: theo dõi các mục 3, 4, 7 và 8 để cấu hình, chạy và thực hành mã hóa/truyền tin.
- **Người phát triển / Bảo trì hệ thống**: theo dõi mục 5 và 6 để hiểu chi tiết đặc tả hàm, giao thức mở rộng và cơ chế xử lý ngoại lệ.

## 3. Tổng quan hệ thống

Hệ thống gồm hai ứng dụng độc lập triển khai trên hai máy ảo Windows:

- **VM1 – Sender** (`sender/`): cho phép người dùng chọn thuật toán mật mã (Playfair, Caesar, hoặc AES-128-CBC), nhập khóa/độ dịch/IV tương ứng, nhập nội dung plaintext, mã hóa, hiển thị trực quan hóa (ma trận 5×5, bảng ánh xạ dịch chuyển, hoặc thông số khối AES), đóng gói khung tin JSON UTF-8 và truyền qua TCP Socket.
- **VM2 – Receiver** (`receiver/`): chạy TCP Server trên luồng nền (QThread), lắng nghe các kết nối từ VM1, tách khung dữ liệu theo ký tự phân cách dòng (`\n`), tự động giải gói tin JSON, nhận diện thuật toán, tự động giải mã và hiển thị trực quan kết quả trên giao diện.

Mỗi phía ứng dụng gồm 8 module:
- `main.py`: Khởi động ứng dụng PySide6.
- `gui.py`: Giao diện đồ họa người dùng tương tác.
- `playfair.py`: Thuật toán mã hóa / giải mã Playfair (ma trận 5×5).
- `caesar.py`: Thuật toán mã hóa / giải mã Caesar (dịch chuyển ký tự).
- `aes_cbc.py`: Thuật toán mã hóa / giải mã khối đối xứng AES-128-CBC với đệm PKCS#7.
- `network.py`: Kết nối mạng TCP Client / Server bất đồng bộ trên QThread.
- `protocol.py`: Đóng gói và giải gói tin JSON Version 2 (hỗ trợ tương thích ngược Version 1).
- `config.py`: Tập trung các tham số cấu hình hệ thống.

Môi trường thực thi: Python 3.12 / 3.13, PySide6, cryptography, TCP Sockets trên Windows.

## 4. Cấu hình hệ thống (`config.py`)

Toàn bộ hằng số và cấu hình hệ thống được tập trung trong `config.py` (đối xứng ở cả `sender/` và `receiver/`):

### 4.1. Nhóm tham số thuật toán

| Hằng số | Giá trị mặc định | Ý nghĩa |
|---|---|---|
| `ALGORITHM_PLAYFAIR` | `"playfair"` | Định danh thuật toán Playfair |
| `ALGORITHM_CAESAR` | `"caesar"` | Định danh thuật toán Caesar |
| `ALGORITHM_AES_128_CBC` | `"aes-128-cbc"` | Định danh thuật toán AES-128-CBC |
| `SUPPORTED_ALGORITHMS` | `["playfair", "caesar", "aes-128-cbc"]` | Danh mục thuật toán được hỗ trợ |
| `DEFAULT_ALGORITHM` | `"playfair"` | Thuật toán mặc định khi khởi động |
| `ALPHABET` | `"ABCDEFGHIKLMNOPQRSTUVWXYZ"` | Bảng chữ cái Playfair 25 ký tự (gộp J vào I) |
| `FILLER` | `"X"` | Ký tự đệm cho cặp trùng hoặc độ dài lẻ trong Playfair |
| `MATRIX_SIZE` | `5` | Kích thước ma trận Playfair 5×5 |
| `DEFAULT_CAESAR_SHIFT` | `3` | Độ dịch mặc định cho Caesar (Caesar cổ điển) |
| `AES_KEY_SIZE` | `16` | Kích thước khóa AES-128 (128 bit = 16 byte) |
| `AES_BLOCK_SIZE` | `16` | Kích thước khối AES (128 bit = 16 byte) |

### 4.2. Nhóm tham số giao thức

| Hằng số | Giá trị mặc định | Ý nghĩa |
|---|---|---|
| `MESSAGE_TYPE` | `"crypto_message"` | Định danh loại gói tin Version 2 |
| `LEGACY_MESSAGE_TYPE` | `"playfair_message"` | Định danh gói tin Version 1 (tương thích ngược) |
| `PROTOCOL_VERSION` | `2` | Phiên bản giao thức hiện tại |
| `ENCODING` | `"utf-8"` | Bảng mã hóa byte cho gói tin JSON |
| `DELIMITER` | `b"\n"` | Ký tự phân tách khung tin trên luồng TCP |

### 4.3. Nhóm tham số mạng & giao diện

| Hằng số | Giá trị mặc định | Ý nghĩa |
|---|---|---|
| `DEFAULT_PORT` | `5000` | Cổng TCP mặc định |
| `DEFAULT_RECEIVER_HOST` | `"192.168.1.2"` | Địa chỉ IP mặc định của Receiver (VM2) |
| `DEFAULT_LISTEN_HOST` | `"0.0.0.0"` | Địa chỉ IP lắng nghe mặc định (mọi card mạng) |
| `PORT_MIN`, `PORT_MAX` | `1`, `65535` | Khoảng cổng TCP hợp lệ |
| `CONNECT_TIMEOUT` | `5.0` s | Thời gian chờ kết nối phía client |
| `ACCEPT_TIMEOUT` | `0.5` s | Chu kỳ kiểm tra yêu cầu dừng server |
| `CLIENT_RECV_TIMEOUT` | `10.0` s | Thời gian chờ dữ liệu từ một client |
| `RECV_BUFFER` | `4096` byte | Kích thước bộ đệm đọc socket |
| `LISTEN_BACKLOG` | `5` | Số kết nối chờ tối đa trong hàng đợi |
| `SERVER_STOP_WAIT_MS` | `2000` ms | Thời gian chờ server dừng khi thoát ứng dụng |
| `SENDER_WINDOW_SIZE` | `(820, 720)` | Kích thước cửa sổ giao diện Sender |
| `RECEIVER_WINDOW_SIZE` | `(820, 740)` | Kích thước cửa sổ giao diện Receiver |
| `MONO_FONT_FAMILY`, `MONO_FONT_SIZE` | `"Consolas"`, `11` | Phông chữ hiển thị ma trận, thông số và log |

---

## 5. Đặc tả tham chiếu các hàm

### 5.1. Module `caesar.py`

#### 5.1.1. `normalize_shift(shift: int | str) -> int`
- **Mục đích**: Chuyển đổi và chuẩn hóa độ dịch về số nguyên hợp lệ trong khoảng $0 \le k \le 25$.
- **Đầu vào**: `shift` (`int | str`) – số nguyên hoặc chuỗi biểu diễn số nguyên.
- **Đầu ra**: `int` – giá trị $k \pmod{26}$.
- **Logic xử lý**: Ép kiểu sang `int`; lấy modulo 26 để hỗ trợ cả số âm lẫn số lớn hơn 26.
- **Ngoại lệ**: `ValueError` nếu `shift` không thể chuyển đổi thành số nguyên.

#### 5.1.2. `encrypt(plaintext: str, shift: int | str) -> str`
- **Mục đích**: Mã hóa văn bản rõ bằng thuật toán dịch chuyển Caesar.
- **Đầu vào**: `plaintext` (`str`) – văn bản cần mã hóa; `shift` (`int | str`) – độ dịch.
- **Đầu ra**: `str` – văn bản mã hóa (ciphertext).
- **Logic xử lý**:
  - Kiểm tra plaintext không rỗng;
  - Chuẩn hóa độ dịch $k$;
  - Với từng ký tự:
    - Nếu là chữ hoa `A-Z`: `chr((ord(ch) - 65 + k) % 26 + 65)`
    - Nếu là chữ thường `a-z`: `chr((ord(ch) - 97 + k) % 26 + 97)`
    - Ký tự khác (khoảng trắng, số, dấu câu): giữ nguyên không đổi.
- **Ngoại lệ**: `ValueError` nếu plaintext rỗng.

#### 5.1.3. `decrypt(ciphertext: str, shift: int | str) -> str`
- **Mục đích**: Giải mã ciphertext Caesar về văn bản ban đầu.
- **Đầu vào**: `ciphertext` (`str`), `shift` (`int | str`).
- **Đầu ra**: `str` – văn bản sau giải mã.
- **Logic xử lý**: Gọi `encrypt(ciphertext, -k)` để thực hiện phép dịch ngược modulo 26.
- **Ngoại lệ**: `ValueError` nếu ciphertext rỗng.

#### 5.1.4. `get_mapping_string(shift: int | str) -> str`
- **Mục đích**: Tạo biểu diễn bảng ánh xạ chữ cái trực quan hiển thị trên giao diện.
- **Đầu vào**: `shift` (`int | str`).
- **Đầu ra**: `str` – chuỗi 2 dòng thể hiện ánh xạ từ bảng chữ cái gốc sang bảng chữ cái đã dịch.

---

### 5.2. Module `aes_cbc.py`

#### 5.2.1. `generate_key() -> bytes` & `generate_iv() -> bytes`
- **Mục đích**: Sinh khóa mật mã ngẫu nhiên an toàn (16 byte) và vector khởi tạo IV (16 byte).
- **Đầu vào**: Không có.
- **Đầu ra**: `bytes` – chuỗi 16 byte ngẫu nhiên từ `os.urandom(16)`.

#### 5.2.2. `parse_bytes(text: str, expected_len: int = 16, label: str = "Khóa") -> bytes`
- **Mục đích**: Chuyển đổi linh hoạt đầu vào của người dùng thành chuỗi byte nhị phân.
- **Đầu vào**: `text` (`str`) – chuỗi do người dùng nhập; `expected_len` (`int`) – độ dài byte kỳ vọng (mặc định 16); `label` (`str`) – tên hiển thị khi báo lỗi.
- **Đầu ra**: `bytes` – chuỗi byte đúng độ dài.
- **Logic xử lý**:
  - Nếu chuỗi có độ dài $2 \times expected\_len$ (32 ký tự) và là chuỗi Hex hợp lệ: chuyển qua `bytes.fromhex()`.
  - Nếu chuỗi ký tự UTF-8 có đúng `expected_len` byte: mã hóa sang UTF-8 bytes.
  - Báo lỗi kèm thông tin chi tiết về độ dài hiện tại nếu không thỏa mãn.
- **Ngoại lệ**: `ValueError` nếu chuỗi rỗng hoặc sai độ dài.

#### 5.2.3. `encrypt(plaintext: str | bytes, key: bytes, iv: bytes) -> bytes`
- **Mục đích**: Mã hóa dữ liệu bằng chuẩn AES-128 ở chế độ CBC với đệm PKCS#7.
- **Đầu vào**: `plaintext` (`str | bytes`), `key` (`bytes`, đúng 16 byte), `iv` (`bytes`, đúng 16 byte).
- **Đầu ra**: `bytes` – bản mã nhị phân với độ dài là bội số của 16 byte.
- **Logic xử lý**:
  - Kiểm tra độ dài khóa và IV;
  - Chuyển plaintext sang UTF-8 byte nếu là `str`;
  - Áp dụng đệm `PKCS7(128)`;
  - Khởi tạo `Cipher(algorithms.AES(key), modes.CBC(iv))` và thực hiện mã hóa.
- **Ngoại lệ**: `ValueError` nếu khóa/IV sai độ dài hoặc plaintext rỗng.

#### 5.2.4. `decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> str`
- **Mục đích**: Giải mã dữ liệu AES-128-CBC, gỡ đệm PKCS#7 và khôi phục chuỗi văn bản UTF-8 ban đầu.
- **Đầu vào**: `ciphertext` (`bytes`), `key` (`bytes`, 16 byte), `iv` (`bytes`, 16 byte).
- **Đầu ra**: `str` – chuỗi plaintext ban đầu.
- **Logic xử lý**:
  - Thẩm định độ dài ciphertext phải là bội số của 16 byte;
  - Giải mã khối AES-128-CBC;
  - Gỡ đệm `PKCS7(128)` (bắt lỗi nếu sai khóa hoặc sai IV dẫn đến đệm không hợp lệ);
  - Giải mã UTF-8 sang chuỗi ký tự.
- **Ngoại lệ**: `ValueError` khi ciphertext sai kích thước khối, giải mã thất bại hoặc đệm PKCS#7 bị sai.

#### 5.2.5. Các hàm chuyển đổi định dạng
- `bytes_to_hex(data: bytes) -> str` / `hex_to_bytes(hex_str: str) -> bytes`: Chuyển đổi qua lại giữa byte và chuỗi Hex.
- `bytes_to_base64(data: bytes) -> str` / `base64_to_bytes(b64_str: str) -> bytes`: Chuyển đổi qua lại giữa byte và chuỗi Base64 chuẩn.
- `get_aes_info_string(key: bytes, iv: bytes, plaintext_len: int, ciphertext_len: int) -> str`: Tạo chuỗi tổng kết tham số khối phục vụ hiển thị trực quan.

---

### 5.3. Module `playfair.py`

*(Kế thừa đầy đủ và duy trì theo Version 2.0)*
- `normalize_text(text: str) -> str`: Viết hoa, thay J bằng I, lọc chỉ giữ ký tự trong bảng chữ cái 25 ký tự.
- `build_matrix(key: str) -> list[list[str]]`: Xây dựng ma trận Playfair 5×5 từ khóa đã chuẩn hóa.
- `matrix_to_string(matrix: list[list[str]]) -> str`: Chuyển ma trận 5×5 thành chuỗi 5 dòng định dạng đẹp.
- `make_digraphs(text: str) -> list[str]`: Chia văn bản thành các cặp ký tự, chèn ký tự đệm `X` khi trùng hoặc lẻ.
- `encrypt(plaintext: str, key: str) -> str`: Mã hóa Playfair theo 3 quy tắc (cùng hàng, cùng cột, hình chữ nhật).
- `decrypt(ciphertext: str, key: str) -> str`: Giải mã Playfair tương ứng.

---

### 5.4. Module `protocol.py` (Version 2)

#### 5.4.1. `pack_message(algorithm: str, key: str, ciphertext: str, iv: str = "") -> bytes`
- **Mục đích**: Đóng gói thông điệp mã hóa thành gói tin JSON UTF-8 kết thúc bằng `\n`.
- **Đầu vào**:
  - `algorithm`: `"playfair"`, `"caesar"` hoặc `"aes-128-cbc"`;
  - `key`: khóa Playfair, độ dịch Caesar (chuỗi số), hoặc khóa AES;
  - `ciphertext`: chuỗi bản mã;
  - `iv`: chuỗi vector khởi tạo Hex (bắt buộc với `aes-128-cbc`).
- **Đầu ra**: `bytes` – khung tin JSON theo giao thức Version 2.
- **Ngoại lệ**: `ValueError` nếu thuật toán không nằm trong danh mục hỗ trợ.

#### 5.4.2. `unpack_message(raw: bytes) -> dict`
- **Mục đích**: Phân tích khung tin JSON nhận được từ luồng TCP, thẩm định tính toàn vẹn và tương thích ngược.
- **Đầu vào**: `raw` (`bytes`) – khung dữ liệu đã tách delimiter.
- **Đầu ra**: `dict` chứa `type`, `version`, `algorithm`, `key`, `ciphertext`, `iv` (nếu có), `timestamp`.
- **Logic xử lý**:
  - Giải mã UTF-8 và phân tích JSON object;
  - Kiểm tra `type`: nếu là `playfair_message` (gói tin Version 1 cũ), tự động gán `algorithm = "playfair"`; nếu là `crypto_message` (Version 2), kiểm tra `algorithm` thuộc `SUPPORTED_ALGORITHMS`;
  - Kiểm tra các trường bắt buộc `key`, `ciphertext`;
  - Với `aes-128-cbc`, bắt buộc trường `iv` phải tồn tại và khác rỗng.
- **Ngoại lệ**: `ValueError` khi sai định dạng JSON, sai loại gói tin, thiếu trường bắt buộc hoặc thiếu `iv` với AES.

---

### 5.5. Module `network.py` (TCP Socket & QThread)

- **`validate_endpoint(host: str, port: int)` / `validate_listen_endpoint(host: str, port: int)`**: Thẩm định địa chỉ IPv4 hợp lệ và số cổng trong khoảng `1 - 65535`.
- **`SenderThread(QThread)`**: Mở kết nối TCP ngắn hạn tới Receiver (timeout 5s), gửi toàn bộ byte qua `sock.sendall()`, phát tín hiệu Qt `log`, `succeeded`, `failed`.
- **`ReceiverServer(QThread)`**: Khởi tạo socket server với cờ `SO_REUSEADDR`, lắng nghe với backlog 5, chấp nhận kết nối với chu kỳ `accept(timeout=0.5s)` để hỗ trợ dừng mềm an toàn, tích lũy bộ đệm và phân tách khung tin theo ký tự `\n` (giải quyết triệt để hiện tượng phân mảnh luồng TCP).

---

### 5.6. Module `gui.py`

#### Phía Sender (`SenderWindow`):
- `_on_algo_changed(index)`: Điều hướng trang nhập liệu tương ứng trên `QStackedWidget` (Trang Playfair: ô nhập khóa chữ cái; Trang Caesar: spinbox chọn độ dịch kèm nút tắt k=3, k=13; Trang AES: ô nhập khóa, ô nhập IV kèm nút sinh ngẫu nhiên).
- `on_encrypt()`: Điều hướng xử lý mã hóa theo thuật toán đang chọn, cập nhật vùng hiển thị trực quan (ma trận Playfair, bảng dịch Caesar, thông số khối AES) và hiển thị ciphertext.
- `on_send()`: Thu thập tham số, đóng gói qua `pack_message` và khởi chạy `SenderThread`.

#### Phía Receiver (`ReceiverWindow`):
- `_on_packet(raw)`: Tự động trích xuất thông tin gói tin; cập nhật nhãn thuật toán; điều hướng giải mã qua `_decrypt_playfair`, `_decrypt_caesar` hoặc `_decrypt_aes`; hiển thị trực quan hóa và plaintext giải mã. Bắt mọi ngoại lệ giải mã mà không làm gián đoạn luồng server.

---

## 6. Tổng hợp cơ chế xử lý ngoại lệ

| Tình huống | Điểm phát hiện | Hành vi hệ thống |
|---|---|---|
| Khóa Playfair không chứa chữ cái | `SenderWindow._encrypt_playfair` | Cảnh báo giao diện, yêu cầu nhập chữ cái A–Z |
| Plaintext rỗng khi mã hóa | `SenderWindow.on_encrypt` | Cảnh báo giao diện, không mã hóa |
| Độ dịch Caesar không phải số nguyên | `caesar.normalize_shift` | `ValueError`, thông báo lỗi rõ ràng |
| Khóa / IV của AES sai độ dài (khác 16 byte) | `aes_cbc.parse_bytes` | `ValueError`, hiển thị số byte hiện tại và hướng dẫn |
| Sai khóa hoặc sai IV khi giải mã AES | `aes_cbc.decrypt` | Bắt lỗi đệm PKCS#7 không hợp lệ, ghi log và hiển thị `(Không giải mã được: ...)` |
| Ciphertext AES không chia hết cho 16 byte | `aes_cbc.decrypt` | `ValueError`, ghi log và không gây crash server |
| IP rỗng / sai định dạng IPv4 | `validate_endpoint` / `validate_listen_endpoint` | `ValueError`, hộp thoại kèm ví dụ đúng |
| Cổng ngoài khoảng 1–65535 | `validate_endpoint` / `validate_listen_endpoint` | `ValueError`, hộp thoại cảnh báo |
| Cổng TCP đã bị chiếm dụng | `ReceiverServer.run` (bind) | Báo lỗi cổng bị chiếm (EADDRINUSE/10048), đề nghị đổi cổng |
| IP lắng nghe không tồn tại | `ReceiverServer.run` (bind) | Báo lỗi IP không tồn tại (EADDRNOTAVAIL/10049), đề nghị dùng 0.0.0.0 |
| Receiver chưa bật / Firewall chặn | `SenderThread.run` (connect) | `ConnectionRefusedError` hoặc `socket.timeout`, gợi ý khắc phục |
| Gói tin sai cú pháp JSON hoặc thiếu trường | `protocol.unpack_message` | Ghi log chi tiết, bỏ qua gói tin hỏng, server tiếp tục phục vụ |

---

## 7. Luồng dữ liệu tổng thể giữa Sender và Receiver

```
VM1 (Sender)                                             VM2 (Receiver)
───────────────────────────────────                      ───────────────────────────────────
[1] Chọn thuật toán (Playfair/Caesar/AES)
[2] Nhập Key (và IV nếu AES), nhập Plaintext
[3] Bấm "Mã hóa"
    → Playfair: sinh ma trận 5×5, chia cặp, encrypt
    → Caesar: dịch modulo 26, sinh bảng ánh xạ
    → AES-128-CBC: đệm PKCS#7, mã hóa khối CBC
[4] Bấm "Gửi ciphertext"
    → pack_message(algo, key, cipher, iv)
    → tạo JSON UTF-8 + '\n'
[5] SenderThread mở TCP socket ──────── TCP ─────────►  [6] ReceiverServer chấp nhận kết nối,
    gửi sendall, đóng kết nối                                đọc bộ đệm, tách khung theo '\n'
                                                         [7] unpack_message phân tích JSON,
                                                             nhận biết thuật toán, key, iv
                                                         [8] Tự động gọi hàm giải mã tương ứng:
                                                             → Playfair: build_matrix + decrypt
                                                             → Caesar: decrypt (-k mod 26)
                                                             → AES: decrypt + unpad PKCS#7
                                                         [9] Cập nhật giao diện: thuật toán,
                                                             khóa, IV, trực quan hóa, plaintext
```

---

## 8. Cấu hình mạng khi triển khai hai máy ảo

1. Gán hai máy ảo trong cùng một mạng nội bộ (Internal Network hoặc Host-Only), đặt IP tĩnh cùng dải:
   - VM1 (Sender): `192.168.1.1`
   - VM2 (Receiver): `192.168.1.2`
2. Kiểm tra ping từ VM1 sang VM2: `ping 192.168.1.2`.
3. Kiểm tra thông cổng TCP 5000: `Test-NetConnection 192.168.1.2 -Port 5000`.
4. Nếu kết nối bị chặn, mở port inbound trên tường lửa của VM2:
   ```powershell
   New-NetFirewallRule -DisplayName "Crypto Receiver" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
   ```

---

## 9. Kiểm thử tự động (Test Automation)

Hệ thống được trang bị bộ kiểm thử tự động toàn diện gồm 27 test cases bao phủ:
1. **Unit Tests (`tests/test_ciphers.py`)**:
   - Thuật toán Playfair: chuẩn hóa văn bản, ma trận 5x5, chia cặp digraph, round-trip mã hóa/giải mã, xử lý ngoại lệ.
   - Thuật toán Caesar: kiểm thử độ dịch cơ bản $k=3$, ROT13 $k=13$, độ dịch âm, độ dịch lớn hơn 26, giữ nguyên dấu câu/số, bảng ánh xạ trực quan.
   - Thuật toán AES-128-CBC: sinh khóa/IV an toàn, phân tích hex/text, mã hóa/giải mã chuỗi văn bản ASCII và Unicode tiếng Việt, chuyển đổi Base64/Hex, phát hiện và bắt lỗi khi sai khóa hoặc sai IV.
   - Giao thức `protocol.py`: đóng gói và giải gói tin cho cả 3 thuật toán, kiểm tra tính tương thích ngược với gói tin Version 1 cũ, bắt lỗi thiếu trường hoặc sai định dạng.
2. **Integration Tests (`tests/test_integration.py`)**:
   - Khởi động socket server thực tế trên localhost.
   - Kết nối client và truyền nhận thông điệp qua mạng TCP cho từng thuật toán, xác thực kết quả giải mã ở máy nhận trùng khớp hoàn toàn với văn bản gốc.
3. **GUI Sanity Tests (`tests/test_gui.py`)**:
   - Khởi tạo giao diện PySide6 ở chế độ offscreen.
   - Kiểm thử chuyển đổi thuật toán và mã hóa trên `SenderWindow`.
   - Kiểm thử tiếp nhận và giải mã hiển thị trên `ReceiverWindow`.

Lệnh chạy kiểm thử:
```powershell
python -m unittest discover -s tests -p "test_*.py"
```
Kết quả nghiệm thu: **27/27 tests PASS**.

---

## 10. Hệ thống đo đạc hiệu năng mạng (Benchmark Suite)

Hệ thống cung cấp một hệ thống đo đạc thực nghiệm độc lập trong thư mục `benchmark/` nhằm so sánh hiệu năng của 4 giải pháp mã hóa (`None`, `Caesar`, `Playfair`, `AES-128-CBC`) trên 3 kích thước tải (`1 KB`, `100 KB`, `1 MB`):
- **Giao thức đo đạc:** TCP Binary Framing với 372 lượt chạy (12 tổ hợp × 31 lượt: 1 warm-up + 30 đo chính), 360 mẫu phân tích.
- **Các chỉ số thu thập:** Thời gian mã hóa/giải mã, độ trễ RTT, tổng thời gian, thông lượng (throughput), mức chiếm dụng CPU (%) và bộ nhớ RAM (RSS & Delta).
- **Tài liệu tham khảo chi tiết:**
  - [Báo cáo Thực nghiệm Benchmark & 8 Biểu đồ (docs/bao-cao-benchmark.md)](bao-cao-benchmark.md)
  - [Bảng tổng hợp số liệu Benchmark (benchmark/results/summary_table.md)](../benchmark/results/summary_table.md)
  - [Tập tin kết quả CSV (benchmark/results/benchmark_results.csv)](../benchmark/results/benchmark_results.csv)

