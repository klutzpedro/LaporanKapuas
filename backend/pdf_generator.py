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

try:
    from staticmap import StaticMap, CircleMarker
    _HAS_STATICMAP = True
except Exception:
    _HAS_STATICMAP = False

from reportlab.graphics.shapes import Drawing, Wedge, String, Circle
from reportlab.graphics import renderPDF

PAGE_W, PAGE_H = A4
MARGIN = 12 * mm

COLOR_HEADER = HexColor("#0B1220")
COLOR_AMBER = HexColor("#F59E0B")
COLOR_AMBER_DARK = HexColor("#B45309")
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
    "indonesia": COLOR_RED,
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


def draw_sentiment_pie(c, cx, cy, radius, positif, negatif, netral, show_label=True):
    """Draw a donut-style sentiment pie chart at (cx, cy) with given radius (points)."""
    from math import cos, sin, radians
    total = max(1, (positif or 0) + (negatif or 0) + (netral or 0))
    segments = [
        ((positif or 0), COLOR_GREEN),
        ((negatif or 0), COLOR_RED),
        ((netral or 0), HexColor("#A1A1AA")),
    ]
    angle_start = 90.0
    for value, color in segments:
        if value <= 0:
            continue
        sweep = -(value / total) * 360.0
        c.setFillColor(color)
        c.setStrokeColor(HexColor("#0A0A0A"))
        c.setLineWidth(0.4)
        path = c.beginPath()
        path.moveTo(cx, cy)
        steps = max(8, int(abs(sweep) / 5))
        ang = angle_start
        path.lineTo(cx + radius * cos(radians(ang)), cy + radius * sin(radians(ang)))
        for i in range(1, steps + 1):
            ang = angle_start + sweep * (i / steps)
            path.lineTo(cx + radius * cos(radians(ang)), cy + radius * sin(radians(ang)))
        path.close()
        c.drawPath(path, stroke=1, fill=1)
        angle_start += sweep
    # donut hole
    c.setFillColor(HexColor("#0A0A0A"))
    c.setStrokeColor(HexColor("#0A0A0A"))
    c.circle(cx, cy, radius * 0.55, stroke=0, fill=1)
    if show_label:
        parts = [("POS", positif or 0, COLOR_GREEN),
                 ("NEG", negatif or 0, COLOR_RED),
                 ("NET", netral or 0, HexColor("#A1A1AA"))]
        top = max(parts, key=lambda p: p[1])
        c.setFillColor(top[2])
        c.setFont("Helvetica-Bold", radius * 0.45)
        c.drawCentredString(cx, cy - radius * 0.12, f"{top[1]}%")
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", radius * 0.2)
        c.drawCentredString(cx, cy - radius * 0.36, top[0])



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


def _draw_sentiment_cases_strip(c, x, y, w, h, data):
    """Draw a strip of sentiment cases (LID + GEOINT) — each case shown as a small card with mini pie + label.
    y, x, w, h are the bounding box (h is total height)."""
    # Title bar
    bar_h = 5 * mm
    c.setFillColor(COLOR_HEADER)
    c.rect(x, y + h - bar_h, w, bar_h, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 2 * mm, y + h - bar_h + 1.4 * mm, "RINGKASAN SENTIMENT PER KASUS")
    # collect cases
    cases = []
    for it in data.get("lid", []):
        if _has_sentiment(it):
            cases.append({
                "kind": "LID",
                "kind_color": COG_COLORS.get(it.get("cog", ""), COLOR_MUTED),
                "label": (it.get("cog") or "").upper(),
                "title": it.get("judul", "—"),
                "p": it.get("sentiment_positif") or 0,
                "n": it.get("sentiment_negatif") or 0,
                "u": it.get("sentiment_netral") or 0,
            })
    for it in data.get("geoint", []):
        if _has_sentiment(it):
            cases.append({
                "kind": "GEOINT",
                "kind_color": COLOR_RED if it.get("status") == "aktif" else COLOR_GREEN,
                "label": (it.get("status") or "").upper().replace("_", " "),
                "title": f"OPM · {it.get('nama_orang', '-')} ({it.get('wilayah','-')})",
                "p": it.get("sentiment_positif") or 0,
                "n": it.get("sentiment_negatif") or 0,
                "u": it.get("sentiment_netral") or 0,
            })

    body_top = y + h - bar_h - 2 * mm
    body_h = body_top - y - 1 * mm
    if not cases:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Oblique", 7)
        c.drawString(x + 2 * mm, body_top - 4 * mm, "Belum ada kasus dengan data sentiment.")
        return

    # Layout: up to 6 cards in a horizontal grid (responsive col count)
    n = len(cases)
    cols = min(n, 6)
    if n > 6:
        cols = 6
        cases = cases[:6]
    gutter = 2 * mm
    cw = (w - (cols + 1) * gutter) / cols
    ch = body_h - 2 * mm
    for i, case in enumerate(cases):
        cx = x + gutter + i * (cw + gutter)
        cy = y + 1 * mm
        # card border
        c.setStrokeColor(COLOR_BORDER)
        c.setLineWidth(0.4)
        c.rect(cx, cy, cw, ch, stroke=1, fill=0)
        # left color stripe
        c.setFillColor(case["kind_color"])
        c.rect(cx, cy, 1 * mm, ch, stroke=0, fill=1)
        # kind badge top
        c.setFillColor(case["kind_color"])
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(cx + 2 * mm, cy + ch - 3 * mm, f"{case['kind']} · {case['label']}")
        # title (2 lines max)
        c.setFillColor(COLOR_HEADER)
        c.setFont("Helvetica-Bold", 6.5)
        lines = wrap_to_width(case["title"], "Helvetica-Bold", 6.5, cw - 3 * mm)[:2]
        ty = cy + ch - 5.5 * mm
        for line in lines:
            c.drawString(cx + 2 * mm, ty, line)
            ty -= 2.3 * mm
        # pie chart centered horizontally below
        pie_area_h = (ty - cy) - 5 * mm
        pie_r = max(6 * mm, min(cw / 2 - 3 * mm, pie_area_h / 2 - 1 * mm))
        pie_cx = cx + cw / 2
        pie_cy = cy + 5 * mm + pie_r
        draw_sentiment_pie(c, pie_cx, pie_cy, pie_r, case["p"], case["n"], case["u"])
        # tiny legend at bottom
        c.setFont("Helvetica", 5)
        legend_y = cy + 1.5 * mm
        c.setFillColor(COLOR_GREEN)
        c.drawString(cx + 2 * mm, legend_y, f"+{case['p']}%")
        c.setFillColor(COLOR_RED)
        c.drawString(cx + 2 * mm + (cw - 4 * mm) * 0.34, legend_y, f"-{case['n']}%")
        c.setFillColor(HexColor("#71717A"))
        c.drawString(cx + 2 * mm + (cw - 4 * mm) * 0.67, legend_y, f"~{case['u']}%")


# ---------- PAPUA STATIC MAP (auto plotted from GEOINT coords) ----------
# Papua region bounding box (rough): lat -10.5..0, lon 130..141
PAPUA_CENTER = (138.5, -4.5)  # (lon, lat) — Tanah Papua center
PAPUA_ZOOM = 6                # covers entire Papua mainland

def render_papua_map(items, width_px=900, height_px=700):
    """Render a Papua-centered map with all OPM positions plotted.
    Aktif = red, tidak_aktif = green. Returns an ImageReader or None.
    """
    if not _HAS_STATICMAP:
        return None
    try:
        m = StaticMap(width_px, height_px, url_template="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
        # Plot markers
        for it in items:
            try:
                lat = float(it.get("lat"))
                lon = float(it.get("lon"))
            except (TypeError, ValueError):
                continue
            color = "#EF4444" if it.get("status") == "aktif" else "#10B981"
            # outer ring (white) + inner colored dot for visibility on OSM tiles
            m.add_marker(CircleMarker((lon, lat), "#FFFFFF", 14))
            m.add_marker(CircleMarker((lon, lat), color, 10))
        # Render forcing the Papua-wide view (do not auto-zoom to markers)
        image = m.render(zoom=PAPUA_ZOOM, center=PAPUA_CENTER)
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)
    except Exception:
        return None


import os

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
_LOGO_IMG = None

def _get_logo():
    global _LOGO_IMG
    if _LOGO_IMG is None and os.path.exists(LOGO_PATH):
        try:
            _LOGO_IMG = ImageReader(LOGO_PATH)
        except Exception:
            _LOGO_IMG = None
    return _LOGO_IMG


# ---------- HEADER / FOOTER ----------
def _draw_header(c, report_date):
    c.setFillColor(COLOR_HEADER)
    c.rect(0, PAGE_H - 18 * mm, PAGE_W, 18 * mm, stroke=0, fill=1)
    c.setFillColor(COLOR_AMBER)
    c.rect(MARGIN, PAGE_H - 18 * mm, 3 * mm, 18 * mm, stroke=0, fill=1)
    # logo (top-left, next to amber bar)
    logo = _get_logo()
    text_x = MARGIN + 6 * mm
    if logo:
        try:
            logo_size = 14 * mm
            c.drawImage(logo, MARGIN + 5 * mm, PAGE_H - 16 * mm, width=logo_size, height=logo_size,
                        mask="auto", preserveAspectRatio=True)
            text_x = MARGIN + 5 * mm + logo_size + 2 * mm
        except Exception:
            pass
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(text_x, PAGE_H - 9 * mm, "BAIS TNI · SUMMARY GEOSPASIKA HARIAN")
    c.setFont("Helvetica", 7)
    c.drawString(text_x, PAGE_H - 13.5 * mm, "Satgas Kapuas  ·  Klasifikasi: TERBATAS")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(COLOR_AMBER)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 9 * mm, f"Tanggal: {report_date}")
    c.setFillColor(HexColor("#94A3B8"))
    c.setFont("Helvetica", 7)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 13.5 * mm,
                      f"Dicetak {datetime.now().strftime('%d %b %Y %H:%M')} WIB")


def _draw_footer(c, page_num):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.4)
    c.line(MARGIN, 9 * mm, PAGE_W - MARGIN, 9 * mm)
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 6.5)
    c.drawString(MARGIN, 5.5 * mm, "DOKUMEN INTERNAL — TIDAK UNTUK DISEBARLUASKAN")
    c.drawRightString(PAGE_W - MARGIN, 5.5 * mm, f"Hal {page_num}")


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
    title_y = _panel_title(c, x, y + h, w, "EXECUTIVE SUMMARY — RINGKASAN HARIAN PIMPINAN")

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
    by_cog = {"aceh": [], "jakarta": [], "indonesia": [], "papua": [], "internasional": []}
    for it in data.get("lid", []):
        by_cog.setdefault(it.get("cog", ""), []).append(it)
    for cog_key, label in [("aceh", "1. ACEH"), ("jakarta", "2. JAKARTA"),
                           ("indonesia", "3. INDONESIA"),
                           ("papua", "4. PAPUA"), ("internasional", "5. INTERNASIONAL")]:
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

    # 5 mini cards horizontal (Aceh, Jakarta, Indonesia, Papua, Internasional)
    by_cog = {"aceh": [], "jakarta": [], "indonesia": [], "papua": [], "internasional": []}
    for it in items:
        by_cog.setdefault(it.get("cog", ""), []).append(it)

    bottom = y + 2 * mm
    col_w = (w - 7 * mm) / 5

    for i, cog in enumerate(["aceh", "jakarta", "indonesia", "papua", "internasional"]):
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
        if img:
            fit_image(c, img, pie_x, ry + 1 * mm, img_w - 1 * mm, row_h - 2 * mm)
        else:
            c.setFillColor(COLOR_LIGHT)
            c.rect(pie_x, ry + 1 * mm, img_w - 1 * mm, row_h - 2 * mm, stroke=0, fill=1)
        # chart sumber
        chart_x = x + w * 0.7
        img2 = decode_image(it.get("chart_sumber_image"))
        if img2:
            fit_image(c, img2, chart_x, ry + 1 * mm, w * 0.28 - 1 * mm, row_h - 2 * mm)
        else:
            c.setFillColor(COLOR_LIGHT)
            c.rect(chart_x, ry + 1 * mm, w * 0.28 - 1 * mm, row_h - 2 * mm, stroke=0, fill=1)
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

    # map image: AUTO-GENERATED Papua map with all plotted markers (overrides user upload)
    map_img = render_papua_map(items, width_px=1200, height_px=900)
    if map_img is None:
        # Fallback to user-uploaded image (if any)
        for it in items:
            if it.get("peta_image"):
                map_img = decode_image(it["peta_image"])
                break
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 5.5)
    c.drawString(x + tbl_w + 2 * mm, cy - 3 * mm, "PETA SEBARAN PAPUA")
    if map_img:
        fit_image(c, map_img, x + tbl_w + 2 * mm, bottom + 1 * mm, img_w - 3 * mm, body_h - 6 * mm)
    else:
        c.setFillColor(COLOR_LIGHT)
        c.rect(x + tbl_w + 2 * mm, bottom + 1 * mm, img_w - 3 * mm, body_h - 6 * mm, stroke=0, fill=1)
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Oblique", 6)
        c.drawCentredString(x + tbl_w + img_w / 2, bottom + body_h / 2,
                            "(peta tidak tersedia)")


def _draw_kontra_with_images(c, x, y, w, h, data):
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    cy = _section_header(c, x, y + h, w, "PROFILING (TIM KONTRA)",
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
        # name + tag (text col width = 55% so badge doesn't overlap)
        c.setFillColor(COLOR_HEADER)
        c.setFont("Helvetica-Bold", 7)
        name = truncate_to_width(it.get("nama_to", "-"), "Helvetica-Bold", 7, w * 0.45)
        c.drawString(x + 2 * mm, ry + row_h - 3 * mm, name)
        is_satgas = it.get("sumber") == "to_satgas"
        c.setFont("Helvetica-Bold", 5.5)
        c.setFillColor(COLOR_RED if is_satgas else COLOR_BLUE)
        c.drawString(x + w * 0.46, ry + row_h - 3 * mm, "TO SATGAS" if is_satgas else "TO INTERNAL")
        # description
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica", 6)
        ket = it.get("keterangan") or it.get("data_diri") or ""
        line_y = ry + row_h - 5.5 * mm
        for ln in wrap_to_width(ket, "Helvetica", 6, w * 0.6 - 2 * mm)[:4]:
            c.drawString(x + 2 * mm, line_y, ln)
            line_y -= 2.3 * mm
        # SNA image (right)
        sna_w = w * 0.18
        sna_x = x + w * 0.62
        img_sna = decode_image(it.get("sna_image"))
        if img_sna:
            fit_image(c, img_sna, sna_x, ry + 0.5 * mm, sna_w - 1 * mm, row_h - 2 * mm)
        # Lainnya image (further right)
        ln_x = x + w * 0.8
        img_ln = decode_image(it.get("lainnya_image"))
        if img_ln:
            fit_image(c, img_ln, ln_x, ry + 0.5 * mm, w * 0.18 - 1 * mm, row_h - 2 * mm)
        if i < len(rows) - 1:
            c.setStrokeColor(COLOR_BORDER2)
            c.setLineWidth(0.3)
            c.line(x + 1 * mm, ry, x + w - 1 * mm, ry)


def _draw_gal_wide(c, x, y, w, h, data):
    """Wide GAL section — shows up to 5 content thumbnails with title + category badge."""
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, y, w, h, stroke=1, fill=0)
    cy = _section_header(c, x, y + h, w, "KONTEN / NARASI / MEME (TIM GAL)",
                         f"{len(data.get('gal', []))} KONTEN")
    bottom = y + 2 * mm
    body_h = cy - bottom

    items = data.get("gal", [])[:5]
    if not items:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawString(x + 2 * mm, cy - 5 * mm, "Tidak ada konten GAL.")
        return

    n = len(items)
    gap = 1.5 * mm
    inner = w - 2 * mm - (n - 1) * gap
    thumb_w = inner / n
    thumb_h = body_h - 2 * mm
    badge_h = 3.5 * mm
    title_h = 4 * mm

    for i, it in enumerate(items):
        tx = x + 1 * mm + i * (thumb_w + gap)
        ty = bottom + 1 * mm
        # background frame
        c.setFillColor(COLOR_LIGHT)
        c.rect(tx, ty, thumb_w, thumb_h, stroke=0, fill=1)
        # image area = middle (between top badge and bottom title)
        img_area_y = ty + title_h
        img_area_h = thumb_h - badge_h - title_h
        img = decode_image(it.get("gambar"))
        if img:
            fit_image(c, img, tx, img_area_y, thumb_w, img_area_h)
        # category badge at top
        cat = (it.get("kategori") or "").upper()
        cat_color = {"NARASI": COLOR_BLUE, "VIDEO": COLOR_RED, "MEDSOS": COLOR_PURPLE}.get(cat, COLOR_MUTED)
        c.setFillColor(cat_color)
        c.rect(tx, ty + thumb_h - badge_h, thumb_w, badge_h, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 6)
        c.drawString(tx + 1 * mm, ty + thumb_h - badge_h + 1 * mm, cat or "—")
        # title at bottom
        c.setFillColor(COLOR_TEXT)
        c.setFont("Helvetica-Bold", 6.5)
        for j, line in enumerate(wrap_to_width(it.get("judul", "-"), "Helvetica-Bold", 6.5, thumb_w - 1 * mm)[:2]):
            c.drawString(tx + 0.7 * mm, ty + title_h - 1.5 * mm - j * 2.2 * mm, line)


# ---------- FULL-DETAIL CARDS (multi-page paginator) ----------
COG_LABEL = {"aceh": "ACEH", "jakarta": "JAKARTA", "indonesia": "INDONESIA", "papua": "PAPUA", "internasional": "INTERNASIONAL"}


def _has_sentiment(item):
    return ((item.get("sentiment_positif") or 0)
            + (item.get("sentiment_negatif") or 0)
            + (item.get("sentiment_netral") or 0)) > 0


def _measure_lid_card(item, w):
    pad = 2 * mm
    inner_w = w - 2 * pad
    has_pie = _has_sentiment(item)
    img_w = 32 * mm if has_pie else 0
    text_w = inner_w - (img_w + 2 * mm if img_w else 0)
    judul_lines = wrap_to_width(item.get("judul", "—"), "Helvetica-Bold", 8, text_w)[:2]
    link = (item.get("link") or "").strip()
    link_lines = wrap_to_width(link, "Helvetica", 6, text_w)[:2] if link else []
    blocks = []
    for key in ["fakta", "analisa", "tindakan", "rekomendasi"]:
        val = (item.get(key) or "").strip()
        if val:
            lines = wrap_to_width(val, "Helvetica", 6.5, text_w)[:4]
            blocks.append(lines)
    h = 3 * mm + 4 * mm
    h += 2.7 * mm * len(judul_lines)
    if link_lines:
        h += 1 * mm + 2.2 * mm * len(link_lines)
    for lines in blocks:
        h += 2.8 * mm + 2.3 * mm * len(lines) + 0.5 * mm
    h += 2 * mm
    if img_w:
        h = max(h, img_w * 0.6 + 4 * mm)
    return h


def _measure_kontra_card(item, w):
    pad = 2 * mm
    inner_w = w - 2 * pad
    medsos = [m for m in (item.get("medsos") or []) if m]
    sna_img = item.get("sna_image")
    lainnya_img = item.get("lainnya_image")
    has_imgs = bool(sna_img or lainnya_img)
    img_block_w = 38 * mm if has_imgs else 0
    text_w = inner_w - (img_block_w + 2 * mm if has_imgs else 0)
    data_lines = wrap_to_width(item.get("data_diri", "") or "", "Helvetica", 6.5, text_w)[:5]
    ket_lines = wrap_to_width(item.get("keterangan", "") or "", "Helvetica", 6.5, text_w)[:3]
    medsos_lines = []
    for m in medsos[:6]:
        for ln in wrap_to_width(m, "Helvetica", 6, text_w):
            medsos_lines.append(ln)
    h = 3 * mm + 4 * mm + 0.5 * mm
    if data_lines:
        h += 2.8 * mm + 2.3 * mm * len(data_lines) + 0.5 * mm
    if medsos_lines:
        h += 2.8 * mm + 2.2 * mm * len(medsos_lines) + 0.5 * mm
    if ket_lines:
        h += 2.8 * mm + 2.3 * mm * len(ket_lines) + 0.5 * mm
    h += 2 * mm
    if has_imgs:
        h = max(h, 35 * mm)
    return h


def _measure_gal_card(item, w):
    pad = 2 * mm
    inner_w = w - 2 * pad
    has_img = bool(item.get("gambar"))
    img_w = 40 * mm if has_img else 0
    text_w = inner_w - (img_w + 2 * mm if has_img else 0)
    judul_lines = wrap_to_width(item.get("judul", "—"), "Helvetica-Bold", 8, text_w)[:2]
    links = [lk for lk in (item.get("links") or []) if lk]
    link_lines = []
    for ln in links[:8]:
        for w_ln in wrap_to_width(ln, "Helvetica", 6, text_w):
            link_lines.append(w_ln)
    ket_lines = wrap_to_width(item.get("keterangan", "") or "", "Helvetica", 6.5, text_w)[:3]
    h = 3 * mm + 4 * mm
    h += 2.7 * mm * len(judul_lines) + 0.5 * mm
    if link_lines:
        h += 2.6 * mm + 2.2 * mm * len(link_lines) + 0.5 * mm
    if ket_lines:
        h += 2.6 * mm + 2.3 * mm * len(ket_lines) + 0.5 * mm
    h += 2 * mm
    if has_img:
        h = max(h, 32 * mm)
    return h


def _draw_lid_card(c, x, y_top, w, item):
    pad = 2 * mm
    cog = item.get("cog", "")
    cog_color = COG_COLORS.get(cog, COLOR_MUTED)
    inner_w = w - 2 * pad
    has_pie = _has_sentiment(item)
    img_w = 32 * mm if has_pie else 0
    text_w = inner_w - (img_w + 2 * mm if img_w else 0)

    # measure text content height
    judul_lines = wrap_to_width(item.get("judul", "—"), "Helvetica-Bold", 8, text_w)[:2]
    link = (item.get("link") or "").strip()
    link_lines = wrap_to_width(link, "Helvetica", 6, text_w)[:2] if link else []

    blocks = []
    for key, label in [("fakta", "FAKTA"), ("analisa", "ANALISA"),
                       ("tindakan", "TINDAKAN SATGAS"), ("rekomendasi", "REKOMENDASI BAIS")]:
        val = (item.get(key) or "").strip()
        if val:
            lines = wrap_to_width(val, "Helvetica", 6.5, text_w)[:4]
            blocks.append((label, lines))

    # estimate height
    h = 3 * mm  # top
    h += 4 * mm  # COG badge + judul row
    h += 2.5 * mm * len(judul_lines)
    if link_lines:
        h += 1 * mm + 2.2 * mm * len(link_lines)
    for _, lines in blocks:
        h += 2.8 * mm + 2.3 * mm * len(lines) + 0.5 * mm
    h += 2 * mm  # bottom
    if img_w:
        h = max(h, img_w * 0.6 + 4 * mm)  # at least image height

    y_bot = y_top - h
    # background card
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.4)
    c.rect(x, y_bot, w, h, stroke=1, fill=0)
    # left color stripe
    c.setFillColor(cog_color)
    c.rect(x, y_bot, 1.2 * mm, h, stroke=0, fill=1)

    tx = x + pad + 1.5 * mm
    cy = y_top - 3 * mm
    # COG badge
    c.setFillColor(cog_color)
    c.rect(tx, cy - 3 * mm, 18 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(tx + 1 * mm, cy - 3 * mm + 0.9 * mm, COG_LABEL.get(cog, cog.upper()))
    # judul
    c.setFillColor(COLOR_HEADER)
    c.setFont("Helvetica-Bold", 8)
    jy = cy - 6.5 * mm
    for line in judul_lines:
        c.drawString(tx, jy, line)
        jy -= 2.7 * mm
    # link
    if link_lines:
        c.setFillColor(COLOR_AMBER_DARK)
        c.setFont("Helvetica", 6)
        jy -= 0.5 * mm
        for line in link_lines:
            c.drawString(tx, jy, line)
            jy -= 2.2 * mm
    # blocks
    for label, lines in blocks:
        jy -= 0.5 * mm
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(tx, jy, label)
        jy -= 2.4 * mm
        c.setFillColor(COLOR_TEXT)
        c.setFont("Helvetica", 6.5)
        for line in lines:
            c.drawString(tx, jy, line)
            jy -= 2.3 * mm

    # sentiment pie (right side)
    if img_w:
        pie_radius = min(img_w, h - 4 * mm) / 2 - 2 * mm
        pie_cx = x + w - pad - img_w / 2
        pie_cy = y_bot + h / 2
        draw_sentiment_pie(c, pie_cx, pie_cy, pie_radius,
                           item.get("sentiment_positif"),
                           item.get("sentiment_negatif"),
                           item.get("sentiment_netral"))

    return h


def _draw_kontra_card(c, x, y_top, w, item):
    pad = 2 * mm
    is_satgas = item.get("sumber") == "to_satgas"
    badge_color = COLOR_RED if is_satgas else COLOR_BLUE
    inner_w = w - 2 * pad

    medsos = [m for m in (item.get("medsos") or []) if m]
    sna_img = decode_image(item.get("sna_image"))
    lainnya_img = decode_image(item.get("lainnya_image"))
    has_imgs = bool(sna_img or lainnya_img)
    img_block_w = 38 * mm if has_imgs else 0
    text_w = inner_w - (img_block_w + 2 * mm if has_imgs else 0)

    data_lines = wrap_to_width(item.get("data_diri", "") or "", "Helvetica", 6.5, text_w)[:5]
    ket_lines = wrap_to_width(item.get("keterangan", "") or "", "Helvetica", 6.5, text_w)[:3]
    medsos_lines = []
    for m in medsos[:6]:
        for ln in wrap_to_width(m, "Helvetica", 6, text_w):
            medsos_lines.append(ln)

    h = 3 * mm + 4 * mm  # top + badge row
    h += 0.5 * mm
    if data_lines:
        h += 2.8 * mm + 2.3 * mm * len(data_lines) + 0.5 * mm
    if medsos_lines:
        h += 2.8 * mm + 2.2 * mm * len(medsos_lines) + 0.5 * mm
    if ket_lines:
        h += 2.8 * mm + 2.3 * mm * len(ket_lines) + 0.5 * mm
    h += 2 * mm
    if has_imgs:
        h = max(h, 35 * mm)

    y_bot = y_top - h
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.4)
    c.rect(x, y_bot, w, h, stroke=1, fill=0)
    c.setFillColor(badge_color)
    c.rect(x, y_bot, 1.2 * mm, h, stroke=0, fill=1)

    tx = x + pad + 1.5 * mm
    cy = y_top - 3 * mm
    # Name + badges
    c.setFillColor(COLOR_HEADER)
    c.setFont("Helvetica-Bold", 9)
    name = truncate_to_width(item.get("nama_to", "-"), "Helvetica-Bold", 9, text_w * 0.7)
    c.drawString(tx, cy - 3 * mm, name)
    c.setFillColor(badge_color)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(tx + stringWidth(name, "Helvetica-Bold", 9) + 3 * mm, cy - 3 * mm,
                 "[TO SATGAS]" if is_satgas else "[TO INTERNAL]")
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica-Bold", 5.5)
    c.drawString(tx + stringWidth(name, "Helvetica-Bold", 9) + 24 * mm, cy - 3 * mm,
                 (item.get("tipe", "") or "").upper())

    jy = cy - 6 * mm
    # data_diri
    if data_lines:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(tx, jy, "DATA DIRI")
        jy -= 2.4 * mm
        c.setFillColor(COLOR_TEXT)
        c.setFont("Helvetica", 6.5)
        for line in data_lines:
            c.drawString(tx, jy, line)
            jy -= 2.3 * mm
        jy -= 0.5 * mm
    # medsos
    if medsos_lines:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(tx, jy, "LINK MEDIA SOSIAL")
        jy -= 2.4 * mm
        c.setFillColor(COLOR_AMBER_DARK)
        c.setFont("Helvetica", 6)
        for line in medsos_lines:
            c.drawString(tx, jy, line)
            jy -= 2.2 * mm
        jy -= 0.5 * mm
    # keterangan
    if ket_lines:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(tx, jy, "KETERANGAN")
        jy -= 2.4 * mm
        c.setFillColor(COLOR_TEXT)
        c.setFont("Helvetica", 6.5)
        for line in ket_lines:
            c.drawString(tx, jy, line)
            jy -= 2.3 * mm

    # SNA + Lainnya stacked vertically on right
    if has_imgs:
        img_x = x + w - pad - img_block_w
        slot_h = (h - 6 * mm) / (2 if (sna_img and lainnya_img) else 1)
        slot_y = y_top - 4 * mm
        if sna_img:
            c.setFillColor(COLOR_MUTED)
            c.setFont("Helvetica-Bold", 5)
            c.drawString(img_x, slot_y, "SNA")
            fit_image(c, sna_img, img_x, slot_y - slot_h, img_block_w, slot_h - 1.5 * mm)
            slot_y -= slot_h
        if lainnya_img:
            c.setFillColor(COLOR_MUTED)
            c.setFont("Helvetica-Bold", 5)
            c.drawString(img_x, slot_y, "LAINNYA")
            fit_image(c, lainnya_img, img_x, slot_y - slot_h, img_block_w, slot_h - 1.5 * mm)

    return h


def _draw_gal_card(c, x, y_top, w, item):
    pad = 2 * mm
    cat = (item.get("kategori") or "").upper()
    cat_color = {"NARASI": COLOR_BLUE, "VIDEO": COLOR_RED, "MEDSOS": COLOR_PURPLE}.get(cat, COLOR_MUTED)
    inner_w = w - 2 * pad
    img = decode_image(item.get("gambar"))
    img_w = 40 * mm if img else 0
    text_w = inner_w - (img_w + 2 * mm if img else 0)

    judul_lines = wrap_to_width(item.get("judul", "—"), "Helvetica-Bold", 8, text_w)[:2]
    links = [lk for lk in (item.get("links") or []) if lk]
    link_lines = []
    for ln in links[:8]:
        for w_ln in wrap_to_width(ln, "Helvetica", 6, text_w):
            link_lines.append(w_ln)
    ket_lines = wrap_to_width(item.get("keterangan", "") or "", "Helvetica", 6.5, text_w)[:3]

    h = 3 * mm + 4 * mm
    h += 2.7 * mm * len(judul_lines) + 0.5 * mm
    if link_lines:
        h += 2.6 * mm + 2.2 * mm * len(link_lines) + 0.5 * mm
    if ket_lines:
        h += 2.6 * mm + 2.3 * mm * len(ket_lines) + 0.5 * mm
    h += 2 * mm
    if img:
        h = max(h, 32 * mm)

    y_bot = y_top - h
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.4)
    c.rect(x, y_bot, w, h, stroke=1, fill=0)
    c.setFillColor(cat_color)
    c.rect(x, y_bot, 1.2 * mm, h, stroke=0, fill=1)

    tx = x + pad + 1.5 * mm
    cy = y_top - 3 * mm
    # category badge
    c.setFillColor(cat_color)
    c.rect(tx, cy - 3 * mm, 16 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(tx + 1 * mm, cy - 3 * mm + 0.9 * mm, cat or "—")
    # judul
    c.setFillColor(COLOR_HEADER)
    c.setFont("Helvetica-Bold", 8)
    jy = cy - 6.5 * mm
    for line in judul_lines:
        c.drawString(tx, jy, line)
        jy -= 2.7 * mm
    # links
    if link_lines:
        jy -= 0.3 * mm
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(tx, jy, "LINK KONTEN")
        jy -= 2.4 * mm
        c.setFillColor(COLOR_AMBER_DARK)
        c.setFont("Helvetica", 6)
        for line in link_lines:
            c.drawString(tx, jy, line)
            jy -= 2.2 * mm
    # keterangan
    if ket_lines:
        jy -= 0.3 * mm
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(tx, jy, "KETERANGAN")
        jy -= 2.4 * mm
        c.setFillColor(COLOR_TEXT)
        c.setFont("Helvetica", 6.5)
        for line in ket_lines:
            c.drawString(tx, jy, line)
            jy -= 2.3 * mm

    if img:
        fit_image(c, img, x + w - pad - img_w, y_bot + 2 * mm, img_w, h - 4 * mm)

    return h


# ---------- MAIN ----------
def build_summary_pdf(data, ai_text, ai_html=None):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    rd = data.get("report_date", "")
    state = {"page": 1, "y": 0}

    avail_top = PAGE_H - 18 * mm - 4 * mm
    avail_bottom = 13 * mm
    w = PAGE_W - 2 * MARGIN

    def new_page():
        _draw_footer(c, state["page"])
        c.showPage()
        state["page"] += 1
        _draw_header(c, rd)
        state["y"] = avail_top

    def ensure_space(needed):
        if state["y"] - needed < avail_bottom:
            new_page()

    def section_title(text, count_text=None):
        ensure_space(7 * mm)
        bar_h = 5 * mm
        c.setFillColor(COLOR_HEADER)
        c.rect(MARGIN, state["y"] - bar_h, w, bar_h, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(MARGIN + 2 * mm, state["y"] - bar_h + 1.4 * mm, text)
        if count_text:
            c.setFillColor(COLOR_AMBER)
            c.setFont("Helvetica-Bold", 6.5)
            c.drawRightString(MARGIN + w - 2 * mm, state["y"] - bar_h + 1.4 * mm, count_text)
        state["y"] -= bar_h + 2 * mm

    # =========== PAGE 1: Executive Summary + Sentiment Cases Strip ===========
    _draw_header(c, rd)
    cases_h = 50 * mm  # bottom strip for sentiment cases
    cases_y = avail_bottom
    sum_top = avail_top
    sum_bottom = cases_y + cases_h + 4 * mm
    sum_h = sum_top - sum_bottom
    _draw_executive_summary(c, MARGIN, sum_bottom, w, sum_h, ai_text, data, ai_html=ai_html)
    _draw_sentiment_cases_strip(c, MARGIN, cases_y, w, cases_h, data)

    # =========== PAGE 2+: Detail cards (auto-paginated) ===========
    new_page()
    state["y"] = avail_top

    # LID
    lid_items = data.get("lid", [])
    section_title("BERITA TRENDING (TIM LID)", f"{len(lid_items)} ITEM")
    if not lid_items:
        c.setFillColor(COLOR_MUTED); c.setFont("Helvetica-Oblique", 7)
        c.drawString(MARGIN + 2 * mm, state["y"] - 4 * mm, "Tidak ada berita.")
        state["y"] -= 6 * mm
    else:
        for it in lid_items:
            h_est = _measure_lid_card(it, w)
            if state["y"] - h_est < avail_bottom:
                new_page()
            _draw_lid_card(c, MARGIN, state["y"], w, it)
            state["y"] -= h_est + 2 * mm

    state["y"] -= 2 * mm

    # KONTRA
    kontra_items = data.get("kontra", [])
    if state["y"] - 12 * mm < avail_bottom:
        new_page()
    section_title("PROFILING (TIM KONTRA)", f"{len(kontra_items)} TO")
    if not kontra_items:
        c.setFillColor(COLOR_MUTED); c.setFont("Helvetica-Oblique", 7)
        c.drawString(MARGIN + 2 * mm, state["y"] - 4 * mm, "Tidak ada profiling.")
        state["y"] -= 6 * mm
    else:
        for it in kontra_items:
            h_est = _measure_kontra_card(it, w)
            if state["y"] - h_est < avail_bottom:
                new_page()
            _draw_kontra_card(c, MARGIN, state["y"], w, it)
            state["y"] -= h_est + 2 * mm

    state["y"] -= 2 * mm

    # GAL
    gal_items = data.get("gal", [])
    if state["y"] - 12 * mm < avail_bottom:
        new_page()
    section_title("KONTEN / NARASI / MEME (TIM GAL)", f"{len(gal_items)} KONTEN")
    if not gal_items:
        c.setFillColor(COLOR_MUTED); c.setFont("Helvetica-Oblique", 7)
        c.drawString(MARGIN + 2 * mm, state["y"] - 4 * mm, "Tidak ada konten.")
        state["y"] -= 6 * mm
    else:
        for it in gal_items:
            h_est = _measure_gal_card(it, w)
            if state["y"] - h_est < avail_bottom:
                new_page()
            _draw_gal_card(c, MARGIN, state["y"], w, it)
            state["y"] -= h_est + 2 * mm

    state["y"] -= 2 * mm

    # MEDMON — adaptive height (fill remaining page 2 if enough room, else new page)
    MEDMON_MIN = 15 * mm
    MEDMON_PREF = 65 * mm
    rem = state["y"] - avail_bottom - 2 * mm
    if rem < MEDMON_MIN:
        new_page()
        rem = state["y"] - avail_bottom - 2 * mm
    h_use = min(MEDMON_PREF, rem)
    _draw_medmon_with_images(c, MARGIN, state["y"] - h_use, w, h_use, data)
    state["y"] -= h_use + 3 * mm

    # GEOINT — adaptive height
    GEOINT_MIN = 35 * mm
    GEOINT_PREF = 75 * mm
    rem = state["y"] - avail_bottom - 2 * mm
    if rem < GEOINT_MIN:
        new_page()
        rem = state["y"] - avail_bottom - 2 * mm
    h_use = min(GEOINT_PREF, rem)
    _draw_geoint_with_map(c, MARGIN, state["y"] - h_use, w, h_use, data)
    state["y"] -= h_use + 3 * mm

    _draw_footer(c, state["page"])
    c.showPage()
    c.save()
    return buf.getvalue()
