# 🛡️ GIAO THỨC BẮT BUỘC: LAYA-OCR-GUARD DUAL-GATE HOOK

Tài liệu này quy định **Chỉ Thị Hoạt Động Bắt Buộc (Mandatory Agent Directives)** cho mọi AI Agent (`omp`, Claude Code, Cursor, Windsurf, Aider) khi làm việc trong kho mã nguồn này.

Để tránh tuyệt đối việc sửa tính năng này làm hỏng hoặc mất các tính năng cũ, **AI AGENT BẮT BUỘC PHẢI THỰC HIỆN ĐỦ 2 NHỊP HOOK BẰNG BASH TOOL**:

```text
[Yêu Cầu Mới / Bugfix từ Người Dùng]
             │
             ▼
┌────────────────────────────────────────────────────────┐
│ 1. NHỊP PRE-TASK (BẮT BUỘC TRƯỚC KHI SỬA BẤT KỲ CODE): │
│ • Agent chạy lệnh: `guard pre "<yêu cầu>"`             │
│ • Đọc file: `.guard/PRE_TASK_NOTE.md` để nắm Invariants│
│ • Trình bày form: ### 🔍 PRE-TASK IMPACT NOTE          │
└────────────────────────────────────────────────────────┘
             │
             ▼ (Agent tiến hành sửa code đúng phạm vi cho phép)
             │
┌────────────────────────────────────────────────────────┐
│ 2. NHỊP POST-TASK (BẮT BUỘC SAU KHI SỬA CODE XONG):    │
│ • Agent chạy lệnh: `guard post`                        │
│ • Kiểm tra kết quả build test & phán quyết LLM Gate    │
│ • Nếu REVISE: Tự động sửa lại theo danh sách lỗi       │
│ • Trình bày form: ### 🧪 POST-TASK VERIFICATION       │
└────────────────────────────────────────────────────────┘
```

---

### 📐 BẢNG MẪU BÁO CÁO BẮT BUỘC CỦA AGENT:

Khi phản hồi Người Dùng, Agent phải luôn tuân thủ form mẫu minh bạch:

```markdown
### 🔍 PRE-TASK IMPACT NOTE:
* **Hiện trạng chức năng:** [Mô tả tính năng hiện tại đã có gì]
* **Dự kiến phạm vi tác động:** [Danh sách file sẽ thay đổi]
* **Locked Invariants:** [Các bất biến kỹ thuật không được làm gãy]

---
(Nội dung thực hiện sửa đổi mã nguồn tối giản, chuẩn xác)
---

### 🧪 POST-TASK VERIFICATION:
* **Phạm vi tác động thực tế:** [Những gì đã thay đổi cụ thể]
* **Build Check:** [Kết quả build/test tự động từ guard post]
* **LLM Gate Verdict:** [APPROVED hoặc REVISE]
```
