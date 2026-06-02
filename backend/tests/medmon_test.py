"""Test MEDMON with very long analisa (matching user's screenshot)."""
import sys
sys.path.insert(0, "/app/backend")
from pdf_generator import build_summary_pdf
from md_to_html import md_to_html

data = {
    "report_date": "2026-06-02",
    "lid": [], "kontra": [], "gal": [], "gal_stats": {},
    "piket": [], "geoint": [],
    "medmon_trend": {"dates": [], "subjects": {}},
    "medmon": [
        {
            "subjek": "Presiden",
            "ringkasan": "Pemberitaan tentang Gibran.",
            "analisa": "Berdasarkan perkembangan pemberitaan terbaru, narasi politik nasional menunjukkan dinamika yang cukup kompleks. Beberapa media menyoroti pernyataan Wakil Presiden terkait visi pertahanan dan diplomasi luar negeri, sementara media lain memberi perhatian pada isu pemenuhan janji kampanye dan implementasi program Astacita.",
            "sentiment_positif": 42, "sentiment_negatif": 30, "sentiment_netral": 28, "berita":[{"sentiment":"positif"},{"sentiment":"negatif"}]
        },
        {
            "subjek": "Andrie Yunus",
            "ringkasan": "Persidangan",
            "analisa": "Masuknya perkara ke tahap persidangan menjadi momentum penting untuk menguji independensi, transparansi, dan akuntabilitas proses penegakan hukum. Mengingat adanya dugaan keterlibatan anggota TNI aktif sebagai pelaku, perhatian publik tidak hanya tertuju pada pembuktian unsur pidana, tetapi juga pada sejauh mana persidangan mampu mengungkap motif, rantai komando, dan kemungkinan adanya pihak lain di balik pelaku lapangan dalam perencanaan maupun pemberian perintah. Proses ini akan menjadi cermin bagi sistem peradilan militer dan koneksitas dalam menangani perkara yang melibatkan anggota TNI aktif, sekaligus uji bagi prinsip equality before the law.",
            "sentiment_positif": 57.8, "sentiment_negatif": 30.2, "sentiment_netral": 12.0, "berita":[{"sentiment":"positif"},{"sentiment":"negatif"}]
        },
        {
            "subjek": "Panglima TNI",
            "ringkasan": "Pemakaman & Prada MR",
            "analisa": """1. Pemakaman militer Jenderal TNI (Purn) Ryamizard Ryacudu di Taman Makam Pahlawan Kalibata mencerminkan penghormatan negara terhadap sosok yang memiliki kontribusi besar dalam bidang pertahanan dan kemiliteran Indonesia. Kehadiran Panglima TNI, para Kepala Staf Angkatan, serta Menteri Pertahanan menunjukkan posisi strategis almarhum dalam sejarah TNI dan pemerintahan nasional. Dengan rekam jejak sebagai Kepala Staf Angkatan Darat dan Menteri Pertahanan, Ryamizard dikenang sebagai figur yang menekankan loyalitas, disiplin, dan komitmen terhadap kedaulatan negara. Selain menjadi penghormatan terakhir, prosesi ini juga berfungsi sebagai simbol penghargaan institusional sekaligus upaya meneguhkan nilai-nilai pengabdian dan kepemimpinan yang diharapkan dapat diwarisi oleh generasi prajurit TNI berikutnya.

2. Kasus dugaan penganiayaan yang melibatkan Prada MR terhadap seorang warga sipil di Situbondo menyoroti pentingnya penegakan disiplin dan akuntabilitas hukum bagi setiap anggota aparat negara. Berdasarkan keterangan keluarga korban dan saksi, dugaan penggunaan identitas palsu untuk mendatangi korban serta tindakan kekerasan yang dipicu persoalan pribadi menunjukkan adanya indikasi penyelesaian masalah di luar mekanisme hukum yang semestinya. Sikap keluarga korban yang menolak perdamaian dan meminta proses hukum dilanjutkan hingga peradilan militer mencerminkan harapan publik agar kasus ditangani secara transparan, profesional, dan tanpa perlakuan istimewa. Apabila dugaan tersebut terbukti, penanganan yang tegas akan menjadi penting untuk menjaga kepercayaan masyarakat terhadap institusi TNI sekaligus menegaskan bahwa setiap pelanggaran hukum oleh aparat tetap harus dipertanggungjawabkan sesuai aturan yang berlaku.""",
            "sentiment_positif": 56.2, "sentiment_negatif": 21.8, "sentiment_netral": 22.0, "berita":[{"sentiment":"positif"},{"sentiment":"negatif"}]
        },
        {
            "subjek": "MBG",
            "ringkasan": "Program MBG",
            "analisa": "Berdasarkan perkembangan pemberitaan terbaru, pelaksanaan Program Makan Bergizi Gratis (MBG) menunjukkan adanya upaya penguatan tata kelola dan pengawasan secara simultan di tengah masih ditemukannya berbagai kendala operasional di lapangan. Penghentian sementara sejumlah SPPG di Pasuruan, Lumajang, dan Banjarnegara akibat belum terpenuhinya standar IPAL maupun kualitas air menunjukkan bahwa aspek sanitasi, infrastruktur, dan kelaikan operasional masih menjadi titik rawan utama yang berpotensi memengaruhi keberlanjutan dan kepercayaan publik terhadap program. Selain itu, evaluasi terhadap menu, prosedur penyaluran, hingga ketepatan sasaran perlu terus diperkuat agar MBG benar-benar memberi dampak gizi nyata bagi penerima manfaat.",
            "sentiment_positif": 53, "sentiment_negatif": 31, "sentiment_netral": 16, "berita":[{"sentiment":"positif"},{"sentiment":"positif"},{"sentiment":"positif"},{"sentiment":"negatif"},{"sentiment":"negatif"},{"sentiment":"negatif"}]
        },
        {
            "subjek": "Indonesia Gelap",
            "ringkasan": "Krisis BBM",
            "analisa": "Diskursus 'Indonesia Gelap' yang muncul kembali di ruang publik mencerminkan ketidakpuasan sebagian masyarakat terhadap kondisi sosial, ekonomi, dan politik nasional yang dinilai stagnan. Narasi ini mengangkat berbagai isu mulai dari pelambatan ekonomi, tingginya angka pengangguran, hingga sengkarut kebijakan publik yang dianggap tidak berpihak pada rakyat kecil.",
            "sentiment_positif": 44, "sentiment_negatif": 27, "sentiment_netral": 29, "berita":[{"sentiment":"positif"},{"sentiment":"negatif"}]
        },
    ],
}

pdf = build_summary_pdf(data, ai_text="Test", ai_html=md_to_html("Test"))
with open("/app/backend/tests/medmon_test.pdf", "wb") as f:
    f.write(pdf)
print(f"Wrote: {len(pdf)} bytes")
