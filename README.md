# Laya OCR Guard (`guard`)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](#-cài-đặt-đa-nền-tảng-windows-linux-macos)
[![Architecture](https://img.shields.io/badge/architecture-Dual--Gate-green.svg)](#-kiến-trúc-3-trụ-cột)

**Dual-Gate Impact Analysis & Regression Guard for AI-Assisted Development.**

`guard` kết hợp sức mạnh của 3 thành phần:
1. **Laya** (System 1 fast reflex triage, <30ms, 0-cost, 0 token)
2. **Alibaba Open Code Review - OCR** (Deterministic git diff blast-radius & static rules, 0-cost)
3. **LLM được bạn add vào** (Claude, GPT-4o, DeepSeek, Ollama...): Đóng vai trò Bộ não Phân tích & **Chốt chặn an toàn cuối cùng (Final Safety Gate)**.

Kế thừa và tự động hóa chuẩn giao thức **Impact & Regression Protocol** từ `oh-my-ainovel`.

---

## 🏛️ Kiến Trúc 3 Trụ Cột

```text
               [Yêu Cầu / Prompt của Bạn]
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. NHỊP PRE-TASK: `guard pre "<yêu cầu>"`                   │
│ • Laya (<30ms, 0đ): Quét intent, domain & phân loại rủi ro   │
│ • Contract Extractor (FE / BE / Infra / MB)                 │
│ • Khóa các điều bất biến kỹ thuật (Locked Invariants)       │
│ ➔ Xuất bản ghi: "### 🔍 PRE-TASK IMPACT NOTE"               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼ (Coding Agent / Developer sửa mã nguồn)
                           │
┌─────────────────────────────────────────────────────────────┐
│ 2. NHỊP POST-TASK: `guard post`                             │
│ • OCR Inspector (0đ): Đo lường diff, kiểm soát Blast Radius  │
│ • Static Rulebook: Bắt lỗi Secrets, SQLi, Memory Leaks, NPE │
│ • Project Health Check: Chạy build & test tự động (0đ)      │
│ • Laya Scoring (0đ): Chấm điểm tuân thủ Invariants (Yes/No) │
│ ➔ Tổng hợp dữ liệu thành "### 🧪 POST-TASK VERIFICATION"   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. CHỐT CHẶN CUỐI CÙNG: LLM ĐƯỢC BẠN ADD VÀO                │
│ (Claude-3.7-Sonnet / GPT-4o / DeepSeek / Ollama...)         │
│ • LLM đọc bản nghiệm thu tóm tắt từ Bước 2                  │
│ • Thẩm định Kỹ thuật (Kiến trúc, Memory Leak, Scope breach) │
│ • Công thái học UX/UI & Trải nghiệm đa nền tảng             │
│ • Phê duyệt: [APPROVED] hoặc [REVISE] kèm Remediation Steps │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Cài Đặt Đa Nền Tảng (Windows, Linux, macOS)

Bạn có thể cài đặt lệnh `guard` trực tiếp vào hệ thống bằng một trong các phương pháp sau:

### Cách 1: Cài trực tiếp từ GitHub (Khuyên dùng)
```bash
# Trên Linux / macOS (Khuyên dùng pipx để tự động quản lý PATH):
pipx install git+https://github.com/okrath/laya-ocr-guard.git

# Hoặc dùng pip thông thường trên mọi hệ điều hành (Windows / Linux / macOS):
pip install git+https://github.com/okrath/laya-ocr-guard.git
```

### Cách 2: Clone repository về máy và cài đặt editable
```bash
git clone https://github.com/okrath/laya-ocr-guard.git
cd laya-ocr-guard
pip install -e .
```

### 💡 Lưu ý về Biến môi trường `$PATH`:
* **Windows**: `guard.exe` tự động nằm trong `Python3xx\Scripts\guard.exe`.
* **Linux / macOS**: File thực thi `guard` nằm tại `~/.local/bin/guard` hoặc `/usr/local/bin/guard`.  
  Nếu terminal báo `command not found: guard`, chỉ cần thêm thư mục này vào file profile của bạn:
  ```bash
  # Cho bash:
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc

  # Cho zsh (mặc định trên macOS):
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
  ```

### Cài đặt bổ sung Alibaba OCR CLI gốc (Tùy chọn):
`guard` đã tích hợp sẵn bộ rulebook và engine quét diff cục bộ (0đ). Nếu muốn kích hoạt thêm CLI gốc của Alibaba:
```bash
npm install -g @alibaba-group/open-code-review
```

Kiểm tra sức khỏe hệ thống:
```bash
guard doctor
```

---

## ⚙️ Cấu hình LLM & Alibaba OCR (Interactive Wizard)

Chỉ cần cấu hình một lần duy nhất, `guard` sẽ tự động kết nối và đồng bộ sang CLI của Alibaba Open Code Review (`ocr`):

```bash
guard config llm
```

Hệ thống dẫn dắt theo chuẩn 2 giao thức tinh gọn (bấm Enter để nhận mặc định):
1. **OpenAI / OpenAI-Compatible**: OpenAI (`gpt-4o`), **Ollama** (`http://localhost:11434/v1`), **DeepSeek** (`https://api.deepseek.com/v1`), OpenRouter, vLLM.
2. **Anthropic**: Claude API (`claude-3-7-sonnet`).

Gửi ping test kiểm tra kết nối ngay tại chỗ:
```bash
guard config test
```

---

## 🌐 Hỗ trợ 4 Miền Công Nghệ (FE, BE, Infra, MB)

`guard` tự động nhận diện domain của repository và áp dụng bộ kiểm tra tương ứng:

| Miền | Tech Stacks | Baseline Contracts & Invariants | Automated Verification |
| :--- | :--- | :--- | :--- |
| **FE** (Frontend) | React, Next.js, Vue, Tailwind, Svelte | UI states (`loading`, `disabled`), phím tắt (`Escape`, `Enter`), responsive layout | `pnpm run build` / `npm run build` |
| **BE** (Backend) | Go, Python (FastAPI/Django), NestJS, Rust | API JSON schema compatibility, SQLi prevention, Database transactions rollback | `pytest`, `go test ./...`, `cargo test` |
| **Infra** (DevOps) | Docker, Kubernetes, Terraform, Helm, CI/CD | Cấm hardcode secrets, cấm mở port nhạy cảm 0.0.0.0, zero-downtime healthcheck | `terraform validate`, `docker compose config` |
| **MB** (Mobile) | Flutter, React Native, iOS (Swift), Android | Hardware permission status, SafeArea notch padding, offline storage fallback | `flutter analyze`, `./gradlew test` |

---

## 📖 Hướng Dẫn Sử Dụng CLI

### 1. Cài đặt Hooks vào Repo mục tiêu (`guard hook`)
Đứng tại bất kỳ repo nào khác và gõ:
```bash
# Cài đặt cả Git hook và Agent wrapper
guard hook install

# Kiểm tra trạng thái hook
guard hook status

# Gỡ bỏ hook an toàn (tự động khôi phục hook cũ của bạn)
guard hook uninstall
```

### 2. Nhịp Pre-Task
Chạy trước khi dev hoặc AI Coding Agent can thiệp vào code:
```bash
guard pre "Chuyển nút checkout sang sticky ở bottom mobile, chỉnh CSS và responsive modal"
```
*Kết quả:* Phân tích rủi ro, khoá Invariants và xuất bản ghi `### 🔍 PRE-TASK IMPACT NOTE` vào `.guard/PRE_TASK_NOTE.md`.

### 3. Nhịp Post-Task
Chạy sau khi đã chỉnh sửa code xong:
```bash
guard post
```
*Kết quả:* Kiểm tra diff, phát hiện out-of-scope files, quét rules Alibaba OCR, chạy build test tự động, Laya chấm điểm Invariant và **LLM đưa ra phán quyết phê duyệt cuối cùng** (`APPROVED` hoặc `REVISE`) vào `.guard/POST_TASK_REPORT.md`.

### 4. Thực thi Kẹp Bánh Mì (Sandwich Pattern Wrapper)
Tự động chạy Pre $\rightarrow$ Chạy lệnh Agent $\rightarrow$ Tự động chạy Post trong 1 cú gõ:
```bash
guard run "Thêm endpoint tính phí vận chuyển" -- git status
```

### 5. Yêu cầu LLM Thẩm định Trực tiếp trên Diff
```bash
guard review
```

---

## 🧪 Chạy Test Suite

Dự án sở hữu bộ test toàn diện 36 tests bao phủ từ Unit tests đến End-to-End integration tests:

```bash
pytest
```
