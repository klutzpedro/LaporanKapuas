"""PDF generator for BAIS daily summary. Max 2 pages, infographic + summary text."""
import io
import base64
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

PAGE_W, PAGE_H = A4
MARGIN = 12 * mm

# Brand colors
COLOR_BG = HexColor("#FFFFFF")
COLOR_HEADER = HexColor("#0B1220")
COLOR_AMBER = HexColor("#F59E0B")
COLOR_RED = HexColor("#EF4444")
COLOR_GREEN = HexColor("#10B981")
COLOR_BLUE = HexColor("#3B82F6")
COLOR_PURPLE = HexColor("#8B5CF6")
COLOR_TEXT = HexColor("#0F172A")
COLOR_MUTED = HexColor("#475569")
COLOR_BORDER = HexColor("#CBD5E1")

COG_COLORS = {
    "aceh": COLOR_GREEN,
    "jakarta": COLOR_BLUE,
    "papua": COLOR_AMBER,
    "internasional": COLOR_PURPLE,
}


def _decode_image(data_url: str):
    if not data_url:
        return None
    try:
        if "," in data_url:
            data_url = data_url.split(",", 1)[1]
        raw = base64.b64decode(data_url)
        return ImageReader(io.BytesIO(raw))
    except Exception:
        return None


def _wrap(text: str, width_chars: int):
    text = text or ""
    out = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        line = ""
        for w in words:
            if len(line) + len(w) + 1 <= width_chars:
                line = (line + " " + w).strip()
            else:
                out.append(line)
                line = w
        out.append(line)
    return [l for l in out if l]


def _draw_header(c: canvas.Canvas, report_date: str):
    c.setFillColor(COLOR_HEADER)
    c.rect(0, PAGE_H - 22 * mm, PAGE_W, 22 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(MARGIN, PAGE_H - 11 * mm, "BAIS TNI — SUMMARY GEOSPASIKA HARIAN")
    c.setFont("Helvetica", 9)
    c.drawString(MARGIN, PAGE_H - 16 * mm, "Satgas Kapuas • Klasifikasi: TERBATAS")
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(COLOR_AMBER)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 11 * mm, f"Tanggal Laporan: {report_date}")
    c.setFillColor(white)
    c.setFont("Helvetica", 8)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 16 * mm, f"Dicetak: {datetime.now().strftime('%d %b %Y %H:%M')} WIB")


def _draw_footer(c: canvas.Canvas, page_num: int, total: int = 2):
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 7)
    c.drawString(MARGIN, 6 * mm, "DOKUMEN INTERNAL — TIDAK UNTUK DISEBARLUASKAN")
    c.drawRightString(PAGE_W - MARGIN, 6 * mm, f"Halaman {page_num} / {total}")
    c.setStrokeColor(COLOR_BORDER)
    c.line(MARGIN, 10 * mm, PAGE_W - MARGIN, 10 * mm)


def _cog_panel(c: canvas.Canvas, x, y, w, h, cog: str, items: list):
    color = COG_COLORS.get(cog, COLOR_AMBER)
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    # color tab
    c.setFillColor(color)
    c.rect(x, y + h - 6 * mm, w, 6 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 2 * mm, y + h - 4.2 * mm, f"COG • {cog.upper()}")
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 7)
    c.drawRightString(x + w - 2 * mm, y + h - 4.2 * mm, f"{len(items)} item")

    # list items
    c.setFillColor(COLOR_TEXT)
    cur_y = y + h - 9 * mm
    if not items:
        c.setFont("Helvetica-Oblique", 8)
        c.setFillColor(COLOR_MUTED)
        c.drawString(x + 2 * mm, cur_y, "— Tidak ada laporan —")
        return
    for it in items[:3]:
        if cur_y < y + 4 * mm:
            break
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(COLOR_TEXT)
        title = it.get("judul", "")
        for line in _wrap(title, 48)[:2]:
            c.drawString(x + 2 * mm, cur_y, "• " + line)
            cur_y -= 3.2 * mm
        c.setFont("Helvetica", 7)
        c.setFillColor(COLOR_MUTED)
        analisa = it.get("analisa", "")
        for line in _wrap(analisa, 56)[:2]:
            c.drawString(x + 3.5 * mm, cur_y, line)
            cur_y -= 3.0 * mm
        cur_y -= 1 * mm


def _draw_kpis(c: canvas.Canvas, x, y, w, h, data: dict):
    c.setStrokeColor(COLOR_BORDER)
    c.rect(x, y, w, h, stroke=1, fill=0)
    c.setFillColor(COLOR_HEADER)
    c.rect(x, y + h - 6 * mm, w, 6 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 2 * mm, y + h - 4.2 * mm, "RINGKASAN STATISTIK HARIAN")

    metrics = [
        ("BERITA LID", len(data.get("lid", [])), COLOR_AMBER),
        ("PROFILING", len(data.get("kontra", [])), COLOR_RED),
        ("KONTEN GAL", len(data.get("gal", [])), COLOR_BLUE),
        ("MEDMON", len(data.get("medmon", [])), COLOR_PURPLE),
        ("POSISI OPM", len(data.get("geoint", [])), COLOR_GREEN),
        ("PIKET", len(data.get("piket", [])), COLOR_MUTED),
    ]
    cw = w / 6
    inner_y = y + 4 * mm
    for i, (label, val, col) in enumerate(metrics):
        cx = x + i * cw
        c.setFillColor(col)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(cx + cw / 2, inner_y + 12 * mm, str(val))
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(cx + cw / 2, inner_y + 6 * mm, label)
        if i < 5:
            c.setStrokeColor(COLOR_BORDER)
            c.line(cx + cw, inner_y + 1 * mm, cx + cw, inner_y + h - 9 * mm)


def _section_title(c: canvas.Canvas, x, y, w, title: str):
    c.setFillColor(COLOR_HEADER)
    c.rect(x, y, w, 5 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x + 2 * mm, y + 1.5 * mm, title)


def _draw_summary_text(c: canvas.Canvas, x, y, w, h, ai_text: str | None, data: dict):
    c.setStrokeColor(COLOR_BORDER)
    c.rect(x, y, w, h, stroke=1, fill=0)
    _section_title(c, x, y + h - 5 * mm, w, "RINGKASAN NARATIF (AI)")

    text = ai_text or _fallback_summary(data)
    text = re.sub(r"\*\*", "", text)  # strip markdown bold
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

    c.setFillColor(COLOR_TEXT)
    cur_y = y + h - 9 * mm
    for paragraph in text.split("\n"):
        if cur_y < y + 4 * mm:
            break
        if not paragraph.strip():
            cur_y -= 2 * mm
            continue
        is_heading = bool(re.match(r"^(RINGKASAN|ANALISA|REKOMENDASI|\d+\.\s*(ACEH|JAKARTA|PAPUA|INTERNASIONAL))",
                                   paragraph.strip(), re.IGNORECASE))
        if is_heading:
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(COLOR_HEADER)
        else:
            c.setFont("Helvetica", 7.8)
            c.setFillColor(COLOR_TEXT)
        for line in _wrap(paragraph.strip(), 95):
            if cur_y < y + 4 * mm:
                break
            c.drawString(x + 2 * mm, cur_y, line)
            cur_y -= 3.1 * mm
        cur_y -= 0.5 * mm


def _fallback_summary(data: dict) -> str:
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
                parts.append(f"- {it.get('judul','')} — {it.get('analisa','')[:160]}")
        else:
            parts.append("- Tidak ada laporan signifikan.")
        parts.append("")
    parts.append("ANALISA & REKOMENDASI:")
    parts.append(f"- Total {len(data.get('lid', []))} berita trending, "
                 f"{len(data.get('kontra', []))} profiling, "
                 f"{len(data.get('geoint', []))} posisi OPM termonitor.")
    parts.append("- Tindak lanjuti rekomendasi tim sesuai prioritas pimpinan.")
    return "\n".join(parts)


def _draw_geoint_table(c: canvas.Canvas, x, y, w, h, data: dict):
    c.setStrokeColor(COLOR_BORDER)
    c.rect(x, y, w, h, stroke=1, fill=0)
    _section_title(c, x, y + h - 5 * mm, w, "GEOINT — POSISI OPM TERMONITOR")
    items = data.get("geoint", [])
    cur_y = y + h - 9 * mm
    # header row
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica-Bold", 6.5)
    cols = [("WILAYAH", 2 * mm), ("NAMA", 38 * mm), ("STATUS", 78 * mm),
            ("LAT, LON", 100 * mm), ("KET.", 130 * mm)]
    for label, dx in cols:
        c.drawString(x + dx, cur_y, label)
    cur_y -= 3 * mm
    c.setStrokeColor(COLOR_BORDER)
    c.line(x + 1 * mm, cur_y + 1 * mm, x + w - 1 * mm, cur_y + 1 * mm)
    c.setFont("Helvetica", 7)
    c.setFillColor(COLOR_TEXT)
    for it in items[:6]:
        if cur_y < y + 4 * mm:
            break
        c.drawString(x + 2 * mm, cur_y, str(it.get("wilayah", ""))[:18])
        c.drawString(x + 38 * mm, cur_y, str(it.get("nama_orang", ""))[:20])
        status = it.get("status", "")
        c.setFillColor(COLOR_RED if status == "aktif" else COLOR_GREEN)
        c.drawString(x + 78 * mm, cur_y, status.upper())
        c.setFillColor(COLOR_TEXT)
        c.drawString(x + 100 * mm, cur_y, f"{it.get('lat','-')}, {it.get('lon','-')}")
        c.drawString(x + 130 * mm, cur_y, str(it.get("keterangan", ""))[:30])
        cur_y -= 3.5 * mm
    if not items:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawString(x + 2 * mm, cur_y - 1 * mm, "— Tidak ada laporan GEOINT —")


def _draw_medmon_summary(c: canvas.Canvas, x, y, w, h, data: dict):
    c.setStrokeColor(COLOR_BORDER)
    c.rect(x, y, w, h, stroke=1, fill=0)
    _section_title(c, x, y + h - 5 * mm, w, "MEDIA MONITORING")
    items = data.get("medmon", [])
    cur_y = y + h - 9 * mm
    if not items:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawString(x + 2 * mm, cur_y, "— Tidak ada laporan MEDMON —")
        return
    for it in items[:4]:
        if cur_y < y + 4 * mm:
            break
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(COLOR_HEADER)
        c.drawString(x + 2 * mm, cur_y, f"• {it.get('subjek','-').upper()}")
        positifs = sum(1 for b in it.get("berita", []) if b.get("sentiment") == "positif")
        negatifs = sum(1 for b in it.get("berita", []) if b.get("sentiment") == "negatif")
        c.setFillColor(COLOR_GREEN)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(x + w - 30 * mm, cur_y, f"+{positifs}")
        c.setFillColor(COLOR_RED)
        c.drawString(x + w - 22 * mm, cur_y, f"-{negatifs}")
        cur_y -= 3.2 * mm
        c.setFont("Helvetica", 7)
        c.setFillColor(COLOR_MUTED)
        for line in _wrap(it.get("analisa", ""), 60)[:2]:
            c.drawString(x + 4 * mm, cur_y, line)
            cur_y -= 2.8 * mm
        cur_y -= 1 * mm


def _draw_kontra_summary(c: canvas.Canvas, x, y, w, h, data: dict):
    c.setStrokeColor(COLOR_BORDER)
    c.rect(x, y, w, h, stroke=1, fill=0)
    _section_title(c, x, y + h - 5 * mm, w, "KONTRA — PROFILING TO")
    items = data.get("kontra", [])
    cur_y = y + h - 9 * mm
    if not items:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Oblique", 7.5)
        c.drawString(x + 2 * mm, cur_y, "— Tidak ada laporan KONTRA —")
        return
    for it in items[:4]:
        if cur_y < y + 4 * mm:
            break
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(COLOR_HEADER)
        c.drawString(x + 2 * mm, cur_y, f"• {it.get('nama_to','')}")
        c.setFillColor(COLOR_RED if it.get("sumber") == "to_satgas" else COLOR_BLUE)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawRightString(x + w - 2 * mm, cur_y, it.get("sumber", "").upper().replace("_", " "))
        cur_y -= 3 * mm
        c.setFont("Helvetica", 7)
        c.setFillColor(COLOR_MUTED)
        for line in _wrap(it.get("keterangan", "") or it.get("data_diri", ""), 60)[:2]:
            c.drawString(x + 4 * mm, cur_y, line)
            cur_y -= 2.8 * mm
        cur_y -= 0.5 * mm


def build_summary_pdf(data: dict, ai_text: str | None) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    rd = data.get("report_date", "")

    # ===== PAGE 1 =====
    _draw_header(c, rd)
    # KPIs strip
    kpi_h = 28 * mm
    kpi_y = PAGE_H - 22 * mm - kpi_h - 4 * mm
    _draw_kpis(c, MARGIN, kpi_y, PAGE_W - 2 * MARGIN, kpi_h, data)

    # 4 COG panels (2x2 grid)
    grid_top = kpi_y - 4 * mm
    grid_bottom = 14 * mm
    grid_h = grid_top - grid_bottom
    grid_w = PAGE_W - 2 * MARGIN
    cell_w = (grid_w - 4 * mm) / 2
    cell_h = (grid_h - 4 * mm) / 2

    by_cog = {"aceh": [], "jakarta": [], "papua": [], "internasional": []}
    for it in data.get("lid", []):
        by_cog.setdefault(it.get("cog", ""), []).append(it)

    positions = [
        ("aceh", MARGIN, grid_top - cell_h),
        ("jakarta", MARGIN + cell_w + 4 * mm, grid_top - cell_h),
        ("papua", MARGIN, grid_top - cell_h * 2 - 4 * mm),
        ("internasional", MARGIN + cell_w + 4 * mm, grid_top - cell_h * 2 - 4 * mm),
    ]
    for cog, px, py in positions:
        _cog_panel(c, px, py, cell_w, cell_h, cog, by_cog.get(cog, []))

    _draw_footer(c, 1)
    c.showPage()

    # ===== PAGE 2 =====
    _draw_header(c, rd)
    # AI summary big block on top
    sum_h = 90 * mm
    sum_y = PAGE_H - 22 * mm - sum_h - 4 * mm
    _draw_summary_text(c, MARGIN, sum_y, PAGE_W - 2 * MARGIN, sum_h, ai_text, data)

    # bottom: 3 columns
    bottom_top = sum_y - 4 * mm
    bottom_bottom = 14 * mm
    bottom_h = bottom_top - bottom_bottom
    total_w = PAGE_W - 2 * MARGIN
    col_w = (total_w - 8 * mm) / 3
    _draw_geoint_table(c, MARGIN, bottom_bottom, col_w, bottom_h, data)
    _draw_medmon_summary(c, MARGIN + col_w + 4 * mm, bottom_bottom, col_w, bottom_h, data)
    _draw_kontra_summary(c, MARGIN + 2 * (col_w + 4 * mm), bottom_bottom, col_w, bottom_h, data)

    _draw_footer(c, 2)
    c.showPage()
    c.save()
    return buf.getvalue()
