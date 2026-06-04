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
    "Pelajari STRUKTUR dan GAYA contoh yang diberikan—lalu ISI dengan analisa berdasarkan data nyata hari ini. "
    "JANGAN copy kalimat dari contoh secara harfiah. "
    "JANGAN sertakan placeholder, instruksi, atau text 'ATURAN WAJIB/CHECKLIST/TEMPLATE' dalam output. "
    "JANGAN gunakan markdown (#, **, _, *). "
    "JANGAN copy-paste raw text mentah dari data ('LAPORAN KEGIATAN', 'I. FAKTA FAKTA', '1. TIM XXX', 'SUBSATGAS')—RINGKAS jadi 1-2 kalimat per item. "
    "Format-specific rules: "
    "(1) RINGKASAN EKSEKUTIF wajib 1 paragraf panjang 5-8 kalimat analitis lintas tim. "
    "(2) ACEH/JAKARTA/PAPUA/INTERNASIONAL wajib 2-4 kalimat per region. "
    "(3) LID, GAL, dan PIKET menggunakan bullet '•' untuk daftar sub-item. "
    "(4) KONTRA dan GEOINT ditulis sebagai paragraf padat 2-4 kalimat. "
    "(5) MEDMON menggunakan format khusus: '• Subjek (±X% positif)' diikuti baris 'a. Positif: ...' "
    "dan 'b. Negatif: ...' jika ada breakdown; atau paragraf 1-2 kalimat untuk subjek yang lebih sederhana. "
    "(6) REKOMENDASI: daftar bullet '•' minimal 4 poin action-oriented (Koordinasi.../Intensifkan.../Akselerasi.../Tingkatkan...)."
)


FORMAT_TEMPLATE_EXAMPLE = """\
RINGKASAN EKSEKUTIF:
Hari ini (04/06/2026) terpantau dinamika tekanan narasi domestik yang didominasi isu tata kelola Program Makan Bergizi Gratis (MBG), stabilitas politik pemerintah, serta meningkatnya perhatian pada isu Papua dan kebijakan lingkungan/ketenagakerjaan. Sentimen media monitoring menunjukkan pola campuran dengan kecenderungan positif moderat pada seluruh objek utama, namun disertai eskalasi narasi kritis terkait dugaan penyimpangan program publik, transparansi penegakan hukum, dan kebijakan pembangunan. Di sisi lain, aktivitas digital menunjukkan intensifikasi kampanye kontra-opini lintas platform dengan isu ekonomi, agraria, dan kebijakan kesehatan sebagai pengungkit utama. Risiko utama hari ini berasal dari konvergensi isu kebijakan publik (MBG, regulasi tembakau, PSN Papua) dengan amplifikasi narasi digital yang berpotensi meningkatkan polarisasi opini.

1. ACEH:
Tidak terpantau dinamika eskalatif signifikan. Aktivitas lebih banyak terkait isu lingkungan dan konservasi (monitoring ekosistem Leuser) tanpa indikasi gangguan stabilitas.

2. JAKARTA:
Sentimen terhadap Presiden berada pada level positif moderat (±39,1%) dengan dominasi pemberitaan penegakan integritas program MBG dan sikap tegas terhadap korupsi. Namun sentimen negatif tetap tinggi akibat isu tata kelola program dan persepsi publik terhadap konsistensi implementasi kebijakan. Dinamika ini menunjukkan polarisasi opini yang masih kuat pada isu domestik prioritas pemerintah.

3. PAPUA:
Isu Papua meningkat dalam konteks narasi pembangunan (PSN), hak masyarakat adat, dan keamanan wilayah. Terdapat konsolidasi opini pro-kontra terkait proyek strategis nasional dan isu pendekatan keamanan. GEOINT mencatat keberadaan 12 titik aktivitas kelompok bersenjata/aktor lokal aktif di sejumlah wilayah Papua Pegunungan, Tengah, dan Barat, yang menunjukkan konsentrasi pada zona rawan operasional. Potensi eskalasi tetap terbuka pada momen momentum sosial dan isu lingkungan.

4. INTERNASIONAL:
Tidak terpantau eskalasi geopolitik langsung, namun terdapat indikasi risiko maritim terkait aktivitas kapal asing di kawasan Natuna dan Selat Malaka yang memerlukan perhatian pengawasan lintas instansi.

LID:
Isu dominan hari ini berasal dari:
• Regulasi kesehatan dan ketenagakerjaan (RPMK kemasan rokok) yang memicu resistensi industri.
• Narasi pembangunan Papua yang dikaitkan dengan isu lingkungan dan hak masyarakat adat. Belum terdapat aksi massa besar terkonfirmasi, namun pola mobilisasi opini digital meningkat signifikan.

KONTRA:
Teridentifikasi tiga TO prioritas: Wilson Lalengke (aktor komunikator strategis PPWI dengan kapasitas konsolidasi narasi kritis lintas isu HAM, kebebasan pers, agraria, dan Papua serta potensi amplifikasi opini melalui jaringan media alternatif dan forum internasional), Forum Konservasi Leuser/FKL (aktor konservasi non-kinetik berbasis Aceh dengan kapasitas pressure opini lingkungan yang dapat memengaruhi kebijakan tata kelola sumber daya alam dan memperkuat isu lingkungan–pembangunan), serta Rudi Kabak (aktor jejaring informasi muda Papua dengan keterhubungan pada simpul mahasiswa/AMP yang berpotensi memperkuat amplifikasi narasi HAM, penolakan kebijakan pembangunan, dan solidaritas lintas kota dalam isu Papua).

GAL:
Konten Cipta/kontra-opini:
• Isu kebijakan kesehatan (RPMK kemasan rokok dan dampak industri).
• Isu Papua (PSN, pembangunan, dan hak masyarakat adat).
• Transparansi hukum militer dan keadilan dalam kasus AY.
Bentuk: meme, video pendek, dan narasi opini lintas platform.

MEDMON:
• Presiden (±39,1% positif)
a. Positif: penegasan integritas MBG dan sikap antikorupsi.
b. Negatif: isu tata kelola program dan persepsi ketidakkonsistenan implementasi.
• Panglima TNI (±61,5% positif)
Dominasi sentimen positif dari narasi diplomasi pertahanan dan penguatan kerja sama internasional. Negatif relatif rendah, terkait dinamika kelembagaan internal.
• MBG (±40,5% positif)
a. Positif: reformasi kelembagaan dan penguatan pengawasan.
b. Negatif: distribusi, dugaan penyimpangan, dan kesiapan operasional.
• Andrie Yunus (±46,7% positif)
Sentimen campuran dengan sorotan pada persepsi keadilan proses hukum.
• Indonesia Gelap (±39% positif)
Didominasi narasi kritik terhadap kebijakan MBG dan tata kelola program strategis.

GEOINT:
Terdeteksi 12 titik aktivitas aktif di wilayah Papua (Pegunungan Tengah, Intan Jaya, Mimika, Sorong, Yapen, Pegunungan Bintang, dan sekitarnya). Pola sebaran menunjukkan konsentrasi pada zona rawan operasional dengan karakter mobilitas lokal dan jaringan simpul kecil.

PIKET:
• Satgas Sandi melaporkan Waspadai Kejahatan SIM Swap yang Bisa Menguras Rekening.
• Satgas Medis melaporkan Pelemahan Rupiah Dorong Kenaikan Harga Obat di Surabaya.
• Satgas Tek melaporkan pemantauan pergerakan kapal asing yang memasuki wilayah perairan Indonesia berdasarkan Automatic Identification System (AIS) serta pola pelayaran kapal berbasis aplikasi SeaVis.

REKOMENDASI:
• Koordinasi kementerian/lembaga terkait untuk memitigasi eskalasi Ribuan Pekerja Rokok Tembakau Tolak Rancangan Aturan Kemasan Kemenkes RI, melalui sinkronisasi narasi resmi dan respons cepat terhadap potensi keresahan publik.
• Intensifkan pengawasan digital-fisik terhadap Wilson Lalengke, Forum Konservasi Leuser (FKL), dan Rudi Kabak untuk mendeteksi dini rencana aksi dan mengamankan agenda strategis nasional.
• Akselerasi publikasi capaian dan komunikasi strategis terkait MBG, Presiden, Andrie Yunus untuk menekan narasi negatif dan memulihkan kepercayaan publik.
• Koordinasi Kodam wilayah Papua untuk memantau 12 titik OPM aktif dan mencegah konvergensi aktor bersenjata dengan aktivis struktural di zona pertambangan.
• Tingkatkan keamanan siber infrastruktur komunikasi pemerintah guna mengantisipasi teknik phishing dan eksploitasi aplikasi komunikasi terenkripsi.
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
        judul_clean = _clean_raw_text(it.get("judul") or "")
        isi_clean = _first_sentences(_clean_raw_text(it.get("isi") or ""), 220)
        lines.append(f"- [{it.get('satgas','').upper()}] {judul_clean} | Ringkasan: {isi_clean}")

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
    # Final pass: cleanup double dots & whitespace introduced by enforcement
    import re
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
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
            sp = it.get("sentiment_positif", 0)
            subj_data[subj.lower()] = {
                "subj": subj,
                "sp": sp,
                "sn": it.get("sentiment_negatif", 0),
                "snt": it.get("sentiment_netral", 0),
                "analisa": _clean_raw_text(analisa)[:400],
            }

        # Build dalam format baru: '• Subj (±X% positif)' + 1-2 baris analisa
        rebuilt_lines = []
        for d in subj_data.values():
            rebuilt_lines.append(f"• {d['subj']} (±{d['sp']}% positif)")
            rebuilt_lines.append(d['analisa'])

        body_has_all = all(d["subj"].lower() in body.lower() for d in subj_data.values())
        body_has_analisa = all(
            re.search(rf"{re.escape(d['subj'])}.*?\n.{{30,}}", body, re.IGNORECASE | re.DOTALL)
            for d in subj_data.values()
        )

        if not (body_has_all and body_has_analisa) and rebuilt_lines:
            text = _replace_section_body(text, "MEDMON", "\n".join(rebuilt_lines))

    # ----- 2) PIKET: pastikan SEMUA satgas tercantum dengan isi spesifik -----
    piket_items = data.get("piket", [])
    if piket_items:
        has, body = has_section("PIKET")
        # Cek apakah ada placeholder "..." di body atau raw dump (panjang > 500 char per line)
        has_placeholder = bool(re.search(r"Satgas\s+\w+\s*\.{2,}", body, re.IGNORECASE))
        # Detect raw dump: body terlalu panjang & ada penanda struktural raw
        has_raw_dump = (
            len(body) > 600 and (
                "FAKTA FAKTA" in body.upper()
                or re.search(r"\bI\.\s+FAKTA", body, re.IGNORECASE)
                or "TIM BIOKIM" in body.upper()
                or "SUBSATGAS" in body.upper()
            )
        )
        # Group by satgas dengan isi YANG SUDAH DICLEAN
        by_satgas: dict[str, list[str]] = {}
        for it in piket_items:
            sg = (it.get("satgas") or "").upper().strip()
            if sg:
                judul = _clean_raw_text(it.get("judul") or "")
                isi = _clean_raw_text(it.get("isi") or "")
                # Ringkas: ambil 1-2 kalimat pertama dari isi (atau judul kalau isi pendek)
                short_isi = _first_sentences(isi, max_chars=200) if isi else judul
                snippet = short_isi if short_isi else judul
                if snippet:
                    by_satgas.setdefault(sg, []).append(snippet[:250])
        missing_satgas = [
            sg for sg in by_satgas
            if not re.search(rf"\bsatgas\s+{re.escape(sg)}\b", body, re.IGNORECASE)
            and not re.search(rf"\b{re.escape(sg)}\b", body, re.IGNORECASE)
        ]
        if missing_satgas or has_placeholder or has_raw_dump:
            # Replace seluruh isi PIKET dengan versi bullet ringkas dari data
            chunks = []
            satgas_order = ["SANDI", "MEDIS", "TEK"]  # Konsisten dengan template
            ordered_keys = [k for k in satgas_order if k in by_satgas] + \
                          [k for k in by_satgas.keys() if k not in satgas_order]
            for sg in ordered_keys:
                items = by_satgas[sg]
                items_text = "; ".join(items[:2])
                chunks.append(f"• Satgas {sg.title()} melaporkan {items_text}.")
            full_piket_body = "\n".join(chunks)
            text = _replace_section_body(text, "PIKET", full_piket_body)

    # ----- 4) LID: pastikan ada konten ringkas -----
    lid_items = data.get("lid", [])
    if lid_items:
        has, body = has_section("LID")
        if not has or len(body.strip()) < 40:
            # Generate fallback dari data: ambil judul + analisa berita prioritas
            top = lid_items[0]
            judul = _clean_raw_text(top.get("judul") or "")
            fakta = _clean_raw_text(top.get("fakta") or "")
            analisa = _clean_raw_text(top.get("analisa") or "")
            primary = analisa or fakta
            if judul:
                body_text = f"{judul}{' — ' + _first_sentences(primary, 220) if primary else '.'}"
            else:
                body_text = _first_sentences(primary, 260) or "Berita trending termonitor."
            if len(lid_items) > 1:
                others = ", ".join((_clean_raw_text(i.get("judul") or "") or "")[:60] for i in lid_items[1:4])
                others = others.strip(", ")
                if others:
                    body_text += f" Selain itu termonitor: {others}."
            if has:
                text = _replace_section_body(text, "LID", body_text)
            else:
                text = _insert_section_before(text, "LID", body_text, ["KONTRA", "GAL", "MEDMON", "GEOINT", "PIKET", "REKOMENDASI"])

    # ----- 5) KONTRA: pastikan ada konten ringkas dengan nama TO -----
    kontra_items = data.get("kontra", [])
    if kontra_items:
        has, body = has_section("KONTRA")
        all_named = all(
            (k.get("nama_to") or "").strip().lower() in body.lower()
            for k in kontra_items if k.get("nama_to")
        )
        if not has or len(body.strip()) < 40 or not all_named:
            chunks = []
            for k in kontra_items[:5]:
                nama = (k.get("nama_to") or "").strip()
                sumber = (k.get("sumber") or "").strip()
                tipe = (k.get("tipe") or "").strip()
                ket = _clean_raw_text(k.get("keterangan") or "")
                desc = _first_sentences(ket, 120) if ket else ""
                chunk = nama
                if tipe or sumber:
                    chunk += f" ({tipe}{', ' + sumber if sumber else ''})"
                if desc:
                    chunk += f": {desc}"
                chunks.append(chunk)
            body_text = (
                f"Teridentifikasi {len(kontra_items)} TO prioritas: "
                + "; ".join(chunks) + "."
            )
            if has:
                text = _replace_section_body(text, "KONTRA", body_text)
            else:
                text = _insert_section_before(text, "KONTRA", body_text, ["GAL", "MEDMON", "GEOINT", "PIKET", "REKOMENDASI"])

    # ----- 6) GAL: pastikan ada konten ringkas -----
    gal_items = data.get("gal", [])
    if gal_items:
        has, body = has_section("GAL")
        if not has or len(body.strip()) < 40:
            # Group by kategori
            by_cat: dict[str, list[str]] = {}
            for g in gal_items:
                cat = (g.get("kategori") or "lain-lain").lower()
                judul = _clean_raw_text(g.get("judul") or "")
                if judul:
                    by_cat.setdefault(cat, []).append(judul[:60])
            cat_parts = []
            for cat, titles in by_cat.items():
                cat_parts.append(f"{cat} ({', '.join(titles[:3])})")
            body_text = (
                f"Konten galang difokuskan pada {len(by_cat)} kategori: "
                + "; ".join(cat_parts) + "."
            )
            if has:
                text = _replace_section_body(text, "GAL", body_text)
            else:
                text = _insert_section_before(text, "GAL", body_text, ["MEDMON", "GEOINT", "PIKET", "REKOMENDASI"])

    # ----- 3) REKOMENDASI: pastikan minimal 4 bullet -----
    has, body = has_section("REKOMENDASI")
    # Count bullets (any of •, -, *, numbered)
    bullet_lines = [
        ln for ln in body.split("\n")
        if re.match(r"^\s*[•\-\*]\s+\S", ln) or re.match(r"^\s*\d+[\.\)]\s+\S", ln)
    ]
    if not has or len(bullet_lines) < 3:
        fallback = _fallback_rekomendasi(data)
        if has and not bullet_lines:
            text = _replace_section_body(text, "REKOMENDASI", fallback)
        elif has:
            text = _append_to_section(text, "REKOMENDASI", "\n" + fallback)
        else:
            text = text.rstrip() + "\n\nREKOMENDASI:\n" + fallback

    return text


def _clean_raw_text(s: str) -> str:
    """Strip HTML tags, structural markers (I. FAKTA, 1. TIM, a., dst), excessive whitespace."""
    if not s:
        return ""
    import re
    # Strip HTML tags
    s = re.sub(r"<[^>]+>", " ", s)
    # Decode common entities
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    # Strip header laporan lengkap di awal (e.g. "LAPORAN HARIAN OPERASI TEKNIK SUBSATGAS ... :")
    s = re.sub(r"LAPORAN\s+(?:HARIAN\s+)?(?:KEGIATAN\s+)?(?:OPERASI\s+)?[A-Z]+\s+SUBSATGAS[^:]*:\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"LAPORAN\s+(?:KEGIATAN|HARIAN)?[^:]*?TANGGAL\s+\d+\s+\w+\s+\d+\s*:?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"Perkembangan\s+Situasi\s+Menonjol[^:]*:\s*", "", s, flags=re.IGNORECASE)
    # Strip "SUBSATGAS XXX" mentions
    s = re.sub(r"\bSUBSATGAS\s+[A-Z]+\b", "", s, flags=re.IGNORECASE)
    # Strip structural roman headings like "I. FAKTA FAKTA", "II. ANALISA"
    s = re.sub(r"\b[IVX]+\.\s+(FAKTA|ANALISA|REKOMENDASI|TINDAKAN|PENDAHULUAN)[\s—–:-]*(FAKTA|ANALISA|REKOMENDASI|TINDAKAN)?\.?\s*", " ", s, flags=re.IGNORECASE)
    # Strip "1. TIM XXX." headers
    s = re.sub(r"\b\d+\.\s+TIM\s+[A-Z]+\.?\s*", " ", s, flags=re.IGNORECASE)
    # Strip "a. ", "b. " inline list markers
    s = re.sub(r"(?m)^\s*[a-z]\.\s+", "", s)
    s = re.sub(r"(?<=\s)[a-z]\.\s+", "", s)
    # Strip standalone day/date markers (e.g., "SELASA, 04 JUNI 2026:")
    s = re.sub(r"\b(SENIN|SELASA|RABU|KAMIS|JUMAT|SABTU|MINGGU),?\s*\d+\s+\w+\s+\d+\s*:?\s*", "", s, flags=re.IGNORECASE)
    # Strip double titik dan whitespace
    s = re.sub(r"\.+", ".", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _first_sentences(s: str, max_chars: int = 200) -> str:
    """Ambil 1-2 kalimat pertama dari teks, max `max_chars` karakter."""
    if not s:
        return ""
    import re
    sentences = re.split(r"(?<=[\.\!\?])\s+", s.strip())
    out = ""
    for sent in sentences:
        if not out:
            out = sent
        else:
            candidate = out + " " + sent
            if len(candidate) > max_chars:
                break
            out = candidate
        if len(out) >= max_chars:
            break
    return out[:max_chars].rstrip(",;: ") + ("." if not out.endswith((".", "!", "?")) else "")


def _insert_section_before(text: str, label: str, body: str, before) -> str:
    """Insert a new section with `label` and `body` right before section `before`.
    `before` can be a string or a list of fallback anchors (cari yang ada lebih dulu)."""
    import re
    anchors = [before] if isinstance(before, str) else list(before)
    for anchor in anchors:
        m = re.search(rf"(?m)^{re.escape(anchor)}:\s*$", text)
        if m:
            block = f"\n{label}:\n{body.strip()}\n\n"
            return text[:m.start()] + block + text[m.start():]
    # Fallback: append to end
    return text.rstrip() + f"\n\n{label}:\n{body.strip()}\n\n"


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

    # Return sebagai bullet list dengan bullet character
    return "\n".join(f"• {p}" for p in paragraphs)


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
            new_body = "\n" + "\n".join(f"• {b}" for b in bullets) + "\n"
        else:
            new_body = "\n"
        text = before + new_body + tail

    # 8) Cleanup excessive blank lines, trailing whitespace & double dots
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    # Fix double/triple dots that appear when joining clean text
    text = re.sub(r"\.{2,}", ".", text)
    # Fix ".." or " .." after sentences
    text = re.sub(r"\s+\.", ".", text)

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
