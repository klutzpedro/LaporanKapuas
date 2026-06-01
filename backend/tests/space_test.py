"""Long AI text test to verify continuation page + space-fill behavior."""
import sys
sys.path.insert(0, "/app/backend")
from pdf_generator import build_summary_pdf
from md_to_html import md_to_html

data = {
    "report_date": "2026-06-01",
    "lid": [], "kontra": [], "gal": [], "gal_stats": {},
    "medmon": [
        {"subjek": "Presiden",     "ringkasan": "Pemberitaan Gibran.","sentiment_positif": 42,"sentiment_negatif":30,"sentiment_netral":28, "berita":[]},
        {"subjek": "Panglima TNI", "ringkasan": "Bantu Polri.",       "sentiment_positif": 57,"sentiment_negatif":19,"sentiment_netral":24, "berita":[]},
        {"subjek": "MBG",          "ringkasan": "Konsolidasi.",       "sentiment_positif": 53,"sentiment_negatif":31,"sentiment_netral":16, "berita":[]},
        {"subjek": "Andrie Yunus", "ringkasan": "Pihak lain.",        "sentiment_positif": 58,"sentiment_negatif":30,"sentiment_netral":12, "berita":[]},
        {"subjek": "Indonesia Gelap","ringkasan":"Janji vs hasil.",    "sentiment_positif": 44,"sentiment_negatif":27,"sentiment_netral":29, "berita":[]},
    ],
    "piket": [], "geoint": [],
    "medmon_trend": {"dates": [], "subjects": {}},
}

ai_text = """**RINGKASAN EKSEKUTIF**

1. ACEH: Kondusif.
2. JAKARTA: Demo buruh tertib.
3. PAPUA: KKB Intan Jaya kembali aktif.

**MEDMON:**
1. Presiden: 42/30/28
2. Panglima TNI: 57/19/24
3. MBG: 53/31/16
4. Andrie Yunus: 58/30/12
5. Indonesia Gelap: 44/27/29

**REKOMENDASI:**
- Tingkatkan pengawasan digital
- Percepat publikasi konkret
- Evaluasi pergerakan OPM
- Verifikasi anomali kapal"""

ai_html = md_to_html(ai_text)
pdf = build_summary_pdf(data, ai_text=ai_text, ai_html=ai_html)
with open("/app/backend/tests/space_test.pdf", "wb") as f:
    f.write(pdf)
print(f"Wrote: {len(pdf)} bytes")
