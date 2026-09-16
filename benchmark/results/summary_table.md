# Bang Tong hop Ket qua Benchmark Ma hoa Mang

## 1. Ti le thanh cong (Success Rate)

| Thuat toan | Kich thuoc | Tong so luot | Thanh cong | Ti le (%) |
|---|---|---:|---:|---:|
| None | 1 KB | 30 | 30 | 100.0% |
| None | 100 KB | 30 | 30 | 100.0% |
| None | 1 MB | 30 | 30 | 100.0% |
| Caesar | 1 KB | 30 | 30 | 100.0% |
| Caesar | 100 KB | 30 | 30 | 100.0% |
| Caesar | 1 MB | 30 | 30 | 100.0% |
| Playfair | 1 KB | 30 | 30 | 100.0% |
| Playfair | 100 KB | 30 | 30 | 100.0% |
| Playfair | 1 MB | 30 | 30 | 100.0% |
| AES-128-CBC | 1 KB | 30 | 30 | 100.0% |
| AES-128-CBC | 100 KB | 30 | 30 | 100.0% |
| AES-128-CBC | 1 MB | 30 | 30 | 100.0% |

## 2. Chi tiet cac chi so thoi gian va bang thong (Chi tinh tren luot thanh cong)

| Thuat toan | Size | Ciphertext (B) | Packet (B) | Encrypt Mean (ms) | Decrypt Mean (ms) | RTT Mean (ms) | Total Mean (ms) | Total Median (ms) | Throughput (KB/s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| None | 1 KB | 1,024 | 1,024 | 0.00 | 0.00 | 0.06 | 0.06 | 0.06 | 16846.3 |
| None | 100 KB | 102,400 | 102,400 | 0.00 | 0.01 | 0.13 | 0.13 | 0.13 | 799051.8 |
| None | 1 MB | 1,048,576 | 1,048,576 | 0.20 | 0.21 | 3.52 | 3.71 | 1.77 | 526288.1 |
| Caesar | 1 KB | 1,024 | 1,024 | 0.01 | 0.01 | 0.10 | 0.10 | 0.10 | 10723.6 |
| Caesar | 100 KB | 102,400 | 102,400 | 0.07 | 0.08 | 0.23 | 0.30 | 0.31 | 356960.8 |
| Caesar | 1 MB | 1,048,576 | 1,048,576 | 0.76 | 0.94 | 4.05 | 4.82 | 3.13 | 299750.1 |
| Playfair | 1 KB | 1,024 | 1,024 | 1.32 | 1.33 | 1.45 | 2.77 | 2.80 | 363.8 |
| Playfair | 100 KB | 102,400 | 102,400 | 111.46 | 107.61 | 107.79 | 219.25 | 219.59 | 456.8 |
| Playfair | 1 MB | 1,048,576 | 1,048,576 | 1181.35 | 1136.77 | 1140.12 | 2321.47 | 2331.22 | 441.6 |
| AES-128-CBC | 1 KB | 1,040 | 1,056 | 0.02 | 0.02 | 0.10 | 0.13 | 0.12 | 8167.0 |
| AES-128-CBC | 100 KB | 102,416 | 102,432 | 0.09 | 0.05 | 0.19 | 0.28 | 0.27 | 371501.2 |
| AES-128-CBC | 1 MB | 1,048,592 | 1,048,608 | 1.44 | 1.20 | 2.92 | 4.36 | 3.98 | 250553.1 |

## 3. Chi tiet muc su dung CPU va RAM (Chi tinh tren luot thanh cong)

| Thuat toan | Size | Sender CPU (%) | Receiver CPU (%) | Sender RAM (MB) | Receiver RAM (MB) | Sender Delta (KB) | Receiver Delta (KB) |
|---|---|---:|---:|---:|---:|---:|---:|
| None | 1 KB | 0.0% | 0.0% | 103.4 MB | 103.4 MB | 0.0 KB | 0.0 KB |
| None | 100 KB | 0.0% | 0.0% | 103.4 MB | 103.4 MB | 0.0 KB | 0.0 KB |
| None | 1 MB | 0.0% | 0.0% | 107.3 MB | 107.5 MB | 0.0 KB | 0.0 KB |
| Caesar | 1 KB | 0.0% | 0.0% | 103.7 MB | 103.7 MB | 0.0 KB | 0.0 KB |
| Caesar | 100 KB | 0.0% | 0.0% | 103.4 MB | 103.4 MB | 0.0 KB | 0.0 KB |
| Caesar | 1 MB | 3.3% | 3.3% | 107.5 MB | 107.6 MB | 0.0 KB | 0.0 KB |
| Playfair | 1 KB | 6.7% | 3.3% | 103.4 MB | 103.4 MB | 0.0 KB | 0.0 KB |
| Playfair | 100 KB | 94.2% | 95.5% | 101.6 MB | 101.7 MB | 106.8 KB | 103.3 KB |
| Playfair | 1 MB | 97.1% | 97.3% | 108.9 MB | 108.9 MB | 0.0 KB | 0.0 KB |
| AES-128-CBC | 1 KB | 0.0% | 0.0% | 104.4 MB | 104.4 MB | 0.0 KB | 0.0 KB |
| AES-128-CBC | 100 KB | 0.0% | 0.0% | 102.4 MB | 102.4 MB | 0.0 KB | 0.0 KB |
| AES-128-CBC | 1 MB | 3.3% | 3.3% | 110.4 MB | 110.9 MB | 0.0 KB | 0.0 KB |

## 4. Danh gia So sanh Do an toan Mat ma hoc (Theoretical Security Comparison)

| Chi so an toan | Y nghia do luong | Caesar | Playfair | AES-128-CBC |
|---|---|:---:|:---:|:---:|
| **Khong gian khoa (H(K))** | Do kho khi do quet vet can | 4.6 bits (25 khoa) | **79.1 bits ($6.2 \times 10^{23}$)** | **128.0 bits ($3.4 \times 10^{38}$)** |
| **Chi so trung phung (IC)** | Kha nang chong phan tich lap | 0.0667 (Kem) | **~0.0482 (Kha tot)** | **0.0385 (Ly tuong)** |
| **Entropy thong tin (H)** | Do hon loan / ngau nhien | 4.15 bits/char | **~4.60 bits/char** | **7.99 bits/byte** |
| **Khoang cach duy nhat (U_D)** | Luong ban ma can de be khoa | ~2 ky tu | **~25 - 50 ky tu** | **Khong kha thi** |