# Đường dẫn MinIO Server
$MinioExe = 'C:\Users\OS\go\bin\minio.exe'

# Thư mục lưu dữ liệu của EduSuggest
$DataDir = 'D:\đồ án\EduSuggest\media\data'

# Tạo thư mục nếu chưa tồn tại
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null

# Tài khoản và mật khẩu cố định
$env:MINIO_ROOT_USER = 'minioadmin'
$env:MINIO_ROOT_PASSWORD = 'minioadmin'

# Khởi động MinIO
& $MinioExe server $DataDir --console-address ':9001'