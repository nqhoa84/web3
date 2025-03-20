WALLET HISTORY

Đây là tài liệu hướng dẫn và giải thích về code trong dự án.

Cấu trúc thư mục:
- tx_his.py: Xử lý lịch sử giao dịch blockchain và xuất dữ liệu ra CSV.
- blacklist_token: Chứa danh sách cac token nằm trong black list và không cần lưu.

Hướng dẫn cài đặt:
Cài đặt Python và các thư viện cần thiết:
- Cài đặt Python mới nhất: https://www.python.org/downloads/
- Thư viện: pip install requests

Chức năng chính:
- Lấy lịch sử giao dịch từ blockchain.
- Lưu lịch sử giao dịch theo từng khoảng block vào file csv.

Cách chạy script:
- python tx_his.py 0x25e5B52696ae6a92E30815FD2d803124Ca46aff2 BSC 46258820 46927340
