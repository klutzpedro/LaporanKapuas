import sys
sys.path.insert(0, "/app/backend")
from pdf_generator import build_summary_pdf

data = {
    "report_date": "2026-06-01",
    "lid": [], "kontra": [], "gal": [], "gal_stats": {}, "medmon": [], "piket": [],
    "geoint": [
        {"nama_orang": "Bonatus Aimai",  "wilayah": "Intan Jaya", "lat": -3.85,  "lon": 137.18, "status": "aktif"},
        {"nama_orang": "Egianus Kogoya", "wilayah": "Nduga",      "lat": -4.45,  "lon": 138.00, "status": "aktif"},
        {"nama_orang": "Lekagak Telenggen","wilayah": "Puncak",   "lat": -3.95,  "lon": 137.65, "status": "aktif"},
        {"nama_orang": "Tenius Gwijangge","wilayah": "Nduga",     "lat": -4.60,  "lon": 138.20, "status": "tidak_aktif"},
        {"nama_orang": "Goliath Tabuni", "wilayah": "Puncak Jaya","lat": -3.70,  "lon": 137.45, "status": "aktif"},
        {"nama_orang": "Joni Botak",     "wilayah": "Yahukimo",   "lat": -4.50,  "lon": 139.30, "status": "aktif"},
        {"nama_orang": "Otniel Giban",   "wilayah": "Peg. Bintang", "lat": -4.55, "lon": 140.20, "status": "aktif"},
        {"nama_orang": "Yotam Bugiangge","wilayah": "Yalimo",     "lat": -4.10,  "lon": 139.50, "status": "tidak_aktif"},
        {"nama_orang": "Undius Kogoya",  "wilayah": "Lanny Jaya", "lat": -3.92,  "lon": 138.05, "status": "tidak_aktif"},
    ],
    "medmon_trend": {"dates": [], "subjects": {}},
}
pdf = build_summary_pdf(data, ai_text="Test")
with open("/app/backend/tests/map_test.pdf", "wb") as f:
    f.write(pdf)
print(f"Wrote /app/backend/tests/map_test.pdf: {len(pdf)} bytes")
