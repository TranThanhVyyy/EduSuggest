# HƯỚNG DẪN SỬ DỤNG 3 BỘ DESIGN SKILLS CHO EDUSUGGEST

Tài liệu này hướng dẫn cách lựa chọn, phối hợp và áp dụng 3 bộ Agent Skills đã cài đặt trong dự án EduSuggest mà **không thay thế** nội dung gốc trong các file `SKILL.md` của từng skill.

---

## 1. Phân vai 3 bộ Design Skills

### A. Emil Kowalski – Design Engineering Skills (`emilkowalski/skills`)
Các skill đã cài trong `.agents/skills/`:
- `emil-design-eng` (triết lý design engineering tổng quát)
- `animate` (xây dựng animation từ đầu)
- `review-animations` (đánh giá motion theo chuẩn khắt khe; có `disable-model-invocation: true` — gọi tường minh khi cần)
- `improve-animations` (audit chỉ đọc toàn codebase motion)
- `animation-performance` (giữ animation trong frame budget, composite-only properties)
- `choreograph` (điều phối chuỗi animation nhiều phần tử)

**Sử dụng cho:**
- Animation & Motion design (chọn có nên animate hay không, easing curve tùy chỉnh, thời lượng < 300ms cho UI).
- Micro-interactions (trạng thái press `:active`, hover có kiểm soát `@media (hover: hover)`).
- Hover và focus states.
- Modal, Drawer, Popover, Dropdown (`transform-origin` theo trigger cho popover/dropdown; modal giữ center).
- Transitions (ưu tiên transition có thể ngắt quãng thay vì keyframe cho thao tác lặp nhanh).
- Loading feedback (chuyển trạng thái mượt, tránh giật bố cục).

### B. Impeccable (`pbakaus/impeccable`, v4.10.0)
Skill đã cài trong `.agents/skills/impeccable/` (kèm 40+ playbook tham chiếu trong `reference/` và CLI cục bộ `scripts/impeccable.cmd`).

**Sử dụng cho:**
- UI audit (`audit`, `critique`) & đánh giá chất lượng kỹ thuật.
- Typography (`typeset`) & phân cấp nội dung.
- Layout & Spacing (`layout`, `distill`).
- Color contrast (`colorize`) & tính nhất quán thị giác.
- Accessibility (a11y, focus ring, semantic HTML, `prefers-reduced-motion`).
- Responsive (`adapt`) cho mobile/tablet/desktop.
- Component consistency (`extract`, `polish`, `document`).
- Empty, loading và error states (`harden`, `onboard`, `clarify`).

### C. Taste – Frontend Design Skill (`Leonxlnx/taste-skill`, `design-taste-frontend` v2.5.1)
Skill đã cài trong `.agents/skills/design-taste-frontend/` (kèm `references/`, `library/`, `assets/`, `scripts/`).

**Sử dụng cho:**
- Art direction & định hướng thẩm mỹ tổng thể cho trang công khai/landing.
- Visual identity & chất lượng thiết kế không mang cảm giác "template AI".
- Page composition & nhịp điệu từng màn hình (equal edges, khoảng thở hợp lý).
- Visual hierarchy & Editorial layout (đặc biệt hữu ích cho Public Homepage, trang giới thiệu khóa học, trang khám phá).
- Tránh các lỗi "AI slop" (copy sáo rỗng, gradient lạm dụng, card lặp vô nghĩa).

---

## 2. Quy trình phối hợp khuyến nghị cho EduSuggest

1. **Khi thiết kế hoặc nâng cấp trang mới (Landing / Catalog / Dashboard):**
   - Dùng **Taste (`design-taste-frontend`)** để chốt bố cục trang, phân cấp thị giác và tránh cảm giác template.
   - Dùng **Impeccable (`impeccable`)** để chuẩn hóa spacing, typography, contrast, responsive và trạng thái loading/empty/error.
   - Dùng **Emil Kowalski (`emil-design-eng`, `animate`, `review-animations`)** để tinh chỉnh micro-interactions, hover/press, dropdown, modal và hiệu năng transition.
2. **Khi audit component hoặc màn hình hiện có:**
   - Dùng **Impeccable (`audit` / `critique`)** cho a11y, responsive, consistency, edge cases.
   - Dùng **Emil Kowalski (`review-animations` / `improve-animations`)** để rà soát `transition-all`, easing, duration và GPU properties.

---

## 3. Quy tắc thiết kế bắt buộc của EduSuggest (Bất biến)

Mọi đề xuất từ 3 bộ skill **phải tuân thủ tuyệt đối** kiến trúc và Design System hiện tại của EduSuggest:

### Bảng màu thương hiệu
- **Deep Navy:** `#112233`
- **Smart Teal:** `#0D9488`
- **Warm Amber:** `#D97706`
- **Canvas:** `#F8FAF9` (token Canvas hiện tại đã chuẩn hóa trong dự án; tương đương nền sáng `#F8F9FA`)
- **Surface:** `#FFFFFF`
- **Subtle:** `#F1F5F4`

### Phong cách thiết kế
- **Editorial EdTech Modernism + Bento Grid**

### Công nghệ Frontend cố định
- **Vue 3** (Composition API `<script setup>`)
- **Vite**
- **JavaScript** (KHÔNG chuyển sang TypeScript)
- **Vue Router**
- **Tailwind CSS**

### Các giới hạn tuyệt đối (Guardrails)
Không để bất kỳ skill nào tự ý:
- Chuyển Vue 3 sang React / Next.js / Svelte / Astro.
- Chuyển JavaScript sang TypeScript.
- Thay Tailwind CSS bằng CSS framework khác.
- Cài thêm thư viện UI không cần thiết vào `package.json`.
- Thay đổi toàn bộ Design System thương hiệu của EduSuggest.
- Chỉnh sửa Backend, API contract, Database, Migration, `.env` hoặc thuật toán gợi ý `TF-IDF + Cosine Similarity`.
