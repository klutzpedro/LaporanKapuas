"""AI summary generator using Claude Sonnet 4.5 via emergentintegrations.

Summarizes ALL data from the day (LID, KONTRA, GAL, MEDMON, GEOINT, PIKET),
not just news. Output should be compact and dense for executive consumption.
"""
import os
import logging
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger("bais.ai")

SYSTEM_PROMPT = (
    "Anda adalah analis intelijen strategis senior BAIS TNI. "
    "Tugas Anda menyusun EXECUTIVE SUMMARY harian yang ringkas, padat, dan langsung-pakai untuk pimpinan, "
    "dari laporan tim LID, KONTRA, GAL, MEDMON, GEOINT, dan PIKET. "
    "Output WAJIB dalam Bahasa Indonesia formal gaya laporan intelijen militer. "
    "Anda HARUS mengikuti template format yang diberikan secara PERSIS — sama persis label, urutan, tanda baca, "
    "dan struktur baris. JANGAN tambah heading bergaya markdown (##, **, dst). "
    "JANGAN tambah penomoran/bullet di luar yang sudah ditentukan. "
    "Tidak ada spekulasi; hanya fakta dari data yang diberikan. Hindari kata pengisi."
)


FORMAT_TEMPLATE_EXAMPLE = """\
RINGKASAN EKSEKUTIF:
Hari ini (DD/MM/YYYY) tercatat tiga titik tekanan domestik: ringkas isu utama dengan dampak strategis dalam 3-4 kalimat padat yang menjelaskan apa kejadian, apa risiko, dan apa yang harus diketahui pimpinan. Sebutkan ancaman hybrid bila ada. Berikan satu kalimat penutup yang memberi rekomendasi tinggi-level kepada pimpinan.

1. ACEH:
Satu paragraf 1-2 kalimat. Bila tidak ada data tulis persis: Tidak ada perkembangan signifikan terpantau periode ini.

2. JAKARTA:
Satu paragraf 1-2 kalimat tentang dinamika ibu kota (sentiment, demo, isu politik).

3. PAPUA:
Satu paragraf 2-3 kalimat. Wajib sebutkan total titik OPM termonitor & wilayah penyebaran bila ada data GEOINT.

4. INTERNASIONAL:
Satu paragraf 1-2 kalimat. Bila tidak ada tulis persis: Tidak ada perkembangan signifikan terpantau periode ini.

LID:
Satu paragraf 1-2 kalimat — berita trending paling penting hari ini & dampak strategisnya.

KONTRA:
Satu paragraf 1-2 kalimat — TO/profiling mencolok hari ini (sebutkan nama TO bila ada), sumber, dan tipe ancaman.

GAL:
Satu paragraf 1-2 kalimat — arahan konten galang & kategori dominan.

MEDMON:
1. Presiden: positif X%/negatif Y%/netral Z% — ringkasan singkat 1 kalimat.
2. Panglima TNI: positif X%/negatif Y%/netral Z% — ringkasan singkat 1 kalimat.
3. MBG: positif X%/negatif Y%/netral Z% — ringkasan singkat 1 kalimat.
4. Andrie Yunus: positif X%/negatif Y%/netral Z% — ringkasan singkat 1 kalimat.
5. Indonesia Gelap: positif X%/negatif Y%/netral Z% — ringkasan singkat 1 kalimat.

GEOINT:
Satu paragraf 1-2 kalimat — total titik OPM aktif, wilayah, dan zona operasi Kodam terkait.

PIKET:
Satu paragraf 1-2 kalimat — laporan ringkas Satgas Tek/Sandi/Medis bila ada.

REKOMENDASI:
Paragraf 1 — rekomendasi koordinasi/aksi prioritas pertama (1-2 kalimat).
Paragraf 2 — rekomendasi kedua (1-2 kalimat).
Paragraf 3 — rekomendasi ketiga (1-2 kalimat).
Paragraf 4 — rekomendasi keempat bila perlu (1-2 kalimat).
Paragraf 5 — rekomendasi kelima bila perlu (1-2 kalimat).
"""


def _format_payload(data: dict) -> str:
    rd = data.get("report_date")
    lines = [f"TANGGAL: {rd}", ""]

    lines.append("== LID (Berita Trending) ==")
    for it in data.get("lid", []):
        lines.append(
            f"- [{it.get('cog','').upper()}] {it.get('judul','')} | Fakta: {it.get('fakta','')[:180]} "
            f"| Analisa: {it.get('analisa','')[:200]} | Tindakan: {it.get('tindakan','')[:140]} "
            f"| Rekomendasi: {it.get('rekomendasi','')[:140]}"
        )

    lines.append("\n== KONTRA (Profiling TO) ==")
    for it in data.get("kontra", []):
        lines.append(
            f"- [{it.get('sumber','').upper()}/{it.get('tipe','')}] {it.get('nama_to','')} — "
            f"DataDiri: {it.get('data_diri','')[:180]} | Ket: {it.get('keterangan','')[:140]}"
        )

    lines.append("\n== GAL (Konten Galang) ==")
    for it in data.get("gal", []):
        lines.append(f"- [{it.get('kategori','').upper()}] {it.get('judul','')} | {it.get('keterangan','')[:140]}")

    lines.append("\n== MEDMON (Media Monitoring) ==")
    for it in data.get("medmon", []):
        pos = sum(1 for b in it.get("berita", []) if b.get("sentiment") == "positif")
        neg = sum(1 for b in it.get("berita", []) if b.get("sentiment") == "negatif")
        sp = it.get("sentiment_positif", 0)
        sn = it.get("sentiment_negatif", 0)
        snt = it.get("sentiment_netral", 0)
        lines.append(
            f"- SUBJEK: {it.get('subjek','')} | Sentiment: positif {sp}%, negatif {sn}%, netral {snt}% "
            f"| Berita +{pos}/-{neg} | "
            f"Analisa: {it.get('analisa','')[:220]} | Rekomendasi: {it.get('rekomendasi','')[:160]}"
        )

    lines.append("\n== GEOINT (Posisi OPM) ==")
    for it in data.get("geoint", []):
        lines.append(
            f"- {it.get('wilayah','')} | {it.get('nama_orang','')} | status: {it.get('status','')} "
            f"| lat={it.get('lat')}, lon={it.get('lon')} | Ket: {it.get('keterangan','')[:140]}"
        )

    lines.append("\n== PIKET (Satgas Tek/Sandi/Medis) ==")
    for it in data.get("piket", []):
        lines.append(f"- [{it.get('satgas','').upper()}] {it.get('judul','')}: {it.get('isi','')[:180]}")

    return "\n".join(lines)


async def generate_ai_summary(data: dict) -> str:
    """Generate executive summary. Provider chosen via env AI_PROVIDER:
    - 'ollama' (DEFAULT for production VPS) — calls local Ollama on
      http://127.0.0.1:11434. ZERO data leaves the server.
    - 'claude' — uses Anthropic via Emergent LLM key (data goes to Anthropic).
    - 'off' — no AI; returns a template message indicating to use the
      built-in fallback summary inside the PDF generator.
    """
    provider = (os.environ.get("AI_PROVIDER") or "ollama").lower().strip()
    rd = data.get("report_date", "unknown")
    user_text = _build_user_prompt(data)

    if provider == "off":
        return ""  # Empty string → PDF generator will use its built-in fallback

    if provider == "ollama":
        raw = await _generate_via_ollama(user_text, rd)
    else:
        # claude (default Emergent path)
        raw = await _generate_via_claude(user_text, rd)

    cleaned = _sanitize_output(raw)
    cleaned = _enforce_completeness(cleaned, data)
    return cleaned


def _enforce_completeness(text: str, data: dict) -> str:
    """Safety net: kalau AI lupa atau ter-truncate section penting,
    tambahkan fallback isi dari data mentah (lebih baik ada daripada hilang).
    """
    if not text or text.lstrip().startswith("[AI SUMMARY ERROR"):
        return text

    import re

    def has_section(label: str) -> tuple[bool, str]:
        """Return (exists, content_after_label_until_next_section)."""
        pattern = re.compile(rf"(?m)^{re.escape(label)}:\s*$")
        m = pattern.search(text)
        if not m:
            return (False, "")
        # Find next label
        rest = text[m.end():]
        next_m = re.search(r"(?m)^[A-Z0-9][A-Z0-9\.\s]*:\s*$", rest)
        body = rest[:next_m.start()] if next_m else rest
        return (True, body.strip())

    # ----- 1) MEDMON: pastikan SEMUA subjek tercantum -----
    medmon_items = data.get("medmon", [])
    if medmon_items:
        has, body = has_section("MEDMON")
        missing = []
        for it in medmon_items:
            subj = (it.get("subjek") or "").strip()
            if subj and subj.lower() not in body.lower():
                missing.append(it)
        if missing:
            extra_lines = []
            # Find starting number based on existing entries
            existing_nums = re.findall(r"(?m)^\s*(\d+)\.\s", body)
            start_n = (max(int(n) for n in existing_nums) + 1) if existing_nums else 1
            for i, it in enumerate(missing):
                subj = (it.get("subjek") or "").strip()
                sp = it.get("sentiment_positif", 0)
                sn = it.get("sentiment_negatif", 0)
                snt = it.get("sentiment_netral", 0)
                analisa = (it.get("analisa") or "").strip()
                short = analisa[:140] + ("..." if len(analisa) > 140 else "")
                if not short:
                    short = "data sentimen termonitor."
                extra_lines.append(
                    f"{start_n + i}. {subj}: positif {sp}%/negatif {sn}%/netral {snt}% — {short}"
                )
            text = _append_to_section(text, "MEDMON", "\n" + "\n".join(extra_lines))

    # ----- 2) PIKET: pastikan SEMUA satgas tercantum -----
    piket_items = data.get("piket", [])
    if piket_items:
        has, body = has_section("PIKET")
        # Group by satgas
        by_satgas: dict[str, list[str]] = {}
        for it in piket_items:
            sg = (it.get("satgas") or "").upper().strip()
            if sg:
                judul = (it.get("judul") or "").strip()
                isi = (it.get("isi") or "").strip()
                snippet = f"{judul}: {isi}" if isi else judul
                by_satgas.setdefault(sg, []).append(snippet[:160])
        missing_satgas = [
            sg for sg in by_satgas
            if not re.search(rf"\bsatgas\s+{re.escape(sg)}\b", body, re.IGNORECASE)
            and not re.search(rf"\b{re.escape(sg)}\b", body, re.IGNORECASE)
        ]
        if missing_satgas:
            chunks = []
            for sg in missing_satgas:
                items_text = "; ".join(by_satgas[sg][:2])
                chunks.append(f"Satgas {sg.title()} melaporkan {items_text}.")
            text = _append_to_section(text, "PIKET", " " + " ".join(chunks))

    # ----- 3) REKOMENDASI: pastikan minimal 4 paragraf -----
    has, body = has_section("REKOMENDASI")
    if not has or not body.strip() or len([p for p in body.split("\n\n") if p.strip()]) < 2:
        # Generate fallback rekomendasi dari data
        fallback = _fallback_rekomendasi(data)
        if has:
            text = _append_to_section(text, "REKOMENDASI", "\n\n" + fallback)
        else:
            text = text.rstrip() + "\n\nREKOMENDASI:\n" + fallback

    return text


def _append_to_section(text: str, label: str, addition: str) -> str:
    """Insert `addition` at the end of section `label` (before next section)."""
    import re
    pattern = re.compile(rf"(?m)^{re.escape(label)}:\s*$")
    m = pattern.search(text)
    if not m:
        return text.rstrip() + f"\n\n{label}:\n{addition.lstrip()}"
    rest = text[m.end():]
    next_m = re.search(r"(?m)^[A-Z0-9][A-Z0-9\.\s]*:\s*$", rest)
    if next_m:
        insert_pos = m.end() + next_m.start()
        return text[:insert_pos].rstrip() + "\n" + addition.lstrip() + "\n\n" + text[insert_pos:]
    return text.rstrip() + "\n" + addition.lstrip()


def _fallback_rekomendasi(data: dict) -> str:
    """Generate 4 rekomendasi standar berdasarkan ringkasan data."""
    paragraphs = []

    # Dari LID — rekomendasi mitigasi
    lid = data.get("lid", [])
    if lid:
        topik = (lid[0].get("judul") or "isu trending hari ini").strip()
        paragraphs.append(
            f"Koordinasi kementerian/lembaga terkait untuk memitigasi eskalasi {topik}, "
            "melalui sinkronisasi narasi resmi dan respons cepat terhadap potensi keresahan publik."
        )

    # Dari KONTRA — rekomendasi pengawasan
    kontra = data.get("kontra", [])
    if kontra:
        names = [k.get("nama_to", "").strip() for k in kontra if k.get("nama_to")][:3]
        names_str = ", ".join(names) if names else "TO yang teridentifikasi"
        paragraphs.append(
            f"Intensifkan pengawasan digital-fisik terhadap {names_str} untuk mendeteksi dini "
            "rencana aksi dan mengamankan agenda strategis nasional."
        )

    # Dari MEDMON — rekomendasi penanganan sentimen
    medmon = data.get("medmon", [])
    negatif_subj = [m.get("subjek") for m in medmon
                    if m.get("subjek") and (m.get("sentiment_negatif") or 0) > 30]
    if negatif_subj:
        paragraphs.append(
            f"Akselerasi publikasi capaian dan komunikasi strategis terkait {', '.join(negatif_subj[:3])} "
            "untuk menekan narasi negatif dan memulihkan kepercayaan publik."
        )

    # Dari GEOINT — rekomendasi keamanan wilayah
    geo = data.get("geoint", [])
    if geo:
        n_aktif = sum(1 for g in geo if str(g.get("status", "")).lower() == "aktif")
        paragraphs.append(
            f"Koordinasi Kodam wilayah Papua untuk memantau {n_aktif} titik OPM aktif "
            "dan mencegah konvergensi aktor bersenjata dengan aktivis struktural di zona pertambangan."
        )

    # Dari PIKET — rekomendasi keamanan siber
    piket = data.get("piket", [])
    if any((p.get("satgas") or "").lower() == "sandi" for p in piket):
        paragraphs.append(
            "Tingkatkan keamanan siber infrastruktur komunikasi pemerintah guna mengantisipasi "
            "teknik phishing dan eksploitasi aplikasi komunikasi terenkripsi."
        )

    if not paragraphs:
        paragraphs.append(
            "Lanjutkan monitoring rutin dan koordinasi antar tim untuk memastikan situasi tetap terkendali."
        )

    # Pastikan minimal 4 paragraf
    while len(paragraphs) < 4:
        paragraphs.append(
            "Lanjutkan koordinasi lintas satuan dan tingkatkan kewaspadaan operasional sesuai prioritas pimpinan."
        )

    return "\n\n".join(paragraphs)


# Standard section labels (urutan WAJIB)
_LABELS = [
    "RINGKASAN EKSEKUTIF",
    "1. ACEH", "2. JAKARTA", "3. PAPUA", "4. INTERNASIONAL",
    "LID", "KONTRA", "GAL", "MEDMON",
    "GEOINT", "PIKET", "REKOMENDASI",
]


def _sanitize_output(text: str) -> str:
    """Bersihkan output AI agar konsisten format baku:
    - Hapus markdown (#, **, _, ```).
    - Pastikan setiap label section ada di baris sendiri diakhiri ':' .
    - Pastikan ada baris kosong sebelum setiap label (kecuali label pertama).
    - Hilangkan preamble/explanatory text di awal sebelum 'RINGKASAN EKSEKUTIF'.
    """
    if not text:
        return text
    # Skip error message blocks (output dari _generate_via_ollama saat fail)
    if text.lstrip().startswith("[AI SUMMARY ERROR"):
        return text

    import re

    # 1) Hapus code fences & bold/italic markdown & heading hashes
    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = text.replace("```", "")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)         # **bold**
    text = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", text)  # *italic*
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)  # _italic_
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)  # # heading

    # 2) Skip preamble: cari label "RINGKASAN EKSEKUTIF" sebagai SECTION HEADER
    #    (harus all-caps & di awal baris, hindari match preamble lowercase)
    m = re.search(r"(?m)^[ \t]*RINGKASAN[ \t]+EKSEKUTIF[ \t]*:?[ \t]*$", text)
    if m:
        text = text[m.start():]

    # 3) Normalize label lines: setiap label canonical "LABEL:\n"
    #    Match HANYA jika label muncul sebagai section header (di awal baris,
    #    optional colon, optional whitespace, end of line atau diikuti newline)
    for label in _LABELS:
        pattern = re.compile(
            r"(?m)^[ \t]*" + re.escape(label) + r"[ \t]*:?[ \t]*$"
        )
        text = pattern.sub(f"\n{label}:", text, count=1)

    # 4) Cleanup excessive blank lines & trailing whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    text = "\n".join(line.rstrip() for line in text.split("\n"))

    return text


def _build_user_prompt(data: dict) -> str:
    """Build the prompt text. Shared between providers."""
    # Pre-compute checklist hints to force AI completeness
    medmon_subjects = [it.get("subjek", "").strip() for it in data.get("medmon", []) if it.get("subjek")]
    piket_satgas = sorted(set([(it.get("satgas") or "").upper().strip() for it in data.get("piket", []) if it.get("satgas")]))
    kontra_names = [it.get("nama_to", "").strip() for it in data.get("kontra", []) if it.get("nama_to")]
    geoint_total = len(data.get("geoint", []))
    geoint_aktif = sum(1 for it in data.get("geoint", []) if str(it.get("status", "")).lower() == "aktif")
    lid_count = len(data.get("lid", []))
    gal_count = len(data.get("gal", []))

    checklist = "=== CHECKLIST WAJIB DICANTUMKAN ===\n"
    checklist += f"- MEDMON: WAJIB sebutkan {len(medmon_subjects)} subjek SEMUA dengan sentimen %: "
    checklist += ", ".join(medmon_subjects) if medmon_subjects else "(tidak ada data)"
    checklist += "\n"
    checklist += f"- PIKET: WAJIB sebutkan SETIAP Satgas yang lapor ({len(piket_satgas)}): "
    checklist += ", ".join(piket_satgas) if piket_satgas else "(tidak ada data)"
    checklist += "\n"
    checklist += f"- KONTRA: WAJIB sebutkan nama TO ({len(kontra_names)}): "
    checklist += ", ".join(kontra_names) if kontra_names else "(tidak ada data)"
    checklist += "\n"
    checklist += f"- GEOINT: WAJIB sebutkan total {geoint_total} titik OPM (aktif {geoint_aktif})\n"
    checklist += f"- LID: {lid_count} berita | GAL: {gal_count} konten\n"
    checklist += "- REKOMENDASI: WAJIB minimal 4 PARAGRAF terpisah, masing-masing actionable.\n\n"

    return (
        "Susun EXECUTIVE SUMMARY harian untuk pimpinan BAIS TNI dengan mengikuti TEMPLATE FORMAT BAKU di bawah ini.\n\n"
        "=== ATURAN WAJIB ===\n"
        "1. Ikuti STRUKTUR, LABEL, dan URUTAN template PERSIS sama. JANGAN tambah/kurangi label.\n"
        "2. Setiap label (RINGKASAN EKSEKUTIF, 1. ACEH, 2. JAKARTA, 3. PAPUA, 4. INTERNASIONAL, "
        "LID, KONTRA, GAL, MEDMON, GEOINT, PIKET, REKOMENDASI) WAJIB ditulis di baris sendiri, "
        "diakhiri dengan tanda titik dua ':' .\n"
        "3. Isi konten dimulai pada baris BERIKUTNYA setelah label.\n"
        "4. JANGAN gunakan markdown (#, **, _, *, -). JANGAN bold/italic.\n"
        "5. Pada bagian MEDMON: WAJIB cantumkan SEMUA subjek tanpa kecuali (lihat checklist di bawah). "
        "Format: 'N. Nama: positif X,X%/negatif Y,Y%/netral Z,Z% — ringkasan 1 kalimat.'\n"
        "6. Pada bagian PIKET: WAJIB cantumkan SEMUA satgas yang melapor (Tek/Sandi/Medis), bukan hanya satu. "
        "Format: 'Satgas Tek ...; Satgas Sandi ...; Satgas Medis ...' atau paragraf yang menyebut tiap satgas.\n"
        "7. Pada bagian KONTRA: WAJIB cantumkan SEMUA nama TO yang ada di data.\n"
        "8. Pada bagian REKOMENDASI: WAJIB MINIMAL 4 paragraf terpisah, masing-masing 1-2 kalimat, "
        "action-oriented (verb di depan: 'Koordinasi...', 'Intensifkan...', 'Akselerasi...', 'Tingkatkan...'). "
        "Bukan bullet, bukan nomor — paragraf biasa dipisah baris kosong.\n"
        "9. Bila bagian COG (ACEH/JAKARTA/PAPUA/INTERNASIONAL) tidak ada data, tulis PERSIS: "
        "'Tidak ada perkembangan signifikan terpantau periode ini.'\n"
        "10. Output hanya teks bersih (plain text) — tidak ada penjelasan/komentar tambahan di luar format.\n"
        "11. Target panjang: 500-800 kata. JANGAN potong di tengah section.\n"
        "12. Bahasa Indonesia formal gaya laporan intelijen militer dengan analisa mendalam (bukan sekedar restate data).\n\n"
        + checklist +
        "=== TEMPLATE FORMAT BAKU ===\n"
        + FORMAT_TEMPLATE_EXAMPLE +
        "\n=== DATA HARI INI ===\n"
        + _format_payload(data) +
        "\n\nSekarang tulis EXECUTIVE SUMMARY LENGKAP mengikuti template & checklist di atas. "
        "Pastikan SEMUA item di checklist ter-cover. Mulai langsung dari 'RINGKASAN EKSEKUTIF:' tanpa preamble. "
        "JANGAN BERHENTI sebelum REKOMENDASI berisi minimal 4 paragraf."
    )


async def _generate_via_ollama(user_text: str, rd: str) -> str:
    """Call local Ollama (100% on-server, no external network).
    Default model: 'llama3.2:3b' (fast, ~2GB RAM). Override via OLLAMA_MODEL.
    """
    import httpx
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
    # Timeout besar karena CPU inference qwen2.5:7b bisa 60-300 detik per request
    timeout_s = float(os.environ.get("OLLAMA_TIMEOUT", "600"))
    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": user_text,
        "stream": False,
        "options": {
            "temperature": 0.2,          # Sedikit naik (0.15 terlalu kaku, AI jadi "malas")
            "top_p": 0.9,
            "repeat_penalty": 1.05,
            "num_ctx": 8192,             # Lebih besar untuk akomodasi checklist + data lengkap
            "num_predict": 4000,         # Lebih besar agar tidak ter-truncate (target 500-800 kata)
        },
    }
    try:
        timeout = httpx.Timeout(timeout_s, connect=10.0, read=timeout_s, write=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{host}/api/generate", json=payload)
            r.raise_for_status()
            body = r.json()
            text = str(body.get("response", "")).strip()
            if not text:
                logger.error(f"Ollama returned empty response. Body keys: {list(body.keys())}")
                return "[AI SUMMARY ERROR — Ollama mengembalikan respons kosong. Coba ulangi atau ganti model lebih kecil (qwen2.5:3b).]"
            return text
    except httpx.ReadTimeout:
        logger.error(f"Ollama TIMEOUT after {timeout_s}s (model={model}). Coba model lebih kecil.")
        return (
            f"[AI SUMMARY ERROR — Ollama timeout setelah {int(timeout_s)} detik dengan model '{model}'.]\n\n"
            "Coba salah satu solusi:\n"
            "1. Ganti ke model lebih kecil: edit backend/.env → OLLAMA_MODEL=qwen2.5:3b lalu restart bais-backend\n"
            "2. Tambah RAM/CPU VPS\n"
            "3. Tunggu beberapa menit lalu coba lagi (mungkin VPS sedang sibuk)"
        )
    except httpx.ConnectError as e:
        logger.exception(f"Ollama connect error (host={host})")
        return (
            f"[AI SUMMARY ERROR — Tidak dapat terhubung ke Ollama di {host}.]\n\n"
            f"Detail: {type(e).__name__}: {e}\n"
            "Periksa: sudo systemctl status ollama"
        )
    except Exception as e:
        err_type = type(e).__name__
        err_msg = str(e) if str(e) else "(no message)"
        logger.exception(f"Ollama summary failed (host={host}, model={model})")
        return (
            f"[AI SUMMARY ERROR — Ollama lokal tidak merespons: {err_type}: {err_msg}]\n\n"
            "Pastikan Ollama berjalan di VPS (sudo systemctl status ollama) "
            f"dan model '{model}' sudah ter-pull (ollama pull {model})."
        )


async def _generate_via_claude(user_text: str, rd: str) -> str:
    """Legacy: call Anthropic Claude via Emergent LLM key.
    NOTE: data will leave the VPS. Only use if AI_PROVIDER=claude explicitly.
    """
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return "[AI SUMMARY UNAVAILABLE] EMERGENT_LLM_KEY tidak tersedia."
    chat = LlmChat(
        api_key=api_key,
        session_id=f"bais-summary-{rd}",
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    try:
        resp = await chat.send_message(UserMessage(text=user_text))
        return str(resp).strip()
    except Exception as e:
        logger.exception("AI summary failed")
        return f"[AI SUMMARY ERROR] {e}"
