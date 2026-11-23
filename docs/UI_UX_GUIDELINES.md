# EduSuggest UI/UX Guidelines

## Quy trình trước khi triển khai

1. Đọc [Design Constitution](./DESIGN_CONSTITUTION.md) và
   [Design System](./DESIGN_SYSTEM.md).
2. Xác định vai trò, thiết bị, mục tiêu và hành động quan trọng nhất.
3. Xác định nguồn dữ liệu/API, quyền truy cập, loading/error/empty/success và
   trạng thái chưa lưu.
4. Vẽ thứ bậc thông tin và chọn bố cục phù hợp nghiệp vụ; không mặc định sidebar
   hoặc card grid.
5. Tái sử dụng token và component; chỉ tạo component mới khi có ít nhất một
   pattern lặp lại hoặc quy tắc tương tác cần thống nhất.

## Hướng dẫn theo vai trò

### USER — khám phá và học tập

- Trang khám phá ưu tiên thanh tìm kiếm, chủ đề, bộ lọc dễ hiểu và nội dung liên
  quan; không bắt người học đọc dashboard trước khi tìm được khóa học.
- Trang chi tiết khóa học thể hiện mục tiêu, cấp độ, khối lượng học, giảng viên,
  nội dung và CTA đăng ký theo đúng dữ liệu API.
- Màn hình học đặt bài học/nội dung ở trung tâm; điều hướng chương và tiến độ là
  hỗ trợ, không lấn át nội dung.
- Gợi ý cá nhân hóa phải phân biệt rõ dữ liệu thật, lý do gợi ý và trạng thái
  chưa có kết quả. Không trình bày số liệu demo như kết quả thực tế.

### PROVIDER — sáng tạo và quản lý nội dung

- Tổ chức khóa học theo vòng đời: bản nháp, gửi duyệt, nhận góp ý, chỉnh sửa,
  gửi lại, đã duyệt. Mỗi trạng thái đi kèm hành động tiếp theo.
- Trình soạn khóa học ưu tiên cấu trúc chương/bài, lưu nháp và xem trước; tránh
  một form dài không phân nhóm.
- Tài liệu, bài học và thông tin khóa học cần trạng thái tải lên, lỗi validation
  và xác nhận lưu riêng.
- Nhận xét của chuyên gia phải gắn với nội dung và có thể quét nhanh.

### EXPERT — đánh giá học thuật

- Danh sách chờ duyệt ưu tiên lọc, độ mới và trạng thái phân công.
- Trang review giữ nội dung khóa học và tiêu chí đánh giá trong cùng ngữ cảnh;
  nhận xét phải có vị trí/đối tượng rõ ràng.
- Phân biệt hành động phê duyệt, từ chối và yêu cầu chỉnh sửa; thao tác từ chối
  hoặc yêu cầu sửa cần lý do.
- Lịch sử quyết định có người thực hiện, thời gian và kết quả để đảm bảo khả năng
  truy vết.

### ADMIN — quản trị và vận hành

- Ưu tiên bảng cho dữ liệu cần so sánh, tìm kiếm/lọc theo tiêu chí nghiệp vụ và
  phân trang minh bạch.
- Thao tác quyền hạn, khóa tài khoản hoặc đổi trạng thái cần mô tả hậu quả và
  xác nhận thích hợp.
- Quản lý hiển thị khóa học không đồng nghĩa với quyền duyệt nội dung học thuật;
  giao diện phải thể hiện đúng ranh giới quyền.
- Dashboard chỉ có KPI/biểu đồ có nguồn dữ liệu và định nghĩa; nếu chưa có API,
  hiển thị trạng thái chưa khả dụng thay vì con số giả.

## Pattern theo loại màn hình

### Dashboard

- Một câu trả lời rõ ràng cho “tôi cần biết/làm gì tiếp theo?”.
- Tối đa 3–5 chỉ số ưu tiên; đặt nguồn/thời điểm dữ liệu ở nơi dễ nhận biết.
- Bố cục khác nhau theo vai trò; không lặp cùng bộ card cho mọi dashboard.

### Form

- Nhóm trường theo mục đích, label rõ, ví dụ định dạng nếu thực sự hữu ích.
- Validation sau thao tác hoặc khi rời trường phù hợp; lỗi nêu cách sửa và giữ
  nguyên dữ liệu khác.
- Nút submit mô tả hành động; khóa nút khi đang gửi và ngăn gửi trùng.
- Với thao tác nguy hiểm, có xác nhận và tóm tắt thay đổi.

### Bảng và danh sách

- Đặt tìm kiếm/lọc gần dữ liệu; hiển thị tiêu chí đang áp dụng và nút xóa lọc.
- Ưu tiên thông tin nhận diện và trạng thái; thao tác phụ nằm trong menu khi cần.
- Empty state phân biệt “chưa có dữ liệu” với “không có kết quả theo bộ lọc”.

### Tìm kiếm và bộ lọc

- Giữ truy vấn khi quay lại danh sách; nêu kết quả và cho xóa bộ lọc nhanh.
- Bộ lọc nhiều lựa chọn có thể áp dụng/xóa tất cả; không đặt quá nhiều control
  trước khi người dùng hiểu nội dung.

### Dialog, toast và thông báo

- Dialog dành cho quyết định cần tập trung; không dùng cho mọi xác nhận đơn giản.
- Toast ngắn gọn, không che CTA hoặc dữ liệu đang thao tác; lỗi cần phục hồi phải
  nằm trong trang.
- Nội dung lỗi không lộ stack trace, token hoặc chi tiết nội bộ.

## Responsive và khả năng tiếp cận

- Kiểm tra tối thiểu 375 px, 768 px và 1280 px; không để trang cuộn ngang ngoài
  thành phần bảng được chủ ý.
- Vùng chạm khoảng 44×44 px; thứ tự tab khớp thứ tự đọc; focus luôn nhìn thấy.
- Dùng heading theo cấp, label/description/error được liên kết với control và
  thông báo thay đổi trạng thái bằng live region phù hợp.
- Không truyền trạng thái chỉ bằng màu; kết hợp nhãn, icon hoặc nội dung.
- Tôn trọng giảm chuyển động, zoom và cỡ chữ hệ thống.

## Hoàn tất và review

Trước khi bàn giao, kiểm tra dữ liệu/API thật, mọi trạng thái, console, keyboard,
responsive, tương phản, nội dung và nhất quán component. Chạy build/test phù hợp
với phạm vi thay đổi. Ghi rõ phần chưa kết nối API hoặc giới hạn nghiệp vụ; không
giả lập thành tính năng hoàn thiện.
