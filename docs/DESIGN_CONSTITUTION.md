# EduSuggest Design Constitution

## Mục đích

EduSuggest là hệ thống gợi ý khóa học và tài liệu học tập. Giao diện phải giúp
người học khám phá và duy trì tiến độ; đồng thời giúp nhà cung cấp tạo nội dung,
chuyên gia đánh giá và quản trị viên vận hành hệ thống một cách chính xác.

Tài liệu này là chuẩn bắt buộc cho giao diện mới và mọi thay đổi UI/UX. Trước khi
thiết kế, hãy đọc thêm [Design System](./DESIGN_SYSTEM.md) và
[UI/UX Guidelines](./UI_UX_GUIDELINES.md).

## Tuyên ngôn thiết kế

EduSuggest kết hợp sự tin cậy của một nền tảng học thuật với cảm giác gần gũi của
một người đồng hành học tập. Sản phẩm có chất biên tập hiện đại, tiết chế và có
chiều sâu; không giống một bộ dashboard bán sẵn.

Thiết kế tốt ở EduSuggest làm rõ nội dung, trạng thái và hành động tiếp theo.
Trang trí chỉ được giữ lại khi củng cố nhận diện hoặc giúp người dùng hiểu thông
tin.

## Nguyên tắc bắt buộc

1. **Nghiệp vụ dẫn dắt bố cục.** Mỗi trang bắt đầu từ người dùng, dữ liệu và
   quyết định chính của trang; không áp một template chung cho mọi vai trò.
2. **Một hành động chính.** Mỗi vùng nội dung có hành động ưu tiên dễ nhận biết;
   hành động phụ có trọng số thị giác thấp hơn.
3. **Thông tin có thứ bậc.** Tiêu đề, nhãn, nội dung, trạng thái và metadata phải
   phân biệt được bằng typography, khoảng cách và tương phản.
4. **Tôn trọng thời gian người dùng.** Nội dung quan trọng xuất hiện sớm; bảng
   dài, form nhiều bước và thao tác nguy hiểm cần hỗ trợ quét, lưu ý và hoàn tác
   phù hợp.
5. **Tin cậy trước hiệu ứng.** Mọi trạng thái tải, rỗng, lỗi, thành công và quyền
   truy cập phải phản ánh dữ liệu hoặc phản hồi API thật. Không tạo số liệu hay
   kết quả giả để lấp chỗ trống.
6. **Nhất quán, không đồng dạng.** Màu, type, spacing và component dùng chung;
   cách sắp xếp nội dung được quyết định theo ngữ cảnh vai trò.
7. **Tiếp cận là tiêu chuẩn.** Ưu tiên HTML ngữ nghĩa, thao tác bàn phím, focus
   nhìn thấy được, nhãn có liên kết với control, thông báo lỗi dễ hiểu và tương
   phản đủ mạnh.
8. **Thiết kế đáp ứng.** Không giả định màn hình rộng hoặc thao tác bằng chuột.
   Nội dung phải duy trì thứ tự, khả năng đọc và hành động chính trên điện thoại.
9. **Dùng hình ảnh có lý do.** Ảnh, minh họa và icon phải liên quan trực tiếp đến
   học tập hoặc tác vụ. Không dùng ảnh stock chung chung để lấp khoảng trống.
10. **Chuyển động có ích.** Chỉ dùng chuyển động ngắn để phản hồi thao tác hoặc
    làm rõ thay đổi trạng thái; tôn trọng `prefers-reduced-motion`.

## Bản sắc thị giác

- Nền giấy ấm, bề mặt sáng và mực xanh than tạo cảm giác học thuật, bình tĩnh.
- Xanh sage dùng cho hành động hỗ trợ và trạng thái tích cực.
- Màu đồng ấm là điểm nhấn; không dùng nó thay cho màu lỗi hoặc cảnh báo.
- Sans-serif rõ ràng dành cho nội dung và điều khiển; serif tiết chế dành cho
  tiêu đề có tính biên tập.
- Ưu tiên bố cục bất đối xứng có chủ đích, lưới rõ ràng và khoảng thở. Không biến
  mọi nhóm thông tin thành card.

## Khác biệt theo vai trò

- **USER:** khám phá, lựa chọn và học liên tục; ưu tiên nội dung, tiến độ và gợi ý.
- **PROVIDER:** sáng tạo và quản lý nội dung; ưu tiên cấu trúc khóa học, trạng thái
  xét duyệt và thao tác chỉnh sửa.
- **EXPERT:** đọc, so sánh và đưa ra nhận định; ưu tiên nội dung học thuật, tiêu chí
  đánh giá và lịch sử quyết định.
- **ADMIN:** vận hành và kiểm soát; ưu tiên mật độ thông tin, lọc, bảng, quyền hạn
  và khả năng truy vết.

Các vai trò dùng chung nhận diện và component, nhưng không bắt buộc dùng chung
sidebar, dashboard hay cách nhóm thông tin.

## Giới hạn thiết kế

- Không dùng gradient tím-xanh phổ thông, glassmorphism tràn lan, emoji làm icon
  hoặc hiệu ứng chuyển động để gây chú ý.
- Không tạo biểu đồ, KPI hoặc nội dung mẫu nếu không có nguồn dữ liệu rõ ràng.
- Không dùng placeholder làm nội dung hoàn thiện; empty state phải giải thích
  nguyên nhân và bước tiếp theo.
- Không biểu đạt quyền truy cập hoặc kết quả nghiệp vụ bằng trạng thái frontend
  không được Backend xác thực.
- Không thay đổi API hoặc nghiệp vụ chỉ để thuận tiện cho cách trình bày.

## Quy trình review

Trước khi code, xác định vai trò, mục tiêu, hành động chính, nguồn dữ liệu/API và
các trạng thái của trang. Chọn bố cục theo nghiệp vụ rồi ánh xạ component vào
Design System.

Sau khi code, kiểm tra trạng thái tải/rỗng/lỗi/thành công, keyboard và focus,
responsive ở mobile/tablet/desktop, nội dung thật, độ tương phản và console. Xóa
chi tiết trang trí không phục vụ hiểu biết hoặc thao tác.

## Checklist bắt buộc

- [ ] Đã đọc ba tài liệu thiết kế hiện hành.
- [ ] Người dùng và quyết định chính của trang đã rõ.
- [ ] API/dữ liệu và mọi trạng thái đã được xác định.
- [ ] Component và token dùng chung được tái sử dụng.
- [ ] Không tạo số liệu, quyền hạn hoặc phản hồi giả.
- [ ] Có keyboard/focus, nhãn, lỗi và thông báo dễ hiểu.
- [ ] Bố cục được kiểm tra trên mobile, tablet và desktop.
- [ ] Không có console error hoặc nội dung placeholder trong trạng thái hoàn thiện.
