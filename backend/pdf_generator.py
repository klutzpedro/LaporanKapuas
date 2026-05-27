"""PDF generator for BAIS daily summary. Max 2 pages.

NEW LAYOUT (per user request):
- Page 1 = EXECUTIVE SUMMARY (AI narrative) at the top + compact KPI strip + 4 small COG tiles.
- Page 2 = Supporting data with uploaded images displayed.

If ai_html is provided, render the executive summary with rich text (bold, italic,
underline, color, font, size) via reportlab Paragraph + HTML translation.
"""
import io
import base64
import re
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT

from bs4 import BeautifulSoup, NavigableString

PAGE_W, PAGE_H = A4
MARGIN = 12 * mm

COLOR_HEADER = HexColor("#0B1220")
COLOR_AMBER = HexColor("#F59E0B")
COLOR_RED = HexColor("#EF4444")
COLOR_GREEN = HexColor("#10B981")
COLOR_BLUE = HexColor("#3B82F6")
COLOR_PURPLE = HexColor("#8B5CF6")
COLOR_TEXT = HexColor("#0F172A")
COLOR_MUTED = HexColor("#475569")
COLOR_BORDER = HexColor("#CBD5E1")
COLOR_BORDER2 = HexColor("#E2E8F0")
COLOR_LIGHT = HexColor("#F8FAFC")

COG_COLORS = {
    "aceh": COLOR_GREEN,
    "jakarta": COLOR_BLUE,
    "papua": COLOR_AMBER,
    "internasional": COLOR_PURPLE,
}


# ---------- UTILS ----------
def wrap_to_width(text, font_name, font_size, max_width_pt):
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
    text = (text or "").strip()
    if stringWidth(text, font_name, font_size) <= max_width_pt:
        return text
    while text and stringWidth(text + "…", font_name, font_size) > max_width_pt:
        text = text[:-1]
    return text + "…" if text else ""


def decode_image(data_url):
    if not data_url:
        return None
    try:
        s = data_url.split(",", 1)[1] if "," in data_url else data_url
        return ImageReader(io.BytesIO(base64.b64decode(s)))
    except Exception:
        return None


def fit_image(c, img, x, y, max_w, max_h):
    """Draw image inside box (x,y) with max_w/max_h, preserving aspect ratio, centered."""
    if not img:
        return
    iw, ih = img.getSize()
    if iw <= 0 or ih <= 0:
        return
    ratio = min(max_w / iw, max_h / ih)
    w, h = iw * ratio, ih * ratio
    cx = x + (max_w - w) / 2
    cy = y + (max_h - h) / 2
    try:
        c.drawImage(img, cx, cy, width=w, height=h, mask="auto", preserveAspectRatio=True)
    except Exception:
        pass


# ---------- HEADER / FOOTER ----------
def _draw_header(c, report_date):
    c.setFillColor(COLOR_HEADER)
    c.rect(0, PAGE_H - 18 * mm, PAGE_W, 18 * mm, stroke=0, fill=1)
    c.setFillColor(COLOR_AMBER)
    c.rect(MARGIN, PAGE_H - 18 * mm, 3 * mm, 18 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(MARGIN + 6 * mm, PAGE_H - 9 * mm, "BAIS TNI · SUMMARY GEOSPASIKA HARIAN")
    c.setFont("Helvetica", 7)
    c.drawString(MARGIN + 6 * mm, PAGE_H - 13.5 * mm, "Satgas Kapuas  ·  Klasifikasi: TERBATAS")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(COLOR_AMBER)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 9 * mm, f"Tanggal: {report_date}")
    c.setFillColor(HexColor("#94A3B8"))
    c.setFont("Helvetica", 7)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 13.5 * mm,
                      f"Dicetak {datetime.now().strftime('%d %b %Y %H:%M')} WIB")


def _draw_footer(c, page_num, total=2):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.4)
    c.line(MARGIN, 9 * mm, PAGE_W - MARGIN, 9 * mm)
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 6.5)
    c.drawString(MARGIN, 5.5 * mm, "DOKUMEN INTERNAL — TIDAK UNTUK DISEBARLUASKAN")
    c.drawRightString(PAGE_W - MARGIN, 5.5 * mm, f"Hal {page_num} / {total}")


def _panel_title(c, x, y, w, title, kicker=None, color=COLOR_HEADER):
    bar_h = 5 * mm
    c.setFillColor(color)
    c.rect(x, y - bar_h, w, bar_h, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + 2 * mm, y - bar_h + 1.5 * mm, title)
    if kicker:
        c.setFillColor(COLOR_AMBER)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawRightString(x + w - 2 * mm, y - bar_h + 1.5 * mm, kicker)
    return y - bar_h - 1 * mm


def _empty(c, x, y, label="— Tidak ada laporan —"):
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica-Oblique", 6.5)
    c.drawString(x + 2.5 * mm, y - 3.5 * mm, label)


# ---------- HTML → reportlab Paragraph markup ----------
# reportlab.platypus.Paragraph supports a limited HTML-like markup:
# <b>, <i>, <u>, <font name=".." size=".." color="#..">, <br/>, <para>, etc.
# We translate Tiptap-generated HTML into a sequence of paragraph dicts with style.

_TIPTAP_FONT_MAP = {
    "ibm plex sans": "Helvetica",
    "georgia": "Times-Roman",
    "times new roman": "Times-Roman",
    "ibm plex mono": "Courier",
    "chivo": "Helvetica-Bold",
}


def _font_lookup(family_css: str) -> str:
    if not family_css:
        return None
    key = family_css.split(",")[0].strip().strip("'\"").lower()
    return _TIPTAP_FONT_MAP.get(key)


def _inline_html(node, inherited=None) -> str:
    """Recursively convert inline HTML nodes to reportlab inline markup."""
    inherited = inherited or {}
    if isinstance(node, NavigableString):
        text = str(node).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return text
    if not getattr(node, "name", None):
        return ""

    name = node.name.lower()
    # Block-level tags handled outside; here only inline
    inner = "".join(_inline_html(c, inherited) for c in node.children)

    if name in ("strong", "b"):
        return f"<b>{inner}</b>"
    if name in ("em", "i"):
        return f"<i>{inner}</i>"
    if name == "u":
        return f"<u>{inner}</u>"
    if name == "br":
        return "<br/>"
    if name in ("span", "font"):
        style = (node.get("style") or "").lower()
        attrs = {}
        # font-family
        m = re.search(r"font-family:\s*([^;]+)", style)
        if m:
            fn = _font_lookup(m.group(1).strip())
            if fn:
                attrs["face"] = fn
        # font-size: support px values
        m = re.search(r"font-size:\s*(\d+(?:\.\d+)?)\s*px", style)
        if m:
            # px -> pt approx (px * 0.75)
            attrs["size"] = str(round(float(m.group(1)) * 0.75, 1))
        # color
        m = re.search(r"color:\s*(#[0-9A-Fa-f]{3,8}|rgb\([^)]+\))", style)
        if m:
            attrs["color"] = m.group(1)
        if not attrs:
            return inner
        attrs_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        return f"<font {attrs_str}>{inner}</font>"
    if name == "a":
        href = node.get("href", "")
        return f'<font color="#3B82F6"><u>{inner}</u></font>' if not href else f'<link href="{href}"><font color="#3B82F6"><u>{inner}</u></font></link>'

    return inner


def html_to_paragraphs(html: str, base_size_pt: float = 8.5) -> list:
    """Parse HTML and return list of (style_kwargs, markup_text) tuples for Paragraph."""
    soup = BeautifulSoup(html or "", "html.parser")
    blocks = []

    def push(text, **style):
        text = (text or "").strip()
        if not text:
            return
        blocks.append((style, text))

    body = soup.body or soup
    for el in body.find_all(recursive=False):
        nm = el.name.lower() if el.name else ""
        if nm in ("h1",):
            push(_inline_html(el), size=base_size_pt + 4, bold=True, color="#0B1220", space=2)
        elif nm == "h2":
            push(_inline_html(el), size=base_size_pt + 2.5, bold=True, color="#F59E0B", space=1.5)
        elif nm == "h3":
            push(_inline_html(el), size=base_size_pt + 1.5, bold=True, color="#0B1220", space=1)
        elif nm in ("p", "div"):
            push(_inline_html(el), size=base_size_pt, space=1)
        elif nm in ("ul", "ol"):
            for i, li in enumerate(el.find_all("li", recursive=False), 1):
                bullet = "•" if nm == "ul" else f"{i}."
                push(f'<font color="#F59E0B">{bullet}</font>&nbsp;&nbsp;{_inline_html(li)}',
                     size=base_size_pt, space=0.5, indent=8)
        elif nm == "hr":
            blocks.append(({"hr": True, "space": 1}, ""))
        elif nm == "br":
            blocks.append(({"space": 0.5}, ""))
        else:
            # Fallback: treat as paragraph
            push(_inline_html(el), size=base_size_pt, space=1)

    # If no block-level tags found, just dump whole content as a paragraph
    if not blocks:
        text = _inline_html(body)
        if text.strip():
            push(text, size=base_size_pt, space=1)
    return blocks


def _make_pstyle(name, size, bold=False, color="#0F172A", indent=0):
    return ParagraphStyle(
        name=name,
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        leading=size * 1.25,
        textColor=HexColor(color),
        alignment=TA_LEFT,
        leftIndent=indent,
        spaceBefore=0,
        spaceAfter=0,
    )


# ---------- EXECUTIVE SUMMARY (PAGE 1 - BIG) ----------
HEADING_RE = re.compile(
    r"^(RINGKASAN\b|ANALISA\b|REKOMENDASI\b|ANALISA\s*&\s*REKOMENDASI\b|"
    r"\d+\.\s*(?:ACEH|JAKARTA|PAPUA|INTERNASIONAL)\b)",
    re.IGNORECASE,
)


def _draw_executive_summary(c, x, y, w, h, ai_text, data, ai_html=None):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    title_y = _panel_title(c, x, y + h, w, "EXECUTIVE SUMMARY — RINGKASAN HARIAN PIMPINAN",
                           kicker="AI · CLAUDE SONNET 4.5 · EDITABLE")

    # Frame for paragraph flow (with inner padding)
    pad_l, pad_r, pad_t, pad_b = 4 * mm, 4 * mm, 2 * mm, 3 * mm
    frame_x = x + pad_l
    frame_y = y + pad_b
    frame_w = w - pad_l - pad_r
    frame_h = title_y - frame_y - pad_t
    frame = Frame(frame_x, frame_y, frame_w, frame_h,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                  showBoundary=0)

    # Render rich HTML if available, else fallback to plain text rendering
    if ai_html:
        blocks = html_to_paragraphs(ai_html, base_size_pt=8.5)
        flowables = []
        from reportlab.platypus import Spacer, HRFlowable
        for style, text in blocks:
            if style.get("hr"):
                flowables.append(HRFlowable(width="100%", thickness=0.4,
                                            color=HexColor("#CBD5E1"),
                                            spaceBefore=2, spaceAfter=2))
                continue
            sp = style.get("space", 1)
            ps = _make_pstyle(
                "p",
                size=style.get("size", 8.5),
                bold=style.get("bold", False),
                color=style.get("color", "#0F172A"),
                indent=style.get("indent", 0),
            )
            try:
                flowables.append(Paragraph(text, ps))
            except Exception:
                # Fallback if markup is invalid: strip tags and retry
                safe = re.sub(r"<[^>]+>", "", text)
                flowables.append(Paragraph(safe, ps))
            if sp > 0:
                flowables.append(Spacer(1, sp * mm))
        # Add flowables until frame full
        for f in flowables:
            if not frame.add(f, c):
                break
    else:
        # Plain text fallback (previous behavior)
        text = ai_text or _fallback_summary(data)
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
        cur_y = title_y - 1 * mm
        inner_w = w - 7 * mm
        bottom = y + 2 * mm
        for paragraph in text.split("\n"):
            if cur_y < bottom + 3 * mm:
                break
            if not paragraph.strip():
                cur_y -= 1.2 * mm
                continue
            is_heading = bool(HEADING_RE.match(paragraph.strip()))
            if is_heading:
                font_name, font_size, line_h = "Helvetica-Bold", 8.2, 3.2 * mm
                c.setFillColor(COLOR_HEADER)
            else:
                font_name, font_size, line_h = "Helvetica", 8, 3.0 * mm
                c.setFillColor(COLOR_TEXT)
            c.setFont(font_name, font_size)
            for line in wrap_to_width(paragraph.strip(), font_name, font_size, inner_w):
                if cur_y < bottom + 2 * mm:
                    break
                c.drawString(x + 3.5 * mm, cur_y - line_h + 0.8 * mm, line)
                cur_y -= line_h
            cur_y -= 0.3 * mm


def _fallback_summary(data):
    parts = ["RINGKASAN EKSEKUTIF:",
             "Laporan harian berdasarkan input seluruh tim operasional.",
             ""]
    by_cog = {"aceh": [], "jakarta": [], "papua": [], "internasional": []}
    for it in data.get("lid", []):
        by_cog.setdefault(it.get("cog", ""), []).append(it)
    for cog_key, label in [("aceh", "1. ACEH"), ("jakarta", "2. JAKARTA"),
                           ("papua", "3. PAPUA"), ("internasional", "4. INTERNASIONAL")]:
        parts.append(label + ":")
        items = by_cog.get(cog_key, [])
        if items:
            for it in items[:2]:
                parts.append(f"- {it.get('judul','')} — {(it.get('analisa','') or '')[:120]}")
        else:
            parts.append("- Tidak ada laporan signifikan.")
    parts.append("")
    parts.append("ANALISA & REKOMENDASI:")
    parts.append(f"- Total {len(data.get('lid', []))} berita, "
                 f"{len(data.get('kontra', []))} profiling, "
                 f"{len(data.get('geoint', []))} posisi OPM, "
                 f"{len(data.get('medmon', []))} medmon, "
                 f"{len(data.get('gal', []))} konten galang.")
    parts.append("- Tindak lanjuti rekomendasi tim sesuai prioritas pimpinan.")
    return "\n".join(parts)


# ---------- KPI STRIP (compact) ----------
def _draw_kpis(c, x, y, w, h, data):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    metrics = [
        ("LID", len(data.get("lid", [])), COLOR_AMBER),
        ("KONTRA", len(data.get("kontra", [])), COLOR_RED),
        ("GAL", len(data.get("gal", [])), COLOR_BLUE),
        ("MEDMON", len(data.get("medmon", [])), COLOR_PURPLE),
        ("GEOINT", len(data.get("geoint", [])), COLOR_GREEN),
        ("PIKET", len(data.get("piket", [])), COLOR_MUTED),
    ]
    cw = w / 6
    val_y = y + h - 6 * mm
    label_y = y + 2 * mm
    for i, (label, val, col) in enumerate(metrics):
        cx = x + i * cw
        c.setFillColor(col)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(cx + cw / 2, val_y, str(val))
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Bold", 6)
        c.drawCentredString(cx + cw / 2, label_y, label)
        if i < 5:
            c.setStrokeColor(COLOR_BORDER2)
            c.setLineWidth(0.3)
            c.line(cx + cw, y + 1.5 * mm, cx + cw, y + h - 1.5 * mm)


# ---------- COG MINI TILES (compact) ----------
def _draw_cog_mini(c, x, y, w, h, cog, items):
    color = COG_COLORS.get(cog, COLOR_AMBER)
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    # left color stripe
    c.setFillColor(color)
    c.rect(x, y, 2 * mm, h, stroke=0, fill=1)
    # title
    c.setFillColor(COLOR_HEADER)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + 3.5 * mm, y + h - 4 * mm, cog.upper())
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawRightString(x + w - 2 * mm, y + h - 4 * mm, f"{len(items)} ITEM")

    inner_w = w - 5 * mm
    cur_y = y + h - 7 * mm
    if not items:
        _empty(c, x + 1 * mm, cur_y + 4 * mm, "— Tidak ada —")
        return
    for it in items[:2]:
        if cur_y < y + 3 * mm:
            break
        c.setFillColor(COLOR_TEXT)
        c.setFont("Helvetica-Bold", 6.8)
        for line in wrap_to_width(it.get("judul", "—"), "Helvetica-Bold", 6.8, inner_w)[:2]:
            if cur_y < y + 3 * mm:
                break
            c.drawString(x + 3.5 * mm, cur_y - 2 * mm, line)
            cur_y -= 2.6 * mm
        cur_y -= 0.5 * mm


# ---------- PAGE 2: SUPPORTING DATA WITH IMAGES ----------
def _section_header(c, x, y, w, text, count_text=None, color=COLOR_HEADER):
    bar_h = 4.5 * mm
    c.setFillColor(color)
    c.rect(x, y - bar_h, w, bar_h, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x + 2 * mm, y - bar_h + 1.3 * mm, text)
    if count_text:
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(COLOR_AMBER)
        c.drawRightString(x + w - 2 * mm, y - bar_h + 1.3 * mm, count_text)
    return y - bar_h


def _draw_lid_strip(c, x, y, w, h, data):
    """LID with thumbnail of sentiment image."""
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    cy = _section_header(c, x, y + h, w, "BERITA TRENDING (TIM LID)",
                         f"{len(data.get('lid', []))} ITEM")

    items = data.get("lid", [])
    if not items:
        _empty(c, x, cy - 1 * mm, "Tidak ada berita.")
        return

    # 4 mini cards horizontal (Aceh, Jakarta, Papua, Internasional)
    by_cog = {"aceh": [], "jakarta": [], "papua": [], "internasional": []}
    for it in items:
        by_cog.setdefault(it.get("cog", ""), []).append(it)

    bottom = y + 2 * mm
    body_h = cy - bottom
    col_w = (w - 6 * mm) / 4

    for i, cog in enumerate(["aceh", "jakarta", "papua", "internasional"]):
        col_x = x + 1.5 * mm + i * (col_w + 0.5 * mm)
        color = COG_COLORS[cog]
        # COG badge
        c.setFillColor(color)
        c.rect(col_x, cy - 4 * mm, col_w, 3 * mm, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 6)
        c.drawString(col_x + 1 * mm, cy - 4 * mm + 0.9 * mm, cog.upper())
        # take first item only (most important news)
        it = (by_cog.get(cog) or [{}])[0]
        if not it:
            continue
        # title (2 lines)
        c.setFillColor(COLOR_TEXT)
        c.setFont("Helvetica-Bold", 6.5)
        title_y = cy - 6.5 * mm
        for line in wrap_to_width(it.get("judul", "—"), "Helvetica-Bold", 6.5, col_w - 1 * mm)[:2]:
            c.drawString(col_x + 0.5 * mm, title_y, line)
            title_y -= 2.5 * mm
        # sentiment image area (if any)
        img_top = title_y - 1 * mm
        img_h = max(8 * mm, img_top - bottom - 1 * mm)
        if it.get("sentiment_image"):
            img = decode_image(it["sentiment_image"])
            if img:
                fit_image(c, img, col_x + 0.5 * mm, bottom, col_w - 1 * mm, img_h)


def _draw_medmon_with_images(c, x, y, w, h, data):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    cy = _section_header(c, x, y + h, w, "MEDIA MONITORING",
                         f"{len(data.get('medmon', []))} SUBJEK")
    items = data.get("medmon", [])
    if not items:
        _empty(c, x, cy - 1 * mm)
        return
    bottom = y + 2 * mm
    body_h = cy - bottom

    # Show up to 3 items as rows: [name+stats text col] | [pie chart] | [chart sumber]
    rows = items[:3]
    row_h = (body_h - 1 * mm) / max(1, len(rows))
    for i, it in enumerate(rows):
        ry = cy - 1 * mm - (i + 1) * row_h
        # subject name
        c.setFillColor(COLOR_HEADER)
        c.setFont("Helvetica-Bold", 7.5)
        subj = truncate_to_width(str(it.get("subjek", "-")).upper(), "Helvetica-Bold", 7.5, w * 0.35)
        c.drawString(x + 2 * mm, ry + row_h - 3 * mm, subj)
        # sentiment chips
        positifs = sum(1 for b in it.get("berita", []) if b.get("sentiment") == "positif")
        negatifs = sum(1 for b in it.get("berita", []) if b.get("sentiment") == "negatif")
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(COLOR_GREEN)
        c.drawString(x + 2 * mm, ry + row_h - 6 * mm, f"+{positifs} positif")
        c.setFillColor(COLOR_RED)
        c.drawString(x + 18 * mm, ry + row_h - 6 * mm, f"−{negatifs} negatif")
        # analisa
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica", 6)
        text_col_w = w * 0.42 - 2 * mm
        line_y = ry + row_h - 9 * mm
        for ln in wrap_to_width(it.get("analisa", ""), "Helvetica", 6, text_col_w)[:3]:
            c.drawString(x + 2 * mm, line_y, ln)
            line_y -= 2.3 * mm
        # pie chart image
        img_w = w * 0.27
        pie_x = x + w * 0.43
        img = decode_image(it.get("pie_sentiment_image"))
        c.setFont("Helvetica", 5.5)
        c.setFillColor(COLOR_MUTED)
        c.drawString(pie_x, ry + row_h - 3 * mm, "PIE SENTIMENT")
        if img:
            fit_image(c, img, pie_x, ry + 1 * mm, img_w - 1 * mm, row_h - 4 * mm)
        else:
            c.setFillColor(COLOR_LIGHT)
            c.rect(pie_x, ry + 1 * mm, img_w - 1 * mm, row_h - 4 * mm, stroke=0, fill=1)
        # chart sumber
        chart_x = x + w * 0.7
        img2 = decode_image(it.get("chart_sumber_image"))
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica", 5.5)
        c.drawString(chart_x, ry + row_h - 3 * mm, "CHART SUMBER")
        if img2:
            fit_image(c, img2, chart_x, ry + 1 * mm, w * 0.28 - 1 * mm, row_h - 4 * mm)
        else:
            c.setFillColor(COLOR_LIGHT)
            c.rect(chart_x, ry + 1 * mm, w * 0.28 - 1 * mm, row_h - 4 * mm, stroke=0, fill=1)
        # divider
        if i < len(rows) - 1:
            c.setStrokeColor(COLOR_BORDER2)
            c.setLineWidth(0.3)
            c.line(x + 1 * mm, ry, x + w - 1 * mm, ry)


def _draw_geoint_with_map(c, x, y, w, h, data):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    cy = _section_header(c, x, y + h, w, "GEOINT · POSISI OPM",
                         f"{len(data.get('geoint', []))} TITIK")
    items = data.get("geoint", [])
    if not items:
        _empty(c, x, cy - 1 * mm)
        return
    bottom = y + 2 * mm
    body_h = cy - bottom

    # left: compact table; right: map image of first item (if any)
    tbl_w = w * 0.55
    img_w = w * 0.45

    # table
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica-Bold", 5.5)
    c.drawString(x + 2 * mm, cy - 3 * mm, "WILAYAH")
    c.drawString(x + 22 * mm, cy - 3 * mm, "NAMA")
    c.drawString(x + tbl_w - 18 * mm, cy - 3 * mm, "STATUS")
    c.drawString(x + tbl_w - 6 * mm, cy - 3 * mm, "")
    line_y = cy - 5 * mm
    c.setStrokeColor(COLOR_BORDER2)
    c.line(x + 1 * mm, line_y, x + tbl_w - 1 * mm, line_y)

    cur_y = line_y - 2.5 * mm
    c.setFont("Helvetica", 6.2)
    for it in items[:8]:
        if cur_y < bottom + 1 * mm:
            break
        c.setFillColor(COLOR_TEXT)
        c.drawString(x + 2 * mm, cur_y, truncate_to_width(str(it.get("wilayah", "-")), "Helvetica", 6.2, 18 * mm))
        c.drawString(x + 22 * mm, cur_y, truncate_to_width(str(it.get("nama_orang", "-")), "Helvetica", 6.2, tbl_w - 22 * mm - 20 * mm))
        is_aktif = it.get("status") == "aktif"
        c.setFillColor(COLOR_RED if is_aktif else COLOR_GREEN)
        c.setFont("Helvetica-Bold", 5.8)
        c.drawString(x + tbl_w - 18 * mm, cur_y, "AKTIF" if is_aktif else "NON-AKTIF")
        c.setFont("Helvetica", 6.2)
        cur_y -= 2.8 * mm

    # map image (first item with peta_image, else first item)
    map_img = None
    for it in items:
        if it.get("peta_image"):
            map_img = decode_image(it["peta_image"])
            break
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 5.5)
    c.drawString(x + tbl_w + 2 * mm, cy - 3 * mm, "PETA SEBARAN")
    if map_img:
        fit_image(c, map_img, x + tbl_w + 2 * mm, bottom + 1 * mm, img_w - 3 * mm, body_h - 6 * mm)
    else:
        c.setFillColor(COLOR_LIGHT)
        c.rect(x + tbl_w + 2 * mm, bottom + 1 * mm, img_w - 3 * mm, body_h - 6 * mm, stroke=0, fill=1)
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Oblique", 6)
        c.drawCentredString(x + tbl_w + img_w / 2, bottom + body_h / 2,
                            "(belum ada gambar peta)")


def _draw_kontra_with_images(c, x, y, w, h, data):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    cy = _section_header(c, x, y + h, w, "KONTRA · PROFILING TO",
                         f"{len(data.get('kontra', []))} TO")
    items = data.get("kontra", [])
    if not items:
        _empty(c, x, cy - 1 * mm)
        return
    bottom = y + 2 * mm
    body_h = cy - bottom
    rows = items[:3]
    row_h = (body_h - 1 * mm) / max(1, len(rows))

    for i, it in enumerate(rows):
        ry = cy - 1 * mm - (i + 1) * row_h
        # name + tag
        c.setFillColor(COLOR_HEADER)
        c.setFont("Helvetica-Bold", 7)
        name = truncate_to_width(it.get("nama_to", "-"), "Helvetica-Bold", 7, w * 0.5)
        c.drawString(x + 2 * mm, ry + row_h - 3 * mm, name)
        is_satgas = it.get("sumber") == "to_satgas"
        c.setFont("Helvetica-Bold", 5.5)
        c.setFillColor(COLOR_RED if is_satgas else COLOR_BLUE)
        c.drawRightString(x + w * 0.6, ry + row_h - 3 * mm, "TO SATGAS" if is_satgas else "TO INTERNAL")
        # description
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica", 6)
        ket = it.get("keterangan") or it.get("data_diri") or ""
        line_y = ry + row_h - 5.5 * mm
        for ln in wrap_to_width(ket, "Helvetica", 6, w * 0.6 - 2 * mm)[:3]:
            c.drawString(x + 2 * mm, line_y, ln)
            line_y -= 2.3 * mm
        # SNA image (right)
        sna_w = w * 0.18
        sna_x = x + w * 0.62
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica", 5)
        c.drawString(sna_x, ry + row_h - 3 * mm, "SNA")
        img_sna = decode_image(it.get("sna_image"))
        if img_sna:
            fit_image(c, img_sna, sna_x, ry + 0.5 * mm, sna_w - 1 * mm, row_h - 4 * mm)
        # Lainnya image (further right)
        ln_x = x + w * 0.8
        c.drawString(ln_x, ry + row_h - 3 * mm, "LAINNYA")
        img_ln = decode_image(it.get("lainnya_image"))
        if img_ln:
            fit_image(c, img_ln, ln_x, ry + 0.5 * mm, w * 0.18 - 1 * mm, row_h - 4 * mm)
        if i < len(rows) - 1:
            c.setStrokeColor(COLOR_BORDER2)
            c.setLineWidth(0.3)
            c.line(x + 1 * mm, ry, x + w - 1 * mm, ry)


def _draw_gal_piket(c, x, y, w, h, data):
    """Combined GAL (with thumbnails) + PIKET notes."""
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    cy = _section_header(c, x, y + h, w, "GAL · KONTEN GALANG / PIKET",
                         f"GAL {len(data.get('gal', []))} · PIKET {len(data.get('piket', []))}")
    bottom = y + 2 * mm
    body_h = cy - bottom

    # split horizontally: left 60% GAL with thumbnails, right 40% PIKET text
    left_w = w * 0.6
    right_x = x + left_w + 1 * mm

    # GAL section
    items = data.get("gal", [])[:3]
    if items:
        thumb_w = (left_w - 4 * mm) / 3
        thumb_h = body_h - 6 * mm
        for i, it in enumerate(items):
            tx = x + 1 * mm + i * (thumb_w + 1 * mm)
            ty = bottom + 1 * mm
            # frame
            c.setFillColor(COLOR_LIGHT)
            c.rect(tx, ty, thumb_w, thumb_h, stroke=0, fill=1)
            img = decode_image(it.get("gambar"))
            if img:
                fit_image(c, img, tx, ty + 5 * mm, thumb_w, thumb_h - 7 * mm)
            # category badge
            cat = (it.get("kategori") or "").upper()
            cat_color = {"NARASI": COLOR_BLUE, "VIDEO": COLOR_RED, "MEDSOS": COLOR_PURPLE}.get(cat, COLOR_MUTED)
            c.setFillColor(cat_color)
            c.rect(tx, ty + thumb_h - 3 * mm, thumb_w, 3 * mm, stroke=0, fill=1)
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 5.5)
            c.drawString(tx + 1 * mm, ty + thumb_h - 3 * mm + 0.8 * mm, cat)
            # title
            c.setFillColor(COLOR_TEXT)
            c.setFont("Helvetica-Bold", 5.8)
            judul = truncate_to_width(it.get("judul", "-"), "Helvetica-Bold", 5.8, thumb_w - 1 * mm)
            c.drawString(tx + 0.5 * mm, ty + 2 * mm, judul)
    else:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawString(x + 2 * mm, cy - 5 * mm, "Tidak ada konten GAL.")

    # PIKET section (right)
    c.setStrokeColor(COLOR_BORDER2)
    c.setLineWidth(0.3)
    c.line(right_x - 1 * mm, cy - 1 * mm, right_x - 1 * mm, bottom + 1 * mm)

    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(right_x, cy - 3 * mm, "PIKET · SATGAS TEK / SANDI / MEDIS")

    piket_items = data.get("piket", [])[:4]
    cur_y = cy - 6 * mm
    if not piket_items:
        c.setFont("Helvetica-Oblique", 6)
        c.drawString(right_x, cur_y, "Tidak ada laporan piket.")
    else:
        SATGAS_COLORS = {"tek": COLOR_BLUE, "sandi": COLOR_PURPLE, "medis": COLOR_GREEN}
        for it in piket_items:
            if cur_y < bottom + 2 * mm:
                break
            c.setFillColor(SATGAS_COLORS.get(it.get("satgas"), COLOR_MUTED))
            c.setFont("Helvetica-Bold", 5.8)
            c.drawString(right_x, cur_y, f"[{(it.get('satgas') or '').upper()}] " +
                         truncate_to_width(it.get("judul", "-"), "Helvetica-Bold", 5.8, w - left_w - 8 * mm))
            cur_y -= 2.6 * mm
            c.setFillColor(COLOR_TEXT)
            c.setFont("Helvetica", 5.8)
            for ln in wrap_to_width(it.get("isi", ""), "Helvetica", 5.8, w - left_w - 4 * mm)[:2]:
                c.drawString(right_x, cur_y, ln)
                cur_y -= 2.4 * mm
            cur_y -= 1 * mm


# ---------- MAIN ----------
def build_summary_pdf(data, ai_text, ai_html=None):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    rd = data.get("report_date", "")

    # =========== PAGE 1 ===========
    _draw_header(c, rd)

    # Big AI Summary block (top, takes ~75% of body)
    body_top = PAGE_H - 18 * mm - 4 * mm
    body_bottom = 13 * mm

    # KPI strip (small, at the bottom right above footer)
    kpi_h = 14 * mm
    kpi_y = body_bottom + 0
    cog_h = 26 * mm
    cog_y = kpi_y + kpi_h + 3 * mm

    sum_top = body_top
    sum_bottom = cog_y + cog_h + 3 * mm
    sum_h = sum_top - sum_bottom
    _draw_executive_summary(c, MARGIN, sum_bottom, PAGE_W - 2 * MARGIN, sum_h, ai_text, data, ai_html=ai_html)

    # 4 mini COG tiles row
    grid_w = PAGE_W - 2 * MARGIN
    gutter = 3 * mm
    cog_w = (grid_w - 3 * gutter) / 4
    by_cog = {"aceh": [], "jakarta": [], "papua": [], "internasional": []}
    for it in data.get("lid", []):
        by_cog.setdefault(it.get("cog", ""), []).append(it)
    for i, cog in enumerate(["aceh", "jakarta", "papua", "internasional"]):
        cx = MARGIN + i * (cog_w + gutter)
        _draw_cog_mini(c, cx, cog_y, cog_w, cog_h, cog, by_cog.get(cog, []))

    # KPI strip
    _draw_kpis(c, MARGIN, kpi_y, PAGE_W - 2 * MARGIN, kpi_h, data)

    _draw_footer(c, 1)
    c.showPage()

    # =========== PAGE 2 ===========
    _draw_header(c, rd)
    avail_top = PAGE_H - 18 * mm - 4 * mm
    avail_bottom = 13 * mm
    avail_h = avail_top - avail_bottom

    # 4 vertical sections stacked, each ~25% of available height
    section_gap = 2 * mm
    section_h = (avail_h - 3 * section_gap) / 4
    w = PAGE_W - 2 * MARGIN

    # 1. LID strip
    _draw_lid_strip(c, MARGIN, avail_top - section_h, w, section_h, data)
    # 2. MEDMON with images
    y2 = avail_top - 2 * section_h - section_gap
    _draw_medmon_with_images(c, MARGIN, y2, w, section_h, data)
    # 3. GEOINT with map
    y3 = avail_top - 3 * section_h - 2 * section_gap
    _draw_geoint_with_map(c, MARGIN, y3, w, section_h, data)
    # 4. KONTRA + GAL/PIKET (split row)
    y4 = avail_bottom
    half = (w - section_gap) / 2
    _draw_kontra_with_images(c, MARGIN, y4, half, section_h, data)
    _draw_gal_piket(c, MARGIN + half + section_gap, y4, half, section_h, data)

    _draw_footer(c, 2)
    c.showPage()
    c.save()
    return buf.getvalue()
