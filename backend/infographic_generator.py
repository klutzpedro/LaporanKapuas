"""Morning Report INFOGRAPHIC generator.

Pipeline:
  1. Build compact data brief from yesterday's collected data + AI text.
  2. Ask Claude Sonnet 4.5 (via Emergent LLM key) to produce ONE A4-portrait SVG
     poster that visualizes the brief.
  3. Sanitize the returned SVG, convert to PNG via CairoSVG, embed in a single-page
     A4 PDF via ReportLab.

Output: PDF bytes (1 page, A4 portrait).
"""

from __future__ import annotations

import io
import logging
import os
import re
from datetime import datetime

import cairosvg
from emergentintegrations.llm.chat import LlmChat, UserMessage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

PAGE_W, PAGE_H = A4  # 595 x 842 pt
TARGET_PNG_W = 1240  # render width (≈150 DPI for A4)
TARGET_PNG_H = 1754

# Map MEDMON subjek → counts (per item)
def _medmon_subject_counts(medmon_items):
    counts = {}
    for it in medmon_items or []:
        subj = (it.get("subjek") or it.get("subject") or "Lainnya").strip() or "Lainnya"
        counts[subj] = counts.get(subj, 0) + 1
    return sorted(counts.items(), key=lambda x: -x[1])[:6]


def _sentiment_counts(medmon_items):
    pos = neg = neu = 0
    for it in medmon_items or []:
        s = (it.get("sentimen") or it.get("sentiment") or "").lower()
        if "pos" in s:
            pos += 1
        elif "neg" in s:
            neg += 1
        else:
            neu += 1
    return {"positif": pos, "negatif": neg, "netral": neu}


def _build_brief(data: dict, ai_text: str | None) -> dict:
    """Build a compact JSON brief for Claude."""
    lid = data.get("lid", []) or []
    kontra = data.get("kontra", []) or []
    gal = data.get("gal", []) or []
    medmon = data.get("medmon", []) or []
    geoint = data.get("geoint", []) or []

    # Short snippets (max 60 chars each)
    def _snip(s, n=60):
        s = (s or "").strip().replace("\n", " ")
        return s[: n - 1] + "…" if len(s) > n else s

    lid_titles = [_snip(it.get("judul") or it.get("title") or "") for it in lid[:5] if (it.get("judul") or it.get("title"))]
    kontra_subjects = [_snip(it.get("subjek") or it.get("subject") or "") for it in kontra[:5] if (it.get("subjek") or it.get("subject"))]
    gal_topics = [_snip(it.get("topik") or it.get("topic") or it.get("judul") or "") for it in gal[:5] if (it.get("topik") or it.get("topic") or it.get("judul"))]
    geoint_locs = [_snip(it.get("nama") or it.get("name") or it.get("lokasi") or "") for it in geoint[:5] if (it.get("nama") or it.get("name") or it.get("lokasi"))]

    medmon_top = _medmon_subject_counts(medmon)
    sentiments = _sentiment_counts(medmon)

    # Try extract REKOMENDASI from AI text
    rec_lines = []
    if ai_text:
        m = re.search(r"(?ims)REKOMENDASI\s*:?\s*\n?(.+?)(?=\n[A-Z]{4,}\s*:|\Z)", ai_text)
        if m:
            for ln in m.group(1).splitlines():
                ln = ln.strip().lstrip("•-*").strip()
                if 6 < len(ln) < 180:
                    rec_lines.append(ln)
                if len(rec_lines) >= 4:
                    break

    return {
        "report_date": data.get("report_date") or "",
        "counts": {
            "LID": len(lid),
            "KONTRA": len(kontra),
            "GAL": len(gal),
            "MEDMON": len(medmon),
            "GEOINT": len(geoint),
        },
        "lid_highlights": lid_titles,
        "kontra_subjects": kontra_subjects,
        "gal_topics": gal_topics,
        "geoint_locations": geoint_locs,
        "medmon_top_subjects": medmon_top,  # list of (name, count)
        "sentiments": sentiments,
        "recommendations": rec_lines,
    }


SYSTEM_PROMPT = """You are an expert intelligence-briefing infographic designer.
You output ONE valid SVG document only — no commentary, no markdown fences.

CONSTRAINTS:
- Output MUST start with <svg xmlns="http://www.w3.org/2000/svg" ...> and end with </svg>.
- Single A4 PORTRAIT poster, viewBox="0 0 1240 1754" (≈150 DPI), preserveAspectRatio="xMidYMid meet".
- Use only inline SVG shapes/text. NO external images, NO <foreignObject>, NO <script>.
- Use ONLY these fonts (with fallback): font-family="Helvetica, Arial, sans-serif".
- Visual style: TACTICAL INTELLIGENCE DASHBOARD — dark deep-navy/slate background (#0B1220),
  amber #F59E0B and teal #14B8A6 as primary accents, white/slate text. Grid lines optional.
- Layout (top → bottom):
  1. Header band (≈120 px tall): title "LAPORAN PAGI GEOSPASIKA", subtitle "INFOGRAFIS HARIAN — BAIS TNI · SATGAS KAPUAS",
     classified tag "TERBATAS", report date on the right.
  2. KPI strip: 5 cards across (LID, KONTRA, GAL, MEDMON, GEOINT) with the count number BIG and the team label below.
  3. Two-column body:
     LEFT column: "TRENDING & PROFILING" — short bullet list of LID highlights + KONTRA subjects.
     RIGHT column: "MEDMON & SENTIMEN" — horizontal bar chart of top medmon subjects, plus a donut/segmented bar showing positif/netral/negatif counts.
  4. "JEJAK LAPANGAN — GEOINT" section: a list of locations (compact pill chips).
  5. "REKOMENDASI HARI INI" section at bottom: numbered list (max 4 items), each with a small amber leading bar.
  6. Footer bar: thin separator + "Dokumen Internal — Klasifikasi: TERBATAS" + "Auto-generated · {date}".
- All text must be Indonesian.
- Use rounded corners (rx=6) on cards. Use stroke="#1F2937" with stroke-width="1" for card borders.
- If a section has zero data, still render the section header with "Tidak ada data" muted text.
- Do NOT exceed 18 KB of SVG markup. Keep it information-dense but readable.
- Numbers and section titles must be tested for readability (font-size >= 16 for labels, >= 56 for KPI numbers).
"""


USER_PROMPT_TEMPLATE = """Buat infografis SVG A4 portrait untuk LAPORAN PAGI berikut.
Tampilkan datanya dengan visualisasi yang jelas, bersih, dan profesional.

DATA (JSON):
{brief_json}

TUGAS:
- Render KPI counts, list highlight LID/KONTRA, bar chart subjek MEDMON, donut sentimen,
  jejak GEOINT, dan rekomendasi.
- Pastikan TIDAK ADA teks yang keluar dari viewBox (1240 x 1754).
- Output HANYA SVG murni (mulai dari <svg ...> sampai </svg>), tanpa ``` fences atau penjelasan apa pun.
"""


def _strip_svg(text: str) -> str:
    """Extract a pure <svg>...</svg> block from Claude's response."""
    if not text:
        return ""
    # Remove markdown code fences
    text = re.sub(r"^```(?:svg|xml)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    # Find first <svg ...> ... </svg>
    m = re.search(r"<svg\b[^>]*>.*?</svg>", text, flags=re.DOTALL | re.IGNORECASE)
    return m.group(0).strip() if m else ""


async def _ask_claude_for_svg(brief: dict) -> str:
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise RuntimeError("EMERGENT_LLM_KEY tidak tersedia di environment.")

    import json as _json

    brief_json = _json.dumps(brief, ensure_ascii=False, indent=2)
    user_text = USER_PROMPT_TEMPLATE.format(brief_json=brief_json)

    chat = LlmChat(
        api_key=api_key,
        session_id=f"bais-infographic-{brief.get('report_date','')}",
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")

    resp = await chat.send_message(UserMessage(text=user_text))
    svg = _strip_svg(str(resp))
    if not svg or "<svg" not in svg:
        raise RuntimeError("Claude tidak mengembalikan SVG yang valid.")
    return svg


def _fallback_svg(brief: dict) -> str:
    """Minimal hard-coded SVG fallback used only when Claude is unreachable.
    Renders the same data so the PDF is never empty.
    """
    c = brief.get("counts", {}) or {}
    rd = brief.get("report_date", "")
    parts = []
    parts.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1240 1754" preserveAspectRatio="xMidYMid meet">')
    parts.append('<rect width="1240" height="1754" fill="#0B1220"/>')
    # Header
    parts.append('<rect x="0" y="0" width="1240" height="120" fill="#0F172A"/>')
    parts.append('<rect x="0" y="118" width="1240" height="3" fill="#F59E0B"/>')
    parts.append('<text x="40" y="62" font-family="Helvetica,Arial,sans-serif" font-size="34" font-weight="700" fill="#F8FAFC">LAPORAN PAGI GEOSPASIKA</text>')
    parts.append(f'<text x="40" y="92" font-family="Helvetica,Arial,sans-serif" font-size="16" fill="#94A3B8">INFOGRAFIS HARIAN · BAIS TNI · SATGAS KAPUAS · {rd}</text>')
    parts.append('<rect x="1080" y="38" width="120" height="36" rx="6" fill="#F59E0B"/>')
    parts.append('<text x="1140" y="62" font-family="Helvetica,Arial,sans-serif" font-size="16" font-weight="700" text-anchor="middle" fill="#0B1220">TERBATAS</text>')
    # KPI strip
    labels = ["LID", "KONTRA", "GAL", "MEDMON", "GEOINT"]
    colors = ["#F59E0B", "#EF4444", "#3B82F6", "#A855F7", "#10B981"]
    for i, lab in enumerate(labels):
        x = 40 + i * 232
        parts.append(f'<rect x="{x}" y="160" width="220" height="160" rx="8" fill="#0F172A" stroke="#1F2937"/>')
        parts.append(f'<rect x="{x}" y="160" width="6" height="160" fill="{colors[i]}"/>')
        parts.append(f'<text x="{x+115}" y="246" font-family="Helvetica,Arial,sans-serif" font-size="64" font-weight="800" text-anchor="middle" fill="{colors[i]}">{c.get(lab,0)}</text>')
        parts.append(f'<text x="{x+115}" y="290" font-family="Helvetica,Arial,sans-serif" font-size="18" font-weight="700" text-anchor="middle" fill="#CBD5E1">{lab}</text>')
    # Body sections (minimal)
    parts.append('<text x="40" y="380" font-family="Helvetica,Arial,sans-serif" font-size="20" font-weight="700" fill="#F59E0B">TRENDING (LID)</text>')
    y = 410
    for t in brief.get("lid_highlights", [])[:5] or ["Tidak ada data"]:
        parts.append(f'<text x="40" y="{y}" font-family="Helvetica,Arial,sans-serif" font-size="14" fill="#E2E8F0">• {t}</text>')
        y += 24
    parts.append('<text x="640" y="380" font-family="Helvetica,Arial,sans-serif" font-size="20" font-weight="700" fill="#14B8A6">TOP MEDMON</text>')
    y = 410
    medmon_top = brief.get("medmon_top_subjects", []) or []
    if not medmon_top:
        parts.append(f'<text x="640" y="{y}" font-family="Helvetica,Arial,sans-serif" font-size="14" fill="#94A3B8">Tidak ada data</text>')
    else:
        max_v = max(v for _, v in medmon_top) or 1
        for name, v in medmon_top[:6]:
            bw = int(400 * v / max_v)
            parts.append(f'<rect x="640" y="{y-12}" width="{bw}" height="16" fill="#14B8A6"/>')
            parts.append(f'<text x="640" y="{y+18}" font-family="Helvetica,Arial,sans-serif" font-size="12" fill="#E2E8F0">{name} ({v})</text>')
            y += 38
    # Rekomendasi
    parts.append('<text x="40" y="1500" font-family="Helvetica,Arial,sans-serif" font-size="20" font-weight="700" fill="#F59E0B">REKOMENDASI HARI INI</text>')
    y = 1530
    recs = brief.get("recommendations") or ["Belum ada rekomendasi otomatis."]
    for i, r in enumerate(recs[:4], 1):
        parts.append(f'<rect x="40" y="{y-12}" width="4" height="18" fill="#F59E0B"/>')
        parts.append(f'<text x="56" y="{y+2}" font-family="Helvetica,Arial,sans-serif" font-size="14" fill="#E2E8F0">{i}. {r}</text>')
        y += 30
    # Footer
    parts.append('<rect x="0" y="1714" width="1240" height="40" fill="#0F172A"/>')
    parts.append('<text x="40" y="1740" font-family="Helvetica,Arial,sans-serif" font-size="12" fill="#94A3B8">Dokumen Internal · Klasifikasi: TERBATAS</text>')
    parts.append(f'<text x="1200" y="1740" font-family="Helvetica,Arial,sans-serif" font-size="12" text-anchor="end" fill="#94A3B8">Auto-generated · {rd}</text>')
    parts.append('</svg>')
    return "".join(parts)


def _svg_to_pdf(svg_str: str) -> bytes:
    """Render SVG → PNG → embed into a 1-page A4 PDF."""
    png_bytes = cairosvg.svg2png(
        bytestring=svg_str.encode("utf-8"),
        output_width=TARGET_PNG_W,
        output_height=TARGET_PNG_H,
    )
    img = ImageReader(io.BytesIO(png_bytes))

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    # Fit the full A4 page (with 6 mm safety margin)
    margin = 6 * mm
    c.drawImage(
        img,
        margin,
        margin,
        width=PAGE_W - 2 * margin,
        height=PAGE_H - 2 * margin,
        preserveAspectRatio=True,
        anchor="c",
        mask="auto",
    )
    c.showPage()
    c.save()
    return buf.getvalue()


async def build_morning_infographic_pdf(data: dict, ai_text: str | None = None) -> bytes:
    """Build the morning report INFOGRAPHIC PDF (1 page, A4 portrait).

    Falls back to a hard-coded SVG layout if Claude is unreachable.
    """
    brief = _build_brief(data, ai_text)
    try:
        svg_str = await _ask_claude_for_svg(brief)
    except Exception as e:
        logger.warning(f"Infographic Claude call failed, using fallback: {e}")
        svg_str = _fallback_svg(brief)

    try:
        return _svg_to_pdf(svg_str)
    except Exception as e:
        # Final safety net: render fallback SVG (which we know is well-formed)
        logger.warning(f"SVG→PNG failed for Claude output, retrying with fallback: {e}")
        return _svg_to_pdf(_fallback_svg(brief))
