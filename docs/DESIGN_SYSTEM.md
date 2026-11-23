# EduSuggest Design System

## Cách sử dụng

Design tokens được triển khai tại `frontend/src/assets/styles/`. `src/style.css`
là entry point duy nhất cho Tailwind và CSS nền tảng. Ưu tiên CSS variables,
utility semantic và các component trong `src/components/ui/`; không tạo màu hoặc
component thay thế cục bộ nếu token hiện có đã đáp ứng.

## Màu sắc

| Token | Giá trị | Vai trò |
| --- | --- | --- |
| `primary` | `#182B3A` | Màu thương hiệu, CTA chính, liên kết quan trọng |
| `navy` | `#122633` | Nền điều hướng tối và vùng thương hiệu đậm |
| `secondary` | `#527568` | Xanh sage, điều hướng hỗ trợ và thành công |
| `accent` | `#8A4F24` | Màu đồng đậm, đủ tương phản cho chữ và nút |
| `brand-accent` | `#D99B65` | Điểm nhấn ấm; dùng cho chi tiết trang trí không mang nghĩa trạng thái |
| `background` | `#F6F3EC` | Nền toàn trang |
| `surface` / `white` | `#FFFFFF` | Bề mặt nội dung, form và menu |
| `ink` | `#202B32` | Nội dung chính |
| `muted` | `#626E72` | Nội dung phụ, mô tả và metadata |
| `border` | `#E2DED4` | Ranh giới nhẹ giữa bề mặt |
| `success` | `#356B55` | Thành công, hoàn tất, đã duyệt |
| `warning` | `#8A5A10` | Cần chú ý hoặc đang chờ |
| `danger` | `#A33E35` | Lỗi, từ chối, thao tác nguy hiểm |
| `info` | `#426B75` | Thông tin trung tính |

`accent` được dùng là sắc đồng đậm để chữ/nút có độ tương phản tốt; sắc đồng
nguyên bản được giữ riêng ở `brand-accent`. Không dùng màu nhấn để thay thế màu
trạng thái. Bảng màu được khai báo cả trong Tailwind theme và CSS variables.
Các utility Tailwind `slate-*` hiện có được ánh xạ sang thang trung tính ấm để
các trang cũ cùng dùng một hệ màu mà không cần thay hàng loạt class.

## Typography

- **Body/UI:** system sans-serif (`Aptos`, `Segoe UI`, `Helvetica Neue`, fallback
  hệ thống). Không tải font bên ngoài khi chưa có quyết định sản phẩm.
- **Display:** `Iowan Old Style`, `Palatino Linotype`, `Book Antiqua`, `Georgia`,
  serif; dành cho H1/H2 hoặc điểm nhấn editorial, không dùng cho bảng/form.
- **Scale:** display 40–60 px responsive; H1 32–40 px; H2 24–30 px; H3 18–22 px;
  body 16 px; supporting 14 px; caption 12 px. Không dùng caption cho nội dung
  cần ra quyết định.
- **Line-height:** tiêu đề 1.1–1.25; body 1.5–1.7; nhãn ngắn 1.3–1.45.
- Giữ tối đa 2 họ font và 3 trọng lượng trong một màn hình; dùng `font-variant`
  và tracking tiết chế.

## Spacing, radius và shadow

- Thang khoảng cách theo bội số 4 px: 4, 8, 12, 16, 24, 32, 40, 48, 64 px.
- Dùng 8–12 px cho control, 16–24 px giữa nhóm, 24–40 px giữa section và tối đa
  64 px cho khoảng thở giữa vùng nội dung lớn.
- Radius: control 10 px; panel 14 px; feature 20 px; pill chỉ cho tag/badge.
  Các utility radius của Tailwind (`rounded-xl`, `rounded-2xl`, `rounded-3xl`)
  được ánh xạ tương ứng để giao diện hiện có cũng tuân chuẩn. Không bo tròn mọi
  container.
- Shadow chỉ để tách lớp cần thiết: panel `0 12px 32px rgba(24,43,58,.06)`;
  floating menu/modal `0 20px 48px rgba(24,43,58,.14)`. Ưu tiên border và nền
  trước shadow. `shadow-sm`/`shadow-xl` dùng cùng hai mức này.
- Token nền tảng có tên `--es-*` trong `tokens.css`; component mới dùng biến thay
  vì giá trị rời.

## Component

### Button

- Biến thể: primary, secondary, accent, outline, quiet, danger.
- Có trạng thái hover, focus-visible, disabled và loading; không đổi kích thước
  khi loading. Văn bản động mô tả tác vụ, không chỉ ghi “OK”.
- Mỗi vùng có tối đa một primary CTA; thao tác phá hủy dùng `danger` và xác nhận
  theo mức độ rủi ro.

### Input và form

- Dùng `UiField` cho nhãn, dấu bắt buộc, hint và error; input/select/textarea giữ
  cùng chiều cao, radius, focus ring và disabled state.
- Luôn có label; placeholder chỉ là ví dụ định dạng, không thay label.
- Lỗi đặt cạnh trường, nêu cách khắc phục; giữ dữ liệu người dùng đã nhập.
- Chia form dài thành nhóm theo nhiệm vụ; thông báo rõ trường bắt buộc và trạng
  thái lưu.

### Navigation, sidebar, header

- Điều hướng thể hiện vị trí hiện tại bằng active state rõ ràng và `aria-current`.
- Sidebar dành cho tác vụ quản trị/nội dung nhiều cấp; USER ưu tiên header và
  khám phá nội dung. Mobile navigation phải có nút đóng và focus dễ dùng.
- Header giữ ngữ cảnh, tài khoản và hành động toàn cục; không lặp lại tiêu đề
  trang không cần thiết.

### Table

- Dùng khi cần so sánh nhiều bản ghi cùng thuộc tính; nếu nội dung dài hoặc giàu
  ngữ cảnh, dùng danh sách có phân cấp thay vì bảng.
- Có heading cột, sort/filter có trạng thái, pagination có tổng/trang hiện tại,
  skeleton khi tải và empty/error state.
- Mobile cho phép cuộn ngang có chỉ dấu hoặc chuyển từng hàng thành bố cục đọc
  được; không cắt mất thao tác.

### Modal và dropdown

- Modal chỉ dành cho tác vụ ngắn, quyết định cần tập trung hoặc nội dung phụ.
  Có tiêu đề, mô tả, nút đóng, focus trap và khôi phục focus.
- Dropdown có nhãn, focus/keyboard, vị trí gần trigger và không che hành động
  chính; menu dài có thể cần tìm kiếm.

### Tabs và pagination

- Tabs chỉ đổi nội dung cùng cấp; dùng `tablist`, `tab`, `tabpanel` đúng ngữ nghĩa
  và giữ trạng thái focus.
- Pagination giữ tiêu chí lọc, thông báo kết quả, disable biên và không nhảy về
  trang đầu khi tải lại cùng truy vấn.

### Badge, toast, loading, empty và error

- `UiStatusBadge` dùng tone ngữ nghĩa; không chỉ dựa vào màu để truyền trạng thái.
- Toast chỉ xác nhận tác vụ đã hoàn tất hoặc cảnh báo ngắn; lỗi cần hành động
  khắc phục nên nằm trong vùng nội dung và được giữ đủ lâu.
- Loading dùng skeleton cho nội dung có cấu trúc và spinner cho một hành động.
  Không khóa toàn trang nếu chỉ một phần đang tải.
- Empty state giải thích vì sao chưa có dữ liệu và đưa ra bước tiếp theo phù hợp.
- Error state nêu tác động, hướng khắc phục/thử lại và không lộ chi tiết kỹ thuật.

## Responsive breakpoints

| Tên | Chiều rộng | Hướng xử lý |
| --- | --- | --- |
| Mobile | `< 640px` | Một cột, nội dung ưu tiên, CTA dễ chạm, navigation thu gọn |
| Tablet | `640–1023px` | Lưới linh hoạt, giảm số cột, panel phụ chuyển xuống dưới |
| Desktop | `1024–1279px` | Điều hướng đầy đủ, lưới nội dung vừa phải |
| Wide | `>= 1280px` | Tăng khoảng thở và giới hạn độ rộng đọc; không kéo dài dòng văn bản |

Breakpoint sử dụng các mốc Tailwind `sm`, `md`, `lg`, `xl` trong theme hiện hành.
