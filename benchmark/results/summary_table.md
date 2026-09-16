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
| None | 1 KB | 1,024 | 1,024 | 0.00 | 0.00 | 0.13 | 0.13 | 0.12 | 8552.4 |
| None | 100 KB | 102,400 | 102,400 | 0.01 | 0.01 | 35.78 | 35.79 | 36.27 | 78000.9 |
| None | 1 MB | 1,048,576 | 1,048,576 | 0.18 | 0.19 | 8.06 | 8.24 | 1.85 | 402883.9 |
| Caesar | 1 KB | 1,024 | 1,024 | 0.01 | 0.01 | 0.12 | 0.12 | 0.12 | 8449.2 |
| Caesar | 100 KB | 102,400 | 102,400 | 0.06 | 0.07 | 25.25 | 25.31 | 22.50 | 109999.1 |
| Caesar | 1 MB | 1,048,576 | 1,048,576 | 0.86 | 0.93 | 6.65 | 7.51 | 3.50 | 231639.0 |
| Playfair | 1 KB | 1,024 | 1,024 | 1.22 | 1.29 | 18.23 | 19.45 | 13.15 | 133.4 |
| Playfair | 100 KB | 102,400 | 102,400 | 104.23 | 103.09 | 103.25 | 207.48 | 204.95 | 482.4 |
| Playfair | 1 MB | 1,048,576 | 1,048,576 | 1096.06 | 1080.66 | 1082.62 | 2178.68 | 2171.74 | 470.6 |
| AES-128-CBC | 1 KB | 1,040 | 1,056 | 0.03 | 0.03 | 0.13 | 0.16 | 0.16 | 6345.1 |
| AES-128-CBC | 100 KB | 102,416 | 102,432 | 0.11 | 0.05 | 3.79 | 3.89 | 0.35 | 235660.1 |
| AES-128-CBC | 1 MB | 1,048,592 | 1,048,608 | 1.43 | 1.18 | 16.55 | 17.98 | 10.09 | 145708.2 |

## 3. Chi tiet muc su dung CPU va RAM (Chi tinh tren luot thanh cong)

| Thuat toan | Size | Sender CPU (%) | Receiver CPU (%) | Sender RAM (MB) | Receiver RAM (MB) | Sender Delta (KB) | Receiver Delta (KB) |
|---|---|---:|---:|---:|---:|---:|---:|
| None | 1 KB | 0.0% | 0.0% | 208.1 MB | 208.1 MB | 0.0 KB | 0.0 KB |
| None | 100 KB | 0.0% | 0.0% | 208.1 MB | 208.1 MB | 0.0 KB | 0.0 KB |
| None | 1 MB | 3.3% | 3.3% | 217.3 MB | 217.5 MB | 0.0 KB | 0.0 KB |
| Caesar | 1 KB | 0.0% | 0.0% | 208.1 MB | 208.1 MB | 0.0 KB | 0.0 KB |
| Caesar | 100 KB | 0.0% | 0.0% | 208.1 MB | 208.1 MB | 0.0 KB | 0.0 KB |
| Caesar | 1 MB | 10.0% | 6.7% | 218.4 MB | 218.8 MB | 0.0 KB | 0.0 KB |
| Playfair | 1 KB | 6.7% | 6.7% | 207.1 MB | 207.1 MB | 0.0 KB | 0.0 KB |
| Playfair | 100 KB | 99.1% | 96.4% | 212.5 MB | 212.5 MB | 28.3 KB | 0.0 KB |
| Playfair | 1 MB | 98.4% | 98.0% | 214.5 MB | 214.4 MB | 1.2 KB | 15.7 KB |
| AES-128-CBC | 1 KB | 0.0% | 0.0% | 208.1 MB | 208.1 MB | 0.1 KB | 0.1 KB |
| AES-128-CBC | 100 KB | 0.0% | 0.0% | 207.1 MB | 207.1 MB | 0.0 KB | 0.0 KB |
| AES-128-CBC | 1 MB | 10.0% | 6.7% | 214.1 MB | 214.5 MB | 0.0 KB | 0.0 KB |