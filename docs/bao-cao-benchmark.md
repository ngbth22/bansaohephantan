# Báo cáo Benchmark Mã hóa và Truyền tin Mạng

**Hệ thống phân tán truyền tin mật mã giữa hai máy ảo Windows**  
**Chuẩn thực nghiệm: 4 Thuật toán × 3 Kích thước = 12 Tổ hợp**  
**Tổng số lượt thực thi:** 372 lượt (12 tổ hợp × 31 lượt: 1 warm-up + 30 lần đo chính)  
**Số mẫu dữ liệu phân tích:** 360 mẫu (12 tổ hợp × 30 mẫu chính thức)  
**Ngày thực hiện:** 12/09/2026  

---

## 1. Mục tiêu và Kịch bản thực nghiệm

### 1.1. Mục tiêu
Đánh giá định lượng hiệu năng tính toán mật mã và ảnh hưởng của nó đến độ trễ truyền mạng, kích thước gói tin và băng thông thực tế (throughput) giữa hai máy ảo Windows trong hệ phân tán, so sánh 4 giải pháp:
1. **None**: Baseline truyền tin thuần qua TCP không mã hóa.
2. **Caesar**: Mã hóa dịch chuyển ký tự cổ điển ($k=3$).
3. **Playfair**: Mã hóa ma trận đa ký tự cổ điển (khóa `MONARCHY`).
4. **AES-128-CBC**: Chuẩn mã hóa khối hiện đại đối xứng 128-bit với đệm PKCS#7 và vector khởi tạo IV 16 byte ngẫu nhiên.

### 1.2. Kịch bản thực nghiệm
- **12 tổ hợp**: 4 thuật toán × 3 kích thước dữ liệu (`1 KB = 1,024 B`, `100 KB = 102,400 B`, `1 MB = 1,048,576 B`).
- **Thứ tự chạy**: Dùng `random.shuffle()` xáo trộn ngẫu nhiên thứ tự 12 tổ hợp **đúng một lần duy nhất**, sau đó mỗi tổ hợp chạy hết 31 lượt liên tiếp.
- **Warm-up**: Mỗi tổ hợp thực hiện **1 lượt warm-up đầu tiên** nhằm kích hoạt buffer mạng, nạp JIT/cache bộ nhớ và ổn định socket, lượt này **được loại khỏi tập mẫu phân tích**.
- **Số lượt đo chính**: Mỗi tổ hợp đo **30 lần liên tiếp**.
- **Tổng số lượt thực thi**: $12 \times 31 = 372$ lượt.
- **Tập mẫu phân tích thống kê**: $12 \times 30 = 360$ mẫu hợp lệ.

---

## 2. Dữ liệu đầu vào và Cơ chế thẩm định (Verification)

### 2.1. Dữ liệu đầu vào tất định
- Plaintext chỉ gồm các ký tự in hoa `A–Z`.
- Dữ liệu được sinh hoàn toàn tất định bằng cách lặp lại mẫu 25 ký tự không chứa `J` (`config.ALPHABET`: `"ABCDEFGHIKLMNOPQRSTUVWXYZ"`).
- Việc loại trừ `J` và không có hai ký tự giống nhau liền kề đảm bảo văn bản giải mã của cả 4 thuật toán (bao gồm cả Playfair) trùng khớp 100% từng byte với bản gốc mà không bị lệch ký tự hay phát sinh ký tự đệm `X` ngoài dự kiến.
- Cùng một plaintext và kích thước được áp dụng đồng nhất cho cả 4 thuật toán.

### 2.2. Luồng đo lường và Công thức tính toán
Quy trình trao đổi gói tin giữa Sender và Receiver tuân thủ công thức chuẩn xác, không có số hạng phái sinh hay tính trùng lặp:

```
Sender: sinh plaintext → encrypt (đo encryption_ms) → gửi packet qua TCP → chờ ACK
Receiver: nhận packet → decrypt (đo decrypt_ms) → verify (đo verify_ms) → gửi ACK
Sender: nhận ACK → rtt_ms = t(nhận ACK) − t(gửi packet)
```

- **Tổng thời gian hoàn tất (`total_ms`)**:
  $$\text{total\_ms} = \text{encryption\_ms} + \text{rtt\_ms}$$
  *(Lưu ý: `rtt_ms` theo định nghĩa tự nhiên đã bao gồm thời gian truyền qua mạng hai chiều, thời gian giải mã `decrypt_ms` và thời gian kiểm tra `verify_ms` tại Receiver. Do đó, không cộng thêm `decrypt_ms` vào `total_ms` để tránh hiện tượng đếm trùng hai lần).*
- **Các thành phần được ghi nhận độc lập**: `decrypt_ms` và `verify_ms` được đo đạc tại Receiver và trả về qua gói tin ACK nhỏ (17 byte) phục vụ phân tích chi tiết và vẽ biểu đồ so sánh.
- **Băng thông hệ thống (`throughput_kbps`)**:
  $$\text{throughput\_kbps} = \frac{\text{size\_bytes} / 1024}{\text{total\_ms} / 1000}$$

### 2.3. Cơ chế thẩm định byte-by-byte
Phía Receiver tự tái sinh lại plaintext kỳ vọng tương ứng với `size_bytes` (nhờ tính tất định), sau đó so sánh chính xác từng byte với văn bản sau khi giải mã:
- Nếu trùng khớp hoàn toàn: `success = True`.
- Nếu có bất kỳ byte nào sai lệch: `success = False`.

---

## 3. Kích thước dữ liệu thực tế trên đường truyền

Toàn bộ kích thước `ciphertext_size_bytes` và `packet_size_bytes` được đo trực tiếp bằng hàm `len()` trên dữ liệu nhị phân thực tế được tạo ra:

| Thuật toán | Plaintext | Ciphertext thực tế | Packet trên mạng | Độ phình dữ liệu (Overhead) |
|---|---:|---:|---:|---:|
| **None** | 1,024 B | 1,024 B | 1,024 B | 0 B (0.00%) |
| **None** | 102,400 B | 102,400 B | 102,400 B | 0 B (0.00%) |
| **None** | 1,048,576 B | 1,048,576 B | 1,048,576 B | 0 B (0.00%) |
| **Caesar** | 1,024 B | 1,024 B | 1,024 B | 0 B (0.00%) |
| **Caesar** | 102,400 B | 102,400 B | 102,400 B | 0 B (0.00%) |
| **Caesar** | 1,048,576 B | 1,048,576 B | 1,048,576 B | 0 B (0.00%) |
| **Playfair** | 1,024 B | 1,024 B | 1,024 B | 0 B (0.00%) |
| **Playfair** | 102,400 B | 102,400 B | 102,400 B | 0 B (0.00%) |
| **Playfair** | 1,048,576 B | 1,048,576 B | 1,048,576 B | 0 B (0.00%) |
| **AES-128-CBC** | 1,024 B | 1,040 B | 1,056 B | +32 B (+3.12%) |
| **AES-128-CBC** | 102,400 B | 102,416 B | 102,432 B | +32 B (+0.03%) |
| **AES-128-CBC** | 1,048,576 B | 1,048,592 B | 1,048,608 B | +32 B (+0.003%) |

> **Nhận xét:**
> - Với **AES-128-CBC**: Do kích thước Plaintext là bội số của 16, thuật toán đệm PKCS#7 luôn bổ sung đúng một khối đệm 16 byte (giá trị mỗi byte là `0x10`). Thêm vào đó, vector khởi tạo ngẫu nhiên (IV) 16 byte được đính kèm ở đầu gói tin. Do đó, kích thước gói tin AES-128-CBC luôn đúng bằng $\text{Plaintext} + 32\text{ bytes}$, đúng tuyệt đối với bảng lý thuyết. Khi kích thước dữ liệu tăng lên 1 MB, độ phình chỉ còn 0.003%, gần như không đáng kể.

---

## 4. Kết quả thống kê chi tiết

### 4.1. Tỉ lệ thành công (Success Rate)

Tất cả 12 tổ hợp thực nghiệm đạt tỉ lệ thành công tuyệt đối **100.0%** (30/30 mẫu kiểm tra trùng khớp byte-by-byte). Không ghi nhận bất kỳ sự cố mất gói, sai lệch đệm hay lỗi kết nối socket nào trong suốt 372 lượt chạy.

| STT | Thuật toán | Kích thước | Tổng số lượt đo | Số lượt thành công | Tỉ lệ thành công |
|:---:|---|:---:|:---:|:---:|:---:|
| 1 | **None** | 1 KB | 30 | 30 | **100.0%** |
| 2 | **None** | 100 KB | 30 | 30 | **100.0%** |
| 3 | **None** | 1 MB | 30 | 30 | **100.0%** |
| 4 | **Caesar** | 1 KB | 30 | 30 | **100.0%** |
| 5 | **Caesar** | 100 KB | 30 | 30 | **100.0%** |
| 6 | **Caesar** | 1 MB | 30 | 30 | **100.0%** |
| 7 | **Playfair** | 1 KB | 30 | 30 | **100.0%** |
| 8 | **Playfair** | 100 KB | 30 | 30 | **100.0%** |
| 9 | **Playfair** | 1 MB | 30 | 30 | **100.0%** |
| 10 | **AES-128-CBC** | 1 KB | 30 | 30 | **100.0%** |
| 11 | **AES-128-CBC** | 100 KB | 30 | 30 | **100.0%** |
| 12 | **AES-128-CBC** | 1 MB | 30 | 30 | **100.0%** |

---

### 4.2. Bảng tổng hợp các chỉ số thời gian và băng thông (Mean & Median)

Dữ liệu được xử lý bằng `pandas.describe()` và `.median()` trên toàn bộ 360 mẫu thành công:

| Thuật toán | Kích thước | Encrypt Mean (ms) | Decrypt Mean (ms) | Verify Mean (ms) | RTT Mean (ms) | Total Mean (ms) | Total Median (ms) | Throughput Mean (KB/s) |
|---|:---:|---:|---:|---:|---:|---:|---:|---:|
| **None** | **1 KB** | 0.00 | 0.00 | 0.001 | 0.08 | **0.08** | 0.07 | 12,749.3 |
| **None** | **100 KB** | 0.00 | 0.01 | 0.007 | 0.14 | **0.14** | 0.13 | 739,441.6 |
| **None** | **1 MB** | 0.16 | 0.18 | 0.40 | 1.45 | **1.61** | 1.57 | 637,905.8 |
| **Caesar** | **1 KB** | 0.01 | 0.01 | 0.001 | 0.08 | **0.09** | 0.08 | 11,856.1 |
| **Caesar** | **100 KB** | 0.07 | 0.07 | 0.007 | 0.22 | **0.29** | 0.30 | 349,013.7 |
| **Caesar** | **1 MB** | 0.72 | 0.75 | 0.40 | 2.55 | **3.27** | 2.65 | 370,911.5 |
| **Playfair** | **1 KB** | 1.15 | 1.18 | 0.001 | 1.28 | **2.43** | 2.34 | 414.2 |
| **Playfair** | **100 KB** | 102.75 | 102.26 | 0.011 | 104.06 | **206.81** | 203.80 | 484.5 |
| **Playfair** | **1 MB** | 1,145.20 | 1,120.57 | 0.41 | 1,124.98 | **2,270.18** | 2,294.41 | 452.0 |
| **AES-128-CBC** | **1 KB** | 0.02 | 0.02 | 0.001 | 0.11 | **0.13** | 0.12 | 7,925.2 |
| **AES-128-CBC** | **100 KB** | 0.10 | 0.05 | 0.007 | 0.21 | **0.30** | 0.30 | 336,974.6 |
| **AES-128-CBC** | **1 MB** | 1.39 | 1.09 | 0.40 | 2.45 | **3.84** | 3.79 | 267,264.8 |

---

### 4.3. Bảng tổng hợp mức sử dụng CPU (%) và Bộ nhớ RAM (RSS & Delta)

Được ghi nhận chính xác không làm sai lệch đồng hồ đo thông qua `psutil.Process().memory_info().rss` và `time.process_time()`:

| Thuật toán | Kích thước | Sender CPU (%) | Receiver CPU (%) | Sender RAM RSS (MB) | Receiver RAM RSS (MB) | Sender Delta (KB) | Receiver Delta (KB) |
|---|:---:|---:|---:|---:|---:|---:|---:|
| **None** | **1 KB** | 0.0% | 0.0% | 104.2 MB | 104.2 MB | 0.0 KB | 0.0 KB |
| **None** | **100 KB** | 0.0% | 0.0% | 104.2 MB | 104.2 MB | 0.0 KB | 0.0 KB |
| **None** | **1 MB** | 0.0% | 0.0% | 108.0 MB | 108.8 MB | 0.0 KB | 0.0 KB |
| **Caesar** | **1 KB** | 0.0% | 0.0% | 104.6 MB | 104.6 MB | 0.0 KB | 0.0 KB |
| **Caesar** | **100 KB** | 0.0% | 0.0% | 104.2 MB | 104.2 MB | 0.0 KB | 0.0 KB |
| **Caesar** | **1 MB** | 0.0% | 0.0% | 108.0 MB | 108.9 MB | 0.0 KB | 0.0 KB |
| **Playfair** | **1 KB** | 0.0% | 0.0% | 103.6 MB | 103.6 MB | 0.0 KB | 0.0 KB |
| **Playfair** | **100 KB** | **95.7%** | **96.0%** | 102.2 MB | 102.1 MB | 157.7 KB | 103.7 KB |
| **Playfair** | **1 MB** | **98.6%** | **98.0%** | 108.9 MB | 108.9 MB | 2.8 KB | 83.9 KB |
| **AES-128-CBC** | **1 KB** | 0.0% | 0.0% | 104.6 MB | 104.6 MB | 0.0 KB | 0.0 KB |
| **AES-128-CBC** | **100 KB** | 0.0% | 0.0% | 103.4 MB | 103.4 MB | 0.0 KB | 0.0 KB |
| **AES-128-CBC** | **1 MB** | **6.7%** | **6.7%** | 110.5 MB | 110.8 MB | 0.0 KB | 0.0 KB |

---

## 5. Phân tích chi tiết qua 8 Biểu đồ trực quan

Toàn bộ 8 biểu đồ so sánh đã được kết xuất tại thư mục `benchmark/results/charts/` với độ phân giải cao (300 DPI), trục X biểu diễn 4 Thuật toán và các nhóm cột biểu diễn 3 Kích thước dữ liệu (1 KB, 100 KB, 1 MB):

### 5.1. Biểu đồ 1: Thời gian mã hóa (Encryption Time)
- **None**: Gần như bằng 0 (0.00 – 0.16 ms cho 1 MB, chỉ gồm chi phí trích xuất byte UTF-8).
- **Caesar**: Nhờ triển khai tối ưu bảng chuyển đổi ký tự `str.maketrans`, thời gian mã hóa 1 MB chỉ mất **0.72 ms**.
- **AES-128-CBC**: Tận dụng thư viện `cryptography` với tập chỉ lệnh phần cứng Intel/AMD AES-NI, việc đệm PKCS#7 và mã hóa khối CBC trên 1 MB dữ liệu chỉ mất **1.39 ms** (rất gần với Caesar dù có độ phức tạp toán học và tính bảo mật tuyệt đối).
- **Playfair**: Thời gian mã hóa tăng tuyến tính theo kích thước dữ liệu nhưng với hệ số góc rất lớn: **1.15 ms** (1 KB) → **102.75 ms** (100 KB) → **1,145.20 ms** (1 MB). Playfair chậm hơn AES-128-CBC tới **824 lần** ở kích thước 1 MB.

### 5.2. Biểu đồ 2: Thời gian giải mã (Decryption Time)
- Thời gian giải mã tại Receiver thể hiện tính đối xứng chặt chẽ với thời gian mã hóa tại Sender:
  - Caesar: **0.75 ms** cho 1 MB.
  - AES-128-CBC: **1.09 ms** cho 1 MB (giải mã khối và gỡ đệm PKCS#7).
  - Playfair: **1,120.57 ms** cho 1 MB.
- Thời gian kiểm định tính đúng đắn (`verify_ms`) độc lập với thuật toán mã hóa (chỉ phụ thuộc vào thao tác tái sinh và so sánh byte) và chiếm tỉ trọng rất nhỏ (~0.40 ms cho 1 MB).

### 5.3. Biểu đồ 3: Thời gian trễ mạng RTT (Round Trip Time)
- Với **None**, **Caesar** và **AES-128-CBC**: RTT dao động từ **0.08 ms** (1 KB) đến **1.45 – 2.55 ms** (1 MB).
- Với **Playfair**: RTT đo được tại Sender lên tới **1,124.98 ms** ở kích thước 1 MB. Điều này hoàn toàn chính xác theo mô hình mạng: Sender tính RTT từ thời điểm gửi packet đến khi nhận được ACK. Do Receiver phải hoàn tất giải mã Playfair (mất ~1,120 ms) rồi mới gửi ACK, `rtt_ms` đã tự nhiên bao trọn thời gian xử lý của Receiver.

### 5.4. Biểu đồ 4: Tổng thời gian thực thi (Total Time = Encrypt + RTT)
- Ở kích thước **1 KB**:
  - None: 0.08 ms
  - Caesar: 0.09 ms
  - AES-128-CBC: 0.13 ms
  - Playfair: 2.43 ms
- Ở kích thước **100 KB**:
  - None: 0.14 ms
  - Caesar: 0.29 ms
  - AES-128-CBC: 0.30 ms
  - Playfair: 206.81 ms
- Ở kích thước **1 MB**:
  - None: 1.61 ms
  - Caesar: 3.27 ms
  - AES-128-CBC: 3.84 ms
  - Playfair: 2,270.18 ms (~2.27 giây)
- Độ lệch chuẩn (`std`) của Total Time ở 1 MB của AES-128-CBC là **0.18 ms** và Playfair là **24.51 ms**, cho thấy kết quả đo lường có tính lặp lại và ổn định cao.

### 5.5. Biểu đồ 5: Kích thước gói tin truyền tải (Packet Size)
- None, Caesar và Playfair giữ nguyên kích thước 100% so với Plaintext gốc (`1,024 B`, `102,400 B`, `1,048,576 B`).
- AES-128-CBC có kích thước lớn hơn chính xác 32 byte (`1,056 B`, `102,432 B`, `1,048,608 B`) do đệm PKCS#7 (+16 byte) và vector khởi tạo IV (+16 byte).

### 5.6. Biểu đồ 6: Băng thông hệ thống (Throughput)
- **None**: Đạt đỉnh **739,442 KB/s** ở 100 KB do không phải chịu chi phí tính toán mật mã.
- **Caesar**: Đạt **349,014 KB/s** ở 100 KB và **370,912 KB/s** ở 1 MB.
- **AES-128-CBC**: Đạt **336,975 KB/s** ở 100 KB và **267,265 KB/s** ở 1 MB (tương đương ~261 MB/s xử lý và truyền tải dữ liệu mã hóa an toàn).
- **Playfair**: Giữ mức băng thông rất thấp: **414.2 – 484.5 KB/s** (bị giới hạn hoàn toàn bởi chi phí CPU chia cặp và tra cứu ma trận Playfair trên Python).

### 5.7. Biểu đồ 7: Mức độ sử dụng CPU (CPU Utilization %)
- **Playfair**: Gây nghẽn CPU cực độ trên cả 2 đầu:
  - Sender: **95.7%** (100 KB) và **98.6%** (1 MB) thời gian chạy là chu kỳ CPU tích cực liên tục trên luồng tính toán ma trận.
  - Receiver: **96.0%** (100 KB) và **98.0%** (1 MB) khi giải mã ngược lại.
- **AES-128-CBC**: Tiêu thụ CPU cực kỳ hiệu quả:
  - Ở 1 KB và  tập 100 KB: CPU usage đo được **0.0%** do thời gian xử lý quá nhanh (< 0.1 ms).
  - Ở 1 MB: CPU usage chỉ dừng ở mức **6.7%**, giải phóng hoàn toàn tài nguyên CPU cho các tiến trình mạng và hệ thống khác.
- **None & Caesar**: Tiêu thụ CPU xấp xỉ **0.0%**, chứng minh bảng dịch ký tự C của Python hoạt động tối ưu.

### 5.8. Biểu đồ 8: Mức độ tiêu thụ Bộ nhớ RAM (Memory RSS & Allocation Delta)
- **Resident Set Size (RAM RSS)**:
  - Mức chiếm dụng bộ nhớ cơ bản của tiến trình Python trên cả Sender và Receiver dao động ổn định trong khoảng **102 – 110 MB** qua tất cả các thuật toán và kích thước gói tin.
  - Không có hiện tượng rò rỉ bộ nhớ (memory leak) qua 372 lượt chạy liên tục.
- **Memory Allocation Delta**:
  - Playfair tạo ra mức tăng bộ nhớ tạm thời rõ rệt nhất (**103.7 – 157.7 KB**) do quá trình phân rã chuỗi thành digraph và khởi tạo danh sách cặp ký tự trong bộ nhớ heap.
  - AES-128-CBC và Caesar gần như không tạo ra biến động bộ nhớ bổ sung (Delta xấp xỉ 0 KB) nhờ cơ chế buffer trực tiếp và quản lý bộ nhớ ở tầng C.

---

## 6. Kết luận và Khuyến nghị kỹ thuật

1. **Sự vượt trội toàn diện của AES-128-CBC**:
   AES-128-CBC chứng minh sự vượt trội toàn diện khi đáp ứng đồng thời ba tiêu chí: **an toàn mật mã cấp độ cao**, **tốc độ xử lý tiệm cận mã hóa không bảo mật (None)** và **tiêu thụ tài nguyên CPU cực thấp (~6.7% ở 1 MB)**. Với băng thông đạt trên 260 MB/s, AES-128-CBC là lựa chọn tiêu chuẩn cho hệ thống phân tán.
2. **Nút thắt cổ chai CPU của Playfair**:
   Playfair là thuật toán cổ điển phù hợp cho mục đích giáo dục. Tuy nhiên, logic phân tách digraph và lặp ma trận thuần Python gây hiện tượng nghẽn CPU gần 100% khi dữ liệu đạt 100 KB – 1 MB (băng thông < 0.5 MB/s), không khả thi cho môi trường sản xuất.
3. **Caesar và bài toán baseline**:
   Caesar có chi phí CPU gần 0 và tốc độ tương đương None, nhưng không an toàn về mặt mật mã. Trong hệ thống phân tán, Caesar đóng vai trò benchmark kiểm định đường truyền tầng ứng dụng.

---

## 7. Hướng dẫn vận hành Benchmark trên môi trường 2 VM

### 7.1. Cấu hình môi trường mạng giữa 2 VM
- Đặt 2 máy ảo Windows (VM1 Sender và VM2 Receiver) trên cùng một máy host, chọn chế độ mạng **Bridge Adapter** (hoặc **Host-Only Network**).
- Gán IP tĩnh:
  - VM1 (Sender): `192.168.1.1`
  - VM2 (Receiver): `192.168.1.2`

### 7.2. Kiểm tra trước đường truyền (Ping Test)
Từ VM1, mở PowerShell và chạy kiểm tra chất lượng kết nối:
```powershell
ping -n 30 192.168.1.2
```
*Yêu cầu: 0% packet loss. Nếu RTT dao động bất thường, chuyển adapter sang Internal Network hoặc Host-Only Network.*

### 7.3. Thực hiện Benchmark
1. **Trên VM2 (Receiver)**:
   ```powershell
   python benchmark/server.py --host 0.0.0.0 --port 5000
   ```
2. **Trên VM1 (Sender)**:
   ```powershell
   python benchmark/client.py --host 192.168.1.2 --port 5000 --output benchmark/results/benchmark_results.csv
   ```
3. **Phân tích và vẽ biểu đồ**:
   ```powershell
   python benchmark/analyze.py --csv benchmark/results/benchmark_results.csv
   ```
   *(Hoặc chạy lệnh tự động tổng thể `python benchmark/run_benchmark.py --host 192.168.1.2 --port 5000 --remote`)*.
