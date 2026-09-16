# Hệ thống Mã hóa & Benchmark Truyền tin Đa Thuật toán

Ứng dụng mô phỏng toàn diện quy trình **Mã hóa → Truyền tin TCP → Giải mã** và hệ thống **Benchmark hiệu năng mạng** giữa hai máy ảo (Windows / Linux) với 3 thuật toán: **Playfair (5×5)**, **Caesar**, và **AES-128-CBC** (đệm PKCS#7 & vector IV ngẫu nhiên).

---

## ⚡ Khởi động nhanh (Quick Start)

### 1. Cài đặt môi trường (Bắt buộc trên máy ảo mới clone)
```powershell
python -m pip install -r requirements.txt
```

### 2. Chạy ứng dụng Demo Truyền nhận
| Máy | Vai trò | Lệnh khởi động | Mô tả |
|---|---|---|---|
| **VM2** | **Receiver (CLI)** | `python receiver/main.py` | Lắng nghe port `5000` (CLI/Headless), hỗ trợ **cURL (HTTP)** & **TCP raw socket**, tự động giải mã & hiển thị log |
| **VM1** | **Sender (GUI)** | `python sender/main.py` | Giao diện PySide6 chọn thuật toán, cấu hình khóa/IV, nhập IP VM2 & gửi tin |

#### 🌐 Sử dụng cURL để tương tác với Receiver (Port 5000):
```bash
# 1. Kiểm tra trạng thái Receiver Server:
curl http://localhost:5000/

# 2. Gửi và giải mã Caesar (k=3):
curl -X POST http://localhost:5000/ -H "Content-Type: application/json" -d "{\"algorithm\":\"caesar\",\"key\":\"3\",\"ciphertext\":\"DEF\"}"

# 3. Gửi và giải mã Playfair (key=MONARCHY):
curl -X POST http://localhost:5000/ -H "Content-Type: application/json" -d "{\"algorithm\":\"playfair\",\"key\":\"MONARCHY\",\"ciphertext\":\"GATLMZCLRQTX\"}"

# 4. Gửi và giải mã AES-128-CBC:
curl -X POST http://localhost:5000/ -H "Content-Type: application/json" -d "{\"algorithm\":\"aes-128-cbc\",\"key\":\"000102030405060708090a0b0c0d0e0f\",\"iv\":\"0f0e0d0c0b0a09080706050403020100\",\"ciphertext\":\"a5T36KlQeIyvHfjdFmDQ8kxnusXn5kX4lXx7o64WdCc=\"}"
```

### 3. Chạy Benchmark Hiệu năng (372 lượt đo)
Hệ thống tự động đo: *Thời gian mã hóa/giải mã, RTT, Throughput, CPU (%) và RAM (RSS/Delta)* trên 4 thuật toán (`None`, `Caesar`, `Playfair`, `AES-128-CBC`) × 3 kích thước payload (`1 KB`, `100 KB`, `1 MB`).

* **Cách 1 - Giao diện đồ họa (Khuyến nghị):**
  ```powershell
  python benchmark_gui.py
  # hoặc: python benchmark/run_benchmark.py --gui
  ```
  *Hỗ trợ 3 chế độ vận hành linh hoạt ngay trên giao diện:*
  - **Local All-in-One**: Tự động chạy Server ngầm + Client đo đạc trên máy cục bộ (`127.0.0.1`).
  - **Sender Server**: Máy gửi đo đạc kết nối tới VM2 từ xa qua IP:Port.
  - **Receiver Server**: Máy chủ lắng nghe kết nối đo đạc từ máy Sender trên cổng TCP (`0.0.0.0:5000`).

* **Cách 2 - Dòng lệnh CLI (Tự động nhận diện chế độ theo `--host`):**
  ```powershell
  # Chế độ Self-Test (Mặc định máy cục bộ: tự bật Receiver ngầm, đo & vẽ 8 biểu đồ)
  python benchmark/run_benchmark.py

  # Chế độ Remote (Đổi IP sang máy ảo khác: tự ping kiểm tra kết nối & gửi trực tiếp)
  python benchmark/run_benchmark.py --host 192.168.1.50 [--port 5000]
  ```

---

## 📁 Cấu trúc dự án

```text
hephantan/
├── sender/             # VM1: Giao diện PySide6, TCP Client & mã hóa (Playfair, Caesar, AES)
├── receiver/           # VM2: Receiver Server CLI (Port 5000), hỗ trợ cURL & TCP, giải mã tự động
├── benchmark/          # Hệ thống đo đạc hiệu năng mạng
│   ├── gui.py          # Benchmark GUI (PySide6)
│   ├── run_benchmark.py# Điều phối benchmark tự động (CLI / GUI)
│   ├── client.py & server.py # Core TCP benchmark framing
│   ├── analyze.py      # Thống kê pandas & vẽ biểu đồ matplotlib
│   └── results/        # Dữ liệu 360 mẫu CSV, bảng tổng hợp & 8 biểu đồ 300 DPI
├── tests/              # Bộ 52 test cases tự động (Ciphers, Network TCP, GUI, Receiver CLI, Pipeline)
├── docs/               # Báo cáo triển khai ISO 26514 & báo cáo phân tích thực nghiệm
├── benchmark_gui.py    # Launcher nhanh cho Benchmark GUI
└── requirements.txt    # Thư viện phụ thuộc (PySide6, cryptography, psutil, pandas, matplotlib)
```

---

## 🧪 Kiểm thử tự động (Unit & Integration Tests)

Dự án bao gồm **52 test cases** kiểm tra toàn diện logic mật mã, giao thức mạng, giao diện và cURL REST API:
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📡 Giao thức truyền tin (JSON Version 2)

Dữ liệu truyền qua TCP Socket dưới dạng chuỗi JSON kết thúc bằng `\n` (`utf-8`):

| Thuật toán | Gói tin mẫu (JSON) |
|---|---|
| **Playfair** | `{"type":"crypto_message","version":2,"algorithm":"playfair","key":"MONARCHY","ciphertext":"...","timestamp":"..."}` |
| **Caesar** | `{"type":"crypto_message","version":2,"algorithm":"caesar","key":"3","ciphertext":"...","timestamp":"..."}` |
| **AES-128-CBC** | `{"type":"crypto_message","version":2,"algorithm":"aes-128-cbc","key":"<hex32>","iv":"<hex32>","ciphertext":"<base64>","timestamp":"..."}` |

*(Hệ thống tự động tương thích ngược với gói tin Version 1).*

---

## ⚙️ Cấu hình mạng giữa 2 máy ảo

1. Thiết lập 2 VM cùng mạng **Host-only** hoặc **Internal Network** (ví dụ: VM1: `192.168.1.1`, VM2: `192.168.1.2`).
2. Kiểm tra thông mạng: `ping 192.168.1.2`.
3. Mở port `5000` trên Windows Firewall của VM2 (nếu bị chặn):
   ```powershell
   New-NetFirewallRule -DisplayName "Crypto Receiver" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
   ```

---

## 📚 Tài liệu kỹ thuật chi tiết

- 📑 [**Báo cáo Triển khai Hệ thống (ISO/IEC/IEEE 26514:2022)**](docs/bao-cao-trien-khai.md)
- 📊 [**Báo cáo Thực nghiệm Benchmark & Phân tích 8 Biểu đồ**](docs/bao-cao-benchmark.md)
- 📈 [**Bảng Thống kê Số liệu Thực nghiệm**](benchmark/results/summary_table.md)
- 🖼️ [**Thư mục 8 Biểu đồ phân giải cao (300 DPI)**](benchmark/results/charts/)
