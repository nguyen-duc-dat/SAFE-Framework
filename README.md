# AUTEF — Automated Unit Testing & Enhancement Framework

AUTEF là một hệ thống kiểm thử tự động hóa đa dự án (**Multi-Project Framework**) được thiết kế theo kiến trúc **Micro-agent** bằng LLM. Hệ thống tự động phân tích mã nguồn, sinh Test Case, tự động gỡ lỗi (**Self-healing**), nâng điểm phủ code (**Coverage**) theo chuẩn SonarQube và tiêu diệt các kịch bản đột biến (**Mutation Testing**) hoàn toàn tự động.

---

## Mục lục

- [Phần 1 — Cài đặt hệ thống lõi (AUTEF Engine)](#phần-1--cài-đặt-hệ-thống-lõi-autef-engine)
- [Phần 2 — Thiết lập dự án đích (Target Project)](#phần-2--thiết-lập-dự-án-đích-target-project)
- [Phần 3 — Hướng dẫn sử dụng CLI](#phần-3--hướng-dẫn-sử-dụng-cli)

---

## Phần 1 — Cài đặt hệ thống lõi (AUTEF Engine)

### Bước 1.1: Cài đặt Python Dependencies

Mở Terminal tại thư mục chứa AUTEF và chạy:

```bash
pip install -r requirements.txt
```

### Bước 1.2: Thiết lập API Keys

Tạo file `.env` tại **thư mục gốc** của hệ thống AUTEF (ngang hàng với thư mục `skills` và `rules`), sau đó điền các khóa API của Google Gemini:

```env
GEMINI_API_KEY_1=your_api_key_here
GEMINI_API_KEY_2=your_api_key_here
# Có thể thêm nhiều key để hệ thống tự động xoay vòng (Load balancing)
```

---

## Phần 2 — Thiết lập dự án đích (Target Project)

Trước khi đưa một dự án Frontend (ví dụ: ReactJS/Vite) vào AUTEF, dự án đó **bắt buộc** phải được cài đặt môi trường kiểm thử tương ứng.

### Bước 2.1: Cài đặt thư viện (NPM)

Mở Terminal tại thư mục gốc của dự án Frontend và chạy:

```bash
npm install -D jest babel-jest jest-environment-jsdom identity-obj-proxy \
  @testing-library/react @testing-library/jest-dom \
  @babel/preset-env @babel/preset-react \
  @stryker-mutator/core @stryker-mutator/jest-runner
```

### Bước 2.2: Cấu hình môi trường

> ⚠️ **Cực kỳ quan trọng** cho các dự án sử dụng ES Modules (ESM).

Tạo 3 file cấu hình sau tại **thư mục gốc** của dự án Frontend:

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

> 📝 **Lưu ý:** File `stryker.conf.json` **không cần tạo thủ công**. AUTEF sẽ tự động sinh và quản lý file này trong quá trình quét.

### Bước 2.3: Tạo file cấu hình AUTEF

Tạo file `autef.config.json` tại **thư mục gốc** của dự án đích. Đây là nơi định nghĩa luật lệ và Tech Stack để hệ thống AI hiểu về dự án của bạn:

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

Sau khi hoàn tất cài đặt, mở Terminal từ **thư mục hệ thống AUTEF** và sử dụng CLI theo cú pháp sau:

```bash
python autogen_pipeline.py -p <Đường_Dẫn_Dự_Án> [Các Tùy Chọn]
```

### Các lệnh thực tế

#### Kiểm thử một hoặc nhiều file cụ thể *(khuyên dùng)*

Dùng cờ `-f` kèm đường dẫn tương đối tới file bên trong dự án đích:

```bash
python autogen_pipeline.py -p "C:/my-react-app" -f "src/pages/AdminPage.jsx" "src/components/Button.jsx"
```

#### Kiểm thử toàn bộ một thư mục

Dùng cờ `-d` để đệ quy toàn bộ file `.js`, `.jsx` trong một thư mục cụ thể:

```bash
python autogen_pipeline.py -p "C:/my-react-app" -d "src/stores"
```

#### Kiểm thử toàn bộ dự án (Full-scan)

Dùng cờ `--all` để hệ thống tự động quét toàn bộ thư mục `src`:

```bash
python autogen_pipeline.py -p "C:/my-react-app" --all
```

> ⚠️ **Lưu ý:** Quá trình Full-scan sẽ tốn nhiều thời gian và token.

### Thư mục Artifacts (Đầu ra)

Sau khi hệ thống hoàn tất, toàn bộ kết quả sẽ được tự động lưu tại thư mục **`autef_outputs_global`** nằm ngang hàng với thư mục dự án của bạn, bao gồm:

| Loại file | Mô tả |
|---|---|
| Test Plans | Kế hoạch kiểm thử được AI sinh ra |
| Logs | Nhật ký quá trình chạy |
| File Test | Các file test `.test.js` / `.test.jsx` |
| Báo cáo Coverage | Báo cáo độ phủ code chuẩn SonarQube |
| Báo cáo Mutation | Kết quả kiểm thử đột biến từ Stryker |