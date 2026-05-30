# PRD — BAIS Summary Geospasika

## Problem Statement
Aplikasi internal BAIS TNI / Satgas Kapuas untuk mengumpulkan input harian dari 6 tim (LID, KONTRA, GAL, MEDMON, GEOINT, PIKET), mengolahnya berdasar 4 Center of Gravity (Aceh, Jakarta, Papua, Internasional), dan menghasilkan output final berupa **infografis + summary** dalam PDF maksimal 2 halaman untuk pimpinan.

## User Personas
- **Admin** — superuser; akses semua fitur; manajemen user; generate PDF.
- **Piket** — input data satgas TEK/SANDI/MEDIS + generate PDF (jam 12 WIB rule).
- **Tim LID** — input 4 berita trending (3 COG + 1 Internasional).
- **Tim Kontra** — input profiling TO Satgas / TO Internal.
- **Tim GAL** — input konten narasi/video/medsos.
- **Tim Medmon** — input media monitoring (Presiden / Panglima TNI / MBG / lainnya).
- **Tim Geoint** — input posisi OPM (lat/lon).

## Core Requirements
1. JWT-based auth dengan role mapping per tim.
2. Form input harian khusus per tim.
3. Dashboard "Control Room" — KPI strip + 4 panel COG + ringkasan kontra/geoint.
4. Aturan 12:00 WIB: generate hari ini hanya valid setelah jam 12; sebelum itu sistem otomatis menarik H-1.
5. AI Summary (Claude Sonnet 4.5 via Emergent LLM key) menyusun narasi terstruktur per COG.
6. PDF 2 halaman: Hal 1 = infografis (KPI + 4 panel COG); Hal 2 = narasi + MEDMON + KONTRA + tabel GEOINT.
7. Image storage: base64 di MongoDB.
8. Map Leaflet (CARTO dark) untuk visualisasi OPM.

## Tech Stack
- Backend: FastAPI + Motor (MongoDB) + bcrypt + PyJWT + reportlab + emergentintegrations
- Frontend: React 19 + Tailwind + Shadcn UI + Phosphor icons + Leaflet + Sonner toasts

## What's Implemented (2026-02)
- Auth (login, me, logout, register admin-only, list users)
- 7 seeded users (admin + 6 team roles)
- CRUD endpoints untuk semua 6 tim
- Aggregation endpoint /api/daily + /api/daily/info dengan WIB rule
- AI summary (POST/GET /api/summary/ai) — returns 502 jika gagal, hanya cache pada sukses
- PDF endpoint /api/pdf dengan enforcement jam 12 WIB
- Login page tactical (split panel) + 7 quick-login buttons
- Dashboard "Control Room" (KPI + 4 panel COG + kontra/geoint preview)
- 6 form pages dengan upload base64 manual
- Map view Leaflet untuk Geoint
- Admin user management page
- Sidebar role-aware navigation
- Collapsible sidebar (localStorage persisted)
- Rich-text AI summary editor (TipTap) + PDF history archive
- Inline PDF preview on history page
- **Edit/Update CRUD on all 6 team report lists (PUT endpoints + pencil-icon UI)** — 2026-02
- **PDF cleanup (2026-02)**: removed "AI · CLAUDE SONNET 4.5 · EDITABLE" kicker, removed KPI count strip (LID/KONTRA/GAL/...), auto-rendered Papua map with OPM coords plotted (replaces user-uploaded peta_image), cleaned overlap labels in MEDMON/KONTRA sections
- **PDF Page 2 restructure (2026-02)**: 5 stacked sections — LID → PROFILING (TIM KONTRA) → KONTEN / NARASI / MEME (TIM GAL, full-width thumbnails) → MEDMON → GEOINT. PIKET section removed from PDF entirely
- **Logo BAIS + multi-page detail PDF (2026-02)**: Logo Waskita Satya Nirbhaya di pojok kiri atas (login, sidebar, semua halaman PDF). PDF auto-paginate ke 3+ halaman dengan card detail penuh per item LID (FAKTA/ANALISA/TINDAKAN/REKOMENDASI + link + sentiment image), KONTRA (data diri + LINK MEDIA SOSIAL semua URL + SNA + Lainnya), GAL (kategori + judul + semua LINK KONTEN + keterangan + gambar)
- **Sentiment Auto Pie Chart (2026-02)**: LID & GEOINT form pakai input 3 persen (positif/negatif/netral), validation total harus 100%. Live SVG pie preview di form. PDF generate pie chart otomatis (ReportLab native, no extra deps). Page 1 PDF tambah "RINGKASAN SENTIMENT PER KASUS" — list semua case dengan mini pie chart per kasus. Gambar sentiment manual dihapus dari LID
- **VPS Self-Hosted Deployment (2026-05)**: Aplikasi production di VPS 187.77.115.220 (Ubuntu 22.04). Stack: Python 3.11 venv + uvicorn workers 2, MongoDB 7, Nginx reverse proxy, Supervisor. Script `deploy.sh` di root repo untuk redeploy. JWT_SECRET auto-generated. Seed users idempotent (race-safe upsert) untuk multi-worker

## Test Results (iteration_1)
- Backend: 30/31 PASS — 1 failure adalah Emergent LLM budget exceeded (bukan code bug).
- Setelah fix: AI summary endpoint sekarang return 502 saat upstream error dan tidak meng-cache error.

## Backlog (P1)
- Histori laporan per tanggal (date picker pada dashboard & summary page)
- Multi-user collaborative editing flag (lock per item per tim per tanggal)
- Export Excel per tim
- Notifikasi reminder 11:30 WIB ke tim yang belum setor

## Backlog (P2)
- Audit trail (siapa ubah/hapus apa)
- 2FA untuk admin
- Auto-archive ke object storage setelah 30 hari
- Auto-generate PDF + email distribute jam 12:30 WIB
- Map kluster + heatmap density OPM
