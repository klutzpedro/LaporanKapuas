"""Iteration 2 tests: PDF persistence + reports history/download/delete + AI summary system prompt."""
import os
import re
import io
import pytest
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
WIB = timezone(timedelta(hours=7))

CREDS = {
    "admin":     ("admin@bais.tni.mil.id",  "Bais2026!"),
    "piket":     ("piket@bais.tni.mil.id",  "Piket2026!"),
    "tim_lid":   ("lid@bais.tni.mil.id",    "Lid2026!"),
}

YESTERDAY = (datetime.now(WIB).date() - timedelta(days=1)).isoformat()


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def tokens():
    return {role: _login(e, p) for role, (e, p) in CREDS.items()}


def H(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


# ---------- AI summary system prompt content check (no LLM call) ----------
class TestAiSystemPrompt:
    def test_system_prompt_mentions_all_teams(self):
        text = open("/app/backend/ai_summary.py").read()
        for team in ["LID", "KONTRA", "GAL", "MEDMON", "GEOINT", "PIKET"]:
            assert team in text, f"team {team} missing from ai_summary.py"
        # user prompt template sections
        for sect in ["MEDMON", "KONTRA", "PIKET", "REKOMENDASI"]:
            assert sect in text


# ---------- PDF generation + persistence ----------
class TestPdfPersistAndHistory:
    rid: str = ""
    original_pdf: bytes = b""

    def test_pdf_yesterday_persists_record(self, tokens):
        r = requests.get(f"{BASE_URL}/api/pdf?report_date={YESTERDAY}",
                         headers=H(tokens["admin"]), timeout=90)
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 1000
        TestPdfPersistAndHistory.original_pdf = r.content

    def test_pdf_today_before_noon_400(self, tokens):
        now = datetime.now(WIB)
        today = now.date().isoformat()
        r = requests.get(f"{BASE_URL}/api/pdf?report_date={today}",
                         headers=H(tokens["admin"]), timeout=60)
        from datetime import time as dtime
        if now.time() < dtime(12, 0):
            assert r.status_code == 400
        else:
            assert r.status_code == 200

    def test_pdf_forbidden_for_tim_lid(self, tokens):
        r = requests.get(f"{BASE_URL}/api/pdf?report_date={YESTERDAY}",
                         headers=H(tokens["tim_lid"]), timeout=30)
        assert r.status_code == 403

    def test_reports_history_lists_generated(self, tokens):
        r = requests.get(f"{BASE_URL}/api/reports/history",
                         headers=H(tokens["admin"]), timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) > 0
        # pick first record for the yesterday date
        yest_records = [it for it in items if it.get("report_date") == YESTERDAY]
        assert yest_records, f"no record for {YESTERDAY} in history"
        rec = yest_records[0]
        for k in ["id", "report_date", "generated_at", "generated_by_name",
                  "filename", "size_bytes", "counts", "has_ai_summary"]:
            assert k in rec, f"missing field {k} in history record: {rec.keys()}"
        # security/perf: must NOT expose pdf_base64 in list
        assert "pdf_base64" not in rec, "pdf_base64 leaked in /reports/history list!"
        # counts structure
        for team in ["lid", "kontra", "gal", "medmon", "geoint", "piket"]:
            assert team in rec["counts"], f"counts missing {team}"
        TestPdfPersistAndHistory.rid = rec["id"]

    def test_reports_history_date_filter(self, tokens):
        start = (datetime.now(WIB).date() - timedelta(days=8)).isoformat()
        end = (datetime.now(WIB).date() + timedelta(days=0)).isoformat()
        r = requests.get(
            f"{BASE_URL}/api/reports/history?start_date={start}&end_date={end}",
            headers=H(tokens["admin"]), timeout=20,
        )
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        for it in items:
            assert start <= it["report_date"] <= end

        # tighter window that should EXCLUDE yesterday
        far_past = "2000-01-01"
        far_past_end = "2000-01-02"
        r2 = requests.get(
            f"{BASE_URL}/api/reports/history?start_date={far_past}&end_date={far_past_end}",
            headers=H(tokens["admin"]), timeout=20,
        )
        assert r2.status_code == 200
        assert r2.json() == []

    def test_reports_download_returns_pdf(self, tokens):
        assert TestPdfPersistAndHistory.rid, "no rid captured"
        r = requests.get(f"{BASE_URL}/api/reports/{TestPdfPersistAndHistory.rid}/download",
                         headers=H(tokens["admin"]), timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"
        # Should match the originally generated PDF bytes
        if TestPdfPersistAndHistory.original_pdf:
            assert r.content == TestPdfPersistAndHistory.original_pdf

    def test_pdf_page_count_at_most_2(self, tokens):
        """PDF should be max ~2 pages with AI summary on page 1."""
        pdf = TestPdfPersistAndHistory.original_pdf
        assert pdf, "no original pdf"
        try:
            from pypdf import PdfReader
        except Exception:
            pytest.skip("pypdf not installed")
        reader = PdfReader(io.BytesIO(pdf))
        n = len(reader.pages)
        assert n <= 2, f"PDF has {n} pages, expected <=2"

    def test_reports_delete_non_admin_forbidden(self, tokens):
        assert TestPdfPersistAndHistory.rid
        r = requests.delete(f"{BASE_URL}/api/reports/{TestPdfPersistAndHistory.rid}",
                            headers=H(tokens["tim_lid"]), timeout=20)
        assert r.status_code == 403

    def test_reports_delete_admin_succeeds(self, tokens):
        assert TestPdfPersistAndHistory.rid
        r = requests.delete(f"{BASE_URL}/api/reports/{TestPdfPersistAndHistory.rid}",
                            headers=H(tokens["admin"]), timeout=20)
        assert r.status_code == 200
        # subsequent download should 404
        r2 = requests.get(f"{BASE_URL}/api/reports/{TestPdfPersistAndHistory.rid}/download",
                          headers=H(tokens["admin"]), timeout=20)
        assert r2.status_code == 404
