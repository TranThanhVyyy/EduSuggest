# EduSuggest database ERD

This diagram documents the existing 11 ERD tables, the previously added JWT
revocation table, and the additive `DonXinNhaCungCap` table. The `NguoiDung`
table now has an additive `tenTaiKhoan` column for username-based sign-in;
the existing primary/foreign keys and other ERD tables are unchanged.

```mermaid
erDiagram
    VaiTro ||--o{ NguoiDung : "maVaiTro"
    NguoiDung ||--o{ NhaCungCapKhoaHoc : "maNguoiDung"
    NguoiDung ||--o{ DonXinNhaCungCap : "maNguoiDung"
    NguoiDung ||--o{ ChuyenGia : "maNguoiDung"
    NhaCungCapKhoaHoc ||--o{ KhoaHoc : "maNhaCungCap"
    DanhMuc ||--o{ KhoaHoc : "maDanhMuc"
    NguoiDung ||--o{ KhoaHoc : "maNguoiDuyet"
    KhoaHoc ||--o{ BaiHoc : "maKhoaHoc"
    BaiHoc ||--o{ TaiLieu : "maBaiHoc"
    KhoaHoc ||--o{ DanhGiaChuyenGia : "maKhoaHoc"
    ChuyenGia ||--o{ DanhGiaChuyenGia : "maChuyenGia"
    NguoiDung ||--o{ LichSuHocTap : "maNguoiDung"
    KhoaHoc ||--o{ LichSuHocTap : "maKhoaHoc"
    BaiHoc ||--o{ LichSuHocTap : "maBaiHoc"
    NguoiDung ||--o{ DangKyKhoaHoc : "maNguoiDung"
    KhoaHoc ||--o{ DangKyKhoaHoc : "maKhoaHoc"

    VaiTro {
        int maVaiTro PK
        varchar tenVaiTro
        text moTa
    }
    NguoiDung {
        int maNguoiDung PK
        int maVaiTro FK
        varchar tenTaiKhoan UK
        varchar hoTen
        varchar email
        varchar matKhau
        varchar soDienThoai
    }
    NhaCungCapKhoaHoc {
        int maNhaCungCap PK
        int maNguoiDung FK
        text tieuSu
        varchar chuyenMon
    }
    DonXinNhaCungCap {
        int maDon PK
        int maNguoiDung FK
        varchar toChuc
        text kinhNghiem
        text lyDoDangKy
        varchar chuyenMon
        text gioiThieu
        varchar trangThai
        text lyDoTuChoi
        datetime ngayGui
        datetime ngayXuLy
    }
    DanhMuc {
        int maDanhMuc PK
        varchar tenDanhMuc
        text moTa
    }
    KhoaHoc {
        int maKhoaHoc PK
        int maNhaCungCap FK
        int maDanhMuc FK
        int maNguoiDuyet FK
        varchar tieuDe
        text moTa
        numeric gia
        varchar trinhDo
        int thoiLuong
        varchar trangThaiDuyet
        varchar trangThaiHienThi
        text lyDoTuChoi
        datetime ngayDuyet
        datetime ngayTao
        datetime ngayCapNhat
    }
    BaiHoc {
        int maBaiHoc PK
        int maKhoaHoc FK
        varchar tieuDe
        text noiDung
        varchar duongDanVideo
        int thoiLuong
        int thuTu
        datetime ngayTao
    }
    TaiLieu {
        int maTaiLieu PK
        int maBaiHoc FK
        varchar tieuDe
        varchar duongDanTep
        varchar loai
        text moTa
        datetime ngayTao
    }
    ChuyenGia {
        int maChuyenGia PK
        int maNguoiDung FK
        varchar chuyenMon
        text tieuSu
    }
    DanhGiaChuyenGia {
        int maDanhGia PK
        int maKhoaHoc FK
        int maChuyenGia FK
        text noiDungDanhGia
        numeric diemKyThuat
        numeric diemNoiDung
        text ghiChu
        varchar trangThai
        datetime ngayTao
    }
    LichSuHocTap {
        int maLichSu PK
        int maNguoiDung FK
        int maKhoaHoc FK
        int maBaiHoc FK
        varchar tienDo
        int thoiGianXem
        numeric danhGia
        datetime ngayTao
    }
    DangKyKhoaHoc {
        int maDangKy PK
        int maNguoiDung FK
        int maKhoaHoc FK
        datetime ngayDangKy
        numeric tienDo
        datetime ngayHoanThanh
    }
    TokenBiThuHoi {
        int maToken PK
        varchar jti UK
        datetime thoiGianHetHan
        datetime ngayTao
    }
```

`KhoaHoc.trangThaiDuyet` and `KhoaHoc.trangThaiHienThi` remain separate:
EXPERT controls review (`PENDING`, `APPROVED`, `REJECTED`, `NEEDS_REVISION`),
while ADMIN may set visibility (`VISIBLE`, `HIDDEN`) only after approval.
`DonXinNhaCungCap.trangThai` uses `PENDING`, `APPROVED`, and `REJECTED`.
