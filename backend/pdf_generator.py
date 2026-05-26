"""PDF generator for BAIS daily summary. Max 2 pages, infographic + summary text.

Layout rules:
- All text wrapping uses reportlab.pdfbase.pdfmetrics.stringWidth to avoid overflow.
- Each panel computes a cursor (cur_y) and clips items that would cross its bottom.
- KPI strip is fixed height; values & labels don't overlap header band.
- Page 1 = Header + KPIs + 2x2 COG panels.
- Page 2 = Header + AI narrative (top) + 3 columns (Geoint, Medmon, Kontra).
"""
import io
import re
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

PAGE_W, PAGE_H = A4
MARGIN = 12 * mm

# Brand colors
COLOR_HEADER = HexColor("#0B1220")
COLOR_AMBER = HexColor("#F59E0B")
COLOR_RED = HexColor("#EF4444")
COLOR_GREEN = HexColor("#10B981")
COLOR_BLUE = HexColor("#3B82F6")
COLOR_PURPLE = HexColor("#8B5CF6")
COLOR_TEXT = HexColor("#0F172A")
COLOR_MUTED = HexColor("#475569")
COLOR_BORDER = HexColor("#CBD5E1")
COLOR_LIGHT = HexColor("#F1F5F9")

COG_COLORS = {
    "aceh": COLOR_GREEN,
    "jakarta": COLOR_BLUE,
    "papua": COLOR_AMBER,
    "internasional": COLOR_PURPLE,
}

# ---------- TEXT WRAP UTILS ----------
def wrap_to_width(text, font_name, font_size, max_width_pt):
    """Wrap text into lines that fit within max_width_pt (points)."""
    text = (text or "").strip()
    if not text:
        return []
    out = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            continue
        line = ""
        for w in words:
            trial = (line + " " + w).strip()
            if stringWidth(trial, font_name, font_size) <= max_width_pt:
                line = trial
            else:
                if line:
                    out.append(line)
                # If word itself is too long, hard-split.
                while stringWidth(w, font_name, font_size) > max_width_pt and len(w) > 4:
                    cut = len(w)
                    while cut > 4 and stringWidth(w[:cut], font_name, font_size) > max_width_pt:
                        cut -= 1
                    out.append(w[:cut])
                    w = w[cut:]
                line = w
        if line:
            out.append(line)
    return out


def truncate_to_width(text, font_name, font_size, max_width_pt):
    """Return text fitted on one line; truncate with ellipsis if needed."""
    text = (text or "").strip()
    if stringWidth(text, font_name, font_size) <= max_width_pt:
        return text
    while text and stringWidth(text + "…", font_name, font_size) > max_width_pt:
        text = text[:-1]
    return text + "…" if text else ""


# ---------- HEADER / FOOTER ----------
def _draw_header(c, report_date):
    c.setFillColor(COLOR_HEADER)
    c.rect(0, PAGE_H - 22 * mm, PAGE_W, 22 * mm, stroke=0, fill=1)
    c.setFillColor(COLOR_AMBER)
    c.rect(MARGIN, PAGE_H - 22 * mm, 4 * mm, 22 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN + 7 * mm, PAGE_H - 11 * mm, "BAIS TNI — SUMMARY GEOSPASIKA HARIAN")
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN + 7 * mm, PAGE_H - 16 * mm, "Satgas Kapuas  •  Klasifikasi: TERBATAS")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(COLOR_AMBER)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 11 * mm, f"Tanggal Laporan: {report_date}")
    c.setFillColor(HexColor("#94A3B8"))
    c.setFont("Helvetica", 7.5)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 16 * mm,
                      f"Dicetak: {datetime.now().strftime('%d %b %Y %H:%M')} WIB")


def _draw_footer(c, page_num, total=2):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.4)
    c.line(MARGIN, 10 * mm, PAGE_W - MARGIN, 10 * mm)
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 7)
    c.drawString(MARGIN, 6 * mm, "DOKUMEN INTERNAL — TIDAK UNTUK DISEBARLUASKAN")
    c.drawRightString(PAGE_W - MARGIN, 6 * mm, f"Halaman {page_num} / {total}")


def _panel_title(c, x, y, w, title, kicker=None):
    """Draw a panel title bar at the TOP of a panel. Returns y for content start (below the bar)."""
    bar_h = 6 * mm
    c.setFillColor(COLOR_HEADER)
    c.rect(x, y - bar_h, w, bar_h, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x + 2.5 * mm, y - bar_h + 1.8 * mm, title)
    if kicker:
        c.setFillColor(COLOR_AMBER)
        c.setFont("Helvetica-Bold", 7)
        c.drawRightString(x + w - 2.5 * mm, y - bar_h + 1.8 * mm, kicker)
    return y - bar_h - 1 * mm  # cursor below bar with small gap


def _empty(c, x, y, w, label="— Tidak ada laporan —"):
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica-Oblique", 7.5)
    c.drawString(x + 3 * mm, y - 4 * mm, label)


# ---------- KPI STRIP ----------
def _draw_kpis(c, x, y, w, h, data):
    # outer border
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    # title bar at top
    cur_top = y + h
    c.setFillColor(COLOR_HEADER)
    c.rect(x, cur_top - 5 * mm, w, 5 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x + 2.5 * mm, cur_top - 5 * mm + 1.4 * mm, "RINGKASAN STATISTIK HARIAN")

    metrics = [
        ("BERITA LID", len(data.get("lid", [])), COLOR_AMBER),
        ("PROFILING", len(data.get("kontra", [])), COLOR_RED),
        ("KONTEN GAL", len(data.get("gal", [])), COLOR_BLUE),
        ("MEDMON", len(data.get("medmon", [])), COLOR_PURPLE),
        ("POSISI OPM", len(data.get("geoint", [])), COLOR_GREEN),
        ("PIKET", len(data.get("piket", [])), COLOR_MUTED),
    ]
    body_top = cur_top - 5 * mm  # below header band
    body_h = h - 5 * mm
    cw = w / 6
    # value baseline
    val_baseline = y + (body_h - 5 * mm) / 2 + y - y + 5.5 * mm  # internal calc
    # simpler: place value and label using body region directly
    val_y = y + body_h / 2 + 1 * mm
    label_y = y + 3.5 * mm

    for i, (label, val, col) in enumerate(metrics):
        cx = x + i * cw
        c.setFillColor(col)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(cx + cw / 2, val_y, str(val))
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(cx + cw / 2, label_y, label)
        if i < 5:
            c.setStrokeColor(COLOR_BORDER)
            c.setLineWidth(0.3)
            c.line(cx + cw, y + 2 * mm, cx + cw, body_top - 1 * mm)


# ---------- COG PANEL ----------
def _cog_panel(c, x, y, w, h, cog, items):
    color = COG_COLORS.get(cog, COLOR_AMBER)
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    # colored top tab
    tab_h = 6 * mm
    c.setFillColor(color)
    c.rect(x, y + h - tab_h, w, tab_h, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 2.5 * mm, y + h - tab_h + 1.8 * mm, f"COG · {cog.upper()}")
    c.setFont("Helvetica-Bold", 7)
    c.drawRightString(x + w - 2.5 * mm, y + h - tab_h + 1.8 * mm, f"{len(items)} ITEM")

    inner_w = w - 5 * mm
    cur_y = y + h - tab_h - 4 * mm
    if not items:
        _empty(c, x, cur_y + 4 * mm, w)
        return

    # show up to 3 items, each capped to ~3 lines
    for it in items[:3]:
        if cur_y < y + 4 * mm:
            break
        # bullet & title
        c.setFillColor(color)
        c.circle(x + 3 * mm, cur_y - 1.2 * mm, 0.8 * mm, stroke=0, fill=1)
        c.setFillColor(COLOR_TEXT)
        c.setFont("Helvetica-Bold", 7.8)
        title_lines = wrap_to_width(it.get("judul", "—"), "Helvetica-Bold", 7.8, inner_w)
        # title max 2 lines
        for line in title_lines[:2]:
            if cur_y < y + 4 * mm:
                break
            c.drawString(x + 5 * mm, cur_y - 1.2 * mm, line)
            cur_y -= 3.2 * mm
        # analisa max 2 lines
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica", 7)
        for line in wrap_to_width(it.get("analisa", ""), "Helvetica", 7, inner_w)[:2]:
            if cur_y < y + 4 * mm:
                break
            c.drawString(x + 5 * mm, cur_y - 1.2 * mm, line)
            cur_y -= 2.9 * mm
        cur_y -= 1.5 * mm  # spacing between items


# ---------- AI SUMMARY ----------
HEADING_RE = re.compile(
    r"^(RINGKASAN\b|ANALISA\b|REKOMENDASI\b|ANALISA\s*&\s*REKOMENDASI\b|"
    r"\d+\.\s*(?:ACEH|JAKARTA|PAPUA|INTERNASIONAL)\b)",
    re.IGNORECASE,
)


def _draw_summary_text(c, x, y, w, h, ai_text, data):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    cur_y = _panel_title(c, x, y + h, w, "RINGKASAN NARATIF AI (CLAUDE SONNET 4.5)",
                         kicker="EXECUTIVE SUMMARY")

    text = ai_text or _fallback_summary(data)
    # strip markdown
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

    inner_w = w - 8 * mm  # 4mm padding each side
    bottom = y + 3 * mm

    for paragraph in text.split("\n"):
        if cur_y < bottom + 3 * mm:
            break
        if not paragraph.strip():
            cur_y -= 2 * mm
            continue
        is_heading = bool(HEADING_RE.match(paragraph.strip()))
        if is_heading:
            c.setFont("Helvetica-Bold", 8.5)
            c.setFillColor(COLOR_HEADER)
            font_name, font_size, line_h = "Helvetica-Bold", 8.5, 3.6 * mm
        else:
            c.setFont("Helvetica", 8)
            c.setFillColor(COLOR_TEXT)
            font_name, font_size, line_h = "Helvetica", 8, 3.4 * mm
        for line in wrap_to_width(paragraph.strip(), font_name, font_size, inner_w):
            if cur_y < bottom + 2 * mm:
                break
            c.drawString(x + 4 * mm, cur_y - line_h + 1 * mm, line)
            cur_y -= line_h
        cur_y -= 0.8 * mm


def _fallback_summary(data):
    parts = ["RINGKASAN EKSEKUTIF:", "Laporan harian berdasarkan input dari tim operasional.", ""]
    by_cog = {"aceh": [], "jakarta": [], "papua": [], "internasional": []}
    for it in data.get("lid", []):
        by_cog.setdefault(it.get("cog", ""), []).append(it)
    for cog_key, label in [("aceh", "1. ACEH"), ("jakarta", "2. JAKARTA"),
                           ("papua", "3. PAPUA"), ("internasional", "4. INTERNASIONAL")]:
        parts.append(label + ":")
        items = by_cog.get(cog_key, [])
        if items:
            for it in items[:2]:
                analisa = (it.get("analisa", "") or "")[:150]
                parts.append(f"- {it.get('judul','')} — {analisa}")
        else:
            parts.append("- Tidak ada laporan signifikan.")
        parts.append("")
    parts.append("ANALISA & REKOMENDASI:")
    parts.append(f"- Total {len(data.get('lid', []))} berita trending, "
                 f"{len(data.get('kontra', []))} profiling, "
                 f"{len(data.get('geoint', []))} posisi OPM termonitor.")
    parts.append("- Tindak lanjuti rekomendasi tim sesuai prioritas pimpinan.")
    return "\n".join(parts)


# ---------- LOWER 3-COLUMN SECTIONS ----------
def _draw_geoint(c, x, y, w, h, data):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    cur_y = _panel_title(c, x, y + h, w, "GEOINT · POSISI OPM", kicker=f"{len(data.get('geoint', []))} TITIK")

    items = data.get("geoint", [])
    bottom = y + 3 * mm
    if not items:
        _empty(c, x, cur_y, w)
        return

    inner_w = w - 5 * mm

    for it in items[:5]:
        if cur_y < bottom + 6 * mm:
            break
        # row block: wilayah + status badge
        c.setFillColor(COLOR_TEXT)
        c.setFont("Helvetica-Bold", 7.5)
        wilayah = truncate_to_width(it.get("wilayah", "—"), "Helvetica-Bold", 7.5, inner_w * 0.6)
        c.drawString(x + 3 * mm, cur_y - 2.6 * mm, wilayah)
        status = (it.get("status") or "").upper().replace("_", " ")
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(COLOR_RED if it.get("status") == "aktif" else COLOR_GREEN)
        c.drawRightString(x + w - 3 * mm, cur_y - 2.6 * mm, status)
        cur_y -= 3.6 * mm
        # name + coords (mono)
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica", 6.8)
        nm = truncate_to_width(it.get("nama_orang", "-"), "Helvetica", 6.8, inner_w)
        c.drawString(x + 3 * mm, cur_y - 2.4 * mm, nm)
        cur_y -= 3 * mm
        c.setFont("Courier", 6.5)
        coords = f"{it.get('lat','-')}, {it.get('lon','-')}"
        coords = truncate_to_width(coords, "Courier", 6.5, inner_w)
        c.drawString(x + 3 * mm, cur_y - 2.4 * mm, coords)
        cur_y -= 4 * mm
        # divider
        c.setStrokeColor(COLOR_BORDER)
        c.setLineWidth(0.2)
        c.line(x + 2 * mm, cur_y, x + w - 2 * mm, cur_y)
        cur_y -= 1.5 * mm


def _draw_medmon(c, x, y, w, h, data):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    cur_y = _panel_title(c, x, y + h, w, "MEDIA MONITORING", kicker=f"{len(data.get('medmon', []))} SUBJEK")

    items = data.get("medmon", [])
    bottom = y + 3 * mm
    if not items:
        _empty(c, x, cur_y, w)
        return

    inner_w = w - 5 * mm

    for it in items[:4]:
        if cur_y < bottom + 8 * mm:
            break
        # subjek
        c.setFillColor(COLOR_HEADER)
        c.setFont("Helvetica-Bold", 8)
        subj = truncate_to_width(str(it.get("subjek", "-")).upper(),
                                 "Helvetica-Bold", 8, inner_w * 0.65)
        c.drawString(x + 3 * mm, cur_y - 2.8 * mm, subj)
        # sentiment counts (right)
        positifs = sum(1 for b in it.get("berita", []) if b.get("sentiment") == "positif")
        negatifs = sum(1 for b in it.get("berita", []) if b.get("sentiment") == "negatif")
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(COLOR_GREEN)
        c.drawRightString(x + w - 9 * mm, cur_y - 2.8 * mm, f"+{positifs}")
        c.setFillColor(COLOR_RED)
        c.drawRightString(x + w - 3 * mm, cur_y - 2.8 * mm, f"−{negatifs}")
        cur_y -= 3.8 * mm
        # analisa wrapped
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica", 6.8)
        for line in wrap_to_width(it.get("analisa", ""), "Helvetica", 6.8, inner_w)[:3]:
            if cur_y < bottom + 2 * mm:
                break
            c.drawString(x + 3 * mm, cur_y - 2.2 * mm, line)
            cur_y -= 2.9 * mm
        cur_y -= 1.5 * mm


def _draw_kontra(c, x, y, w, h, data):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    cur_y = _panel_title(c, x, y + h, w, "KONTRA · PROFILING TO", kicker=f"{len(data.get('kontra', []))} TO")

    items = data.get("kontra", [])
    bottom = y + 3 * mm
    if not items:
        _empty(c, x, cur_y, w)
        return

    inner_w = w - 5 * mm

    for it in items[:4]:
        if cur_y < bottom + 8 * mm:
            break
        c.setFillColor(COLOR_HEADER)
        c.setFont("Helvetica-Bold", 7.8)
        name = truncate_to_width(it.get("nama_to", "-"), "Helvetica-Bold", 7.8, inner_w * 0.65)
        c.drawString(x + 3 * mm, cur_y - 2.6 * mm, name)
        # tag
        is_satgas = it.get("sumber") == "to_satgas"
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(COLOR_RED if is_satgas else COLOR_BLUE)
        tag = "TO SATGAS" if is_satgas else "TO INTERNAL"
        c.drawRightString(x + w - 3 * mm, cur_y - 2.6 * mm, tag)
        cur_y -= 3.6 * mm
        # description (data_diri or keterangan)
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica", 6.8)
        descr = it.get("keterangan") or it.get("data_diri") or ""
        for line in wrap_to_width(descr, "Helvetica", 6.8, inner_w)[:3]:
            if cur_y < bottom + 2 * mm:
                break
            c.drawString(x + 3 * mm, cur_y - 2.2 * mm, line)
            cur_y -= 2.9 * mm
        cur_y -= 1.5 * mm


# ---------- MAIN ----------
def build_summary_pdf(data, ai_text):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    rd = data.get("report_date", "")

    # =========== PAGE 1 ===========
    _draw_header(c, rd)

    # KPI strip
    kpi_h = 26 * mm
    kpi_y = PAGE_H - 22 * mm - 5 * mm - kpi_h
    _draw_kpis(c, MARGIN, kpi_y, PAGE_W - 2 * MARGIN, kpi_h, data)

    # 4 COG panels (2x2 grid)
    grid_top = kpi_y - 5 * mm
    grid_bottom = 14 * mm
    grid_h = grid_top - grid_bottom
    grid_w = PAGE_W - 2 * MARGIN
    gutter = 4 * mm
    cell_w = (grid_w - gutter) / 2
    cell_h = (grid_h - gutter) / 2

    by_cog = {"aceh": [], "jakarta": [], "papua": [], "internasional": []}
    for it in data.get("lid", []):
        by_cog.setdefault(it.get("cog", ""), []).append(it)

    positions = [
        ("aceh", MARGIN, grid_top - cell_h),
        ("jakarta", MARGIN + cell_w + gutter, grid_top - cell_h),
        ("papua", MARGIN, grid_top - cell_h * 2 - gutter),
        ("internasional", MARGIN + cell_w + gutter, grid_top - cell_h * 2 - gutter),
    ]
    for cog, px, py in positions:
        _cog_panel(c, px, py, cell_w, cell_h, cog, by_cog.get(cog, []))

    _draw_footer(c, 1)
    c.showPage()

    # =========== PAGE 2 ===========
    _draw_header(c, rd)
    # AI narrative top block
    sum_h = 95 * mm
    sum_y = PAGE_H - 22 * mm - 5 * mm - sum_h
    _draw_summary_text(c, MARGIN, sum_y, PAGE_W - 2 * MARGIN, sum_h, ai_text, data)

    # bottom: 3 columns (Geoint, Medmon, Kontra)
    bottom_top = sum_y - 5 * mm
    bottom_bottom = 14 * mm
    bottom_h = bottom_top - bottom_bottom
    total_w = PAGE_W - 2 * MARGIN
    col_w = (total_w - 2 * gutter) / 3
    _draw_geoint(c, MARGIN, bottom_bottom, col_w, bottom_h, data)
    _draw_medmon(c, MARGIN + col_w + gutter, bottom_bottom, col_w, bottom_h, data)
    _draw_kontra(c, MARGIN + 2 * (col_w + gutter), bottom_bottom, col_w, bottom_h, data)

    _draw_footer(c, 2)
    c.showPage()
    c.save()
    return buf.getvalue()
