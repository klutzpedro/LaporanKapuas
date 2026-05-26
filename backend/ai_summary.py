"""AI summary generator using Claude Sonnet 4.5 via emergentintegrations."""
import os
import logging
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger("bais.ai")

SYSTEM_PROMPT = (
    "Anda adalah analis intelijen strategis senior BAIS TNI. "
    "Tugas Anda menyusun ringkasan harian (summary) yang ringkas, padat, dan profesional "
    "dari laporan tim LID, KONTRA, GAL, MEDMON, GEOINT, dan PIKET. "
    "Output harus dalam Bahasa Indonesia formal, gaya laporan intelijen militer, "
    "menggunakan istilah baku, tidak melebihi 350 kata, terstruktur per Center of Gravity "
    "(ACEH, JAKARTA, PAPUA, INTERNASIONAL), diikuti analisa singkat dan rekomendasi prioritas. "
    "Hindari spekulasi; gunakan hanya data yang diberikan."
)


def _format_payload(data: dict) -> str:
    rd = data.get("report_date")
    lines = [f"TANGGAL LAPORAN: {rd}", ""]

    lines.append("== TIM LID (Berita Trending) ==")
    for it in data.get("lid", []):
        lines.append(
            f"- [{it.get('cog','').upper()}] {it.get('judul','')} | Fakta: {it.get('fakta','')[:200]} "
            f"| Analisa: {it.get('analisa','')[:200]} | Tindakan: {it.get('tindakan','')[:160]} "
            f"| Rekomendasi: {it.get('rekomendasi','')[:160]} | Sentiment: {it.get('sentiment_label','-')}"
        )

    lines.append("\n== TIM KONTRA (Profiling TO) ==")
    for it in data.get("kontra", []):
        lines.append(
            f"- [{it.get('sumber','').upper()}/{it.get('tipe','')}] {it.get('nama_to','')}: "
            f"{it.get('data_diri','')[:200]} | Ket: {it.get('keterangan','')[:160]}"
        )

    lines.append("\n== TIM GAL (Konten Galang) ==")
    for it in data.get("gal", []):
        lines.append(f"- [{it.get('kategori','').upper()}] {it.get('judul','')} | {it.get('keterangan','')[:160]}")

    lines.append("\n== TIM MEDMON (Media Monitoring) ==")
    for it in data.get("medmon", []):
        positifs = [b for b in it.get("berita", []) if b.get("sentiment") == "positif"]
        negatifs = [b for b in it.get("berita", []) if b.get("sentiment") == "negatif"]
        lines.append(
            f"- Subjek {it.get('subjek','')}: positif={len(positifs)}, negatif={len(negatifs)} | "
            f"Analisa: {it.get('analisa','')[:200]} | Rekomendasi: {it.get('rekomendasi','')[:160]}"
        )

    lines.append("\n== TIM GEOINT (Posisi OPM) ==")
    for it in data.get("geoint", []):
        lines.append(
            f"- {it.get('wilayah','')} | {it.get('nama_orang','')} | status: {it.get('status','')} "
            f"| lat={it.get('lat')}, lon={it.get('lon')} | Ket: {it.get('keterangan','')[:160]}"
        )

    lines.append("\n== PIKET (TEK / SANDI / MEDIS) ==")
    for it in data.get("piket", []):
        lines.append(f"- [{it.get('satgas','').upper()}] {it.get('judul','')}: {it.get('isi','')[:200]}")

    return "\n".join(lines)


async def generate_ai_summary(data: dict) -> str:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return "[AI SUMMARY UNAVAILABLE] EMERGENT_LLM_KEY tidak tersedia."

    rd = data.get("report_date", "unknown")
    chat = LlmChat(
        api_key=api_key,
        session_id=f"bais-summary-{rd}",
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    user_text = (
        "Susun ringkasan harian BAIS TNI berdasarkan data berikut. "
        "Format output (Bahasa Indonesia, maksimal 350 kata):\n\n"
        "RINGKASAN EKSEKUTIF: (2-3 kalimat).\n"
        "1. ACEH: (2-3 kalimat penting).\n"
        "2. JAKARTA: (2-3 kalimat penting).\n"
        "3. PAPUA: (2-3 kalimat penting, sertakan info OPM bila ada).\n"
        "4. INTERNASIONAL: (1-2 kalimat).\n"
        "ANALISA & REKOMENDASI: (3-5 poin singkat).\n\n"
        "Data:\n" + _format_payload(data)
    )

    try:
        resp = await chat.send_message(UserMessage(text=user_text))
        return str(resp).strip()
    except Exception as e:
        logger.exception("AI summary failed")
        return f"[AI SUMMARY ERROR] {e}"
