"""Test LID cards with very long content (matching user's PDF)."""
import sys
sys.path.insert(0, "/app/backend")
from pdf_generator import build_summary_pdf
from md_to_html import md_to_html

data = {
    "report_date": "2026-06-01",
    "lid": [
        {
            "cog": "indonesia",
            "judul": "Rencana Demo Aliansi PPS Berpotensi Ganggu Objek Vital dan Stabilitas Kawasan NTB",
            "link": "https://www.detik.com/bali/nusra/d-8512499/asdp-pastikan-penyeberangan-di-pelabuhan-poto-tano-tetap-buka-jelang-demo-pps",
            "fakta": "Massa yang tergabung dalam Aliansi Provinsi Pulau Sumbawa (PPS) akan menggelar aksi demonstrasi besar-besaran pada 2 Juni 2026. Mereka menuntut pemekaran wilayah sehingga Pulau Sumbawa menjadi provinsi baru dan tak lagi di bawah Provinsi Nusa Tenggara Barat (NTB).\nAksi demo rencananya dilakukan serentak di lima kabupaten/kota di Pulau Sumbawa, mulai dari Kabupaten Sumbawa Barat, Sumbawa, Dompu, Bima, dan Kota Bima. Mereka bahkan mengancam akan menutup Pelabuhan Poto Tano, Kabupaten Sumbawa Barat (KSB).",
            "analisa": "Aliansi Provinsi Pulau Sumbawa (PPS) berencana menggelar aksi demonstrasi pada 2 Juni 2026 di lima kabupaten/kota di Pulau Sumbawa dengan tuntutan pencabutan moratorium Daerah Otonomi Baru (DOB) dan percepatan pembentukan Provinsi Pulau Sumbawa. Aksi akan dipusatkan pada sejumlah titik strategis, termasuk Pelabuhan Poto Tano yang merupakan simpul utama mobilitas orang dan logistik antara Pulau Sumbawa dan Pulau Lombok. Adapun tuntutan yang diserukan meliputi pencabutan moratorium DOB oleh pemerintah pusat melalui Kemendagri serta percepatan pembentukan Provinsi Pulau Sumbawa. Di tengah tuntutan tersebut, pemerintah masih mempertahankan moratorium.",
            "tindakan": "Satgas Kapuas melaksanakan monitoring melalui media terbuka dan ruang digital terkait rencana aksi Aliansi PPS dengan fokus pada konsolidasi massa, narasi pemekaran wilayah, serta potensi gangguan terhadap objek vital nasional dan layanan publik. Pendalaman diarahkan pada pemetaan aktor penggerak, jaringan pendukung aksi lintas kabupaten/kota, serta pola mobilisasi yang berkembang menjelang pelaksanaan demonstrasi. Analisis juga mencermati indikasi pemanfaatan isu pemekaran oleh kelompok tertentu untuk membangun tekanan politik terhadap pemerintah pusat dan stabilitas kawasan NTB.",
            "rekomendasi": "Satgas berkoordinasi dengan Kemendagri, Pemprov NTB, Polda NTB, ASDP, KSOP, dan instansi terkait lainnya guna memastikan objek vital dan jalur distribusi strategis tetap beroperasi normal selama rangkaian aksi berlangsung. Rekomendasi strategis meliputi: 1) memperkuat pengamanan berlapis pada Pelabuhan Poto Tano dan titik aksi yang berpotensi mengganggu layanan publik; 2) melakukan pendekatan preventif kepada tokoh penggerak Aliansi PPS guna menegaskan batasan hukum terhadap aksi yang menghambat fasilitas umum; 3) mengoptimalkan operasi intelijen untuk mengidentifikasi pihak yang mendorong eskalasi maupun narasi provokatif; 4) menyiapkan skema komunikasi publik yang terukur untuk meredam disinformasi dan memastikan stabilitas kawasan NTB tetap terjaga.",
        },
        {
            "cog": "papua",
            "judul": "TUDUHAN THEO HESEGEM TERHADAP SUMBER ANCAMAN MASA DEPAN OAP",
            "link": "https://suarapapua.com/2026/05/31/theo-hesegem-ungkap-beberapa-sumber-ancaman-masa-depan-oap/",
            "fakta": "Direktur Yayasan Keadilan dan Keutuhan Manusia Papua (YKKMP), Theo Hesegem, menyatakan keprihatinan mendalam terhadap berbagai persoalan yang mengancam keberlangsungan hidup dan masa depan orang asli Papua (OAP) di tanah leluhurnya sendiri.\nDalam pernyataan tertulis yang diterima di Wamena, Sabtu (30/5/2026), Theo menegaskan, OAP berpotensi menghadapi kemunduran populasi serta tantangan serius dalam mempertahankan keberlangsungan generasi apabila persoalan-persoalan mendasar tidak segera ditangani secara serius dan terukur.",
            "analisa": "Pernyataan Theo Hesegem mengenai berbagai ancaman terhadap masa depan OAP menunjukkan adanya konstruksi narasi yang mengaitkan persoalan demografi, konflik sosial, eksploitasi SDA, serta kebijakan pembangunan sebagai faktor yang berpotensi mengubah posisi strategis OAP di tanah Papua. Isu yang diangkat tidak hanya berkaitan dengan keamanan fisik, tetapi juga menyentuh dimensi identitas, budaya, hak ulayat, dan keberlanjutan eksistensi masyarakat adat. Theo menyoroti kekhawatiran bahwa arus investasi, pemekaran wilayah, migrasi penduduk, serta berbagai proyek pembangunan dianggap sebagai pemicu marginalisasi OAP. Selain itu, narasi tersebut dapat berpotensi memperkuat sentimen separatis.",
            "tindakan": "Satgas melaksanakan monitoring dan pendalaman siber secara intensif terkait penyebaran pemberitaan, opini, dan narasi yang berkembang mengenai pernyataan Theo Hesegem terkait ancaman terhadap masa depan OAP serta upaya pemanfaatannya dalam mendiskritkan Pemri, guna mengumpulkan fakta-fakta sebagai bahan analisis dalam memetakan potensi kerawanan. Selain itu, mengintensifkan cipta opini di media siber terkait komitmen Pemri dalam melindungi hak-hak OAP, mendorong pembangunan yang inklusif dan berkeadilan, serta mengedepankan berbagai program pemberdayaan masyarakat adat, peningkatan kesejahteraan, perlindungan budaya lokal, dan pelibatan masyarakat Papua.",
            "rekomendasi": "Satgas berkoordinasi dengan Kemkomdigi RI, Puspen TNI, Kodam XVII/Cendrawasih, Kodam XVIII/Kasuari, Kominda, dan K/L terkait lainnya, untuk merumuskan langkah strategis dalam merespons pernyataan Theo Hesegem yang mengangkat isu ancaman terhadap masa depan OAP. Rekomendasi yang perlu diterapkan meliputi: 1) penguatan strategi komunikasi publik terpadu melalui penyebarluasan informasi yang faktual, berimbang, dan edukatif terkait berbagai program perlindungan, pemberdayaan, serta peningkatan kesejahteraan OAP; 2) mendorong pelibatan yang lebih luas terhadap OAP dalam perencanaan, pelaksanaan, dan evaluasi program pembangunan guna memastikan keberhasilan program tepat sasaran dan diterima masyarakat lokal.",
        }
    ],
    "kontra": [], "gal": [], "gal_stats": {}, "medmon": [], "piket": [], "geoint": [],
    "medmon_trend": {"dates": [], "subjects": {}},
}

pdf = build_summary_pdf(data, ai_text="Test LID overflow", ai_html=md_to_html("Test LID overflow"))
with open("/app/backend/tests/lid_test.pdf", "wb") as f:
    f.write(pdf)
print(f"Wrote: {len(pdf)} bytes")
