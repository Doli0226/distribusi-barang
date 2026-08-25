# LogistiPro Indonesia — Sistem Distribusi Barang

## Problem Statement
Bangun Web-Based Distribution Management System (Sistem Distribusi Barang) profesional, modern, aman, scalable, responsive, dengan 2 role (Admin, User). Django MVT + React frontend + SQLite (dev). Modul: authentication, dashboard, manajemen barang/kategori/gudang/stok/penerima/kendaraan, workflow permintaan, distribusi & tracking timeline, notifikasi internal, laporan + export (PDF/Excel/CSV/Print), activity log/audit trail.

## Architecture
- **Backend**: Django 5.2 (ASGI via uvicorn di server.py) — port 8001
- **Frontend**: React (CRA) dengan React Router — port 3000
- **Database**: SQLite (path via env DB_NAME, default `test_database`)
- **Auth**: Session-based Django auth dengan cookie SameSite=None; Secure=True (cross-site preview)
- **CORS**: withCredentials true; regex-based origin whitelist
- **Modules**: `distribution` app (models, views, urls, migrations, management/commands/seed_demo.py)

## User Personas
- **Admin (Adi Rahman)**: Kelola master data, review & approve permintaan, buat distribusi, laporan.
- **User (Siti Rahma / Budi Santoso)**: Buat permintaan barang, pantau status distribusi.

## Test Credentials
- Admin: `admin@logistipro.id / admin123`
- User:  `user@logistipro.id / user123` dan `budi@logistipro.id / user123`

## Core Requirements (Static)
- Auth: login, logout, register, reset password, change password, profile
- Dashboard admin (stats + charts + activity) & user (stats miliknya)
- Master data: barang, kategori, gudang, stok (mutasi masuk/keluar/adjust), penerima, kendaraan, pengguna
- Workflow permintaan: pending → processed → approved → prepared → shipped → in_transit → arrived → completed. Rejected dengan alasan.
- Distribusi + timeline + kendaraan assignment
- Notifikasi internal + bell badge
- Activity log dengan IP
- Laporan + export CSV/Excel/PDF/Print

## Implemented (2026-08-25)
- ✅ Django backend penuh: 15+ endpoint (auth, dashboard, categories, products, warehouses, stocks, recipients, vehicles, users, requests, distributions, tracking, notifications, activities, reports+export)
- ✅ Seed demo (3 users, 4 kategori, 9 barang, 3 gudang + stok, 4 penerima, 4 kendaraan, 4 sample requests + 1 distribusi selesai)
- ✅ Frontend modular: 20+ pages (Login, Register, ResetPassword, Dashboard, Products, Categories, Warehouses, Stock, Recipients, Vehicles, Requests, RequestDetail, Distributions, DistributionDetail, Tracking, Notifications, Activities, Reports, Users, Profile)
- ✅ Layout: Sidebar (14 menu admin / 5 menu user), Topbar dengan bell notif live
- ✅ Role-based routing (AdminRoute redirects user to /dashboard)
- ✅ Bahasa Indonesia across UI
- ✅ Charts: bar (aktivitas distribusi 6 bulan), pie (kategori)
- ✅ Timeline tracking (permintaan + distribusi)
- ✅ Modal + Toast + Confirm + StatusBadge + EmptyState + Loading (reusable)
- ✅ Modal close via X, backdrop click, Escape
- ✅ Export PDF (reportlab), Excel (openpyxl), CSV (native)
- ✅ Activity log dengan IP address via HTTP_X_FORWARDED_FOR
- ✅ Atomic stock validation (select_for_update, retry-safe number generation via next_number())
- ✅ Distribution status transitions guard (no backwards)
- ✅ Global @catch_errors decorator (404 for DoesNotExist, 400 for KeyError/ValueError)

## Bug Fixes (2026-08-25)
- Fixed: Distribution number collision (max(id)+1 → next_number scanning existing numbers by year prefix)
- Fixed: `needed_date` / `estimated_arrival` string not converted → parse_date() coerces ISO string to date object
- Fixed: DoesNotExist and KeyError caused 500 HTML tracebacks → catch_errors decorator returns JSON
- Fixed: Admin notification fan-out (was only is_superuser) → now is_superuser|is_staff|profile.role=admin
- Fixed: Product deactivate one-way → added "Aktifkan" button
- Fixed: Profile page inputs unstyled outside .modal scope → added `.panel form label input` styling
- Fixed: Notification badge stale after "Tandai semua" from Notifications page → window event `notifs:refresh`
- Fixed: Modal ESC-close
- Fixed: `?ids=abc` on report export returned full dataset → now correctly returns empty
- Fixed: SQLite "database is locked" on concurrent writes → added WAL + busy_timeout=30s
- Fixed: Toast stack overlapping topbar bell badge → moved down 68px

## New Features (2026-08-25 iteration 4)
- ✅ Notifikasi realtime: polling 4s + toast otomatis untuk notifikasi baru
- ✅ Format cetak rapi: `@media print` menyembunyikan sidebar/topbar/tombol; header cetak dengan periode & timestamp
- ✅ Foto bukti kirim: Distribution.arrival_photo (base64 data URL), modal upload saat transisi ke "arrived", tampilan foto di detail
- ✅ Ekspor terpilih: checkbox di /permintaan (admin) + bulk export CSV/Excel/PDF via `?ids=1,2,3`

## New Features (2026-08-25 iteration 5)
- ✅ Notif Anti-Ganda: helper `notify(user, ..., actor=request.user)` mem-block self-notif. Diterapkan di requests, approve/reject, distributions, distribution status, dan manual run report schedule
- ✅ Jadwal Otomatis Laporan (Inbox Internal): model `ReportSchedule` (daily/weekly/monthly, day_of_month/day_of_week, next_run_at otomatis) + `GeneratedReport` (base64 content). Endpoint CRUD + `/run` (manual). Opportunistic scheduler jalan pada tiap GET /report-schedules. Frontend: halaman `/jadwal-laporan` (CRUD + Run Now + toggle aktif) dan `/inbox-laporan` (card list + Unduh). Notifikasi "Laporan siap diunduh" mengarah ke inbox
- ✅ Fixed: ReportSchedule/GeneratedReport DoesNotExist -> 404 via catch_errors

## Prioritized Backlog
### P1 (nice-to-have polish)
- Real MySQL/PostgreSQL migration for production
- Email/reset link (currently demo direct reset)
- Real-time tracking via websocket (currently polling 30s)
- Filter tanggal di /aktivitas
- Print CSS untuk /laporan agar rapi saat cetak

### P2 (future)
- Multi-warehouse per barang consolidation view
- Bulk actions (approve multiple, export selected)
- Kendaraan maintenance history
- Attachment/foto pada permintaan
- Push notification (browser Notification API)

## Directory Structure
```
/app
├── backend/
│   ├── config/                (Django settings)
│   ├── distribution/          (models, views, urls, migrations, management/commands)
│   ├── server.py              (ASGI entry - Django app)
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api.js
│       ├── App.js             (router shell)
│       ├── App.css / Extra.css / Mobile.css
│       ├── context/           (AuthContext, ToastContext)
│       ├── components/
│       │   ├── layout/        (Sidebar, Topbar)
│       │   └── ui/            (Modal, StatusBadge, EmptyState, Loading, Confirm)
│       ├── constants/         (status labels, helpers)
│       └── pages/             (20+ pages)
└── memory/
    ├── PRD.md
    └── test_credentials.md
```
