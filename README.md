"""
# Laya OCR Guard (`guard`)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Architecture](https://img.shields.io/badge/architecture-Dual--Gate-green.svg)](#kiến-trúc-3-trụ-cột)

**Dual-Gate Impact Analysis & Regression Guard for AI-Assisted Development.**

`guard` kết hợp sức mạnh của 3 thành phần:
1. **Laya** (System 1 fast reflex triage, <30ms, 0-cost, 0 token)
2. **Alibaba Open Code Review - OCR** (Deterministic git diff blast-radius & static rules, 0-cost)
3. **LLM được bạn add vào** (Claude, GPT-4o, DeepSeek, Ollama...): Đóng vai trò Bộ não Phân tích & **Chốt chặn cuối cùng (Final Safety Gate)**.

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
│ • Project Health Check: Chạy build & test tự động           │
│ • Laya Scoring (0đ): Chấm điểm tuân thủ Invariants (Yes/No) │
│ ➔ Tổng hợp dữ liệu thành "### 🧪 POST-TASK VERIFICATION"   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. CHỐT CHẶN CUỐI CÙNG: LLM ĐƯỢC BẠN ADD VÀO                │
│ (Claude-3.7-Sonnet / GPT-4o / DeepSeek / Ollama...)         │
│ • LLM chỉ cần đọc bản nghiệm thu tóm tắt từ Bước 2          │
│ • Thẩm định Kỹ thuật (Kiến trúc, Memory Leak, Scope breach) │
│ • Công thái học UX/UI & Trải nghiệm đa nền tảng             │
│ • Phê duyệt: [APPROVED] hoặc [REVISE] kèm Remediation Steps │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Cài đặt & Khởi động

```bash
# Cài đặt guard
git clone https://github.com/your-org/laya-ocr-guard.git
cd laya-ocr-guard
pip install -e .

# Kiểm tra chẩn đoán hệ thống
guard doctor
```

---

## ⚙️ Cấu hình LLM & Alibaba OCR (Interactive Wizard)

Chỉ cần cấu hình một lần duy nhất, `guard` sẽ tự động kết nối và đồng bộ sang CLI của Alibaba Open Code Review (`ocr`):

```bash
guard config llm
```

Hệ thống dẫn dắt theo chuẩn 2 giao thức tinh gọn:
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

### 1. Nhịp Pre-Task
Chạy trước khi dev hoặc AI Coding Agent can thiệp vào code:
```bash
guard pre "Chuyển nút checkout sang sticky ở bottom mobile, chỉnh CSS và responsive modal"
```
*Kết quả:* Phân tích rủi ro, khoá Invariants và xuất bản ghi `### 🔍 PRE-TASK IMPACT NOTE` vào `.guard/PRE_TASK_NOTE.md`.

### 2. Nhịp Post-Task
Chạy sau khi đã chỉnh sửa code xong:
```bash
guard post
```
*Kết quả:* Kiểm tra diff, phát hiện out-of-scope files, quét rules Alibaba OCR, chạy build test tự động, Laya chấm điểm Invariant và **LLM đưa ra phán quyết phê duyệt cuối cùng** (`APPROVED` hoặc `REVISE`) vào `.guard/POST_TASK_REPORT.md`.

### 3. Thực thi Kẹp Bánh Mì (Sandwich Pattern Wrapper)
Tự động chạy Pre $\rightarrow$ Chạy lệnh Agent $\rightarrow$ Tự động chạy Post:
```bash
guard run "Thêm endpoint tính phí vận chuyển" -- git status
```

### 4. Cài đặt Hooks vào Repo khác (`guard hook`)
Đứng tại bất kỳ repo nào khác và gõ:
```bash
# Cài đặt cả Git hook và Agent wrapper
guard hook install

# Kiểm tra trạng thái hook
guard hook status

# Gỡ bỏ hook an toàn (tự động khôi phục hook cũ của bạn)
guard hook uninstall
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
"""[1:]
