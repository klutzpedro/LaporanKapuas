"""BAIS Summary Geospasika - backend integration tests."""
import os
import pytest
import requests
from datetime import datetime, timezone, timedelta, time as dtime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://geospasial-summary.preview.emergentagent.com").rstrip("/")
WIB = timezone(timedelta(hours=7))

CREDS = {
    "admin":     ("admin@bais.tni.mil.id",  "Bais2026!"),
    "piket":     ("piket@bais.tni.mil.id",  "Piket2026!"),
    "tim_lid":   ("lid@bais.tni.mil.id",    "Lid2026!"),
    "tim_kontra":("kontra@bais.tni.mil.id", "Kontra2026!"),
    "tim_gal":   ("gal@bais.tni.mil.id",    "Gal2026!"),
    "tim_medmon":("medmon@bais.tni.mil.id", "Medmon2026!"),
    "tim_geoint":("geoint@bais.tni.mil.id", "Geoint2026!"),
}

YESTERDAY = (datetime.now(WIB).date() - timedelta(days=1)).isoformat()


# ---------- Helpers / fixtures ----------
def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    body = r.json()
    assert "token" in body and body["token"]
    return body


@pytest.fixture(scope="session")
def tokens():
    out = {}
    for role, (email, pwd) in CREDS.items():
        out[role] = _login(email, pwd)["token"]
    return out


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- AUTH ----------
class TestAuth:
    def test_login_admin_returns_token_and_user(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": CREDS["admin"][0], "password": CREDS["admin"][1]}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == CREDS["admin"][0]
        assert d["role"] == "admin"
        assert isinstance(d["token"], str) and len(d["token"]) > 20

    def test_login_invalid_password(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": CREDS["admin"][0], "password": "wrong"}, timeout=20)
        assert r.status_code == 401

    def test_me_with_bearer_token(self, tokens):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=H(tokens["admin"]), timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == CREDS["admin"][0]
        assert d["role"] == "admin"
        assert "id" in d

    def test_me_unauthenticated(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=20)
        assert r.status_code == 401

    def test_register_non_admin_forbidden(self, tokens):
        r = requests.post(f"{BASE_URL}/api/auth/register",
                          headers=H(tokens["piket"]),
                          json={"email": "TEST_x@bais.tni.mil.id", "password": "Pass123!",
                                "name": "x", "role": "tim_lid"}, timeout=20)
        assert r.status_code == 403

    def test_users_list_admin_only(self, tokens):
        r = requests.get(f"{BASE_URL}/api/auth/users", headers=H(tokens["admin"]), timeout=20)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list)
        emails = [u["email"] for u in users]
        for _, (em, _p) in CREDS.items():
            assert em in emails

    def test_users_list_non_admin_forbidden(self, tokens):
        r = requests.get(f"{BASE_URL}/api/auth/users", headers=H(tokens["tim_lid"]), timeout=20)
        assert r.status_code == 403


# ---------- LID ----------
class TestLid:
    created_ids: list[str] = []

    @pytest.mark.parametrize("cog", ["aceh", "jakarta", "papua", "internasional"])
    def test_create_lid_all_cogs(self, tokens, cog):
        payload = {
            "cog": cog,
            "judul": f"TEST_LID {cog}",
            "link": "https://example.com",
            "fakta": "Fakta uji.",
            "analisa": "Analisa uji.",
            "tindakan": "Tindakan uji.",
            "rekomendasi": "Rekomendasi uji.",
            "sentiment_label": "neutral",
        }
        r = requests.post(f"{BASE_URL}/api/lid", headers=H(tokens["tim_lid"]), json=payload, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["cog"] == cog
        assert d["judul"] == payload["judul"]
        assert "id" in d
        assert d["created_by_role"] == "tim_lid"
        TestLid.created_ids.append(d["id"])

    def test_list_lid_with_filter(self, tokens):
        today = datetime.now(WIB).date().isoformat()
        r = requests.get(f"{BASE_URL}/api/lid?report_date={today}",
                         headers=H(tokens["admin"]), timeout=20)
        assert r.status_code == 200
        items = r.json()
        ids = [i["id"] for i in items]
        for cid in TestLid.created_ids:
            assert cid in ids

    def test_delete_lid(self, tokens):
        if not TestLid.created_ids:
            pytest.skip("no created ids")
        rid = TestLid.created_ids.pop()
        r = requests.delete(f"{BASE_URL}/api/lid/{rid}", headers=H(tokens["admin"]), timeout=20)
        assert r.status_code == 200
        # verify gone
        today = datetime.now(WIB).date().isoformat()
        r2 = requests.get(f"{BASE_URL}/api/lid?report_date={today}", headers=H(tokens["admin"]), timeout=20)
        assert rid not in [i["id"] for i in r2.json()]


# ---------- KONTRA ----------
class TestKontra:
    def test_create_to_satgas(self, tokens):
        r = requests.post(f"{BASE_URL}/api/kontra", headers=H(tokens["tim_kontra"]),
                          json={"sumber": "to_satgas", "tipe": "perorangan",
                                "nama_to": "TEST_TO1", "data_diri": "ABC",
                                "medsos": ["https://t.me/x"], "keterangan": "ket"}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["sumber"] == "to_satgas"

    def test_create_to_internal(self, tokens):
        r = requests.post(f"{BASE_URL}/api/kontra", headers=H(tokens["tim_kontra"]),
                          json={"sumber": "to_internal", "tipe": "group",
                                "nama_to": "TEST_TO2", "data_diri": "Group XYZ",
                                "medsos": [], "keterangan": "internal"}, timeout=20)
        assert r.status_code == 200
        assert r.json()["sumber"] == "to_internal"

    def test_role_lid_cannot_post_kontra(self, tokens):
        r = requests.post(f"{BASE_URL}/api/kontra", headers=H(tokens["tim_lid"]),
                          json={"sumber": "to_internal", "tipe": "group",
                                "nama_to": "X", "data_diri": "X"}, timeout=20)
        assert r.status_code == 403


# ---------- GAL ----------
class TestGal:
    @pytest.mark.parametrize("kategori", ["narasi", "video", "medsos"])
    def test_create_gal(self, tokens, kategori):
        r = requests.post(f"{BASE_URL}/api/gal", headers=H(tokens["tim_gal"]),
                          json={"kategori": kategori, "judul": f"TEST_GAL {kategori}",
                                "links": ["https://example.com"], "keterangan": "ket"}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["kategori"] == kategori


# ---------- MEDMON ----------
class TestMedmon:
    def test_create_medmon(self, tokens):
        r = requests.post(f"{BASE_URL}/api/medmon", headers=H(tokens["tim_medmon"]),
                          json={
                              "subjek": "Presiden",
                              "berita": [
                                  {"judul": "T1+", "link": "https://a.com", "sentiment": "positif"},
                                  {"judul": "T2-", "link": "https://b.com", "sentiment": "negatif"},
                                  {"judul": "T3+", "link": "https://c.com", "sentiment": "positif"},
                              ],
                              "analisa": "a", "rekomendasi": "r"
                          }, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["subjek"] == "Presiden"
        assert len(d["berita"]) == 3


# ---------- GEOINT ----------
class TestGeoint:
    def test_create_geoint(self, tokens):
        r = requests.post(f"{BASE_URL}/api/geoint", headers=H(tokens["tim_geoint"]),
                          json={"wilayah": "Papua Pegunungan", "nama_orang": "TEST_OPM",
                                "no_hp": "0812", "lat": -3.5, "lon": 138.5,
                                "status": "aktif", "keterangan": "ket"}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["lat"] == -3.5 and d["lon"] == 138.5
        assert d["status"] == "aktif"


# ---------- PIKET ----------
class TestPiket:
    @pytest.mark.parametrize("satgas", ["tek", "sandi", "medis"])
    def test_create_piket(self, tokens, satgas):
        r = requests.post(f"{BASE_URL}/api/piket", headers=H(tokens["piket"]),
                          json={"satgas": satgas, "judul": f"TEST_PIKET {satgas}",
                                "isi": "Isi laporan"}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["satgas"] == satgas


# ---------- DAILY ----------
class TestDaily:
    def test_daily_info(self, tokens):
        r = requests.get(f"{BASE_URL}/api/daily/info", headers=H(tokens["admin"]), timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ["now_wib", "report_date", "input_date", "before_noon"]:
            assert k in d
        assert isinstance(d["before_noon"], bool)

    def test_daily_aggregation(self, tokens):
        today = datetime.now(WIB).date().isoformat()
        r = requests.get(f"{BASE_URL}/api/daily?report_date={today}",
                         headers=H(tokens["admin"]), timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ["lid", "kontra", "gal", "medmon", "geoint", "piket"]:
            assert k in d
            assert isinstance(d[k], list)


# ---------- AI SUMMARY ----------
class TestAiSummary:
    def test_ai_summary_generate(self, tokens):
        today = datetime.now(WIB).date().isoformat()
        r = requests.post(f"{BASE_URL}/api/summary/ai", headers=H(tokens["admin"]),
                          json={"report_date": today}, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["report_date"] == today
        assert isinstance(d["summary"], str) and len(d["summary"]) > 30
        # not an obvious error wrapper
        assert "[AI SUMMARY ERROR]" not in d["summary"]
        assert "[AI SUMMARY UNAVAILABLE]" not in d["summary"]

    def test_ai_summary_cached_get(self, tokens):
        today = datetime.now(WIB).date().isoformat()
        r = requests.get(f"{BASE_URL}/api/summary/ai?report_date={today}",
                         headers=H(tokens["admin"]), timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["report_date"] == today
        assert d["summary"] is not None


# ---------- PDF ----------
class TestPdf:
    def test_pdf_yesterday_admin(self, tokens):
        r = requests.get(f"{BASE_URL}/api/pdf?report_date={YESTERDAY}",
                         headers={"Authorization": f"Bearer {tokens['admin']}"}, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        # rough size sanity
        assert len(r.content) > 1500

    def test_pdf_today_before_noon_rule(self, tokens):
        """If currently before 12 WIB, generating today's PDF should return 400."""
        now = datetime.now(WIB)
        today = now.date().isoformat()
        r = requests.get(f"{BASE_URL}/api/pdf?report_date={today}",
                         headers={"Authorization": f"Bearer {tokens['admin']}"}, timeout=60)
        if now.time() < dtime(12, 0):
            assert r.status_code == 400
            assert "12:00 WIB" in r.text or "12 WIB" in r.text
        else:
            # after noon -> should succeed
            assert r.status_code == 200
            assert r.content[:4] == b"%PDF"

    def test_pdf_requires_role(self, tokens):
        r = requests.get(f"{BASE_URL}/api/pdf?report_date={YESTERDAY}",
                         headers={"Authorization": f"Bearer {tokens['tim_lid']}"}, timeout=30)
        assert r.status_code == 403
