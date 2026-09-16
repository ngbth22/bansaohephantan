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
| None | 1 KB | 1,024 | 1,024 | 0.00 | 0.00 | 0.08 | 0.08 | 0.08 | 13558.0 |
| None | 100 KB | 102,400 | 102,400 | 0.00 | 0.01 | 0.12 | 0.13 | 0.13 | 815005.5 |
| None | 1 MB | 1,048,576 | 1,048,576 | 0.19 | 0.18 | 2.14 | 2.33 | 1.70 | 564703.1 |
| Caesar | 1 KB | 1,024 | 1,024 | 0.01 | 0.01 | 0.09 | 0.10 | 0.09 | 11180.6 |
| Caesar | 100 KB | 102,400 | 102,400 | 0.06 | 0.06 | 0.20 | 0.27 | 0.25 | 386281.4 |
| Caesar | 1 MB | 1,048,576 | 1,048,576 | 0.76 | 0.86 | 3.57 | 4.33 | 2.99 | 316320.2 |
| Playfair | 1 KB | 1,024 | 1,024 | 1.31 | 1.32 | 1.45 | 2.76 | 2.76 | 363.5 |
| Playfair | 100 KB | 102,400 | 102,400 | 114.99 | 115.11 | 115.30 | 230.29 | 229.04 | 435.2 |
| Playfair | 1 MB | 1,048,576 | 1,048,576 | 1155.02 | 1161.74 | 1165.62 | 2320.64 | 2348.35 | 442.0 |
| AES-128-CBC | 1 KB | 1,040 | 1,056 | 0.02 | 0.02 | 0.11 | 0.14 | 0.12 | 7900.5 |
| AES-128-CBC | 100 KB | 102,416 | 102,432 | 0.09 | 0.04 | 0.17 | 0.26 | 0.26 | 396010.9 |
| AES-128-CBC | 1 MB | 1,048,592 | 1,048,608 | 1.45 | 1.20 | 3.15 | 4.59 | 4.10 | 239789.7 |

## 3. Chi tiet muc su dung CPU va RAM (Chi tinh tren luot thanh cong)

| Thuat toan | Size | Sender CPU (%) | Receiver CPU (%) | Sender RAM (MB) | Receiver RAM (MB) | Sender Delta (KB) | Receiver Delta (KB) |
|---|---|---:|---:|---:|---:|---:|---:|
| None | 1 KB | 0.0% | 0.0% | 104.2 MB | 104.2 MB | 0.0 KB | 0.0 KB |
| None | 100 KB | 0.0% | 0.0% | 104.2 MB | 104.2 MB | 0.0 KB | 0.0 KB |
| None | 1 MB | 0.0% | 0.0% | 107.9 MB | 108.0 MB | 0.0 KB | 0.0 KB |
| Caesar | 1 KB | 0.0% | 0.0% | 104.5 MB | 104.5 MB | 0.0 KB | 0.0 KB |
| Caesar | 100 KB | 0.0% | 0.0% | 104.2 MB | 104.2 MB | 0.0 KB | 0.0 KB |
| Caesar | 1 MB | 3.3% | 3.3% | 107.7 MB | 107.9 MB | 0.0 KB | 0.0 KB |
| Playfair | 1 KB | 0.0% | 0.0% | 104.2 MB | 104.2 MB | 0.0 KB | 0.0 KB |
| Playfair | 100 KB | 94.1% | 94.3% | 102.1 MB | 102.1 MB | 64.0 KB | 76.0 KB |
| Playfair | 1 MB | 97.2% | 97.6% | 109.6 MB | 109.6 MB | 0.0 KB | 0.0 KB |
| AES-128-CBC | 1 KB | 0.0% | 0.0% | 105.2 MB | 105.2 MB | 0.0 KB | 0.1 KB |
| AES-128-CBC | 100 KB | 0.0% | 0.0% | 103.2 MB | 103.2 MB | 0.0 KB | 0.0 KB |
| AES-128-CBC | 1 MB | 6.7% | 6.7% | 111.2 MB | 111.3 MB | 0.0 KB | 0.0 KB |

## 4. Danh gia So sanh Do an toan Mat ma hoc (Theoretical Security Comparison)

| Chi so an toan | Y nghia do luong | Caesar | Playfair | AES-128-CBC |
|---|---|:---:|:---:|:---:|
| **Khong gian khoa (H(K))** | Do kho khi do quet vet can | 4.6 bits (25 khoa) | **79.1 bits ($6.2 \times 10^{23}$)** | **128.0 bits ($3.4 \times 10^{38}$)** |
| **Chi so trung phung (IC)** | Kha nang chong phan tich lap | 0.0667 (Kem) | **~0.0482 (Kha tot)** | **0.0385 (Ly tuong)** |
| **Entropy thong tin (H)** | Do hon loan / ngau nhien | 4.15 bits/char | **~4.60 bits/char** | **7.99 bits/byte** |
| **Khoang cach duy nhat (U_D)** | Luong ban ma can de be khoa | ~2 ky tu | **~25 - 50 ky tu** | **Khong kha thi** |