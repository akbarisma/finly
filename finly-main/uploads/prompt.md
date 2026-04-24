# PROMPT — Financial Analyst App (Full-Stack + LSTM ML Integration)

---

## KONTEKS PROYEK

Bangun aplikasi **Financial Analyst** full-stack untuk startup dan SMEs. Stack utama:
- **Frontend**: React + Tailwind CSS (Single Page Application)
- **Backend API**: PHP (Laravel atau plain PHP dengan PDO)
- **Database**: MySQL
- **ML Service**: Python Flask (`ml_api.py`) — sudah tersedia, hanya perlu diintegrasikan
- **Model ML**: LSTM Keras (`LSTM_model.keras`) — sudah dilatih, prediksi sales harian

Aplikasi ini memiliki **7 modul utama**: Autentikasi (Sign Up / Login), Dashboard, Pencatatan Transaksi, Budgeting, Detail Transaksi, Prediksi ML, dan History Prediksi.

---

## ARSITEKTUR SISTEM

```
React Frontend  ←→  PHP Backend API  ←→  MySQL DB
                          ↓
                   Python Flask ML API (port 5000)
                          ↓
                   LSTM_model.keras + lstm_scaler.pkl
```

### Aturan komunikasi:
- React memanggil PHP via REST API (JSON)
- PHP memanggil Flask ML API via `curl` atau `file_get_contents` saat prediksi diminta
- Flask ML API hanya berjalan di `localhost:5000` (tidak diakses langsung dari React)

---

## SKEMA DATABASE (MySQL)

```sql
-- Tabel user (autentikasi)
CREATE TABLE users (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  email      VARCHAR(255) NOT NULL UNIQUE,
  password   VARCHAR(255) NOT NULL,        -- bcrypt hash, JANGAN simpan plain text
  name       VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel sesi login (token-based, stateless JWT atau server-side token)
CREATE TABLE sessions (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  token      VARCHAR(64) NOT NULL UNIQUE,  -- random_bytes(32) di-hex
  expires_at DATETIME NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabel transaksi income
CREATE TABLE transactions (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,               -- FK ke users, data terisolasi per user
  type         ENUM('income', 'outcome') NOT NULL,
  category     VARCHAR(100) NOT NULL,
  amount       DECIMAL(15,2) NOT NULL,
  description  TEXT,
  date         DATE NOT NULL,
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabel budget bulanan
CREATE TABLE budgets (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL,
  month      DATE NOT NULL,                -- format: YYYY-MM-01
  category   VARCHAR(100) NOT NULL,
  amount     DECIMAL(15,2) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user_month_cat (user_id, month, category),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Tabel history prediksi ML
CREATE TABLE prediction_history (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  user_id         INT NOT NULL,
  predicted_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  n_days          INT NOT NULL,
  month_target    VARCHAR(7) NOT NULL,     -- contoh: "2025-05"
  total_predicted DECIMAL(15,2) NOT NULL,
  avg_daily       DECIMAL(15,2) NOT NULL,
  min_daily       DECIMAL(15,2) NOT NULL,
  max_daily       DECIMAL(15,2) NOT NULL,
  detail_json     LONGTEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

---

## MODUL 0 — AUTENTIKASI (SIGN UP & LOGIN)

### Alur lengkap:
1. User baru membuka aplikasi → diarahkan ke halaman **Sign Up**
2. User mengisi form Sign Up (email + password + konfirmasi password) → submit → akun dibuat → **redirect otomatis ke halaman Login** dengan pesan sukses
3. User mengisi form Login (email + password) → submit → token session disimpan di `localStorage` → redirect ke **Dashboard**
4. Setiap request ke API yang butuh autentikasi wajib menyertakan header `Authorization: Bearer <token>`
5. Tombol **Logout** di sidebar → hapus token dari `localStorage` → redirect ke Login

---

### HALAMAN SIGN UP

**URL**: `/signup`

**Form fields**:
- Email: `<input type="email">` — wajib, validasi format email
- Password: `<input type="password">` — wajib, minimal 8 karakter
- Konfirmasi Password: `<input type="password">` — harus sama persis dengan Password

**Validasi client-side (tampil inline, bukan alert)**:
- Email wajib diisi & format valid
- Password minimal 8 karakter
- Konfirmasi password harus cocok
- Semua field wajib diisi sebelum tombol "Daftar" bisa diklik

**Setelah submit berhasil**:
- Tampilkan pesan: _"Akun berhasil dibuat! Silakan login."_
- Redirect ke halaman Login setelah 1.5 detik (atau langsung)

**Link di bawah form**: _"Sudah punya akun? Login di sini"_ → navigasi ke `/login`

---

### HALAMAN LOGIN

**URL**: `/login`

**Form fields**:
- Email: `<input type="email">`
- Password: `<input type="password">`
- Tombol "Masuk"

**Validasi**:
- Email & password tidak boleh kosong
- Tampilkan error inline jika kredensial salah: _"Email atau password salah."_

**Setelah login berhasil**:
- Simpan token ke `localStorage` dengan key `auth_token`
- Simpan data user (id, email, name) ke `localStorage` dengan key `user_data`
- Redirect ke Dashboard

**Link di bawah form**: _"Belum punya akun? Daftar di sini"_ → navigasi ke `/signup`

---

### API ENDPOINTS AUTENTIKASI (PHP)

```
POST /api/auth/register.php
Body: { email, password, name? }

Validasi server:
- Email format valid (filter_var)
- Email belum terdaftar (cek ke tabel users)
- Password minimal 8 karakter
- Hash password dengan password_hash($password, PASSWORD_BCRYPT)

Response sukses (201):
{ "success": true, "message": "Akun berhasil dibuat" }

Response error (400/409):
{ "success": false, "message": "Email sudah terdaftar" }
{ "success": false, "message": "Password minimal 8 karakter" }
```

```
POST /api/auth/login.php
Body: { email, password }

Logika server:
1. Cari user by email di tabel users
2. Verifikasi password: password_verify($password, $hashed)
3. Jika valid: buat token = bin2hex(random_bytes(32))
4. Simpan ke tabel sessions: (user_id, token, expires_at = NOW() + 7 hari)
5. Return token + data user

Response sukses (200):
{
  "success": true,
  "token": "abc123...",
  "user": { "id": 1, "email": "user@example.com", "name": "Budi" }
}

Response error (401):
{ "success": false, "message": "Email atau password salah" }
```

```
POST /api/auth/logout.php
Header: Authorization: Bearer <token>

Logika: Hapus baris session dari tabel sessions berdasarkan token
Response: { "success": true }
```

---

### MIDDLEWARE AUTENTIKASI PHP (auth_middleware.php)

Buat file `backend/config/auth_middleware.php` yang dipanggil di SETIAP endpoint API yang membutuhkan login:

```php
<?php
// backend/config/auth_middleware.php
function requireAuth($pdo) {
    $headers = getallheaders();
    $authHeader = $headers['Authorization'] ?? $headers['authorization'] ?? '';

    if (!preg_match('/Bearer\s+(.+)/i', $authHeader, $matches)) {
        http_response_code(401);
        echo json_encode(['error' => true, 'message' => 'Unauthorized: Token tidak ditemukan']);
        exit;
    }

    $token = trim($matches[1]);

    $stmt = $pdo->prepare("
        SELECT s.user_id, u.email, u.name
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND s.expires_at > NOW()
    ");
    $stmt->execute([$token]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$user) {
        http_response_code(401);
        echo json_encode(['error' => true, 'message' => 'Unauthorized: Token tidak valid atau sudah kedaluwarsa']);
        exit;
    }

    return $user; // return ['user_id' => ..., 'email' => ..., 'name' => ...]
}
```

**Cara pakai di setiap endpoint** (contoh di `dashboard.php`):
```php
require_once '../config/auth_middleware.php';
$authUser = requireAuth($pdo);
$user_id = $authUser['user_id'];
// Gunakan $user_id untuk filter semua query DB
```

---

### ISOLASI DATA PER USER

**WAJIB**: Semua query database di modul Dashboard, Transaksi, Budgeting, Detail Transaksi, Prediksi, dan History Prediksi HARUS menambahkan filter `WHERE user_id = $user_id`. Contoh:

```sql
-- BENAR ✓
SELECT * FROM transactions WHERE user_id = ? AND date >= ?

-- SALAH ✗ (data bocor antar user)
SELECT * FROM transactions WHERE date >= ?
```

---

### ROUTE PROTECTION DI REACT

Buat komponen `ProtectedRoute` yang membungkus semua halaman yang butuh login:

```jsx
// src/components/ProtectedRoute.jsx
import { Navigate } from 'react-router-dom';

export function ProtectedRoute({ children }) {
  const token = localStorage.getItem('auth_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
```

**Routing di App.jsx**:
```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Halaman publik */}
        <Route path="/login"  element={<LoginPage />} />
        <Route path="/signup" element={<SignUpPage />} />

        {/* Halaman yang butuh login */}
        <Route path="/" element={
          <ProtectedRoute>
            <Layout /> {/* Layout mengandung Sidebar + outlet */}
          </ProtectedRoute>
        }>
          <Route index            element={<Dashboard />} />
          <Route path="transaksi" element={<TransactionForm />} />
          <Route path="budgeting" element={<Budgeting />} />
          <Route path="detail"    element={<DetailTransaksi />} />
          <Route path="prediksi"  element={<Prediction />} />
          <Route path="history"   element={<PredictionHistory />} />
        </Route>

        {/* Redirect default */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

---

### UPDATE services/api.js — Tambahkan token di semua request

```javascript
const BASE_URL = 'http://localhost/backend/api';

// Helper: tambahkan Authorization header otomatis
const authHeaders = () => ({
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${localStorage.getItem('auth_token') || ''}`
});

// Helper: handle 401 → logout otomatis
const handleResponse = async (res) => {
  if (res.status === 401) {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
    window.location.href = '/login';
    return;
  }
  return res.json();
};

export const api = {
  // AUTH (tidak butuh token)
  register:  (data) => fetch(`${BASE_URL}/auth/register.php`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(r => r.json()),
  login:     (data) => fetch(`${BASE_URL}/auth/login.php`,    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(r => r.json()),
  logout:    ()     => fetch(`${BASE_URL}/auth/logout.php`,   { method: 'POST', headers: authHeaders() }).then(r => r.json()),

  // DATA (butuh token — semua pakai authHeaders)
  getDashboard:         (month)    => fetch(`${BASE_URL}/dashboard.php?month=${month}`, { headers: authHeaders() }).then(handleResponse),
  getTransactions:      (params)   => fetch(`${BASE_URL}/transactions.php?${new URLSearchParams(params)}`, { headers: authHeaders() }).then(handleResponse),
  addTransaction:       (data)     => fetch(`${BASE_URL}/transactions.php`, { method: 'POST', headers: authHeaders(), body: JSON.stringify(data) }).then(handleResponse),
  deleteTransaction:    (id)       => fetch(`${BASE_URL}/transactions.php?id=${id}`, { method: 'DELETE', headers: authHeaders() }).then(handleResponse),
  getBudgets:           (month)    => fetch(`${BASE_URL}/budgets.php?month=${month}`, { headers: authHeaders() }).then(handleResponse),
  saveBudgets:          (data)     => fetch(`${BASE_URL}/budgets.php`, { method: 'POST', headers: authHeaders(), body: JSON.stringify(data) }).then(handleResponse),
  predict:              (n_days)   => fetch(`${BASE_URL}/predict.php`, { method: 'POST', headers: authHeaders(), body: JSON.stringify({ n_days }) }).then(handleResponse),
  getPredictionHistory: (page = 1) => fetch(`${BASE_URL}/prediction_history.php?page=${page}`, { headers: authHeaders() }).then(handleResponse),
  getPredictionDetail:  (id)       => fetch(`${BASE_URL}/prediction_history.php?id=${id}`, { headers: authHeaders() }).then(handleResponse),
};
```

---

### SIDEBAR — Tampilkan info user + tombol logout

```jsx
// Di Sidebar.jsx
const userData = JSON.parse(localStorage.getItem('user_data') || '{}');

const handleLogout = async () => {
  await api.logout();
  localStorage.removeItem('auth_token');
  localStorage.removeItem('user_data');
  navigate('/login');
};

// Di JSX sidebar:
<div className="user-info">
  <span>{userData.name || userData.email}</span>
  <button onClick={handleLogout}>Logout</button>
</div>
```

---

## MODUL 1 — DASHBOARD


### Tampilan:
- Header: nama bulan + tahun yang sedang berjalan (otomatis)
- **4 KPI Cards**:
  1. **Total Revenue** bulan ini (SUM income WHERE date di bulan ini)
  2. **Total Pengeluaran** bulan ini (SUM outcome WHERE date di bulan ini + SUM budget bulan ini)
  3. **Profit / Loss** = Revenue − (Pengeluaran outcome + Total Budget)
  4. **Jumlah Transaksi** bulan ini
- **Chart Line/Bar**: pemasukan vs pengeluaran per hari dalam bulan berjalan
- Indikator Profit berwarna: hijau jika positif, merah jika negatif

### API endpoint (PHP):
```
GET /api/dashboard?month=YYYY-MM
Response:
{
  "revenue": 15000000,
  "outcome": 8000000,
  "budget_total": 3000000,
  "profit_loss": 4000000,
  "transaction_count": 42,
  "daily_chart": [
    { "date": "2025-05-01", "income": 500000, "outcome": 200000 },
    ...
  ]
}
```

### Formula Profit & Loss:
```
profit_loss = total_revenue - (total_outcome + total_budget_bulan_ini)
```

---

## MODUL 2 — PENCATATAN TRANSAKSI

### Fitur form input:
- **Jenis transaksi**: toggle antara `income` / `outcome`
- **Kategori**: dropdown (contoh income: Penjualan, Jasa, Lainnya; outcome: Operasional, Marketing, Gaji, Lainnya)
- **Nominal**: input angka dengan format Rupiah otomatis (gunakan `Intl.NumberFormat`)
- **Deskripsi**: textarea opsional
- **Tanggal**: `<input type="date">` — **default diisi otomatis dengan hari ini**, tapi user **dapat mengubah manual**

### Validasi:
- Nominal harus > 0
- Tanggal tidak boleh kosong
- Kategori wajib dipilih
- Tampilkan pesan error inline (bukan alert browser)

### API endpoints (PHP):
```
POST /api/transactions
Body: { type, category, amount, description, date }
Response: { success: true, id: 123 }

GET /api/transactions?month=YYYY-MM&type=income|outcome|all&page=1&limit=20
Response: { data: [...], total: 100, page: 1 }

DELETE /api/transactions/{id}
Response: { success: true }
```

---

## MODUL 3 — BUDGETING

### Fitur:
- Input budget per kategori untuk **awal bulan tertentu**
- Pilih bulan via `<input type="month">`
- Tambah baris kategori dinamis (tombol "+ Tambah Kategori")
- Tampilkan total budget yang sudah diinput untuk bulan tersebut
- Tampilkan perbandingan: Budget vs Realisasi Pengeluaran (outcome aktual bulan tersebut)

### Tampilan tabel:
| Kategori | Budget | Realisasi | Selisih | Status |
|----------|--------|-----------|---------|--------|

Status: hijau (dalam budget) / merah (over budget)

### API endpoints (PHP):
```
GET /api/budgets?month=YYYY-MM
Response: { budgets: [...], total_budget: 5000000, total_realisasi: 3200000 }

POST /api/budgets
Body: { month, items: [{ category, amount }] }
Response: { success: true }

PUT /api/budgets/{id}
Body: { amount }
Response: { success: true }
```

---

## MODUL 4 — DETAIL TRANSAKSI

### Fitur:
- Tabel semua transaksi dengan filter:
  - Filter bulan/tahun
  - Filter tipe (income/outcome/semua)
  - Filter kategori
  - Search deskripsi
- Pagination (20 per halaman)
- Setiap baris: tanggal, jenis, kategori, nominal (format Rp), deskripsi, tombol hapus
- Export ke CSV (opsional tapi direkomendasikan)

### Tampilan summary di atas tabel:
- Total income hasil filter
- Total outcome hasil filter
- Net (income - outcome)

### API: gunakan endpoint `GET /api/transactions` dari Modul 2 dengan query params tambahan.

---

## MODUL 5 — PREDIKSI ML

### Alur prediksi:
1. User memilih **jumlah hari prediksi** (slider: 7, 14, 30, atau custom 1–90)
2. User klik "Prediksi Sekarang"
3. React POST ke PHP → PHP kirim ke Flask ML API
4. Flask ML API menggunakan LSTM model + data transaksi income user sebagai konteks tambahan
5. Hasil dikembalikan ke React → tampilkan chart + tabel + ringkasan
6. PHP **otomatis simpan** hasil prediksi ke tabel `prediction_history`

### Payload dari PHP ke Flask:
```json
{
  "n_days": 30,
  "transactions": [
    { "tanggal": "2025-04-15", "nominal": 2500000 },
    { "tanggal": "2025-04-16", "nominal": 1800000 }
  ]
}
```
> Ambil transaksi income 90 hari terakhir dari database untuk dikirim ke Flask.

### Tampilan hasil:
- **Ringkasan**: Total prediksi, Rata-rata harian, Min, Max
- **Line chart**: prediksi penjualan per hari
- **Tabel detail**: Tanggal | Hari | Prediksi (Rp)
- Tombol: "Simpan ke History" (atau auto-simpan)

### PHP endpoint:
```
POST /api/predict
Body: { n_days: 30 }
→ PHP ambil transaksi income 90 hari dari DB
→ PHP POST ke http://localhost:5000/forecast
→ PHP simpan ke prediction_history
→ Response: { predictions: [...], summary: {...} }
```

### Penanganan error:
- Jika Flask tidak aktif: tampilkan pesan "ML Service sedang tidak tersedia. Pastikan server Python aktif."
- Jika data transaksi kosong: tampilkan warning "Data transaksi terbatas, prediksi mungkin kurang akurat"

---

## MODUL 6 — HISTORY PREDIKSI

### Tampilan:
- Daftar semua prediksi yang pernah dibuat (dari tabel `prediction_history`)
- Urutkan: terbaru di atas
- Setiap item menampilkan:
  - Tanggal prediksi dibuat
  - Target bulan prediksi
  - Jumlah hari diprediksi
  - Total & rata-rata prediksi
  - Tombol "Lihat Detail"
- Modal/drawer saat "Lihat Detail": tampilkan chart + tabel prediksi harian dari `detail_json`

### API endpoint (PHP):
```
GET /api/prediction-history?page=1&limit=10
Response: { data: [...], total: 25 }

GET /api/prediction-history/{id}
Response: { ...record, detail_json: [...] }
```

---

## STRUKTUR FOLDER PROYEK

```
/project-root
├── frontend/                   # React app
│   ├── src/
│   │   ├── components/
│   │   │   ├── auth/
│   │   │   │   ├── LoginPage.jsx
│   │   │   │   └── SignUpPage.jsx
│   │   │   ├── ProtectedRoute.jsx
│   │   │   ├── Layout.jsx           # Sidebar + <Outlet />
│   │   │   ├── Dashboard.jsx
│   │   │   ├── TransactionForm.jsx
│   │   │   ├── TransactionList.jsx
│   │   │   ├── Budgeting.jsx
│   │   │   ├── DetailTransaksi.jsx
│   │   │   ├── Prediction.jsx
│   │   │   ├── PredictionHistory.jsx
│   │   │   └── Sidebar.jsx
│   │   ├── services/
│   │   │   └── api.js           # semua fetch ke PHP backend
│   │   └── App.jsx
│   └── package.json
│
├── backend/                    # PHP API
│   ├── config/
│   │   ├── db.php              # koneksi MySQL (PDO)
│   │   └── auth_middleware.php # fungsi requireAuth()
│   ├── api/
│   │   ├── auth/
│   │   │   ├── register.php    # POST signup
│   │   │   ├── login.php       # POST login → buat session token
│   │   │   └── logout.php      # POST logout → hapus session token
│   │   ├── dashboard.php
│   │   ├── transactions.php
│   │   ├── budgets.php
│   │   ├── predict.php         # proxy ke Flask
│   │   └── prediction_history.php
│   └── .htaccess               # URL routing
│
├── ml_service/                 # Python Flask
│   ├── ml_api.py               # Flask server (sudah ada)
│   ├── models/
│   │   ├── LSTM_model.keras    # model sudah dilatih
│   │   └── lstm_scaler.pkl
│   └── requirements.txt
│
└── database/
    └── schema.sql              # CREATE TABLE statements (termasuk users & sessions)
```

---

## DETAIL IMPLEMENTASI PHP (backend/api/predict.php)

```php
<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200); exit;
}

require_once '../../config/db.php';
require_once '../../config/auth_middleware.php';

// Wajib login — ambil user_id dari token
$authUser = requireAuth($pdo);
$user_id  = $authUser['user_id'];

$body   = json_decode(file_get_contents('php://input'), true);
$n_days = intval($body['n_days'] ?? 30);
$n_days = max(1, min(90, $n_days));

// Ambil transaksi income 90 hari terakhir milik user ini saja
$stmt = $pdo->prepare("
    SELECT date as tanggal, amount as nominal
    FROM transactions
    WHERE user_id = ? AND type = 'income'
      AND date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
    ORDER BY date ASC
");
$stmt->execute([$user_id]);
$transactions = $stmt->fetchAll(PDO::FETCH_ASSOC);

// Kirim ke Flask ML API
$payload = json_encode([
    'n_days'       => $n_days,
    'transactions' => $transactions
]);

$ch = curl_init('http://localhost:5000/forecast');
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST           => true,
    CURLOPT_POSTFIELDS     => $payload,
    CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
    CURLOPT_TIMEOUT        => 60,
]);
$result     = curl_exec($ch);
$http_code  = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curl_error = curl_error($ch);
curl_close($ch);

if ($curl_error || $http_code !== 200) {
    http_response_code(503);
    echo json_encode([
        'error'   => true,
        'message' => 'ML Service tidak tersedia. Pastikan server Python aktif di port 5000.'
    ]);
    exit;
}

$ml_data = json_decode($result, true);
if (!$ml_data || $ml_data['status'] !== 'success') {
    http_response_code(500);
    echo json_encode(['error' => true, 'message' => 'Prediksi gagal: ' . ($ml_data['message'] ?? 'unknown')]);
    exit;
}

// Simpan ke prediction_history
$summary     = $ml_data['ringkasan'];
$detail_json = json_encode($ml_data['predictions']);
$month_target = date('Y-m', strtotime($ml_data['predictions'][0]['tanggal']));

$ins = $pdo->prepare("
    INSERT INTO prediction_history
        (user_id, n_days, month_target, total_predicted, avg_daily, min_daily, max_daily, detail_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
");
$ins->execute([
    $user_id,
    $n_days,
    $month_target,
    $summary['total'],
    $summary['rata_rata'],
    $summary['minimum'],
    $summary['maksimum'],
    $detail_json
]);

echo json_encode([
    'success'     => true,
    'predictions' => $ml_data['predictions'],
    'summary'     => $summary
]);
```

---

## DETAIL IMPLEMENTASI REACT (komponen kunci)

### TransactionForm.jsx — Tanggal dinamis:
```jsx
const [date, setDate] = useState(() => new Date().toISOString().split('T')[0]); // default hari ini

<input
  type="date"
  value={date}
  onChange={e => setDate(e.target.value)}
  max={new Date().toISOString().split('T')[0]}  // opsional: batasi max = hari ini
/>
```

### Format Rupiah helper:
```javascript
export const formatRupiah = (amount) =>
  new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR', minimumFractionDigits: 0 }).format(amount);
```

---

## ATURAN KODING WAJIB (ANTI-BUG)

### PHP:
1. **Selalu gunakan PDO prepared statements** — jangan pernah string concat SQL
2. **Selalu validasi input**: cek `isset()`, cast ke tipe yang benar (`intval`, `floatval`, `trim`)
3. **Wrap semua DB operation dalam try-catch**, return JSON error jika gagal
4. **Set header CORS** di setiap file API — tambahkan `Authorization` di `Access-Control-Allow-Headers`
5. **Handle OPTIONS preflight** di setiap endpoint
6. Koneksi DB di `config/db.php` dengan `PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION`
7. **Password WAJIB di-hash** dengan `password_hash($pass, PASSWORD_BCRYPT)` — jangan simpan plain text
8. **Verifikasi password** hanya dengan `password_verify()` — jangan pakai `md5` atau `sha1`
9. **Setiap endpoint data** (bukan auth) wajib memanggil `requireAuth($pdo)` di baris pertama setelah header
10. **Semua query data** wajib filter `WHERE user_id = $user_id` — tidak boleh ada query tanpa filter user

### React:
1. **Semua state async** (fetch) harus memiliki: loading state, error state, data state
2. **Jangan manipulasi DOM langsung** — selalu lewat state/useState
3. **useEffect cleanup**: batalkan fetch jika komponen unmount (gunakan AbortController)
4. **Input tanggal** harus selalu punya default value `new Date().toISOString().split('T')[0]`
5. **Form validation** dilakukan sebelum submit, tampilkan error inline bukan `alert()`
6. **Angka dari API** selalu di-parse dengan `Number()` atau `parseFloat()` sebelum dihitung
7. **Format Rupiah** konsisten menggunakan `Intl.NumberFormat` — jangan manual format
8. **Token disimpan di localStorage** dengan key `auth_token` — jangan simpan di state (hilang saat refresh)
9. **Jika API return 401**: hapus `auth_token` dari localStorage dan redirect ke `/login` secara otomatis (sudah ada di `handleResponse` di `api.js`)
10. **ProtectedRoute** membungkus SEMUA route yang butuh login — halaman `/login` dan `/signup` tidak dibungkus

### Flask ML API (`ml_api.py`):
1. Sudah ada — **jangan ubah logika model**
2. Pastikan path `MODEL_PATH` dan `RAW_DATA_PATH` benar di environment deployment
3. Jalankan dengan: `python ml_api.py` sebelum menggunakan fitur prediksi
4. Test health: `GET http://localhost:5000/health` → harus return `{"status": "ok"}`

---

## EDGE CASES YANG HARUS DITANGANI

| Skenario | Penanganan |
|---|---|
| Email sudah terdaftar saat Sign Up | PHP return 409, React tampilkan "Email sudah terdaftar" |
| Password konfirmasi tidak cocok | Validasi client-side sebelum submit, tampil error inline |
| Login dengan email/password salah | PHP return 401, React tampilkan "Email atau password salah" |
| Token kedaluwarsa (lebih dari 7 hari) | API return 401, `handleResponse` di api.js auto-redirect ke /login |
| User akses URL protected tanpa login | `ProtectedRoute` redirect ke /login langsung |
| Flask ML API mati | PHP return 503, React tampilkan banner error merah |
| Tidak ada transaksi income di DB | Kirim array kosong ke Flask, tampilkan warning di UI |
| Prediksi untuk bulan yang sudah ada di history | Tetap simpan (bukan update), history bisa memiliki multiple prediksi per bulan |
| Budget bulan belum diisi | Dashboard tetap berjalan, kolom budget dihitung 0 |
| Pengguna input nominal dengan koma/titik | Strip karakter non-digit sebelum kirim ke API |
| Delete transaksi yang mempengaruhi budget tracking | Hanya hapus transaksi, tidak hapus budget |

---

## PANDUAN DEPLOYMENT LOKAL

```bash
# 1. Database
mysql -u root -p < database/schema.sql

# 2. Backend PHP
# Letakkan folder backend/ di htdocs (XAMPP) atau www (WAMP)
# Akses: http://localhost/backend/api/

# 3. ML Service Python
cd ml_service/
pip install flask flask-cors tensorflow pandas numpy scikit-learn
python ml_api.py
# Verifikasi: curl http://localhost:5000/health

# 4. Frontend React
cd frontend/
npm install
npm start
# Akses: http://localhost:3000
```

---

## CHECKLIST FINAL SEBELUM DELIVERY

- [ ] Halaman Sign Up: form berjalan, validasi inline, redirect ke Login setelah sukses
- [ ] Halaman Login: form berjalan, token tersimpan di localStorage, redirect ke Dashboard
- [ ] ProtectedRoute: semua halaman app tidak bisa diakses tanpa token
- [ ] Token expired / invalid → auto-redirect ke Login
- [ ] Tombol Logout: hapus token + user_data dari localStorage, redirect ke Login
- [ ] Semua query DB difilter `WHERE user_id = ?` — data tidak bocor antar user
- [ ] Password di-hash bcrypt, tidak ada plain text di database
- [ ] Dashboard menampilkan data bulan berjalan secara real-time
- [ ] Form transaksi: tanggal default = hari ini, bisa diubah manual
- [ ] P&L formula benar: Revenue - (Outcome + Budget)
- [ ] Budgeting: bisa input per kategori, tampil vs realisasi
- [ ] Detail transaksi: filter, search, pagination berjalan
- [ ] Prediksi ML: PHP proxy ke Flask berfungsi, error handling ada
- [ ] History prediksi: tersimpan di DB, bisa dilihat detail
- [ ] Semua input divalidasi (client + server side)
- [ ] Format Rupiah konsisten di seluruh aplikasi
- [ ] Responsive UI (minimal desktop + tablet)
- [ ] Tidak ada `console.error` yang tidak ditangani di production
