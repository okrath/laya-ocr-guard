"""
Hook Script Templates for Git and AI Coding Agents.
"""

# Git pre-commit hook: runs guard post to verify build, blast radius, and invariants before allowing commit
GIT_PRE_COMMIT_HOOK = """#!/usr/bin/env sh
# --- LAYA-OCR-GUARD AUTO-GENERATED HOOK ---
echo "🛡️  Running Laya-OCR-Guard Pre-Commit Check..."
guard post
STATUS=$?
if [ $STATUS -ne 0 ]; then
  echo "❌ Guard Verification FAILED! Commit aborted."
  echo "💡 Tip: Review the violations above or run 'guard post' manually."
  exit 1
fi
echo "✅ Guard Verification PASSED. Proceeding with commit."
exit 0
"""

# Git prepare-commit-msg hook: appends post-task verification summary to commit message
GIT_PREPARE_COMMIT_MSG_HOOK = """#!/usr/bin/env sh
# --- LAYA-OCR-GUARD COMMIT MSG HOOK ---
COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Only append if message is not an amend or merge
if [ "$COMMIT_SOURCE" != "commit" ] && [ -f ".guard/session.json" ]; then
  echo "" >> "$COMMIT_MSG_FILE"
  echo "Approved-by: Laya-OCR-Guard (LLM Gate Verification)" >> "$COMMIT_MSG_FILE"
fi
"""

# Agent wrapper script template (for command line harness execution)
AGENT_WRAPPER_SCRIPT = """#!/usr/bin/env sh
# --- LAYA-OCR-GUARD AGENT HARNESS ---
PROMPT="$1"
shift
CMD="$@"

echo "🛡️  [1/3] Triggering Pre-Task Guard..."
guard pre "$PROMPT" || exit 1

echo "🤖 [2/3] Executing Agent Command: $CMD"
$CMD
CMD_STATUS=$?

echo "🧪 [3/3] Triggering Post-Task Guard..."
guard post
POST_STATUS=$?

if [ $CMD_STATUS -ne 0 ]; then
  exit $CMD_STATUS
fi
exit $POST_STATUS
"""

# Agent Instruction Directive Template for CLAUDE.md & AGENT.md (Auto-consumed by omp, Claude Code, Cursor, Windsurf)
AGENT_DIRECTIVES_TEMPLATE = """# 🛡️ GIAO THỨC BẮT BUỘC: LAYA-OCR-GUARD DUAL-GATE HOOK

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

### 🛋️ NGUYÊN TẮC "LƯỜI BIẾNG HIỆU QUẢ" (KISS & YAGNI — THE NECESSITY LADDER):
*"Đoạn code ít lỗi nhất là đoạn code chưa bao giờ được viết ra."*

Trước khi viết bất kỳ hàm mới hoặc thêm file mới, Agent **BẮT BUỘC** leo thang đo cần thiết:
1. **[YAGNI]** Có thực sự cần code này không? Xóa bớt code luôn tốt hơn viết thêm code.
2. **[Tái sử dụng]** Soi kỹ codebase hiện tại xem đã có hàm/component tương tự chưa (tránh viết lại bánh xe).
3. **[Thư viện chuẩn & Native]** Dùng stdlib (Python) hoặc runtime native API (Browser/Node: fetch, crypto, Intl).
4. **[Dependencies đã cài]** Tuyệt đối KHÔNG tự ý cài package npm/pip mới trừ khi có yêu cầu rõ ràng.
5. **[KISS / 1-liner]** Ưu tiên giải pháp ngắn gọn, đơn giản. Cấm tạo interface/factory/class rườm rà cho logic nhỏ.

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
"""
