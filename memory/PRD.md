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
- **Sentiment Decimal/Comma Input Fix (2026-05)**: `SentimentInput.jsx` sekarang punya local string state per-row sehingga user bisa mengetik nilai desimal pakai koma (mis. `44,38` / `30,12` / `25,5`) tanpa nilai loncat ke 100 atau koma terpotong. Visual-verified via screenshot tool.
- **Remove LID Sentiment + Cutoff 12:00→09:00 WIB (2026-05)**: (1) **LID sentiment removed**: Hapus sentiment_positif/negatif/netral dari `LidIn` model + 3 field dari `EMPTY` state TimLid + `SentimentInput` import + validation di submit() + draw_sentiment_pie di `_draw_lid_card`/`_measure_lid_card` + LID dari "RINGKASAN SENTIMENT PER KASUS" strip (sekarang hanya MEDMON). (2) **Cutoff hour 12→09 WIB**: Sentralisasi konstanta `CUTOFF_HOUR_WIB=9` di backend; semua `dtime(12,0)` hardcoded diganti `dtime(CUTOFF_HOUR_WIB, CUTOFF_MINUTE_WIB)` di `today_wib_date_str`, `report_date_for_generation`, dan PDF guard di `/api/pdf`. `/daily/info` sekarang return `cutoff_hour`/`cutoff_minute` + `before_cutoff` field (plus `before_noon` legacy alias). Frontend `usePeriod` baca cutoff dari API, periodLabel pakai cutoff dinamis "DD MMM YYYY 09:00 — DD MMM YYYY 09:00 WIB". Dashboard & Summary page banner pakai cutoff dinamis. **Hasilnya**: setiap jam 09:01 WIB, semua form team auto-reset ke "today" baru, data kemarin tersimpan di History.
- **GAL Kategori MEDSOS → MEME + MEDMON Indented Numbered List (2026-05)**: (1) Tim GAL pilihan kategori diganti `medsos` → `meme`. Backend `GalIn` punya `field_validator` yang coerce legacy "medsos" → "meme"; startup migration auto-update existing `gal_reports` rows. Frontend dropdown sekarang NARASI/VIDEO/MEME, label di list pakai `normalizeKategori()`. PDF color mapping & section title diupdate (MEME purple). Subheader page `Narasi · Video · Meme`. (2) MEDMON di executive summary PDF sekarang tampil sebagai NUMBERED LIST per-subjek (`1. Presiden: ...`, `2. Panglima TNI: ...`, dst) yang **menjorok ke dalam** sama level dengan COG (indent 6mm). Implementasi: prompt AI diubah format inline → numbered multi-line, regex `medmon_prefix_re` di `html_to_paragraphs` auto-apply indent ke paragraf yang awalannya `\d+\. <subjek>:`.
- **PDF Page-1 Enhancement (2026-05)**: (1) Tambah **TREN SENTIMENT POSITIF 7 HARI TERAKHIR (MEDMON)** — multi-line chart native ReportLab (tanpa matplotlib), 1 garis per subjek MEDMON (Presiden/Panglima TNI/MBG/dll) menampilkan % positif selama 7 hari ke belakang. Ditempatkan ANTARA Executive Summary & Sentiment Per Kasus. Backend helper `collect_medmon_7day_trend(rd)` query 7 hari di `medmon_reports` & union semua subjek. (2) Tabel **GEOINT · POSISI OPM** sekarang punya kolom **KOORDINAT** baru (lat/lon 4-decimal) antara NAMA dan STATUS. Visual-verified via Gemini PDF analyzer (95% confidence).
- **Executive Summary PDF Layout Refinement (2026-05)**: (1) COG list `1. ACEH / 2. JAKARTA / 3. PAPUA / 4. INTERNASIONAL` sekarang **menjorok ke dalam** (indent 6mm) via deteksi regex di `html_to_paragraphs`. (2) AI prompt direvisi: LID, KONTRA, GAL, MEDMON, GEOINT, PIKET masing-masing PARAGRAF TERPISAH (sebelumnya KONTRA+GAL digabung, LID malah hilang). (3) MEDMON sekarang ENUMERATE setiap subjek (Presiden, Panglima TNI, MBG, dll) dengan persentase sentimen per-subjek (positif/negatif/netral). Max kata naik 320→380 untuk akomodasi enumerasi MEDMON. Payload AI juga diperluas dengan field sentiment_positif/negatif/netral mentah biar AI bisa kutip persentase akurat.
- **Blank-Page Bug Fix (2026-05)**: Root cause = `toast.error(e.response?.data?.detail)` mengoper ARRAY of objects (Pydantic 422 response) ke Sonner toast → React melempar "Objects are not valid as a React child" → seluruh halaman blank putih. Fix: tambah helper `apiErrorMsg(err, fallback)` di `lib/api.js` yang selalu return string (handle string/array/object/null), dan ganti SEMUA 13 unsafe `toast.error(detail)` di TimLid/TimKontra/TimGal/TimMedmon/TimGeoint/Piket/AdminUsers/Summary/History. Tambah `<ErrorBoundary>` di root `App.js` sebagai safety-net agar kalau ada React error tak terduga, user lihat halaman "Coba Lagi" instead of blank.

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
