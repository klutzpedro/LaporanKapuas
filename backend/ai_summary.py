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

    return _sanitize_output(raw)


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
    return (
        "Susun EXECUTIVE SUMMARY harian untuk pimpinan BAIS TNI dengan mengikuti TEMPLATE FORMAT BAKU di bawah ini.\n\n"
        "=== ATURAN WAJIB ===\n"
        "1. Ikuti STRUKTUR, LABEL, dan URUTAN template PERSIS sama. JANGAN tambah/kurangi label.\n"
        "2. Setiap label (RINGKASAN EKSEKUTIF, 1. ACEH, 2. JAKARTA, 3. PAPUA, 4. INTERNASIONAL, "
        "LID, KONTRA, GAL, MEDMON, GEOINT, PIKET, REKOMENDASI) WAJIB ditulis di baris sendiri, "
        "diakhiri dengan tanda titik dua ':' .\n"
        "3. Isi konten dimulai pada baris BERIKUTNYA setelah label.\n"
        "4. JANGAN gunakan markdown (#, **, _, *, -). JANGAN bold/italic.\n"
        "5. Pada bagian MEDMON: setiap subjek di baris terpisah dengan format "
        "'N. Nama: positif X,X%/negatif Y,Y%/netral Z,Z% — ringkasan.'\n"
        "6. Pada bagian REKOMENDASI: tiap rekomendasi adalah PARAGRAF terpisah (bukan bullet, bukan nomor).\n"
        "7. Bila bagian COG (ACEH/JAKARTA/PAPUA/INTERNASIONAL) tidak ada data, tulis PERSIS: "
        "'Tidak ada perkembangan signifikan terpantau periode ini.'\n"
        "8. Output hanya teks bersih (plain text) — tidak ada penjelasan/komentar tambahan di luar format.\n"
        "9. Total panjang maksimal 500 kata.\n"
        "10. Bahasa Indonesia formal gaya laporan intelijen militer.\n\n"
        "=== TEMPLATE FORMAT BAKU ===\n"
        + FORMAT_TEMPLATE_EXAMPLE +
        "\n=== DATA HARI INI ===\n"
        + _format_payload(data) +
        "\n\nSekarang tulis EXECUTIVE SUMMARY mengikuti template baku di atas. "
        "Mulai langsung dari 'RINGKASAN EKSEKUTIF:' tanpa preamble."
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
            "temperature": 0.15,         # Lebih deterministik = lebih disiplin ikut template
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "num_ctx": 6144,            # Cukup untuk system+template+data harian
            "num_predict": 1500,        # Cap output token agar lengkap (≤500 kata)
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
