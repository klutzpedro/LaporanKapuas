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
    "dari laporan tim LID (berita trending), KONTRA (profiling TO), GAL (konten galang), "
    "MEDMON (media monitoring), GEOINT (posisi OPM), dan PIKET (Satgas Tek/Sandi/Medis). "
    "Output harus dalam Bahasa Indonesia formal gaya laporan intelijen militer. "
    "Total panjang maksimal 320 kata. "
    "Wajib mengintegrasikan SEMUA tim — bukan hanya berita LID. "
    "Tidak ada spekulasi; hanya data yang diberikan. Hindari kata pengisi."
)


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
        return await _generate_via_ollama(user_text, rd)

    # claude (default Emergent path)
    return await _generate_via_claude(user_text, rd)


def _build_user_prompt(data: dict) -> str:
    """Build the prompt text. Shared between providers."""
    return (
        "Susun EXECUTIVE SUMMARY harian untuk pimpinan BAIS TNI. Wajib gabungkan SEMUA tim. "
        "Format WAJIB (Bahasa Indonesia, total max 380 kata, kalimat efisien & padat):\n\n"
        "RINGKASAN EKSEKUTIF: (3 kalimat menjawab: apa kejadian utama hari ini, apa risiko, apa yang harus diketahui pimpinan).\n\n"
        "(Bagian COG — masing-masing 1-2 kalimat. Jika tidak ada data, tulis: 'Tidak ada perkembangan signifikan terpantau periode ini.')\n"
        "1. ACEH:\n"
        "2. JAKARTA:\n"
        "3. PAPUA: (sertakan total titik OPM termonitor & berapa AKTIF bila ada).\n"
        "4. INTERNASIONAL:\n\n"
        "(Bagian Per-Tim — masing-masing satu paragraf terpisah di baris baru)\n"
        "LID: (1-2 kalimat — berita trending paling penting hari ini & dampaknya).\n"
        "KONTRA: (1-2 kalimat — TO/profiling mencolok hari ini, sumber & tipe ancaman).\n"
        "GAL: (1-2 kalimat — arahan konten galang & kategori dominan).\n"
        "MEDMON: SEBUTKAN SETIAP SUBJEK SEBAGAI ITEM TERPISAH dengan format DAFTAR BERNOMOR. "
        "Tulis kata 'MEDMON:' pada baris sendiri, lalu pada baris-baris BERIKUTNYA tulis: "
        "'1. Presiden: positif X%/negatif Y%/netral Z% — ringkasan singkat.', "
        "'2. Panglima TNI: positif X%/negatif Y%/netral Z% — ringkasan.', "
        "'3. MBG: ...', dst hingga semua subjek tercantum. "
        "Setiap nomor di baris baru. JANGAN gabungkan menjadi 1 paragraf.\n"
        "GEOINT: (1 kalimat — total titik OPM aktif & wilayah utama).\n"
        "PIKET: (1 kalimat — laporan satgas tek/sandi/medis bila ada).\n\n"
        "REKOMENDASI: (3-5 poin singkat, action-oriented, gunakan bullet '-').\n\n"
        "Jangan ulang label menjadi heading panjang. Jangan pakai bullet selain pada bagian REKOMENDASI. "
        "Pastikan tiap section LID/KONTRA/GAL/MEDMON/GEOINT/PIKET adalah PARAGRAF TERPISAH (pisahkan dengan baris kosong).\n\n"
        "Data hari ini:\n" + _format_payload(data)
    )


async def _generate_via_ollama(user_text: str, rd: str) -> str:
    """Call local Ollama (100% on-server, no external network).
    Default model: 'llama3.2:3b' (fast, ~2GB RAM). Override via OLLAMA_MODEL.
    """
    import httpx
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": user_text,
        "stream": False,
        "options": {"temperature": 0.3, "num_ctx": 8192},
    }
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            r = await client.post(f"{host}/api/generate", json=payload)
            r.raise_for_status()
            body = r.json()
            return str(body.get("response", "")).strip()
    except Exception as e:
        logger.exception(f"Ollama summary failed (host={host}, model={model})")
        return (
            f"[AI SUMMARY ERROR — Ollama lokal tidak merespons: {e}]\n\n"
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
