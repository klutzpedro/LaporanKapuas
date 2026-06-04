"""AI summary generator using Claude Sonnet 4.5 via emergentintegrations.

Summarizes ALL data from the day (LID, KONTRA, GAL, MEDMON, GEOINT, PIKET),
not just news. Output should be compact and dense for executive consumption.
"""
import os
import logging
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger("bais.ai")

SYSTEM_PROMPT = (
    "Anda adalah analis intelijen strategis senior BAIS TNI. "
    "Tugas Anda menyusun EXECUTIVE SUMMARY harian yang ringkas, padat, langsung-pakai, dan ANALITIS untuk pimpinan, "
    "dari laporan tim LID, KONTRA, GAL, MEDMON, GEOINT, dan PIKET. "
    "Output WAJIB dalam Bahasa Indonesia formal gaya laporan intelijen militer. "
    "JANGAN copy kalimat dari contoh yang diberikan—pelajari STRUKTUR dan GAYA-nya saja, "
    "lalu ISI dengan analisa berdasarkan data nyata hari ini. "
    "JANGAN sertakan placeholder seperti 'ringkasan 1 kalimat', 'Paragraf N — ...', 'X%/Y%/Z%', "
    "atau text instruksi apapun dalam output. SEMUA harus berupa kalimat analisa lengkap. "
    "JANGAN gunakan markdown (#, **, _, *). "
    "Pada bagian REKOMENDASI: tulis daftar bullet dengan awalan tanda '-' (dash), "
    "setiap rekomendasi 1-2 kalimat action-oriented. "
    "Pada bagian MEDMON: setiap subjek di baris terpisah dengan format "
    "'1. Nama: positif X,X%/negatif Y,Y%/netral Z,Z% — analisa konkret berdasarkan berita/data subjek tersebut.' "
    "Pada bagian PIKET: jelaskan SECARA SPESIFIK isi laporan tiap satgas yang lapor (jangan placeholder '...'). "
    "RINGKASAN EKSEKUTIF wajib panjang 4-6 kalimat analitis yang merangkum tema utama lintas tim."
)


FORMAT_TEMPLATE_EXAMPLE = """\
RINGKASAN EKSEKUTIF:
Hari ini (DD/MM/YYYY) tercatat tiga titik tekanan domestik: eskalasi protes petani tebu Blora dengan aksi destruktif, polarisasi publik atas film "Pesta Babi" terkait agraria Papua, dan kontroversi MBG yang mempertahankan sentimen negatif tinggi (35,7%). Ancaman hybrid meningkat dengan terdeteksinya tiga aktor strategis Papua (dua individu kunci, satu LSM) serta serangan siber terhadap aplikasi terenkripsi Signal. GEOINT mencatat 11 titik OPM aktif tersebar di delapan kabupaten Papua, terkonsentrasi di zona operasi Kodam Cenderawasih dan Kasuari. Pimpinan perlu mewaspadai potensi konvergensi isu agraria Papua–aktivisme struktural dan kelemahan tata kelola program pemerintah sebagai pintu masuk destabilisasi narasi.

1. ACEH:
Tidak ada perkembangan signifikan terpantau periode ini.

2. JAKARTA:
Sentimen Presiden menunjukkan polarisasi ketat (positif 40,27%, negatif 34,06%) di tengah liputan diplomasi Qatar, memerlukan penguatan narasi capaian konkret untuk menyeimbangkan persepsi domestik.

3. PAPUA:
Polemik film "Pesta Babi" berkembang dari isu agraria menjadi instrumen polarisasi oleh jaringan advokasi (JATAM, Johny Teddy Wakum, Vincentius Siep) dengan potensi eksploitasi sentimen anti-pemerintah. GEOINT mencatat 11 titik OPM aktif di Maybrat, Biak Numfor, Mimika, Intan Jaya, Puncak Jaya, Sorong, Yapen, dan Pegubin—semuanya status aktif dan terkonsentrasi di zona 1-3 operasi Cenderawasih dan Kasuari.

4. INTERNASIONAL:
Tidak ada perkembangan signifikan terpantau periode ini.

LID:
Aksi "Tumpah Tebu" ratusan petani Blora di PT GMM mengindikasikan kegagalan perjanjian Bulog dan eskalasi metode protes destruktif yang berpotensi menular ke daerah lain jika tidak dimitigasi segera.

KONTRA:
Teridentifikasi tiga TO prioritas: Johny Teddy Wakum (aktor advokasi struktural Papua-agraria), Vincentius Siep (aktivis mahasiswa Papua Jakarta berkembang jadi simpul strategis), dan JATAM (LSM jaringan advokasi tambang sejak 1995 dengan kapasitas mobilisasi lintas wilayah).

GAL:
Konten dominan kontra-opini difokuskan pada tiga kategori: isu sapi kurban APBN (meme, video, narasi), kontroversi film "Pesta Babi" (narasi, meme, video), dan dukungan persidangan terbuka Andrie Yunus (meme).

MEDMON:
1. Presiden: positif 40,27%/negatif 34,06%/netral 25,67% — pemberitaan pertemuan dengan Wakil PM Qatar mendominasi sentimen positif, namun sentimen negatif masih tinggi terkait isu domestik MBG dan kebijakan agraria.
2. Panglima TNI: positif 56,2%/negatif 17,0%/netral 26,8% — pemakaman Jenderal (Purn) Ryamizard Ryacudu meningkatkan citra positif TNI melalui narasi penghormatan dan profesionalisme institusi.
3. MBG: positif 48,2%/negatif 35,7%/netral 16,1% — kritik perencanaan dan penganggaran program masih dominan; persoalan IPAL, sanitasi, dan standardisasi SPPG belum terselesaikan dan menjadi titik rentan narasi.
4. Andrie Yunus: positif 57,4%/negatif 31,7%/netral 10,9% — momentum persidangan terbuka menjadi ujian transparansi dan independensi hukum militer.
5. Indonesia Gelap: positif 46,1%/negatif 27,3%/netral 26,6% — artikel opini mengkritik pelaksanaan MBG sebagai program bermasalah dalam eksekusi.

GEOINT:
Terpantau 11 personel OPM aktif tersebar di Maybrat (2), Biak Numfor (1), Mimika (2), Intan Jaya (1), Puncak Jaya (2), Sorong (1), Yapen (1), dan Pegubin (1) dengan konsentrasi zona 1-3 wilayah operasi Kodam XVII/Cenderawasih dan XVIII/Kasuari.

PIKET:
Satgas Tek melaporkan monitoring kapal asing via AIS di perairan Laut Natuna Utara serta indikasi spoofing sinyal navigasi; Satgas Sandi mendeteksi serangan phishing canggih terhadap pengguna aplikasi Signal di lingkungan instansi pemerintah; Satgas Medis mencatat kenaikan kasus leptospirosis di Gunungkidul dengan 6 kematian, memerlukan koordinasi cepat dengan Dinkes setempat.

REKOMENDASI:
- Koordinasi Kemenko Polkam RI, Kementan RI, dan Perum Bulog untuk memitigasi eskalasi aksi protes petani tebu Blora, melalui negosiasi teknis perjanjian tebu serta mengantisipasi potensi meluasnya aksi destruktif ke daerah produsen tebu dan gula lainnya yang mengalami permasalahan serupa.
- Intensifkan pengawasan digital-fisik terhadap Johny Teddy Wakum, Vincentius Siep, dan JATAM terkait eksploitasi isu film "Pesta Babi" sebagai trigger mobilisasi aksi berbasis isu konflik agraria di Papua.
- Akselerasi publikasi standardisasi SPPG dan audit transparan MBG untuk menekan narasi negatif dan memulihkan kepercayaan publik terhadap program strategis pemerintah.
- Tingkatkan keamanan siber infrastruktur komunikasi pemerintah guna mengantisipasi teknik phishing Signal dan AIS spoofing yang dapat mengancam kedaulatan digital Indonesia.
- Koordinasi Satkowil Papua–Kodam XVII/XVIII untuk mencegah konvergensi aktor OPM-aktivis struktural di zona pertambangan Mimika yang dapat mengeskalasi gangguan Kamtibmas.
"""


def _format_payload(data: dict) -> str:
    rd = data.get("report_date")
    lines = [f"TANGGAL: {rd}", ""]

    lines.append("== LID (Berita Trending) ==")
    for it in data.get("lid", []):
        lines.append(
            f"- [{it.get('cog','').upper()}] {it.get('judul','')} | Fakta: {it.get('fakta','')[:180]} "
            f"| Analisa: {it.get('analisa','')[:200]} | Tindakan: {it.get('tindakan','')[:140]} "
            f"| Rekomendasi: {it.get('rekomendasi','')[:140]}"
        )

    lines.append("\n== KONTRA (Profiling TO) ==")
    for it in data.get("kontra", []):
        lines.append(
            f"- [{it.get('sumber','').upper()}/{it.get('tipe','')}] {it.get('nama_to','')} — "
            f"DataDiri: {it.get('data_diri','')[:180]} | Ket: {it.get('keterangan','')[:140]}"
        )

    lines.append("\n== GAL (Konten Galang) ==")
    for it in data.get("gal", []):
        lines.append(f"- [{it.get('kategori','').upper()}] {it.get('judul','')} | {it.get('keterangan','')[:140]}")

    lines.append("\n== MEDMON (Media Monitoring) ==")
    for it in data.get("medmon", []):
        pos = sum(1 for b in it.get("berita", []) if b.get("sentiment") == "positif")
        neg = sum(1 for b in it.get("berita", []) if b.get("sentiment") == "negatif")
        sp = it.get("sentiment_positif", 0)
        sn = it.get("sentiment_negatif", 0)
        snt = it.get("sentiment_netral", 0)
        lines.append(
            f"- SUBJEK: {it.get('subjek','')} | Sentiment: positif {sp}%, negatif {sn}%, netral {snt}% "
            f"| Berita +{pos}/-{neg} | "
            f"Analisa: {it.get('analisa','')[:220]} | Rekomendasi: {it.get('rekomendasi','')[:160]}"
        )

    lines.append("\n== GEOINT (Posisi OPM) ==")
    for it in data.get("geoint", []):
        lines.append(
            f"- {it.get('wilayah','')} | {it.get('nama_orang','')} | status: {it.get('status','')} "
            f"| lat={it.get('lat')}, lon={it.get('lon')} | Ket: {it.get('keterangan','')[:140]}"
        )

    lines.append("\n== PIKET (Satgas Tek/Sandi/Medis) ==")
    for it in data.get("piket", []):
        lines.append(f"- [{it.get('satgas','').upper()}] {it.get('judul','')}: {it.get('isi','')[:180]}")

    return "\n".join(lines)


async def generate_ai_summary(data: dict) -> str:
    """Generate executive summary. Provider chosen via env AI_PROVIDER:
    - 'ollama' (DEFAULT for production VPS) — calls local Ollama on
      http://127.0.0.1:11434. ZERO data leaves the server.
    - 'claude' — uses Anthropic via Emergent LLM key (data goes to Anthropic).
    - 'off' — no AI; returns a template message indicating to use the
      built-in fallback summary inside the PDF generator.
    """
    provider = (os.environ.get("AI_PROVIDER") or "ollama").lower().strip()
    rd = data.get("report_date", "unknown")
    user_text = _build_user_prompt(data)

    if provider == "off":
        return ""  # Empty string → PDF generator will use its built-in fallback

    if provider == "ollama":
        raw = await _generate_via_ollama(user_text, rd)
    else:
        # claude (default Emergent path)
        raw = await _generate_via_claude(user_text, rd)

    cleaned = _sanitize_output(raw)
    cleaned = _enforce_completeness(cleaned, data)
    return cleaned


def _enforce_completeness(text: str, data: dict) -> str:
    """Safety net: kalau AI lupa atau ter-truncate section penting,
    tambahkan fallback isi dari data mentah (lebih baik ada daripada hilang).
    """
    if not text or text.lstrip().startswith("[AI SUMMARY ERROR"):
        return text

    import re

    def has_section(label: str) -> tuple[bool, str]:
        """Return (exists, content_after_label_until_next_section)."""
        pattern = re.compile(rf"(?m)^{re.escape(label)}:\s*$")
        m = pattern.search(text)
        if not m:
            return (False, "")
        # Find next label
        rest = text[m.end():]
        next_m = re.search(r"(?m)^[A-Z0-9][A-Z0-9\.\s]*:\s*$", rest)
        body = rest[:next_m.start()] if next_m else rest
        return (True, body.strip())

    # ----- 1) MEDMON: pastikan SEMUA subjek tercantum dengan analisa lengkap -----
    medmon_items = data.get("medmon", [])
    if medmon_items:
        has, body = has_section("MEDMON")
        # Build dict { subj_lower: analisa_string }
        subj_data = {}
        for it in medmon_items:
            subj = (it.get("subjek") or "").strip()
            if not subj:
                continue
            analisa = (it.get("analisa") or "").strip()
            if not analisa:
                berita = it.get("berita") or []
                if berita and isinstance(berita, list):
                    first = berita[0]
                    if isinstance(first, dict):
                        analisa = (first.get("judul") or first.get("ringkasan") or "").strip()
            analisa = analisa or "sentimen termonitor pada periode pelaporan."
            subj_data[subj.lower()] = {
                "subj": subj,
                "sp": it.get("sentiment_positif", 0),
                "sn": it.get("sentiment_negatif", 0),
                "snt": it.get("sentiment_netral", 0),
                "analisa": analisa[:400],
            }

        # Rebuild seluruh MEDMON body untuk ensure setiap subjek lengkap & ada analisa
        rebuilt_lines = []
        for i, (key, d) in enumerate(subj_data.items(), start=1):
            rebuilt_lines.append(
                f"{i}. {d['subj']}: positif {d['sp']}%/negatif {d['sn']}%/netral {d['snt']}% — {d['analisa']}"
            )

        # Check if existing body sudah baik (ada semua subjek + ada analisa text > 30 char per line)
        body_has_all = all(d["subj"].lower() in body.lower() for d in subj_data.values())
        body_has_analisa = all(
            re.search(rf"{re.escape(d['subj'])}.*?—\s*\S.{{30,}}", body, re.IGNORECASE | re.DOTALL)
            for d in subj_data.values()
        )

        if not (body_has_all and body_has_analisa) and rebuilt_lines:
            text = _replace_section_body(text, "MEDMON", "\n".join(rebuilt_lines))

    # ----- 2) PIKET: pastikan SEMUA satgas tercantum dengan isi spesifik -----
    piket_items = data.get("piket", [])
    if piket_items:
        has, body = has_section("PIKET")
        # Cek apakah ada placeholder "..." di body
        has_placeholder = bool(re.search(r"Satgas\s+\w+\s*\.{2,}", body, re.IGNORECASE))
        # Group by satgas
        by_satgas: dict[str, list[str]] = {}
        for it in piket_items:
            sg = (it.get("satgas") or "").upper().strip()
            if sg:
                judul = (it.get("judul") or "").strip()
                isi = (it.get("isi") or "").strip()
                snippet = f"{judul}: {isi}" if isi and judul else (judul or isi)
                by_satgas.setdefault(sg, []).append(snippet[:300])
        missing_satgas = [
            sg for sg in by_satgas
            if not re.search(rf"\bsatgas\s+{re.escape(sg)}\b", body, re.IGNORECASE)
            and not re.search(rf"\b{re.escape(sg)}\b", body, re.IGNORECASE)
        ]
        if missing_satgas or has_placeholder:
            # Replace seluruh isi PIKET dengan versi lengkap dari data
            chunks = []
            for sg, items in by_satgas.items():
                items_text = "; ".join(items[:3])
                chunks.append(f"Satgas {sg.title()} melaporkan {items_text}.")
            full_piket_body = " ".join(chunks)
            # Replace section body
            text = _replace_section_body(text, "PIKET", full_piket_body)

    # ----- 3) REKOMENDASI: pastikan minimal 4 bullet -----
    has, body = has_section("REKOMENDASI")
    # Count bullets / non-empty lines
    bullet_lines = [ln for ln in body.split("\n") if ln.strip().startswith("-") and len(ln.strip()) > 3]
    if not has or len(bullet_lines) < 3:
        fallback = _fallback_rekomendasi(data)
        if has:
            text = _append_to_section(text, "REKOMENDASI", "\n" + fallback)
        else:
            text = text.rstrip() + "\n\nREKOMENDASI:\n" + fallback

    return text


def _append_to_section(text: str, label: str, addition: str) -> str:
    """Insert `addition` at the end of section `label` (before next section)."""
    import re
    pattern = re.compile(rf"(?m)^{re.escape(label)}:\s*$")
    m = pattern.search(text)
    if not m:
        return text.rstrip() + f"\n\n{label}:\n{addition.lstrip()}"
    rest = text[m.end():]
    next_m = re.search(r"(?m)^[A-Z0-9][A-Z0-9\.\s]*:\s*$", rest)
    if next_m:
        insert_pos = m.end() + next_m.start()
        return text[:insert_pos].rstrip() + "\n" + addition.lstrip() + "\n\n" + text[insert_pos:]
    return text.rstrip() + "\n" + addition.lstrip()


def _replace_section_body(text: str, label: str, new_body: str) -> str:
    """Replace the body of a section (label:...next_label) with new_body."""
    import re
    pattern = re.compile(rf"(?m)^{re.escape(label)}:\s*$")
    m = pattern.search(text)
    if not m:
        return text.rstrip() + f"\n\n{label}:\n{new_body.lstrip()}"
    rest = text[m.end():]
    next_m = re.search(r"(?m)^[A-Z0-9][A-Z0-9\.\s]*:\s*$", rest)
    if next_m:
        end_pos = m.end() + next_m.start()
        return text[:m.end()] + "\n" + new_body.strip() + "\n\n" + text[end_pos:]
    return text[:m.end()] + "\n" + new_body.strip()


def _fallback_rekomendasi(data: dict) -> str:
    """Generate 4 rekomendasi standar berdasarkan ringkasan data."""
    paragraphs = []

    # Dari LID — rekomendasi mitigasi
    lid = data.get("lid", [])
    if lid:
        topik = (lid[0].get("judul") or "isu trending hari ini").strip()
        paragraphs.append(
            f"Koordinasi kementerian/lembaga terkait untuk memitigasi eskalasi {topik}, "
            "melalui sinkronisasi narasi resmi dan respons cepat terhadap potensi keresahan publik."
        )

    # Dari KONTRA — rekomendasi pengawasan
    kontra = data.get("kontra", [])
    if kontra:
        names = [k.get("nama_to", "").strip() for k in kontra if k.get("nama_to")][:3]
        names_str = ", ".join(names) if names else "TO yang teridentifikasi"
        paragraphs.append(
            f"Intensifkan pengawasan digital-fisik terhadap {names_str} untuk mendeteksi dini "
            "rencana aksi dan mengamankan agenda strategis nasional."
        )

    # Dari MEDMON — rekomendasi penanganan sentimen
    medmon = data.get("medmon", [])
    negatif_subj = [m.get("subjek") for m in medmon
                    if m.get("subjek") and (m.get("sentiment_negatif") or 0) > 30]
    if negatif_subj:
        paragraphs.append(
            f"Akselerasi publikasi capaian dan komunikasi strategis terkait {', '.join(negatif_subj[:3])} "
            "untuk menekan narasi negatif dan memulihkan kepercayaan publik."
        )

    # Dari GEOINT — rekomendasi keamanan wilayah
    geo = data.get("geoint", [])
    if geo:
        n_aktif = sum(1 for g in geo if str(g.get("status", "")).lower() == "aktif")
        paragraphs.append(
            f"Koordinasi Kodam wilayah Papua untuk memantau {n_aktif} titik OPM aktif "
            "dan mencegah konvergensi aktor bersenjata dengan aktivis struktural di zona pertambangan."
        )

    # Dari PIKET — rekomendasi keamanan siber
    piket = data.get("piket", [])
    if any((p.get("satgas") or "").lower() == "sandi" for p in piket):
        paragraphs.append(
            "Tingkatkan keamanan siber infrastruktur komunikasi pemerintah guna mengantisipasi "
            "teknik phishing dan eksploitasi aplikasi komunikasi terenkripsi."
        )

    if not paragraphs:
        paragraphs.append(
            "Lanjutkan monitoring rutin dan koordinasi antar tim untuk memastikan situasi tetap terkendali."
        )

    # Pastikan minimal 4 paragraf
    while len(paragraphs) < 4:
        paragraphs.append(
            "Lanjutkan koordinasi lintas satuan dan tingkatkan kewaspadaan operasional sesuai prioritas pimpinan."
        )

    # Return sebagai bullet list dengan dash
    return "\n".join(f"- {p}" for p in paragraphs)


# Standard section labels (urutan WAJIB)
_LABELS = [
    "RINGKASAN EKSEKUTIF",
    "1. ACEH", "2. JAKARTA", "3. PAPUA", "4. INTERNASIONAL",
    "LID", "KONTRA", "GAL", "MEDMON",
    "GEOINT", "PIKET", "REKOMENDASI",
]


def _sanitize_output(text: str) -> str:
    """Bersihkan output AI agar konsisten format baku:
    - Hapus markdown (#, **, _, ```).
    - Hapus leakage instruksi (ATURAN WAJIB, CHECKLIST, dst).
    - Hapus placeholder template (ringkasan singkat 1 kalimat, Paragraf N, dst).
    - Pastikan setiap label section ada di baris sendiri diakhiri ':' .
    - Hilangkan preamble/explanatory text di awal sebelum 'RINGKASAN EKSEKUTIF'.
    - Normalize REKOMENDASI sebagai bullet '-'.
    """
    if not text:
        return text
    # Skip error message blocks
    if text.lstrip().startswith("[AI SUMMARY ERROR"):
        return text

    import re

    # 1) Hapus code fences & bold/italic markdown & heading hashes
    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = text.replace("```", "")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)

    # 2) Hapus blok instruksi yang ke-leak (ATURAN WAJIB, CHECKLIST, ===, dst)
    #    Hapus seluruh paragraf yang diawali penanda instruksi
    text = re.sub(r"={2,}\s*[A-Z][^=\n]*={2,}\s*\n", "", text)  # === HEADER ===
    text = re.sub(r"(?im)^\s*ATURAN\s+WAJIB[\s\S]*?(?=^\s*RINGKASAN\s+EKSEKUTIF|^$)", "", text, count=1)
    text = re.sub(r"(?im)^\s*CHECKLIST[^\n]*\n[\s\S]*?(?=^\s*RINGKASAN\s+EKSEKUTIF)", "", text, count=1)
    text = re.sub(r"(?im)^\s*TEMPLATE\s+FORMAT[\s\S]*?(?=^\s*RINGKASAN\s+EKSEKUTIF)", "", text, count=1)

    # 3) Skip preamble: cari label "RINGKASAN EKSEKUTIF" sebagai SECTION HEADER
    m = re.search(r"(?m)^[ \t]*RINGKASAN[ \t]+EKSEKUTIF[ \t]*:?[ \t]*$", text)
    if m:
        text = text[m.start():]
    else:
        # fallback: any occurrence
        m2 = re.search(r"RINGKASAN\s+EKSEKUTIF\s*:", text, re.IGNORECASE)
        if m2:
            text = text[m2.start():]

    # 4) Hapus placeholder text yang nyangkut
    placeholders = [
        r"—\s*ringkasan\s+singkat\s+1\s+kalimat\.?",
        r"—\s*ringkasan\s+singkat\.?",
        r"—\s*analisa\s+konkret[^\.]*\.?",
        r"X,?X?%/Y,?Y?%/Z,?Z?%",
        r"DD/MM/YYYY",
        r"Satgas\s+Tek\s*\.{2,}\s*;?\s*",
        r"Satgas\s+Sandi\s*\.{2,}\s*;?\s*",
        r"Satgas\s+Medis\s*\.{2,}\s*;?\s*",
    ]
    for p in placeholders:
        text = re.sub(p, "", text, flags=re.IGNORECASE)

    # 5) Strip "Paragraf N — " prefix di section REKOMENDASI
    text = re.sub(r"(?m)^\s*Paragraf\s+\d+\s*[—\-:.]?\s*", "- ", text, flags=re.IGNORECASE)

    # 6) Normalize label lines: setiap label canonical "LABEL:\n"
    for label in _LABELS:
        pattern = re.compile(
            r"(?m)^[ \t]*" + re.escape(label) + r"[ \t]*:?[ \t]*$"
        )
        text = pattern.sub(f"\n{label}:", text, count=1)

    # 7) Pada section REKOMENDASI: pastikan setiap line jadi bullet "- "
    rekom_match = re.search(r"(?m)^REKOMENDASI:\s*$", text)
    if rekom_match:
        before = text[:rekom_match.end()]
        after = text[rekom_match.end():]
        next_label = re.search(r"(?m)^[A-Z0-9][A-Z0-9\.\s]{1,30}:\s*$", after)
        body = after[:next_label.start()] if next_label else after
        tail = after[next_label.start():] if next_label else ""

        # SPLIT body menjadi rekomendasi-rekomendasi individual.
        # Pisahkan per baris dulu, kalau ada multiple kalimat dalam 1 baris,
        # pisahkan per kalimat (titik akhir).
        bullets = []
        for ln in body.split("\n"):
            ln = ln.strip()
            if not ln:
                continue
            # Strip existing bullet/dash/number prefix
            ln = re.sub(r"^[\-\*•·]\s*", "", ln)
            ln = re.sub(r"^\d+[\.\)]\s*", "", ln)
            # If line mengandung beberapa kalimat panjang (mis. "Koor.... Inten.... Aksel..."),
            # split per kalimat tapi merge kalimat pendek (<30 char).
            sentences = re.split(r"(?<=[\.\!])\s+(?=[A-Z])", ln)
            for s in sentences:
                s = s.strip()
                if s and len(s) > 10:
                    bullets.append(s)

        bullets = [b for b in bullets if b]
        if bullets:
            new_body = "\n" + "\n".join(f"- {b}" for b in bullets) + "\n"
        else:
            new_body = "\n"
        text = before + new_body + tail

    # 8) Cleanup excessive blank lines & trailing whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    text = "\n".join(line.rstrip() for line in text.split("\n"))

    return text


def _build_user_prompt(data: dict) -> str:
    """Build the prompt text. Shared between providers."""
    medmon_subjects = [it.get("subjek", "").strip() for it in data.get("medmon", []) if it.get("subjek")]
    piket_satgas = sorted(set([(it.get("satgas") or "").upper().strip() for it in data.get("piket", []) if it.get("satgas")]))
    kontra_names = [it.get("nama_to", "").strip() for it in data.get("kontra", []) if it.get("nama_to")]
    geoint_total = len(data.get("geoint", []))
    geoint_aktif = sum(1 for it in data.get("geoint", []) if str(it.get("status", "")).lower() == "aktif")

    checklist_lines = []
    if medmon_subjects:
        checklist_lines.append(f"- MEDMON wajib mencakup {len(medmon_subjects)} subjek: {', '.join(medmon_subjects)}")
    if piket_satgas:
        checklist_lines.append(f"- PIKET wajib menyebut tiap satgas yang lapor: {', '.join(piket_satgas)}")
    if kontra_names:
        checklist_lines.append(f"- KONTRA wajib menyebut nama TO: {', '.join(kontra_names)}")
    if geoint_total:
        checklist_lines.append(f"- GEOINT wajib menyebut total {geoint_total} titik OPM (aktif {geoint_aktif}) dan distribusi wilayah")
    checklist = "\n".join(checklist_lines) if checklist_lines else "(tidak ada data tim hari ini)"

    return (
        "Tugas Anda: Tulis EXECUTIVE SUMMARY harian BAIS TNI berdasarkan DATA HARI INI di bawah. "
        "Pelajari CONTOH OUTPUT di bawah dan tiru STRUKTUR, GAYA BAHASA, dan KEDALAMAN ANALISA-nya. "
        "Ganti setiap kalimat dalam contoh dengan kalimat baru berdasarkan DATA HARI INI yang sebenarnya. "
        "JANGAN copy kalimat dari contoh secara harfiah—gunakan hanya sebagai panduan format.\n\n"
        "=== CONTOH OUTPUT BAGUS (gunakan ini sebagai panduan format & gaya saja) ===\n"
        + FORMAT_TEMPLATE_EXAMPLE +
        "\n=== CHECKLIST KELENGKAPAN UNTUK HARI INI ===\n"
        + checklist +
        "\n\n=== DATA HARI INI ===\n"
        + _format_payload(data) +
        "\n\n"
        "Sekarang tulis EXECUTIVE SUMMARY untuk DATA HARI INI di atas. "
        "Mulai langsung dengan 'RINGKASAN EKSEKUTIF:' di baris pertama. "
        "Output hanya teks bersih tanpa markdown, tanpa preamble, tanpa penjelasan tambahan."
    )


async def _generate_via_ollama(user_text: str, rd: str) -> str:
    """Call local Ollama (100% on-server, no external network).
    Default model: 'llama3.2:3b' (fast, ~2GB RAM). Override via OLLAMA_MODEL.
    """
    import httpx
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
    # Timeout besar karena CPU inference qwen2.5:7b bisa 60-300 detik per request
    timeout_s = float(os.environ.get("OLLAMA_TIMEOUT", "600"))
    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": user_text,
        "stream": False,
        "options": {
            "temperature": 0.2,          # Sedikit naik (0.15 terlalu kaku, AI jadi "malas")
            "top_p": 0.9,
            "repeat_penalty": 1.05,
            "num_ctx": 8192,             # Lebih besar untuk akomodasi checklist + data lengkap
            "num_predict": 4000,         # Lebih besar agar tidak ter-truncate (target 500-800 kata)
        },
    }
    try:
        timeout = httpx.Timeout(timeout_s, connect=10.0, read=timeout_s, write=30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{host}/api/generate", json=payload)
            r.raise_for_status()
            body = r.json()
            text = str(body.get("response", "")).strip()
            if not text:
                logger.error(f"Ollama returned empty response. Body keys: {list(body.keys())}")
                return "[AI SUMMARY ERROR — Ollama mengembalikan respons kosong. Coba ulangi atau ganti model lebih kecil (qwen2.5:3b).]"
            return text
    except httpx.ReadTimeout:
        logger.error(f"Ollama TIMEOUT after {timeout_s}s (model={model}). Coba model lebih kecil.")
        return (
            f"[AI SUMMARY ERROR — Ollama timeout setelah {int(timeout_s)} detik dengan model '{model}'.]\n\n"
            "Coba salah satu solusi:\n"
            "1. Ganti ke model lebih kecil: edit backend/.env → OLLAMA_MODEL=qwen2.5:3b lalu restart bais-backend\n"
            "2. Tambah RAM/CPU VPS\n"
            "3. Tunggu beberapa menit lalu coba lagi (mungkin VPS sedang sibuk)"
        )
    except httpx.ConnectError as e:
        logger.exception(f"Ollama connect error (host={host})")
        return (
            f"[AI SUMMARY ERROR — Tidak dapat terhubung ke Ollama di {host}.]\n\n"
            f"Detail: {type(e).__name__}: {e}\n"
            "Periksa: sudo systemctl status ollama"
        )
    except Exception as e:
        err_type = type(e).__name__
        err_msg = str(e) if str(e) else "(no message)"
        logger.exception(f"Ollama summary failed (host={host}, model={model})")
        return (
            f"[AI SUMMARY ERROR — Ollama lokal tidak merespons: {err_type}: {err_msg}]\n\n"
            "Pastikan Ollama berjalan di VPS (sudo systemctl status ollama) "
            f"dan model '{model}' sudah ter-pull (ollama pull {model})."
        )


async def _generate_via_claude(user_text: str, rd: str) -> str:
    """Legacy: call Anthropic Claude via Emergent LLM key.
    NOTE: data will leave the VPS. Only use if AI_PROVIDER=claude explicitly.
    """
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return "[AI SUMMARY UNAVAILABLE] EMERGENT_LLM_KEY tidak tersedia."
    chat = LlmChat(
        api_key=api_key,
        session_id=f"bais-summary-{rd}",
        system_message=SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    try:
        resp = await chat.send_message(UserMessage(text=user_text))
        return str(resp).strip()
    except Exception as e:
        logger.exception("AI summary failed")
        return f"[AI SUMMARY ERROR] {e}"
