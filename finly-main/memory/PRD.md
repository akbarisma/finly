# Finly — Financial Analyst (PRD)

## Problem Statement
Refactor Finly app yang dikirim via zip: perbaiki 18 bug dari `bug_report_finly.md` (3 Critical, 5 High, 6 Medium, 4 Low) + rapikan UI yang sedikit berantakan.

## Architecture
- Backend: FastAPI 0.110 + Motor/MongoDB, LSTM forecast (Keras), prefixed `/api`
- Frontend: React 19, React Router 7, Tailwind + Recharts + Phosphor icons, brutalist design

## What's been implemented (2026-04-24)
All 18 bugs patched:
- **Critical**: BUG-01 dashboard P&L single source (`total_expense`+`profit_loss`), BUG-02 stale-token purge, BUG-03 `formatDateID` TZ-safe parsing.
- **High**: BUG-04 month validation 422, BUG-05 ProtectedRoute user_data check, BUG-06 Budgeting refresh-after-delete, BUG-07 ML history padding, BUG-08 exportCSV fetch-all.
- **Medium**: BUG-09 ConfirmDialog everywhere (removed `window.confirm` from TransactionForm/Detail/Budgeting/PredictionHistory), BUG-10 actual last-day-of-month ticker, BUG-11/12/13 error handling on loads & deletes, BUG-14 CORS middleware ordering.
- **Low**: BUG-15 `lifespan` context, BUG-16 `stripDigits` 15-digit cap, BUG-17 MongoDB indexes on startup, BUG-18 `useCallback` pattern.

## UI polish
- "Rp" prefix overlap fixed (`pl-12` + bolder colour) on TransactionForm & Budgeting capital input.
- Budgeting error banner (testid=`budget-load-error`), PredictionHistory toast/error banners.

## Backend test coverage
12/12 bug-fix tests pass (`/app/backend/tests/test_bug_fixes.py`) + existing 27 tests still green.

## Known small items (not blockers)
- `expires_at_dt` TTL index created but stored `expires_at` is ISO string (proactive purge in `current_user` handles it).
- Dashboard P&L formula includes budget plan (per bug-report spec); product may revisit.

## Next Action Items
- Optional product review of P&L formula (budget plan vs actuals).
- Optional: stable testid on Dashboard ticker for automated period assertions.

## Iteration 5 — Export PDF Laporan Bulanan (2026-04-24)
- New feature: button **Export PDF** di Dashboard hero (testid `dashboard-export-pdf`).
- Client-side PDF generation via `jspdf` + `jspdf-autotable` — no backend changes needed.
- PDF isi: header Finly + periode + user, 4 KPI cards, rincian pengeluaran (Outcome/Anggaran/Modal Awal), bar chart arus harian, bar chart top kategori, tabel Anggaran vs Realisasi, tabel semua transaksi, section Modal Awal, footer dengan page number.
- File: `/app/frontend/src/services/pdfExport.js` (365 lines, focused).
- Testing: iteration_5.json 100% pass (PDF valid, download works via Playwright `expect_download`, content verified with pdfplumber).

## Iteration 4 — UI overlap final fix (2026-04-24)
- **"Rp" prefix overlap permanently solved**: replaced absolute-positioned prefix with flex-based `.money-group` (prefix + input as physical siblings separated by 2px border). Applied to TransactionForm.jsx nominal input and Budgeting.jsx monthly-capital input. Zero overlap structurally guaranteed regardless of value length / viewport.
- **Page-hero stripe overlap fixed**: `.page-hero` now reserves right padding (8.5rem desktop / 4.5rem mobile) + `.page-hero > *` gets `position:relative; z-index:1`, so headings and month pickers never get painted under the diagonal stripe pseudo-element.
- **Dashboard KPI formula verified**: `Total Pengeluaran` uses backend `data.total_expense` (= outcome + budget_total + monthly_capital) and `Laba/Rugi` uses `data.profit_loss` — Modal Awal ikut terhitung.
- Testing: iteration_4.json 100% pass (backend 3/3 pytest + frontend visual at 1440 & 390 viewports).

## Iteration 3 — Code review clean-up (2026-04-24)
Real issues fixed:
- Empty catch blocks in TransactionForm + Layout → now console.error for visibility
- Unstable list keys → PredictionHistory detail table (key=p.tanggal), Prediction forecast table (key=p.tanggal), Budgeting server rows (key=b.category), Budgeting editor rows (stable client uid on addRow), ConfirmDialog (key=`${r.label}-${i}`)
- `loadRecent` wrapped in useCallback + useEffect dep fixed in TransactionForm

Intentionally NOT changed (false positives / out-of-scope per guidelines):
- `is None` / `is not None` are correct PEP-8 (reviewer confused None with literal)
- `b` in `sum(b["amount"] for b in budgets)` is a generator variable, not an undefined name
- Hardcoded "secrets" flagged were literally email regex and a test password
- localStorage for auth tokens is standard SPA pattern; moving to httpOnly cookies requires full arch change (not requested)
- Component complexity: user asked not to refactor beyond what's required
