# Hệ thống Mã hóa & Benchmark Truyền tin Đa Thuật toán

Hệ thống phân tán mô phỏng toàn diện quy trình **Mã hóa → Truyền tin Socket TCP → Giải mã** và hệ thống **Đo đạc hiệu năng Benchmark** giữa hai máy (Windows / Linux) với 3 thuật toán: **Caesar**, **Playfair (5×5)**, và **AES-128-CBC** (đệm PKCS#7 & vector IV ngẫu nhiên).

---

## ⚡ 1. Cài đặt môi trường
Chạy lệnh sau trên terminal của cả hai máy:
```bash
python -m pip install -r requirements.txt
```

---

## 🚀 2. Hướng dẫn chạy bằng dòng lệnh (CMD / Terminal)

Hệ thống hỗ trợ 2 kịch bản chính: **Truyền tin ứng dụng** và **Benchmark hiệu năng**.

### 💬 KỊCH BẢN A: ỨNG DỤNG TRUYỀN TIN MÃ HÓA (App Demo)

#### **Bước 1: Phía Máy Nhận (Receiver - giả sử IP: `192.168.0.4`)**
Mở CMD/Terminal và khởi động server nhận tin:
```bash
python receiver/main.py --host 0.0.0.0 --port 5000
```
*(Server lắng nghe trên cổng 5000, hỗ trợ HTTP REST API và TCP Socket, tự động giải mã và in log ra màn hình).*

#### **Bước 2: Phía Máy Gửi (Sender)**
Bạn có thể chọn 1 trong 2 cách sau:

* **Cách 1: Gửi tin trực tiếp từ CMD bằng lệnh `curl` (Không cần GUI):**
  * **Caesar:**
    ```bash
    curl -X POST http://192.168.0.4:5000/ -H "Content-Type: application/json" -d "{\"algorithm\":\"caesar\",\"key\":\"3\",\"ciphertext\":\"DEF\"}"
    ```
  * **Playfair:**
    ```bash
    curl -X POST http://192.168.0.4:5000/ -H "Content-Type: application/json" -d "{\"algorithm\":\"playfair\",\"key\":\"MONARCHY\",\"ciphertext\":\"GATLMZCLRQTX\"}"
    ```
  * **AES-128-CBC:**
    ```bash
    curl -X POST http://192.168.0.4:5000/ -H "Content-Type: application/json" -d "{\"algorithm\":\"aes-128-cbc\",\"key\":\"000102030405060708090a0b0c0d0e0f\",\"iv\":\"0f0e0d0c0b0a09080706050403020100\",\"ciphertext\":\"a5T36KlQeIyvHfjdFmDQ8kxnusXn5kX4lXx7o64WdCc=\"}"
    ```

* **Cách 2: Mở giao diện đồ họa PySide6 trên Máy Gửi (nếu có màn hình Desktop):**
  ```bash
  python sender/main.py
  ```

---

### 📊 KỊCH BẢN B: ĐO ĐẠC HIỆU NĂNG BENCHMARK (372 lượt đo / 9 Biểu đồ)

Đo đạc khoa học 5 tiêu chí: *Thời gian Enc/Dec, RTT mạng, Throughput, CPU (%) và RAM (RSS/Delta)* trên 4 thuật toán (`None`, `Caesar`, `Playfair`, `AES-128-CBC`) $\times$ 3 kích thước (`1 KB`, `100 KB`, `1 MB`).

#### **Trường hợp 1: Tự host trên 1 máy duy nhất (Self-Test Local - Khuyên dùng khi test)**
Chỉ cần chạy **1 lệnh duy nhất**, hệ thống tự bật server ngầm, đo đạc, xuất CSV và sinh đủ 9 biểu đồ:
```bash
python benchmark/run_benchmark.py
```

#### **Trường hợp 2: Chạy phân tán trên 2 máy (Sender $\leftrightarrow$ Receiver qua mạng LAN/VM)**
* **Phía Máy Nhận (Receiver - IP: `192.168.0.4`):**
  ```bash
  python benchmark/server.py --host 0.0.0.0 --port 5000
  ```
  *(Màn hình hiện: `RECEIVER BENCHMARK SERVER DANG CHAY TAI 0.0.0.0:5000`)*.

* **Phía Máy Gửi (Sender):**
  ```bash
  python benchmark/run_benchmark.py --host 192.168.0.4 --port 5000 --no-ping
  ```
  *(Thêm `--no-ping` để bỏ qua bước ping và vào đo đạc ngay lập tức)*.

#### **Trường hợp 3: Chạy bằng Giao diện đồ họa Benchmark Dashboard**
```bash
python benchmark_gui.py
# hoặc trên Windows: click đúp file run_gui.bat
```

---

## 📁 3. Kết quả đầu ra (Sau khi chạy Benchmark)

Sau khi benchmark hoàn tất, toàn bộ kết quả nằm trong thư mục `benchmark/results/`:
* **Dữ liệu thô 360 mẫu hợp lệ:** `benchmark/results/benchmark_results.csv`
* **Bảng báo cáo Markdown:** `benchmark/results/summary_table.md`
* **Bộ 9 Biểu đồ khoa học (300 DPI) tại `benchmark/results/charts/`:**
  1. `01_encryption_time.png`: Thời gian mã hóa trung bình (ms)
  2. `02_decryption_time.png`: Thời gian giải mã trung bình (ms)
  3. `03_rtt.png`: Độ trễ mạng khứ hồi RTT (ms)
  4. `04_total_time.png`: Tổng thời gian thực thi hoàn tất (ms)
  5. `05_sizes.png`: Kích thước gói tin truyền tải & độ phình (+32B của AES)
  6. `06_throughput.png`: Băng thông truyền tải hệ thống (KB/s & MB/s)
  7. `07_cpu_usage.png`: Mức độ chiếm dụng CPU % (Sender vs Receiver)
  8. `08_ram_usage.png`: Mức tiêu thụ bộ nhớ RAM (RSS MB & Delta KB)
  9. `09_security_comparison.png`: Đánh giá so sánh 4 chỉ số An toàn Mật mã học (Key Space, IC, Entropy, Unicity Distance)

---

## 🧪 4. Chạy kiểm thử tự động (Unit Tests)

Dự án gồm **52 test cases** tự động kiểm tra tính đúng đắn của mật mã, mạng TCP, GUI và pipeline:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📚 5. Tài liệu chi tiết

* 📑 [**Báo cáo Triển khai Hệ thống (ISO/IEC/IEEE 26514:2022)**](docs/bao-cao-trien-khai.md)
* 📊 [**Báo cáo Thực nghiệm Benchmark & Phân tích Biểu đồ**](docs/bao-cao-benchmark.md)
* 📈 [**Bảng Thống kê Số liệu Thực nghiệm**](benchmark/results/summary_table.md)

