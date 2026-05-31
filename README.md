# AUTOM — Automated Unit Test Orchestration with Multi-agent

> Hệ thống tự động sinh, kiểm chứng và tối ưu hóa Unit Test cho dự án JavaScript/ReactJS bằng kiến trúc đa tác nhân LLM.

AUTOM phân tích mã nguồn, lập kế hoạch kiểm thử, sinh test case, tự động sửa lỗi (**Self-healing**), nâng cao độ phủ code theo chuẩn **SonarQube** và tiêu diệt các đột biến còn sống (**Mutation Testing**) — hoàn toàn tự động, không cần can thiệp thủ công.

---

## Mục lục

- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Phần 1 — Cài đặt AUTOM Engine](#phần-1--cài-đặt-autom-engine)
- [Phần 2 — Thiết lập dự án đích](#phần-2--thiết-lập-dự-án-đích)
- [Phần 3 — Hướng dẫn sử dụng CLI](#phần-3--hướng-dẫn-sử-dụng-cli)
- [Kết quả đầu ra](#kết-quả-đầu-ra)

---

## Kiến trúc hệ thống

AUTOM được tổ chức theo ba lớp phân tách rõ ràng:

```
AUTOM/
│
├── rules/                      # Lớp tri thức — System Prompt cho từng Agent
│   ├── prompt_analyzer.txt     # Analyst Agent — phân tích mã nguồn, lập test plan
│   ├── prompt_coder.txt        # Coder Agent — sinh mã unit test chuẩn Jest
│   ├── prompt_fixer.txt        # Fixer Agent — tự động sửa lỗi (Self-healing)
│   ├── prompt_coverage.txt     # Coverage Agent — tối ưu độ phủ theo SonarQube
│   └── prompt_mutation.txt     # Mutation Agent — tiêu diệt mutant còn sống (Stryker)
│
├── skills/                     # Lớp hành động — Công cụ thực thi cho Agent
│   ├── context_analyzer.py     # Đọc hiểu Tech Stack từ autef.config.json
│   ├── test_generation.py      # Lắp ráp và ghi file test từ LLM output
│   ├── test_execution.py       # Chạy lệnh Jest, thu thập stdout/stderr
│   ├── auto_fixing.py          # Điều phối vòng lặp tự sửa lỗi
│   ├── coverage_agent.py       # Tính toán điểm Branch/Line Coverage
│   ├── mutation_execution.py   # Kích hoạt và quản lý tiến trình Stryker
│   ├── mutation_refiner.py     # Trích xuất danh sách mutant sống sót từ JSON
│   └── file_utils.py           # Xử lý I/O, đọc/ghi/sao lưu file an toàn
│
├── workflows/                  # Lớp điều phối — Trung tâm điều khiển pipeline
│   └── autogen_pipeline.py     # Pipeline 13 bước — kết nối AutoGen & 5 LLM Agent
│
├── .env                        # API Keys (không được đẩy lên Git)
├── .gitignore
├── requirements.txt
└── README.md
```

### Luồng hoạt động

```
Source code (.js/.jsx)
        │
        ▼
  Analyst Agent ──────► test_plan.md
        │
        ▼
   Coder Agent ──────► *.test.js
        │
        ▼
   npx jest --coverage
        │
   ┌────┴─────┐
   │ Có lỗi?  │
   └────┬─────┘
     YES│                    NO
        ▼                    │
  Fixer Agent ◄──────────────┘
  (tự sửa lỗi)
        │
        ▼ (toàn bộ pass)
  Coverage Agent ──► bổ sung test case
        │
        ▼ (đạt ngưỡng 80%)
  Mutation Agent ──► tiêu diệt mutant
        │
        ▼
  Test suite hoàn chỉnh ✓
```

---

## Phần 1 — Cài đặt AUTOM Engine

### Bước 1.1 — Cài đặt Python dependencies

Mở Terminal tại thư mục gốc của AUTOM và chạy:

```bash
pip install -r requirements.txt
```

### Bước 1.2 — Thiết lập API Keys

Tạo file `.env` tại **thư mục gốc của AUTOM** (ngang hàng với `rules/` và `skills/`):

```env
GEMINI_API_KEY_1=your_api_key_here
GEMINI_API_KEY_2=your_api_key_here
# Có thể thêm nhiều key để hệ thống tự động xoay vòng (load balancing)
```

> ⚠️ File `.env` đã được thêm vào `.gitignore`. Không bao giờ đẩy file này lên Git.

---

## Phần 2 — Thiết lập dự án đích

Trước khi đưa một dự án ReactJS/Vite vào AUTOM, dự án đó **bắt buộc** phải được cài đặt môi trường kiểm thử tương ứng.

### Bước 2.1 — Cài đặt thư viện NPM

Mở Terminal tại **thư mục gốc của dự án Frontend** và chạy:

```bash
npm install -D jest babel-jest jest-environment-jsdom identity-obj-proxy \
  @testing-library/react @testing-library/jest-dom \
  @babel/preset-env @babel/preset-react \
  @stryker-mutator/core @stryker-mutator/jest-runner
```

### Bước 2.2 — Tạo các file cấu hình

> ⚠️ Bước này cực kỳ quan trọng với các dự án dùng ES Modules (ESM).

Tạo 3 file sau tại **thư mục gốc của dự án Frontend**:

#### `babel.config.cjs`

```js
module.exports = {
  presets: [
    ['@babel/preset-env', { targets: { node: 'current' }, modules: false }],
    ['@babel/preset-react', { runtime: 'automatic' }]
  ],
};
```

#### `jest.setup.js`

```js
import { TextEncoder, TextDecoder } from 'util';
import '@testing-library/jest-dom';

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

if (typeof global.import === 'undefined') {
  global.import = {
    meta: {
      env: {
        VITE_API_URL: '',
        MODE: 'test'
      }
    }
  };
}
```

#### `jest.config.cjs`

```js
module.exports = {
  testEnvironment: "jest-environment-jsdom",
  extensionsToTreatAsEsm: [".jsx"],
  transform: {
    "^.+\\.[t|j]sx?$": "babel-jest"
  },
  moduleNameMapper: {
    '^react$': '<rootDir>/node_modules/react',
    '^react-dom$': '<rootDir>/node_modules/react-dom',
    "\\.(css|less|scss|sass)$": "identity-obj-proxy",
    "^@/(.*)$": "<rootDir>/src/$1"
  },
  setupFilesAfterEnv: ["<rootDir>/jest.setup.js"],
  testPathIgnorePatterns: ["/node_modules/"],
  coveragePathIgnorePatterns: ["/node_modules/", "/.stryker-tmp/"],
};
```

> 📝 File `stryker.conf.json` **không cần tạo thủ công** — AUTOM tự động sinh và quản lý file này.

### Bước 2.3 — Tạo file cấu hình AUTOM

Tạo file `autef.config.json` tại **thư mục gốc của dự án đích**. File này giúp các Agent AI hiểu đúng Tech Stack và quy ước của dự án:

```json
{
  "MODULE_SYSTEM": "ES Modules (ESM) thuần",
  "PROJECT_STRUCTURE": "Monorepo, các file ở src",
  "TEST_FRAMEWORK": "Jest v30.3.0 (chạy với --experimental-vm-modules)",
  "UI_TESTING_LIBRARY": "React Testing Library v16.3.2",
  "STATE_MANAGEMENT_LIBRARY": "Zustand v5.0.2",
  "PROJECT_SPECIFIC_RULES": [
    "JEST MOCKING: BẮT BUỘC dùng jest.unstable_mockModule() ở TRÊN CÙNG file và nạp module bằng await import(). TUYỆT ĐỐI CẤM dùng jest.mock() hoặc require().",
    "ZUSTAND TESTING: BẮT BUỘC test state trực tiếp bằng Vanilla JS thông qua API .getState() của store.",
    "REACT ROUTER: BẮT BUỘC dùng <MemoryRouter>. CẤM dùng thư viện history."
  ]
}
```

---

## Phần 3 — Hướng dẫn sử dụng CLI

Mở Terminal tại **thư mục gốc của AUTOM** và dùng cú pháp sau:

```bash
python autogen_pipeline.py -p <Đường_Dẫn_Dự_Án> [Tùy chọn]
```

### Các lệnh thực tế

**Kiểm thử một hoặc nhiều file cụ thể** *(khuyên dùng)*

```bash
python autogen_pipeline.py -p "C:/my-react-app" -f "src/pages/AdminPage.jsx" "src/stores/useCartStore.js"
```

**Kiểm thử toàn bộ một thư mục**

```bash
python autogen_pipeline.py -p "C:/my-react-app" -d "src/stores"
```

**Kiểm thử toàn bộ dự án (Full-scan)**

```bash
python autogen_pipeline.py -p "C:/my-react-app" --all
```

> ⚠️ Full-scan sẽ tốn nhiều thời gian và token API. Nên dùng `-f` hoặc `-d` cho từng module.

---

## Kết quả đầu ra

Sau mỗi lần chạy, hệ thống tự động tạo thư mục `autef_outputs_global/run_YYYYMMDD_HHMMSS/` nằm **ngang hàng với thư mục dự án đích**:

```
autef_outputs_global/
└── run_20250531_143022/
    ├── test_plans/         # Kế hoạch kiểm thử do Analyst Agent lập
    ├── test_scripts/       # File test hoàn chỉnh đã vượt qua Quality Gates
    ├── execution_logs/     # Lịch sử giao tiếp giữa các Agent
    └── reports/
        ├── coverage/       # Báo cáo độ phủ (SonarQube)
        └── mutation/       # Báo cáo đột biến (Stryker)
```

| Thư mục | Nội dung |
|---|---|
| `test_plans/` | File `.md` chứa kịch bản kiểm thử do Analyst Agent sinh ra |
| `test_scripts/` | File `.test.js` / `.test.jsx` đã pass toàn bộ Jest |
| `execution_logs/` | Log thực thi từng bước của pipeline |
| `reports/coverage/` | Báo cáo HTML + JSON từ Jest/Istanbul |
| `reports/mutation/` | Báo cáo HTML + JSON từ Stryker Mutator |

---

## Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| Google Gemini API Key | Bắt buộc |

---

## Giấy phép

MIT License — Tự do sử dụng, chỉnh sửa và phân phối.