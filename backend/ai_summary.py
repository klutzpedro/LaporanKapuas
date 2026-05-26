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
        lines.append(
            f"- {it.get('subjek','')}: positif={pos}, negatif={neg} | "
            f"Analisa: {it.get('analisa','')[:200]} | Rekomendasi: {it.get('rekomendasi','')[:140]}"
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
        "Susun EXECUTIVE SUMMARY harian untuk pimpinan BAIS TNI. Wajib gabungkan SEMUA tim. "
        "Format WAJIB (Bahasa Indonesia, total max 320 kata, kalimat efisien & padat):\n\n"
        "RINGKASAN EKSEKUTIF: (3 kalimat menjawab: apa kejadian utama hari ini, apa risiko, apa yang harus diketahui pimpinan).\n"
        "1. ACEH: (2 kalimat).\n"
        "2. JAKARTA: (2 kalimat).\n"
        "3. PAPUA: (2 kalimat, sertakan total titik OPM termonitor & berapa AKTIF bila ada).\n"
        "4. INTERNASIONAL: (1-2 kalimat).\n"
        "MEDMON: (1-2 kalimat ringkas — subjek penting, tren sentimen positif/negatif).\n"
        "KONTRA & GAL: (1-2 kalimat — TO mencolok hari ini & arahan konten galang).\n"
        "PIKET: (1 kalimat — laporan satgas tek/sandi/medis bila ada).\n"
        "REKOMENDASI: (3-4 poin singkat, action-oriented).\n\n"
        "Jangan ulang label menjadi heading panjang. Jangan pakai bullet selain pada bagian REKOMENDASI.\n\n"
        "Data hari ini:\n" + _format_payload(data)
    )

    try:
        resp = await chat.send_message(UserMessage(text=user_text))
        return str(resp).strip()
    except Exception as e:
        logger.exception("AI summary failed")
        return f"[AI SUMMARY ERROR] {e}"
