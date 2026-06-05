"""PDF generator for BAIS daily summary. Max 2 pages.

NEW LAYOUT (per user request):
- Page 1 = EXECUTIVE SUMMARY (AI narrative) at the top + compact KPI strip + 4 small COG tiles.
- Page 2 = Supporting data with uploaded images displayed.

If ai_html is provided, render the executive summary with rich text (bold, italic,
underline, color, font, size) via reportlab Paragraph + HTML translation.
"""
import io
import math
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
        # Format value: integer -> "65%", decimal -> "70.5%" (strip trailing .0)
        val = top[1]
        if isinstance(val, float) and abs(val - round(val)) < 0.05:
            val_str = f"{int(round(val))}%"
        elif isinstance(val, float):
            val_str = f"{val:.1f}%"
        else:
            val_str = f"{val}%"
        # Auto-fit font: donut hole inner diameter = radius * 1.1; reserve 10% padding
        target_w = radius * 1.10 * 0.85
        base_size = radius * 0.45
        from reportlab.pdfbase.pdfmetrics import stringWidth
        font_size = base_size
        tw = stringWidth(val_str, "Helvetica-Bold", font_size)
        if tw > target_w:
            font_size = font_size * (target_w / tw)
        c.setFillColor(top[2])
        c.setFont("Helvetica-Bold", font_size)
        c.drawCentredString(cx, cy - radius * 0.12, val_str)
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


def _draw_sentiment_trend_chart(c, x, y, w, h, trend):
    """Draw a multi-line trend chart of MEDMON positif % over the last 7 days.
    trend = {"dates": [...x7], "subjects": {name: [{date, pos, neg, net, present}, ...x7], ...}}
    """
    # Title bar
    bar_h = 5 * mm
    c.setFillColor(COLOR_HEADER)
    c.rect(x, y + h - bar_h, w, bar_h, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 2 * mm, y + h - bar_h + 1.4 * mm, "TREN SENTIMENT POSITIF 7 HARI TERAKHIR (MEDMON)")

    # Frame
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.4)
    c.rect(x, y, w, h - bar_h, stroke=1, fill=0)

    dates = (trend or {}).get("dates") or []
    subjects = (trend or {}).get("subjects") or {}

    # Empty state
    if not dates or not subjects:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Oblique", 7)
        c.drawString(x + 2 * mm, y + (h - bar_h) / 2 - 1 * mm,
                     "Belum ada data MEDMON dalam 7 hari terakhir.")
        return

    # Layout: legend on the right (~30mm), plot area on the left
    legend_w = 36 * mm
    pad_l, pad_r, pad_t, pad_b = 8 * mm, 2 * mm, 3 * mm, 7 * mm
    plot_x = x + pad_l
    plot_y = y + pad_b
    plot_w = w - legend_w - pad_l - pad_r
    plot_h = h - bar_h - pad_t - pad_b

    # Axes
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.4)
    # Y-axis
    c.line(plot_x, plot_y, plot_x, plot_y + plot_h)
    # X-axis
    c.line(plot_x, plot_y, plot_x + plot_w, plot_y)

    # Y gridlines at 0, 25, 50, 75, 100
    c.setFont("Helvetica", 5.2)
    c.setFillColor(COLOR_MUTED)
    for pct in (0, 25, 50, 75, 100):
        gy = plot_y + (pct / 100.0) * plot_h
        c.setStrokeColor(COLOR_BORDER2)
        c.setLineWidth(0.3)
        c.line(plot_x, gy, plot_x + plot_w, gy)
        c.drawRightString(plot_x - 1 * mm, gy - 0.8 * mm, f"{pct}%")

    # X labels (DD/MM) — show every date, compact
    n = len(dates)
    step_x = plot_w / max(1, n - 1) if n > 1 else 0
    c.setFont("Helvetica", 5)
    c.setFillColor(COLOR_MUTED)
    for i, d in enumerate(dates):
        gx = plot_x + i * step_x
        c.setStrokeColor(COLOR_BORDER2)
        c.line(gx, plot_y, gx, plot_y + 1.2 * mm)
        try:
            dd = d[8:10]; mm_lbl = d[5:7]
            label = f"{dd}/{mm_lbl}"
        except Exception:
            label = d
        c.drawCentredString(gx, plot_y - 3 * mm, label)

    # Palette for subject lines (cycle if more)
    palette = [
        "#F59E0B", "#3B82F6", "#10B981", "#EF4444",
        "#8B5CF6", "#06B6D4", "#EAB308", "#EC4899",
    ]

    # Plot up to 8 subjects (legend space limit)
    items = list(subjects.items())[:8]

    for idx, (name, series) in enumerate(items):
        color = HexColor(palette[idx % len(palette)])
        c.setStrokeColor(color)
        c.setFillColor(color)
        c.setLineWidth(0.9)
        # Build points (skip days with no data — represent as gap)
        pts = []
        for i, point in enumerate(series):
            if not point.get("present"):
                pts.append(None)
            else:
                px = plot_x + i * step_x
                py = plot_y + (float(point["pos"]) / 100.0) * plot_h
                pts.append((px, py))
        # Draw line segments only between consecutive present points
        prev = None
        for p in pts:
            if p and prev:
                c.line(prev[0], prev[1], p[0], p[1])
            prev = p
        # Draw markers
        for p in pts:
            if p:
                c.circle(p[0], p[1], 0.9 * mm, stroke=0, fill=1)

    # Legend
    lx = plot_x + plot_w + 4 * mm
    ly = y + h - bar_h - pad_t - 1 * mm
    c.setFont("Helvetica-Bold", 5.6)
    c.setFillColor(COLOR_HEADER)
    c.drawString(lx, ly, "LEGENDA")
    ly -= 3 * mm
    c.setFont("Helvetica", 6)
    for idx, (name, _series) in enumerate(items):
        if ly < y + 2 * mm:
            break
        color = HexColor(palette[idx % len(palette)])
        c.setFillColor(color)
        c.circle(lx + 1.2 * mm, ly + 0.6 * mm, 0.9 * mm, stroke=0, fill=1)
        c.setFillColor(COLOR_TEXT)
        label = truncate_to_width(str(name), "Helvetica", 6, legend_w - 6 * mm)
        c.drawString(lx + 3.2 * mm, ly, label)
        ly -= 3 * mm


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
    # collect cases — MEDMON only (LID no longer has sentiment as of 2026-05)
    cases = []
    for it in data.get("medmon", []):
        if _has_sentiment(it):
            cases.append({
                "kind": "MEDMON",
                "kind_color": COLOR_PURPLE,
                "label": (it.get("subjek") or "").upper()[:14],
                "title": f"Media Monitoring · {it.get('subjek','-')}",
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
        def _fmt_pct(v):
            try:
                if isinstance(v, float) and abs(v - round(v)) < 0.05:
                    return f"{int(round(v))}%"
                if isinstance(v, float):
                    return f"{v:.1f}%"
                return f"{v}%"
            except Exception:
                return f"{v}%"
        c.setFont("Helvetica", 5)
        legend_y = cy + 1.5 * mm
        c.setFillColor(COLOR_GREEN)
        c.drawString(cx + 2 * mm, legend_y, f"+{_fmt_pct(case['p'])}")
        c.setFillColor(COLOR_RED)
        c.drawString(cx + 2 * mm + (cw - 4 * mm) * 0.34, legend_y, f"-{_fmt_pct(case['n'])}")
        c.setFillColor(HexColor("#71717A"))
        c.drawString(cx + 2 * mm + (cw - 4 * mm) * 0.67, legend_y, f"~{_fmt_pct(case['u'])}")


# ---------- PAPUA STATIC MAP (auto plotted from GEOINT coords) ----------
# Render full Papua region at zoom 6 (same physical size as before).
# Mask layer covers non-Indonesian areas so visually ONLY Tanah Papua tampil.
PAPUA_CENTER = (138.5, -4.5)  # (lon, lat) — Tanah Papua center
PAPUA_ZOOM = 6                # original zoom — keeps map physically large

# Indonesian Papua bounds — anything outside is masked
INDO_PAPUA_LON_MAX = 141.02   # Indonesia-PNG border
INDO_PAPUA_LON_MIN = 130.5    # West edge (Sorong area)
INDO_PAPUA_LAT_MAX = 0.6      # North edge
INDO_PAPUA_LAT_MIN = -10.6    # South edge (Merauke)

# Module-level cache: (width, height) -> base PIL image of Papua with NO markers.
# Fetching OSM tiles costs 30-60s on the first call; subsequent renders just
# copy this image and overlay markers/labels (~30ms). Critical for 20+
# concurrent users sharing the same map background.
_PAPUA_BASE_CACHE: dict = {}
_PAPUA_BASE_LOCK = None


def _get_papua_base(width_px: int, height_px: int):
    """Fetch & cache the Papua base map (without markers). Thread-safe."""
    global _PAPUA_BASE_LOCK
    if _PAPUA_BASE_LOCK is None:
        import threading
        _PAPUA_BASE_LOCK = threading.Lock()
    # Cache key includes zoom & center so config changes invalidate cache
    key = (width_px, height_px, PAPUA_ZOOM, PAPUA_CENTER)
    cached = _PAPUA_BASE_CACHE.get(key)
    if cached is not None:
        return cached.copy()
    with _PAPUA_BASE_LOCK:
        cached = _PAPUA_BASE_CACHE.get(key)
        if cached is not None:
            return cached.copy()
        try:
            base_map = StaticMap(
                width_px, height_px,
                url_template="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
            )
            base_image = base_map.render(zoom=PAPUA_ZOOM, center=PAPUA_CENTER)
            _PAPUA_BASE_CACHE[key] = base_image
            return base_image.copy()
        except Exception:
            return None


def _draw_non_indonesia_mask(draw, width_px: int, height_px: int):
    """Overlay a translucent dim layer on regions outside Indonesian Papua,
    so only the Indonesian portion of the map stands out. Computes pixel
    bounds from PAPUA_CENTER + PAPUA_ZOOM.
    """
    center_x = _lon_to_x(PAPUA_CENTER[0], PAPUA_ZOOM)
    center_y = _lat_to_y(PAPUA_CENTER[1], PAPUA_ZOOM)

    def lon_to_px(lon):
        return (_lon_to_x(lon, PAPUA_ZOOM) - center_x) * 256 + width_px / 2

    def lat_to_py(lat):
        return (_lat_to_y(lat, PAPUA_ZOOM) - center_y) * 256 + height_px / 2

    x_east = lon_to_px(INDO_PAPUA_LON_MAX)  # east border (PNG side)
    x_west = lon_to_px(INDO_PAPUA_LON_MIN)  # west border (Maluku side)
    y_north = lat_to_py(INDO_PAPUA_LAT_MAX)  # north border
    y_south = lat_to_py(INDO_PAPUA_LAT_MIN)  # south border

    # Opaque mask matching the OSM ocean color, so non-ID areas blend as if
    # they were ocean — Tanah Papua becomes the only visible landmass.
    # OSM 'mapnik' ocean tone ≈ (170, 211, 223). Use FULLY opaque so PNG,
    # Halmahera, Sonsorol, etc are completely hidden.
    mask_fill = (170, 211, 223, 255)
    # East (PNG)
    if x_east < width_px:
        draw.rectangle([x_east, 0, width_px, height_px], fill=mask_fill)
    # West (Maluku/Halmahera)
    if x_west > 0:
        draw.rectangle([0, 0, x_west, height_px], fill=mask_fill)
    # North (Sonsorol/Belau)
    if y_north > 0:
        draw.rectangle([0, 0, width_px, y_north], fill=mask_fill)
    # South (Arafura sea / Australia)
    if y_south < height_px:
        draw.rectangle([0, y_south, width_px, height_px], fill=mask_fill)

    # Draw a thin red boundary line along Indonesia–PNG border (east side)
    # for clarity. Skip west boundary since Maluku islands aren't a hard border.
    boundary_color = (200, 30, 30, 220)
    draw.line([(x_east, max(0, y_north)), (x_east, min(height_px, y_south))],
              fill=boundary_color, width=2)

# WIB timezone helper for update banner — same as backend WIB
try:
    from zoneinfo import ZoneInfo  # type: ignore
    _WIB = ZoneInfo("Asia/Jakarta")
except Exception:
    _WIB = None


def _format_update_text(items):
    """Format 'POSISI OPM UPDATE TANGGAL DD/MM/YYYY JAM HH.MM WIB' from latest
    updated_at among items. Falls back to report_date or today if missing.
    """
    from datetime import datetime
    latest = None
    for it in items or []:
        for key in ("updated_at", "created_at"):
            v = it.get(key)
            if not v:
                continue
            try:
                if isinstance(v, str):
                    # ISO format
                    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                elif isinstance(v, datetime):
                    dt = v
                else:
                    continue
                if latest is None or dt > latest:
                    latest = dt
            except Exception:
                continue
    if latest is None:
        latest = datetime.now()
    try:
        if _WIB is not None:
            if latest.tzinfo is None:
                from datetime import timezone
                latest = latest.replace(tzinfo=timezone.utc)
            latest = latest.astimezone(_WIB)
    except Exception:
        pass
    return (
        f"POSISI OPM  ·  UPDATE TANGGAL {latest.strftime('%d/%m/%Y')}"
        f"  ·  JAM {latest.strftime('%H.%M')} WIB"
    )


def _lon_to_x(lon, zoom):
    return ((lon + 180.0) / 360.0) * (2 ** zoom)


def _lat_to_y(lat, zoom):
    rad = math.radians(lat)
    return (
        1.0 - math.log(math.tan(rad) + 1 / math.cos(rad)) / math.pi
    ) / 2.0 * (2 ** zoom)


def render_papua_map(items, width_px=900, height_px=700, draw_labels=False, update_text=None):
    """Render a Papua-centered map with all OPM positions plotted using a
    CACHED base map (fetched once, reused thousands of times). Markers and
    labels are drawn via PIL ImageDraw on a copy of the cached base.

    - markers: white ring + red disc (aktif) or green disc (non-aktif)
    - draw_labels=True : number each marker (1..N matching table order)
    - update_text      : top header strip with timestamp
    Returns an ImageReader or None.
    """
    if not _HAS_STATICMAP:
        return None
    image = _get_papua_base(width_px, height_px)
    if image is None:
        return None
    try:
        from PIL import ImageDraw, ImageFont
        # Mode RGBA for translucent banner / boxes
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        draw = ImageDraw.Draw(image, "RGBA")
        # Apply mask over non-Indonesian regions FIRST (so markers stay on top)
        _draw_non_indonesia_mask(draw, width_px, height_px)
        center_x = _lon_to_x(PAPUA_CENTER[0], PAPUA_ZOOM)
        center_y = _lat_to_y(PAPUA_CENTER[1], PAPUA_ZOOM)

        # Compute marker pixel positions + status colors
        valid = []
        for it in items or []:
            try:
                lat = float(it.get("lat"))
                lon = float(it.get("lon"))
            except (TypeError, ValueError):
                continue
            color = (239, 68, 68) if it.get("status") == "aktif" else (16, 185, 129)
            mx = _lon_to_x(lon, PAPUA_ZOOM)
            my = _lat_to_y(lat, PAPUA_ZOOM)
            px = (mx - center_x) * 256 + width_px / 2
            py = (my - center_y) * 256 + height_px / 2
            valid.append((px, py, color))

        # Draw markers (white ring + colored disc)
        ring = 22 if draw_labels else 14
        inner = 18 if draw_labels else 10
        for px, py, color in valid:
            draw.ellipse(
                [px - ring, py - ring, px + ring, py + ring],
                fill=(255, 255, 255, 255), outline=(0, 0, 0, 80), width=2,
            )
            draw.ellipse(
                [px - inner, py - inner, px + inner, py + inner],
                fill=(*color, 255), outline=(255, 255, 255, 255), width=2,
            )

        # Font loader with fallback chain
        def load_font(size):
            for fp in [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            ]:
                try:
                    return ImageFont.truetype(fp, size)
                except Exception:
                    pass
            try:
                import reportlab
                rl_dir = os.path.dirname(reportlab.__file__)
                for cand in [
                    os.path.join(rl_dir, "fonts", "VeraBd.ttf"),
                    os.path.join(rl_dir, "fonts", "Vera.ttf"),
                ]:
                    if os.path.exists(cand):
                        return ImageFont.truetype(cand, size)
            except Exception:
                pass
            return ImageFont.load_default()

        num_font = load_font(20)
        banner_font = load_font(22)

        # Update banner (top strip)
        if update_text:
            BANNER_H = 38
            draw.rectangle([0, 0, width_px, BANNER_H], fill=(15, 23, 42, 220))
            try:
                bb = draw.textbbox((0, 0), update_text, font=banner_font)
                tw = bb[2] - bb[0]
            except Exception:
                tw = len(update_text) * 11
            tx = max(8, (width_px - tw) // 2)
            draw.text((tx, 8), update_text, fill=(245, 158, 11, 255), font=banner_font)

        # Numbered labels CENTERED on each marker (1..N matching table order)
        if draw_labels:
            for idx, (px, py, _color) in enumerate(valid, 1):
                label = str(idx)
                try:
                    bb = draw.textbbox((0, 0), label, font=num_font)
                    tw = bb[2] - bb[0]
                    th = bb[3] - bb[1]
                except Exception:
                    tw, th = 12, 16
                draw.text(
                    (px - tw / 2, py - th / 2 - 2),
                    label, fill=(255, 255, 255, 255), font=num_font,
                )

        buf = io.BytesIO()
        # Crop image to Indonesian Papua bounds so the landmass FILLS the frame
        try:
            center_x_t = _lon_to_x(PAPUA_CENTER[0], PAPUA_ZOOM)
            center_y_t = _lat_to_y(PAPUA_CENTER[1], PAPUA_ZOOM)

            def _lon_px(lon):
                return (_lon_to_x(lon, PAPUA_ZOOM) - center_x_t) * 256 + width_px / 2

            def _lat_py(lat):
                return (_lat_to_y(lat, PAPUA_ZOOM) - center_y_t) * 256 + height_px / 2

            pad_px = 24  # small padding around the cropped Indo Papua rect
            left = max(0, int(_lon_px(INDO_PAPUA_LON_MIN)) - pad_px)
            right = min(width_px, int(_lon_px(INDO_PAPUA_LON_MAX)) + pad_px)
            top_py = max(0, int(_lat_py(INDO_PAPUA_LAT_MAX)) - pad_px)
            bottom_py = min(height_px, int(_lat_py(INDO_PAPUA_LAT_MIN)) + pad_px)
            if right > left + 100 and bottom_py > top_py + 100:
                # If banner present, keep it (re-paste later isn't worth it;
                # banner is wider than Indonesian Papua anyway so we trim it
                # — that's OK, update banner is also drawn on PDF caption).
                image = image.crop((left, top_py, right, bottom_py))
        except Exception:
            pass
        image.convert("RGB").save(buf, format="PNG")
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
def _draw_morning_cover_page(c, report_date, title_text=None):
    """Cyber-themed cover page for Laporan Pagi.
    - Dark navy/cyan background with grid pattern
    - Glowing neon title 'LAPORAN PAGI GEOSPASIKA'
    - Period subtitle: 'PERIODE DD MMM YYYY'
    - Corner brackets, scan lines, classification stamp
    """
    # Colors
    BG_DARK = HexColor("#020617")           # Slate-950 (almost black)
    NEON_CYAN = HexColor("#22D3EE")         # Cyan-400
    NEON_TEAL = HexColor("#2DD4BF")         # Teal-400
    NEON_AMBER = HexColor("#FBBF24")        # Amber-400
    GRID_GLOW = HexColor("#134E4A")         # Teal-900 (subtle grid lines)

    # 1) Full-page dark background
    c.setFillColor(BG_DARK)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

    # 2) Subtle vertical gradient effect (multiple thin rectangles)
    for i in range(20):
        ratio = i / 20.0
        # Blend BG_DARK → BG_DARK2 going up
        r = 0x02 + int((0x0B - 0x02) * ratio)
        g = 0x06 + int((0x15 - 0x06) * ratio)
        b = 0x17 + int((0x30 - 0x17) * ratio)
        c.setFillColor(HexColor(f"#{r:02x}{g:02x}{b:02x}"))
        band_h = PAGE_H / 20
        c.rect(0, i * band_h, PAGE_W, band_h, stroke=0, fill=1)

    # 3) Grid pattern (subtle cyber grid)
    c.setStrokeColor(GRID_GLOW)
    c.setLineWidth(0.2)
    grid_step = 10 * mm
    # vertical lines
    x = 0
    while x <= PAGE_W:
        c.line(x, 0, x, PAGE_H)
        x += grid_step
    # horizontal lines
    y = 0
    while y <= PAGE_H:
        c.line(0, y, PAGE_W, y)
        y += grid_step

    # 4) Major accent grid lines (every 50mm)
    c.setStrokeColor(HexColor("#1E293B"))
    c.setLineWidth(0.4)
    for x in range(0, int(PAGE_W), int(50 * mm)):
        c.line(x, 0, x, PAGE_H)
    for y in range(0, int(PAGE_H), int(50 * mm)):
        c.line(0, y, PAGE_W, y)

    # 5) Corner brackets (cyber-style frame)
    bracket_len = 18 * mm
    bracket_off = 12 * mm
    c.setStrokeColor(NEON_CYAN)
    c.setLineWidth(1.8)
    # Top-left
    c.line(bracket_off, PAGE_H - bracket_off, bracket_off + bracket_len, PAGE_H - bracket_off)
    c.line(bracket_off, PAGE_H - bracket_off, bracket_off, PAGE_H - bracket_off - bracket_len)
    # Top-right
    c.line(PAGE_W - bracket_off, PAGE_H - bracket_off, PAGE_W - bracket_off - bracket_len, PAGE_H - bracket_off)
    c.line(PAGE_W - bracket_off, PAGE_H - bracket_off, PAGE_W - bracket_off, PAGE_H - bracket_off - bracket_len)
    # Bottom-left
    c.line(bracket_off, bracket_off, bracket_off + bracket_len, bracket_off)
    c.line(bracket_off, bracket_off, bracket_off, bracket_off + bracket_len)
    # Bottom-right
    c.line(PAGE_W - bracket_off, bracket_off, PAGE_W - bracket_off - bracket_len, bracket_off)
    c.line(PAGE_W - bracket_off, bracket_off, PAGE_W - bracket_off, bracket_off + bracket_len)

    # 6) Top label strip: classification + timestamp
    c.setFillColor(NEON_AMBER)
    c.setFont("Courier-Bold", 8)
    c.drawString(bracket_off + 4 * mm, PAGE_H - bracket_off - 8 * mm, "[ CLASSIFIED · TERBATAS ]")
    c.setFillColor(HexColor("#94A3B8"))
    c.setFont("Courier", 7)
    c.drawRightString(PAGE_W - bracket_off - 4 * mm, PAGE_H - bracket_off - 8 * mm,
                      f">> {datetime.now().strftime('%Y.%m.%d %H:%M:%S')} WIB")

    # 7) Centered title block
    center_y = PAGE_H / 2 + 30 * mm

    # Small label above main title
    c.setFillColor(NEON_TEAL)
    c.setFont("Courier-Bold", 11)
    label = "BADAN INTELIJEN STRATEGIS · TNI"
    label_w = stringWidth(label, "Courier-Bold", 11)
    c.drawString((PAGE_W - label_w) / 2, center_y + 18 * mm, label)

    # Underline of small label (cyber tick marks)
    c.setStrokeColor(NEON_TEAL)
    c.setLineWidth(0.5)
    tick_y = center_y + 15 * mm
    line_w = label_w + 20 * mm
    line_x = (PAGE_W - line_w) / 2
    c.line(line_x, tick_y, line_x + line_w, tick_y)
    # Tick marks at endpoints
    c.line(line_x, tick_y - 1.5 * mm, line_x, tick_y + 1.5 * mm)
    c.line(line_x + line_w, tick_y - 1.5 * mm, line_x + line_w, tick_y + 1.5 * mm)

    # Main title — big bold
    main = "LAPORAN PAGI"
    c.setFont("Helvetica-Bold", 46)
    main_w = stringWidth(main, "Helvetica-Bold", 46)
    # Glow effect: draw outline in cyan slightly offset
    c.setFillColor(NEON_CYAN)
    c.setFont("Helvetica-Bold", 46)
    c.drawString((PAGE_W - main_w) / 2 + 1, center_y - 1, main)  # slight cyan shadow
    c.setFillColor(white)
    c.drawString((PAGE_W - main_w) / 2, center_y, main)

    # Sub title — GEOSPASIKA
    sub = "GEOSPASIKA"
    c.setFont("Helvetica-Bold", 40)
    sub_w = stringWidth(sub, "Helvetica-Bold", 40)
    c.setFillColor(NEON_TEAL)
    c.drawString((PAGE_W - sub_w) / 2 + 1, center_y - 14 * mm - 1, sub)  # teal glow
    c.setFillColor(white)
    c.drawString((PAGE_W - sub_w) / 2, center_y - 14 * mm, sub)

    # Decorative separator
    sep_y = center_y - 22 * mm
    c.setStrokeColor(NEON_AMBER)
    c.setLineWidth(0.8)
    sep_w = 80 * mm
    sep_x = (PAGE_W - sep_w) / 2
    c.line(sep_x, sep_y, sep_x + sep_w, sep_y)
    # Diamond at center
    cx = PAGE_W / 2
    c.setFillColor(NEON_AMBER)
    c.setStrokeColor(NEON_AMBER)
    c.setLineWidth(1)
    diamond_size = 2 * mm
    p = c.beginPath()
    p.moveTo(cx, sep_y + diamond_size)
    p.lineTo(cx + diamond_size, sep_y)
    p.lineTo(cx, sep_y - diamond_size)
    p.lineTo(cx - diamond_size, sep_y)
    p.close()
    c.drawPath(p, stroke=0, fill=1)

    # Period
    period_text = title_text or f"PERIODE {report_date}"
    # Try to format: "LAPORAN GEOSPASIKA PERIODE 05 JUN 2026" -> "PERIODE 05 JUN 2026"
    if title_text and "PERIODE" in title_text.upper():
        idx = title_text.upper().find("PERIODE")
        period_text = title_text[idx:]
    c.setFont("Helvetica-Bold", 16)
    pw = stringWidth(period_text, "Helvetica-Bold", 16)
    c.setFillColor(HexColor("#E2E8F0"))
    c.drawString((PAGE_W - pw) / 2, sep_y - 12 * mm, period_text)

    # 8) Bottom info block — "Generated by automated intel pipeline" + version
    bottom_y = bracket_off + 24 * mm
    c.setStrokeColor(HexColor("#334155"))
    c.setLineWidth(0.4)
    c.line(MARGIN * 2, bottom_y + 6 * mm, PAGE_W - MARGIN * 2, bottom_y + 6 * mm)

    c.setFillColor(NEON_CYAN)
    c.setFont("Courier-Bold", 8)
    c.drawCentredString(PAGE_W / 2, bottom_y + 1 * mm, ">>> SATGAS KAPUAS · INTEL AUTOMATED PIPELINE <<<")

    c.setFillColor(HexColor("#64748B"))
    c.setFont("Courier", 7)
    c.drawCentredString(PAGE_W / 2, bottom_y - 4 * mm,
                        "Auto-generated daily at 07:00 WIB · Source: D-1 team reports")

    # 9) Faux IP-like badge bottom-left
    c.setFillColor(HexColor("#0F172A"))
    c.setStrokeColor(NEON_TEAL)
    c.setLineWidth(0.6)
    badge_w, badge_h = 36 * mm, 10 * mm
    bx = bracket_off + 4 * mm
    by = bracket_off + 4 * mm
    c.rect(bx, by, badge_w, badge_h, stroke=1, fill=1)
    c.setFillColor(NEON_TEAL)
    c.setFont("Courier-Bold", 6)
    c.drawString(bx + 2 * mm, by + 6 * mm, "DOC.ID:")
    c.setFillColor(white)
    c.setFont("Courier", 7)
    doc_id = f"BAIS-MOR-{report_date.replace('-', '')}"
    c.drawString(bx + 2 * mm, by + 1.5 * mm, doc_id)

    # 10) Status badge bottom-right
    sbx = PAGE_W - bracket_off - 4 * mm - badge_w
    c.setFillColor(HexColor("#0F172A"))
    c.setStrokeColor(NEON_AMBER)
    c.rect(sbx, by, badge_w, badge_h, stroke=1, fill=1)
    c.setFillColor(NEON_AMBER)
    c.setFont("Courier-Bold", 6)
    c.drawString(sbx + 2 * mm, by + 6 * mm, "STATUS:")
    c.setFillColor(white)
    c.setFont("Courier", 7)
    c.drawString(sbx + 2 * mm, by + 1.5 * mm, "ACTIVE · SYNCED")


def _draw_header(c, report_date, title_override=None, subtitle_override=None, variant="default"):
    # Morning variant: teal/cyan palette instead of dark+amber
    if variant == "morning":
        bg = HexColor("#0F766E")       # Teal-700
        accent_bar = HexColor("#FBBF24")  # Amber-400 (sunrise feel)
        tag_color = HexColor("#FEF3C7")   # Cream highlight
    else:
        bg = COLOR_HEADER
        accent_bar = COLOR_AMBER
        tag_color = COLOR_AMBER

    c.setFillColor(bg)
    c.rect(0, PAGE_H - 18 * mm, PAGE_W, 18 * mm, stroke=0, fill=1)
    c.setFillColor(accent_bar)
    c.rect(MARGIN, PAGE_H - 18 * mm, 3 * mm, 18 * mm, stroke=0, fill=1)
    # logo (top-left, next to accent bar)
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
    c.drawString(text_x, PAGE_H - 9 * mm, title_override or "BAIS TNI · SUMMARY GEOSPASIKA HARIAN")
    c.setFont("Helvetica", 7)
    c.drawString(text_x, PAGE_H - 13.5 * mm, subtitle_override or "Satgas Kapuas  ·  Klasifikasi: TERBATAS")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(tag_color)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 9 * mm, f"Tanggal: {report_date}")
    c.setFillColor(HexColor("#CBD5E1") if variant == "morning" else HexColor("#94A3B8"))
    c.setFont("Helvetica", 7)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 13.5 * mm,
                      f"Dicetak {datetime.now().strftime('%d %b %Y %H:%M')} WIB")


def _draw_footer(c, page_num, variant="default"):
    accent = HexColor("#0F766E") if variant == "morning" else COLOR_BORDER
    c.setStrokeColor(accent)
    c.setLineWidth(0.6 if variant == "morning" else 0.4)
    c.line(MARGIN, 9 * mm, PAGE_W - MARGIN, 9 * mm)
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica", 6.5)
    label = "LAPORAN PAGI · INTERNAL — TIDAK UNTUK DISEBARLUASKAN" if variant == "morning" \
        else "DOKUMEN INTERNAL — TIDAK UNTUK DISEBARLUASKAN"
    c.drawString(MARGIN, 5.5 * mm, label)
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

    # Match COG header items: "1. ACEH:", "2. JAKARTA:", "3. PAPUA:", "4. INTERNASIONAL:"
    cog_prefix_re = re.compile(
        r"^\s*\d+\.\s*(?:ACEH|JAKARTA|PAPUA|INTERNASIONAL)\b",
        re.IGNORECASE,
    )
    # Match MEDMON numbered subject items: "1. Presiden:", "2. Panglima TNI:", "3. MBG:", etc.
    # We accept any short subject token followed by a colon, but exclude bullet rekomendasi etc.
    medmon_prefix_re = re.compile(
        r"^\s*\d+\.\s+[A-Za-zÀ-ÿ][\wÀ-ÿ\s\.\-/]{0,40}\s*:",
    )
    COG_INDENT_MM = 6 * mm  # visually "menjorok ke dalam"

    def push(text, **style):
        text = (text or "").strip()
        if not text:
            return
        # Auto-indent numbered items (COG headers + MEDMON subjects) — both menjorok
        plain = re.sub(r"<[^>]+>", "", text)
        if cog_prefix_re.match(plain) or medmon_prefix_re.match(plain):
            style["indent"] = COG_INDENT_MM
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


def _make_pstyle(name, size, bold=False, color="#0F172A", indent=0, leading=None):
    return ParagraphStyle(
        name=name,
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        leading=leading if leading is not None else size * 1.25,
        textColor=HexColor(color),
        alignment=TA_LEFT,
        leftIndent=indent,
        spaceBefore=0,
        spaceAfter=0,
    )


# ---------- EXECUTIVE SUMMARY (PAGE 1 - BIG) ----------
HEADING_RE = re.compile(
    r"^(RINGKASAN\b|ANALISA\b|REKOMENDASI\b|ANALISA\s*&\s*REKOMENDASI\b|"
    r"LID\s*:?|KONTRA\s*:?|GAL\s*:?|MEDMON\s*:?|GEOINT\s*:?|PIKET\s*:?|"
    r"\d+\.\s*(?:ACEH|JAKARTA|PAPUA|INTERNASIONAL)\b)",
    re.IGNORECASE,
)


def _draw_executive_summary(c, x, y, w, h, ai_text, data, ai_html=None):
    """Draws the AI executive summary into the given frame.
    Returns (leftover_flowables_list, is_richtext_bool, content_bottom_y).
    If leftover is non-empty, the caller should render the remaining items on
    continuation pages. content_bottom_y is where the actual content ended
    (so caller can flow next sections naturally below if there's space).
    """
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
        flowables = _blocks_to_flowables(blocks)
        leftover = _fill_frame(frame, c, flowables)
        try:
            content_bottom = frame._y
        except Exception:
            content_bottom = frame_y
        # Draw tight border around panel (top of header → just below content)
        c.setStrokeColor(COLOR_BORDER)
        c.setLineWidth(0.5)
        c.rect(x, content_bottom - pad_b, w,
               (y + h) - (content_bottom - pad_b), stroke=1, fill=0)
        return leftover, True, content_bottom

    # Plain text fallback (previous behavior).
    text = ai_text or _fallback_summary(data)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    flowables = _plain_text_to_flowables(text)
    leftover = _fill_frame(frame, c, flowables)
    try:
        content_bottom = frame._y
    except Exception:
        content_bottom = frame_y
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x, content_bottom - pad_b, w,
           (y + h) - (content_bottom - pad_b), stroke=1, fill=0)
    return leftover, False, content_bottom


def _blocks_to_flowables(blocks):
    from reportlab.platypus import Spacer, HRFlowable
    out = []
    for style, text in blocks:
        if style.get("hr"):
            out.append(HRFlowable(width="100%", thickness=0.4,
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
            out.append(Paragraph(text, ps))
        except Exception:
            safe = re.sub(r"<[^>]+>", "", text)
            out.append(Paragraph(safe, ps))
        if sp > 0:
            out.append(Spacer(1, sp * mm))
    return out


def _plain_text_to_flowables(text):
    from reportlab.platypus import Spacer
    out = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            out.append(Spacer(1, 1.2 * mm))
            continue
        is_heading = bool(HEADING_RE.match(paragraph.strip()))
        ps = _make_pstyle(
            "p",
            size=8.2 if is_heading else 8.0,
            bold=is_heading,
            color="#1E293B" if is_heading else "#0F172A",
        )
        try:
            out.append(Paragraph(paragraph.strip(), ps))
        except Exception:
            safe = re.sub(r"<[^>]+>", "", paragraph.strip())
            out.append(Paragraph(safe, ps))
        out.append(Spacer(1, 0.6 * mm))
    return out


def _fill_frame(frame, c, flowables):
    """Add flowables into frame until full. Returns list that didn't fit.
    Tries to split a paragraph that can't fit so content is never lost.
    Guarantees forward progress: if first flowable can't even split, it is
    forced in (truncated by reportlab) so the loop cannot stall.
    """
    i = 0
    while i < len(flowables):
        f = flowables[i]
        # Try adding whole
        if frame.add(f, c, trySplit=False):
            i += 1
            continue
        # Try splitting
        try:
            avail_w = frame._aW
            avail_h = frame._aH
            parts = f.split(avail_w, avail_h)
        except Exception:
            parts = []
        if parts and len(parts) >= 2:
            head = parts[0]
            tail = parts[1:]
            if frame.add(head, c, trySplit=False):
                return list(tail) + flowables[i + 1:]
            # Head still doesn't fit — return remainder so next frame retries
            return flowables[i:]
        # Cannot split. If we've already added at least one item to this frame,
        # return remainder so it can be retried in next (bigger) frame.
        if i > 0 or frame._atTop is False:
            return flowables[i:]
        # First flowable in a fresh frame still doesn't fit (very rare,
        # e.g. an oversized HRFlowable). Skip it to guarantee progress.
        i += 1
    return []


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


MEDMON_MIN_ROW_H = 38 * mm  # minimum to fit pie chart + chips


def _medmon_analisa_flowables(item, text_col_w):
    """Build flowables for the MEDMON analisa column (full text)."""
    from reportlab.platypus import Paragraph, Spacer
    out = []
    val = (item.get("analisa") or "").strip()
    if val:
        ps_body = _make_pstyle("medmon_body", size=6.5, color="#3F3F46", leading=8.2)
        body_html = _safe_html(val).replace("\n", "<br/>")
        out.append(Paragraph(body_html, ps_body))
    return out


def _measure_medmon_card(item, w):
    pad = 2 * mm
    text_col_w = w * 0.42 - 2 * mm
    flowables = _medmon_analisa_flowables(item, text_col_w)
    overhead = 4 * mm + 3 * mm + 3 * mm + 2 * mm  # name + chips + spacing + bottom
    content_h = _measure_flowables_height(flowables, text_col_w) if flowables else 0
    return max(MEDMON_MIN_ROW_H, overhead + content_h)


def _draw_medmon_card(c, x, y, w, it):
    """Draw a single MEDMON subject card. Top-anchored at y.
    Returns: card height (total y consumed)."""
    from reportlab.platypus import Frame
    row_h = _measure_medmon_card(it, w)
    ry = y - row_h
    # Card border
    c.setStrokeColor(COLOR_BORDER2)
    c.setLineWidth(0.3)
    c.rect(x, ry, w, row_h, stroke=1, fill=0)
    # subject name (full, no truncation — uppercased)
    c.setFillColor(COLOR_HEADER)
    c.setFont("Helvetica-Bold", 9)
    subj = truncate_to_width(str(it.get("subjek", "-")).upper(),
                             "Helvetica-Bold", 9, w * 0.42)
    c.drawString(x + 2 * mm, y - 4 * mm, subj)
    # sentiment chips
    positifs = sum(1 for b in it.get("berita", []) if b.get("sentiment") == "positif")
    negatifs = sum(1 for b in it.get("berita", []) if b.get("sentiment") == "negatif")
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(COLOR_GREEN)
    c.drawString(x + 2 * mm, y - 7 * mm, f"+{positifs} positif")
    c.setFillColor(COLOR_RED)
    c.drawString(x + 22 * mm, y - 7 * mm, f"−{negatifs} negatif")

    # ANALISA — full text via Paragraph in Frame
    text_col_w = w * 0.42 - 2 * mm
    flowables = _medmon_analisa_flowables(it, text_col_w)
    frame_top = y - 9 * mm
    frame_bottom = ry + 2 * mm
    frame_h = frame_top - frame_bottom
    if flowables and frame_h > 0:
        body_frame = Frame(x + 2 * mm, frame_bottom, text_col_w, frame_h,
                           leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                           showBoundary=0)
        _fill_frame(body_frame, c, flowables)

    # auto pie chart from MEDMON sentiment percentages (right side)
    img_w = w * 0.27
    pie_x = x + w * 0.43
    if _has_sentiment(it):
        pie_r = min(img_w - 4 * mm, MEDMON_MIN_ROW_H - 4 * mm) / 2
        pie_cx = pie_x + img_w / 2
        pie_cy = y - 2 * mm - (MEDMON_MIN_ROW_H - 4 * mm) / 2
        draw_sentiment_pie(c, pie_cx, pie_cy, pie_r,
                           it.get("sentiment_positif"),
                           it.get("sentiment_negatif"),
                           it.get("sentiment_netral"))
    else:
        c.setFillColor(COLOR_LIGHT)
        c.rect(pie_x, y - MEDMON_MIN_ROW_H + 1 * mm, img_w - 1 * mm,
               MEDMON_MIN_ROW_H - 2 * mm, stroke=0, fill=1)
    # chart sumber (right-most column)
    chart_x = x + w * 0.7
    img2 = decode_image(it.get("chart_sumber_image"))
    if img2:
        fit_image(c, img2, chart_x, y - MEDMON_MIN_ROW_H + 1 * mm,
                  w * 0.28 - 1 * mm, MEDMON_MIN_ROW_H - 2 * mm)
    else:
        c.setFillColor(COLOR_LIGHT)
        c.rect(chart_x, y - MEDMON_MIN_ROW_H + 1 * mm, w * 0.28 - 1 * mm,
               MEDMON_MIN_ROW_H - 2 * mm, stroke=0, fill=1)
    return row_h


def _draw_medmon_with_images(c, x, y, w, h, data):
    """LEGACY single-page MEDMON. Kept for back-compat; do not use in new flow."""
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
        # auto pie chart from MEDMON sentiment percentages
        img_w = w * 0.27
        pie_x = x + w * 0.43
        if _has_sentiment(it):
            pie_r = min(img_w - 4 * mm, row_h - 4 * mm) / 2
            pie_cx = pie_x + img_w / 2
            pie_cy = ry + row_h / 2
            draw_sentiment_pie(c, pie_cx, pie_cy, pie_r,
                               it.get("sentiment_positif"),
                               it.get("sentiment_negatif"),
                               it.get("sentiment_netral"))
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


def _draw_geoint_fullpage(c, x_left, x_right, top, bottom, data):
    """Render the GEOINT section on its own dedicated page.
    Layout (vertical):
      [section header bar]
      [compact 4-col table — full width]
      [LARGE Papua map (~150mm tall) with target name labels]
    """
    items = data.get("geoint", [])
    w = x_right - x_left

    # Section header bar
    bar_h = 5 * mm
    c.setFillColor(COLOR_HEADER)
    c.rect(x_left, top - bar_h, w, bar_h, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x_left + 2 * mm, top - bar_h + 1.4 * mm, "GEOINT · POSISI OPM")
    c.setFillColor(COLOR_AMBER)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawRightString(x_left + w - 2 * mm, top - bar_h + 1.4 * mm, f"{len(items)} TITIK")
    cur_y = top - bar_h - 2 * mm

    if not items:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Oblique", 7)
        c.drawString(x_left + 2 * mm, cur_y - 4 * mm, "Tidak ada titik OPM termonitor periode ini.")
        return

    # ---------- TABLE (full width, 4 columns) ----------
    # Render up to 14 rows.

    # Column boundaries — equal-ish widths across full page width
    col_no_w = 8 * mm
    col_wilayah_w = (w - col_no_w) * 0.32
    col_nama_w = (w - col_no_w) * 0.30
    col_koord_w = (w - col_no_w) * 0.22
    # status fills remainder
    cx_no = x_left + 2 * mm
    cx_wilayah = cx_no + col_no_w
    cx_nama = cx_wilayah + col_wilayah_w
    cx_koord = cx_nama + col_nama_w
    cx_status = cx_koord + col_koord_w

    # Table header
    c.setFillColor(COLOR_LIGHT)
    c.rect(x_left, cur_y - 5 * mm, w, 5 * mm, stroke=0, fill=1)
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica-Bold", 6.5)
    hy = cur_y - 3.4 * mm
    c.drawString(cx_no, hy, "NO")
    c.drawString(cx_wilayah, hy, "WILAYAH")
    c.drawString(cx_nama, hy, "NAMA TARGET")
    c.drawString(cx_koord, hy, "KOORDINAT")
    c.drawString(cx_status, hy, "STATUS")
    cur_y -= 5 * mm
    c.setStrokeColor(COLOR_BORDER2)
    c.setLineWidth(0.3)
    c.line(x_left, cur_y, x_left + w, cur_y)

    # Rows
    for idx, it in enumerate(items[:14], 1):
        cur_y -= 4 * mm
        c.setFillColor(COLOR_TEXT)
        c.setFont("Helvetica", 7)
        c.drawString(cx_no, cur_y + 0.8 * mm, str(idx))
        c.drawString(cx_wilayah, cur_y + 0.8 * mm,
                     truncate_to_width(str(it.get("wilayah", "-")), "Helvetica", 7, col_wilayah_w - 1 * mm))
        c.setFont("Helvetica-Bold", 7)
        c.drawString(cx_nama, cur_y + 0.8 * mm,
                     truncate_to_width(str(it.get("nama_orang", "-")), "Helvetica-Bold", 7, col_nama_w - 1 * mm))
        lat = it.get("lat"); lon = it.get("lon")
        if lat is not None and lon is not None:
            try:
                koord = f"{float(lat):.4f}, {float(lon):.4f}"
            except Exception:
                koord = f"{lat}, {lon}"
        else:
            koord = "-"
        c.setFont("Helvetica", 6.5)
        c.drawString(cx_koord, cur_y + 0.8 * mm,
                     truncate_to_width(koord, "Helvetica", 6.5, col_koord_w - 1 * mm))
        is_aktif = it.get("status") == "aktif"
        c.setFillColor(COLOR_RED if is_aktif else COLOR_GREEN)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(cx_status, cur_y + 0.8 * mm, "AKTIF" if is_aktif else "NON-AKTIF")
        # divider
        c.setStrokeColor(COLOR_BORDER2)
        c.setLineWidth(0.2)
        c.line(x_left, cur_y, x_left + w, cur_y)

    cur_y -= 4 * mm

    # ---------- LARGE PAPUA MAP with name labels ----------
    map_top = cur_y
    map_bottom = bottom + 2 * mm
    map_h = map_top - map_bottom
    if map_h < 60 * mm:
        return  # not enough space — skip map

    # Map label
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(x_left, map_top - 3 * mm, "PETA SEBARAN PAPUA — POSISI TARGET")
    map_top -= 5 * mm
    map_h = map_top - map_bottom

    # Border frame
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.5)
    c.rect(x_left, map_bottom, w, map_h, stroke=1, fill=0)

    # Render map at high resolution with numbered labels + update banner.
    # Match image aspect ratio to frame aspect (no whitespace inside the frame).
    frame_inner_w_mm = (w - 2 * mm) / mm  # mm
    frame_inner_h_mm = (map_h - 2 * mm) / mm
    target_aspect = frame_inner_w_mm / max(1.0, frame_inner_h_mm)
    map_width_px = 1800
    map_height_px = max(800, int(map_width_px / target_aspect))

    # Build update banner text from latest updated_at among items (fallback to today)
    update_text = _format_update_text(items)
    map_img = render_papua_map(
        items,
        width_px=map_width_px,
        height_px=map_height_px,
        draw_labels=True,
        update_text=update_text,
    )
    if map_img is None:
        # Fallback: try user-uploaded image
        for it in items:
            if it.get("peta_image"):
                map_img = decode_image(it["peta_image"])
                break
    if map_img:
        fit_image(c, map_img, x_left + 1 * mm, map_bottom + 1 * mm,
                  w - 2 * mm, map_h - 2 * mm)
    else:
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Oblique", 7)
        c.drawCentredString(x_left + w / 2, map_bottom + map_h / 2, "(peta tidak tersedia)")

    # Legend overlay (bottom-right corner of map)
    leg_w = 35 * mm
    leg_h = 9 * mm
    leg_x = x_left + w - leg_w - 2 * mm
    leg_y = map_bottom + 2 * mm
    c.setFillColor(COLOR_HEADER)
    c.rect(leg_x, leg_y, leg_w, leg_h, stroke=0, fill=1)
    c.setStrokeColor(COLOR_AMBER)
    c.setLineWidth(0.5)
    c.rect(leg_x, leg_y, leg_w, leg_h, stroke=1, fill=0)
    c.setFillColor(COLOR_RED)
    c.circle(leg_x + 3 * mm, leg_y + leg_h - 2.5 * mm, 1.2 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(leg_x + 5.5 * mm, leg_y + leg_h - 3 * mm, "AKTIF")
    c.setFillColor(COLOR_GREEN)
    c.circle(leg_x + 3 * mm, leg_y + 3 * mm, 1.2 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.drawString(leg_x + 5.5 * mm, leg_y + 2.5 * mm, "NON-AKTIF")


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
        if cat == "MEDSOS":
            cat = "MEME"  # legacy alias
        cat_color = {"NARASI": COLOR_BLUE, "VIDEO": COLOR_RED, "MEME": COLOR_PURPLE}.get(cat, COLOR_MUTED)
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


def _lid_card_flowables(item, inner_w):
    """Build a list of flowables for one LID card body (NOT including the
    outer card frame border or COG badge). Returns flowables list."""
    from reportlab.platypus import Paragraph, Spacer

    flowables = []
    # Judul
    judul = item.get("judul", "—") or "—"
    ps_judul = _make_pstyle("lid_judul", size=8, bold=True, color="#0F172A")
    flowables.append(Paragraph(_safe_html(judul), ps_judul))

    # Link
    link = (item.get("link") or "").strip()
    if link:
        ps_link = _make_pstyle("lid_link", size=6, color="#B45309")
        flowables.append(Spacer(1, 0.6 * mm))
        flowables.append(Paragraph(f'<u>{_safe_html(link)}</u>', ps_link))

    # Each block (FAKTA / ANALISA / TINDAKAN / REKOMENDASI) — FULL text, no truncation
    for key, label in [("fakta", "FAKTA"), ("analisa", "ANALISA"),
                       ("tindakan", "TINDAKAN SATGAS"),
                       ("rekomendasi", "REKOMENDASI BAIS")]:
        val = (item.get(key) or "").strip()
        if not val:
            continue
        flowables.append(Spacer(1, 1.4 * mm))
        ps_lbl = _make_pstyle("lid_lbl", size=5.5, bold=True, color="#64748B")
        ps_body = _make_pstyle("lid_body", size=6.8, color="#0F172A", leading=8.4)
        flowables.append(Paragraph(label, ps_lbl))
        flowables.append(Spacer(1, 0.6 * mm))
        # Preserve line breaks from input by converting \n -> <br/>
        body_html = _safe_html(val).replace("\n", "<br/>")
        flowables.append(Paragraph(body_html, ps_body))
    return flowables


def _safe_html(text: str) -> str:
    """Escape HTML special chars for ReportLab Paragraph except already-tagged."""
    if not text:
        return ""
    # Strip any existing HTML tags first (input may come from rich text editor)
    plain = re.sub(r"<[^>]+>", "", str(text))
    return (plain.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;"))


def _measure_flowables_height(flowables, width):
    """Measure total height needed for a list of flowables at given width."""
    total = 0
    for f in flowables:
        try:
            w_, h_ = f.wrap(width, 100000)
            total += h_
            if hasattr(f, "spaceBefore"):
                total += f.spaceBefore
            if hasattr(f, "spaceAfter"):
                total += f.spaceAfter
        except Exception:
            total += 5 * mm
    return total


def _measure_lid_card(item, w):
    pad = 2 * mm
    inner_w = w - 2 * pad - 1.5 * mm
    flowables = _lid_card_flowables(item, inner_w)
    # Card overhead: top padding + COG badge (3mm) + bottom padding
    overhead = 3 * mm + 3 * mm + 2.5 * mm + 2 * mm
    content_h = _measure_flowables_height(flowables, inner_w)
    return overhead + content_h


def _measure_kontra_card(item, w):
    pad = 2 * mm
    inner_w = w - 2 * pad
    medsos = [m for m in (item.get("medsos") or []) if m]
    sna_img = item.get("sna_image")
    lainnya_img = item.get("lainnya_image")
    has_imgs = bool(sna_img or lainnya_img)
    img_block_w = 38 * mm if has_imgs else 0
    text_w = inner_w - (img_block_w + 2 * mm if has_imgs else 0)
    data_lines = wrap_to_width(item.get("data_diri", "") or "", "Helvetica", 6.5, text_w)
    ket_lines = wrap_to_width(item.get("keterangan", "") or "", "Helvetica", 6.5, text_w)
    medsos_lines = []
    for m in medsos:
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
    judul_lines = wrap_to_width(item.get("judul", "—"), "Helvetica-Bold", 8, text_w)[:3]
    links = [lk for lk in (item.get("links") or []) if lk]
    link_lines = []
    for ln in links:
        for w_ln in wrap_to_width(ln, "Helvetica", 6, text_w):
            link_lines.append(w_ln)
    ket_lines = wrap_to_width(item.get("keterangan", "") or "", "Helvetica", 6.5, text_w)
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


def _draw_lid_card(c, x, y_top, w, item, max_height=None):
    """Draw an LID card. If content exceeds max_height (when given), the
    overflow flowables are returned as `leftover` so caller can render the
    rest on the next page. When `max_height` is None, the card grows to fit
    all its content.

    Returns (card_height_drawn, leftover_flowables_or_None).
    """
    from reportlab.platypus import Frame
    pad = 2 * mm
    cog = item.get("cog", "")
    cog_color = COG_COLORS.get(cog, COLOR_MUTED)
    inner_w = w - 2 * pad - 1.5 * mm

    flowables = _lid_card_flowables(item, inner_w)
    natural_h = _measure_lid_card(item, w)

    # Decide actual card height
    if max_height is None or natural_h <= max_height:
        card_h = natural_h
        clipped_flowables = flowables
        leftover = None
    else:
        card_h = max_height
        # Fit subset into available height; remainder becomes leftover
        clipped_flowables = flowables
        leftover = "__SPLIT__"  # marker; computed below by Frame

    y_bot = y_top - card_h

    # Outer border + COG side stripe
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.4)
    c.rect(x, y_bot, w, card_h, stroke=1, fill=0)
    c.setFillColor(cog_color)
    c.rect(x, y_bot, 1.2 * mm, card_h, stroke=0, fill=1)

    # COG badge at top
    tx = x + pad + 1.5 * mm
    cy = y_top - 3 * mm
    c.setFillColor(cog_color)
    c.rect(tx, cy - 3 * mm, 18 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(tx + 1 * mm, cy - 3 * mm + 0.9 * mm, COG_LABEL.get(cog, cog.upper()))

    # Body frame (below COG badge)
    frame_top = cy - 3.6 * mm
    frame_bottom = y_bot + 2 * mm
    frame_h = frame_top - frame_bottom
    body_frame = Frame(tx, frame_bottom, inner_w, frame_h,
                       leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                       showBoundary=0)
    remainder = _fill_frame(body_frame, c, clipped_flowables)
    # Strip trailing pure-Spacer flowables — they don't represent meaningful
    # content, so we shouldn't trigger a continuation page just to render
    # blank space.
    if remainder:
        from reportlab.platypus import Spacer
        meaningful = [f for f in remainder if not isinstance(f, Spacer)]
        if not meaningful:
            remainder = []
    if remainder:
        # Card content overflowed — return leftover so caller can continue
        return card_h, remainder
    return card_h, None


def _draw_lid_card_continuation(c, x, y_top, w, item, leftover_flowables, max_height):
    """Draw the continuation of an LID card on a new page. Returns
    (height_drawn, leftover_flowables_or_None)."""
    from reportlab.platypus import Frame
    pad = 2 * mm
    cog = item.get("cog", "")
    cog_color = COG_COLORS.get(cog, COLOR_MUTED)
    inner_w = w - 2 * pad - 1.5 * mm

    # Measure remaining content
    remaining_h = _measure_flowables_height(leftover_flowables, inner_w)
    overhead = 3 * mm + 2 * mm + 2 * mm  # top + small label + bottom padding
    needed_h = min(max_height, remaining_h + overhead)
    y_bot = y_top - needed_h

    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.4)
    c.rect(x, y_bot, w, needed_h, stroke=1, fill=0)
    c.setFillColor(cog_color)
    c.rect(x, y_bot, 1.2 * mm, needed_h, stroke=0, fill=1)

    tx = x + pad + 1.5 * mm
    cy = y_top - 3 * mm
    # Mini continuation label
    c.setFillColor(COLOR_MUTED)
    c.setFont("Helvetica-Oblique", 6)
    c.drawString(tx, cy - 1.5 * mm,
                 f"« lanjutan: {COG_LABEL.get(cog, cog.upper())} — {(item.get('judul') or '—')[:60]} »")

    frame_top = cy - 4 * mm
    frame_bottom = y_bot + 2 * mm
    frame_h = frame_top - frame_bottom
    body_frame = Frame(tx, frame_bottom, inner_w, frame_h,
                       leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                       showBoundary=0)
    remainder = _fill_frame(body_frame, c, leftover_flowables)
    return needed_h, (remainder if remainder else None)


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

    data_lines = wrap_to_width(item.get("data_diri", "") or "", "Helvetica", 6.5, text_w)
    ket_lines = wrap_to_width(item.get("keterangan", "") or "", "Helvetica", 6.5, text_w)
    medsos_lines = []
    for m in medsos:
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


def _draw_gal_stats_chart(c, x, y_top, w, gal_stats):
    """Draw the Tim GAL platform statistics as a stacked horizontal bar chart.
    gal_stats shape: {"narasi": {plat:int,...}, "video": {...}, "meme": {...}}
    Returns the height consumed.
    """
    PLATFORMS = [
        ("instagram",    "INSTAGRAM",    HexColor("#E1306C")),
        ("facebook",     "FACEBOOK",     HexColor("#1877F2")),
        ("twitter",      "TWITTER/X",    HexColor("#1DA1F2")),
        ("tiktok",       "TIKTOK",       HexColor("#69C9D0")),
        ("youtube",      "YOUTUBE",      HexColor("#FF0000")),
        ("threads",      "THREADS",      HexColor("#A1A1AA")),
        ("media_online", "MEDIA ONLINE", HexColor("#10B981")),
    ]
    CATS = [
        ("narasi", "NARASI", HexColor("#10B981")),
        ("video",  "VIDEO",  HexColor("#3B82F6")),
        ("meme",   "MEME",   HexColor("#EC4899")),
    ]
    # Per-platform totals
    rows = []
    grand = 0
    for pkey, plabel, pcolor in PLATFORMS:
        seg = {}
        total = 0
        for ckey, _clabel, _ccolor in CATS:
            v = int((gal_stats.get(ckey) or {}).get(pkey) or 0)
            seg[ckey] = v
            total += v
        grand += total
        rows.append({"key": pkey, "label": plabel, "color": pcolor, "seg": seg, "total": total})

    # Chart frame
    title_h = 4 * mm
    row_h = 4 * mm
    legend_h = 4 * mm
    chart_h = title_h + len(rows) * row_h + legend_h + 4 * mm

    # Subheading bar (lighter than section header)
    c.setFillColor(COLOR_LIGHT)
    c.rect(x, y_top - title_h, w, title_h, stroke=0, fill=1)
    c.setFillColor(COLOR_HEADER)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(x + 2 * mm, y_top - title_h + 1.2 * mm, "STATISTIK PENGGALANGAN PER PLATFORM")
    c.setFillColor(COLOR_AMBER)
    c.drawRightString(x + w - 2 * mm, y_top - title_h + 1.2 * mm, f"TOTAL {grand} POST")

    cur_y = y_top - title_h - 1.5 * mm
    label_w = 22 * mm
    count_w = 28 * mm
    bar_x = x + label_w + 1 * mm
    bar_w_max = w - label_w - count_w - 2 * mm

    max_total = max(1, max(r["total"] for r in rows))

    for r in rows:
        # platform label (left)
        c.setFillColor(r["color"])
        c.setFont("Helvetica-Bold", 6)
        c.drawString(x + 1.5 * mm, cur_y - 2.5 * mm, r["label"])
        # bar background
        c.setFillColor(HexColor("#1F1F23"))
        c.rect(bar_x, cur_y - 3 * mm, bar_w_max, 2.4 * mm, stroke=0, fill=1)
        # stacked segments
        if r["total"] > 0:
            seg_x = bar_x
            full_w = (r["total"] / max_total) * bar_w_max
            for ckey, _, ccolor in CATS:
                v = r["seg"][ckey]
                if v <= 0:
                    continue
                seg_w = (v / r["total"]) * full_w
                c.setFillColor(ccolor)
                c.rect(seg_x, cur_y - 3 * mm, seg_w, 2.4 * mm, stroke=0, fill=1)
                seg_x += seg_w
        # numbers (right)
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica", 5.2)
        n_str = (
            f"N {r['seg']['narasi']}  ·  V {r['seg']['video']}  ·  M {r['seg']['meme']}  "
        )
        c.drawRightString(x + w - 6 * mm, cur_y - 2.4 * mm, n_str)
        c.setFillColor(COLOR_AMBER)
        c.setFont("Helvetica-Bold", 6)
        c.drawRightString(x + w - 1.5 * mm, cur_y - 2.4 * mm, str(r["total"]))
        cur_y -= row_h

    # Legend strip
    cur_y -= 1 * mm
    lx = x + 1.5 * mm
    c.setFont("Helvetica-Bold", 5.5)
    for ckey, clabel, ccolor in CATS:
        c.setFillColor(ccolor)
        c.rect(lx, cur_y - 2.2 * mm, 2 * mm, 2 * mm, stroke=0, fill=1)
        c.setFillColor(COLOR_TEXT)
        c.drawString(lx + 3 * mm, cur_y - 2 * mm, clabel)
        # width of " LABEL " ≈ len*1.4mm
        lx += 3 * mm + len(clabel) * 1.5 * mm + 4 * mm
    cur_y -= legend_h

    return chart_h + 2 * mm  # plus small bottom gap


def _draw_gal_card(c, x, y_top, w, item):
    pad = 2 * mm
    cat = (item.get("kategori") or "").upper()
    if cat == "MEDSOS":
        cat = "MEME"
    cat_color = {"NARASI": COLOR_BLUE, "VIDEO": COLOR_RED, "MEME": COLOR_PURPLE}.get(cat, COLOR_MUTED)
    inner_w = w - 2 * pad
    img = decode_image(item.get("gambar"))
    img_w = 40 * mm if img else 0
    text_w = inner_w - (img_w + 2 * mm if img else 0)

    judul_lines = wrap_to_width(item.get("judul", "—"), "Helvetica-Bold", 8, text_w)[:3]
    links = [lk for lk in (item.get("links") or []) if lk]
    link_lines = []
    for ln in links:
        for w_ln in wrap_to_width(ln, "Helvetica", 6, text_w):
            link_lines.append(w_ln)
    ket_lines = wrap_to_width(item.get("keterangan", "") or "", "Helvetica", 6.5, text_w)

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


SATGAS_LABEL_PIKET = {"tek": "SATGAS TEK", "sandi": "SATGAS SANDI", "medis": "SATGAS MEDIS"}
SATGAS_COLOR_PIKET = {"tek": COLOR_BLUE, "sandi": COLOR_PURPLE, "medis": COLOR_RED}


def _measure_piket_card(item, w):
    pad = 2 * mm
    has_img = bool(item.get("gambar"))
    img_w = 35 * mm if has_img else 0
    text_w = w - 2 * pad - (img_w + 2 * mm if has_img else 0)
    judul_lines = wrap_to_width(item.get("judul", "—"), "Helvetica-Bold", 8, text_w)[:3]
    # Full isi text — no [:8] cap
    isi_lines = wrap_to_width(item.get("isi", "") or "", "Helvetica", 6.5, text_w)
    h = 3 * mm + 4 * mm  # badge row
    h += 2.7 * mm * len(judul_lines) + 0.5 * mm
    if isi_lines:
        h += 2.4 * mm + 2.3 * mm * len(isi_lines) + 0.5 * mm
    h += 2 * mm
    if has_img:
        h = max(h, 28 * mm)
    return h


def _draw_piket_card(c, x, y_top, w, item):
    pad = 2 * mm
    sat = (item.get("satgas") or "").lower()
    sat_label = SATGAS_LABEL_PIKET.get(sat, sat.upper() or "SATGAS")
    sat_color = SATGAS_COLOR_PIKET.get(sat, COLOR_MUTED)
    inner_w = w - 2 * pad
    img = decode_image(item.get("gambar"))
    img_w = 35 * mm if img else 0
    text_w = inner_w - (img_w + 2 * mm if img else 0)

    judul_lines = wrap_to_width(item.get("judul", "—"), "Helvetica-Bold", 8, text_w)[:3]
    # Full isi text — no [:8] cap; preserve user input fully
    isi_lines = wrap_to_width(item.get("isi", "") or "", "Helvetica", 6.5, text_w)

    h = 3 * mm + 4 * mm
    h += 2.7 * mm * len(judul_lines) + 0.5 * mm
    if isi_lines:
        h += 2.4 * mm + 2.3 * mm * len(isi_lines) + 0.5 * mm
    h += 2 * mm
    if img:
        h = max(h, 28 * mm)

    y_bot = y_top - h
    c.setStrokeColor(COLOR_BORDER)
    c.setLineWidth(0.4)
    c.rect(x, y_bot, w, h, stroke=1, fill=0)
    c.setFillColor(sat_color)
    c.rect(x, y_bot, 1.2 * mm, h, stroke=0, fill=1)

    tx = x + pad + 1.5 * mm
    cy = y_top - 3 * mm
    # SATGAS badge
    c.setFillColor(sat_color)
    c.rect(tx, cy - 3 * mm, 22 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 6)
    c.drawString(tx + 1 * mm, cy - 3 * mm + 0.9 * mm, sat_label)
    # Judul
    c.setFillColor(COLOR_HEADER)
    c.setFont("Helvetica-Bold", 8)
    jy = cy - 6.5 * mm
    for line in judul_lines:
        c.drawString(tx, jy, line)
        jy -= 2.7 * mm
    # Isi
    if isi_lines:
        jy -= 0.3 * mm
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica-Bold", 5.5)
        c.drawString(tx, jy, "ISI LAPORAN")
        jy -= 2.2 * mm
        c.setFillColor(COLOR_TEXT)
        c.setFont("Helvetica", 6.5)
        for line in isi_lines:
            c.drawString(tx, jy, line)
            jy -= 2.3 * mm
    # Image (right)
    if img:
        fit_image(c, img, x + w - pad - img_w, y_bot + 2 * mm, img_w, h - 4 * mm)
    return h


# ---------- MAIN ----------
def build_summary_pdf(data, ai_text, ai_html=None, header_title=None, header_subtitle=None, skip_piket=False, variant="default"):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    rd = data.get("report_date", "")
    state = {"page": 1, "y": 0}

    # If skip_piket: clear piket data so PIKET section renders empty/skipped
    if skip_piket:
        data = dict(data)
        data["piket"] = []

    avail_top = PAGE_H - 18 * mm - 4 * mm
    avail_bottom = 13 * mm
    w = PAGE_W - 2 * MARGIN

    def new_page():
        _draw_footer(c, state["page"], variant=variant)
        c.showPage()
        state["page"] += 1
        _draw_header(c, rd, title_override=header_title, subtitle_override=header_subtitle, variant=variant)
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

    def begin_section(title, count_text, first_item_h):
        """Ensure section header has at least `first_item_h` mm of content space
        below it on the same page. Prevents orphan headers (judul yatim).
        """
        section_header_h = 7 * mm
        min_needed = section_header_h + first_item_h
        if state["y"] - min_needed < avail_bottom:
            new_page()
        section_title(title, count_text)

    # =========== COVER PAGE (Morning variant only) ===========
    if variant == "morning":
        _draw_morning_cover_page(c, rd, title_text=header_title)
        c.showPage()
        state["page"] = 2  # next page after cover

    # =========== PAGE 1: Executive Summary (FULL PAGE) ===========
    _draw_header(c, rd, title_override=header_title, subtitle_override=header_subtitle, variant=variant)
    sum_top = avail_top
    sum_bottom = avail_bottom
    sum_h = sum_top - sum_bottom
    leftover, is_rich, exec_content_bottom = _draw_executive_summary(
        c, MARGIN, sum_bottom, w, sum_h, ai_text, data, ai_html=ai_html)
    state["y"] = exec_content_bottom - 2 * mm

    # === Continuation pages for AI Executive Summary (if any leftover) ===
    cont_idx = 1
    while leftover:
        new_page()
        # Full-page frame for continuation: from avail_top down to avail_bottom
        cont_title_y = state["y"]
        cont_title_y = _panel_title(c, MARGIN, cont_title_y, w,
                                    f"EXECUTIVE SUMMARY — RINGKASAN HARIAN PIMPINAN (lanjutan {cont_idx})")
        frame_x = MARGIN + 4 * mm
        frame_y = avail_bottom
        frame_w = w - 8 * mm
        frame_h = cont_title_y - frame_y - 2 * mm
        cont_frame = Frame(frame_x, frame_y, frame_w, frame_h,
                           leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                           showBoundary=0)
        leftover = _fill_frame(cont_frame, c, leftover)
        cont_idx += 1
        # Track where content actually ended in the frame so the next section
        # can flow below it instead of jumping to next page.
        try:
            content_bottom = cont_frame._y
        except Exception:
            content_bottom = avail_bottom
        # Tight border around the panel (top of header → just below content)
        c.setStrokeColor(COLOR_BORDER)
        c.setLineWidth(0.5)
        c.rect(MARGIN,
               content_bottom - 1 * mm,
               w,
               cont_title_y - content_bottom + 7 * mm,
               stroke=1, fill=0)
        state["y"] = content_bottom - 2 * mm

    # =========== TREND CHART + PIE CHART STRIP + MEDMON DETAIL ===========
    # Continue from where the executive summary ends — fill the leftover space
    # on the current page instead of always starting a new page (user wants
    # supporting visuals to flow naturally below the narrative).
    trend_h = 95 * mm
    cases_h = 70 * mm
    # If executive summary ended exactly at page bottom, state["y"] is at
    # avail_bottom; ensure we have at least trend_h+breathing room or new_page.
    if state["y"] - trend_h < avail_bottom:
        new_page()
        state["y"] = avail_top
    else:
        # Small breathing gap below executive summary panel
        state["y"] -= 4 * mm
    _draw_sentiment_trend_chart(c, MARGIN, state["y"] - trend_h, w, trend_h, data.get("medmon_trend") or {})
    state["y"] -= trend_h + 4 * mm
    if state["y"] - cases_h < avail_bottom:
        new_page()
        state["y"] = avail_top
    _draw_sentiment_cases_strip(c, MARGIN, state["y"] - cases_h, w, cases_h, data)
    state["y"] -= cases_h + 3 * mm

    # MEDMON detail cards — all subjects, auto-paginated (no longer capped at 3)
    medmon_items = data.get("medmon", [])
    begin_section("MEDIA MONITORING (DETAIL PER SUBJEK)",
                  f"{len(medmon_items)} SUBJEK",
                  _measure_medmon_card(medmon_items[0], w) if medmon_items else 12 * mm)
    if not medmon_items:
        c.setFillColor(COLOR_MUTED); c.setFont("Helvetica-Oblique", 7)
        c.drawString(MARGIN + 2 * mm, state["y"] - 4 * mm, "Tidak ada subjek medmon.")
        state["y"] -= 6 * mm
    else:
        for it in medmon_items:
            h_est = _measure_medmon_card(it, w)
            if state["y"] - h_est < avail_bottom:
                new_page()
            _draw_medmon_card(c, MARGIN, state["y"], w, it)
            state["y"] -= h_est + 2 * mm

    state["y"] -= 2 * mm

    # =========== Detail cards (auto-paginated): LID → KONTRA → GAL → PIKET ===========
    new_page()
    state["y"] = avail_top

    # LID
    lid_items = data.get("lid", [])
    first_h = _measure_lid_card(lid_items[0], w) if lid_items else 12 * mm
    begin_section("BERITA TRENDING (TIM LID)", f"{len(lid_items)} ITEM", min(first_h, 60 * mm))
    if not lid_items:
        c.setFillColor(COLOR_MUTED); c.setFont("Helvetica-Oblique", 7)
        c.drawString(MARGIN + 2 * mm, state["y"] - 4 * mm, "Tidak ada berita.")
        state["y"] -= 6 * mm
    else:
        page_max = avail_top - avail_bottom
        for it in lid_items:
            h_est = _measure_lid_card(it, w)
            avail_now = state["y"] - avail_bottom
            if h_est <= avail_now:
                # Card fits in current available space — draw whole
                drawn_h, leftover = _draw_lid_card(c, MARGIN, state["y"], w, it)
                state["y"] -= drawn_h + 2 * mm
            elif h_est <= page_max:
                # Card fits on a fresh page — start new page and draw whole
                # (no "lanjutan" label needed; avoids ugly stub on previous page)
                new_page()
                drawn_h, leftover = _draw_lid_card(c, MARGIN, state["y"], w, it)
                state["y"] -= drawn_h + 2 * mm
            else:
                # Card truly too tall for one page — split across pages
                first_chunk_h = avail_now - 2 * mm
                drawn_h, leftover = _draw_lid_card(c, MARGIN, state["y"], w, it,
                                                   max_height=first_chunk_h)
                state["y"] -= drawn_h + 2 * mm
                while leftover:
                    new_page()
                    avail_now = state["y"] - avail_bottom
                    drawn_h, leftover = _draw_lid_card_continuation(
                        c, MARGIN, state["y"], w, it, leftover,
                        max_height=avail_now)
                    state["y"] -= drawn_h + 2 * mm

    state["y"] -= 2 * mm

    # KONTRA
    kontra_items = data.get("kontra", [])
    first_h = _measure_kontra_card(kontra_items[0], w) if kontra_items else 12 * mm
    begin_section("PROFILING (TIM KONTRA)", f"{len(kontra_items)} TO", first_h)
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
    gal_stats = data.get("gal_stats") or {}
    stats_h = 24 * mm if gal_stats else 0
    first_h = _measure_gal_card(gal_items[0], w) if gal_items else 12 * mm
    begin_section("KONTEN / NARASI / MEME (TIM GAL)", f"{len(gal_items)} KONTEN", first_h + stats_h)
    if gal_stats:
        consumed = _draw_gal_stats_chart(c, MARGIN, state["y"], w, gal_stats)
        state["y"] -= consumed
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

    # PIKET — laporan Satgas Tek/Sandi/Medis (placed BEFORE GEOINT per requirement)
    piket_items = data.get("piket", [])
    first_h = _measure_piket_card(piket_items[0], w) if piket_items else 12 * mm
    begin_section("LAPORAN SATGAS TEK / SANDI / MEDIS (PIKET)", f"{len(piket_items)} LAPORAN", first_h)
    if not piket_items:
        c.setFillColor(COLOR_MUTED); c.setFont("Helvetica-Oblique", 7)
        c.drawString(MARGIN + 2 * mm, state["y"] - 4 * mm, "Tidak ada laporan piket.")
        state["y"] -= 6 * mm
    else:
        for it in piket_items:
            h_est = _measure_piket_card(it, w)
            if state["y"] - h_est < avail_bottom:
                new_page()
            _draw_piket_card(c, MARGIN, state["y"], w, it)
            state["y"] -= h_est + 2 * mm

    # GEOINT — DEDICATED FULL PAGE with big map + name labels
    new_page()
    _draw_geoint_fullpage(c, MARGIN, MARGIN + w, avail_top, avail_bottom, data)

    _draw_footer(c, state["page"], variant=variant)
    c.showPage()
    c.save()
    return buf.getvalue()
