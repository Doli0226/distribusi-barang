"""Regression tests for iteration 3 fixes: number generation, 404/400 handling, status validation."""
import os
import uuid
import pytest
import requests
from dotenv import dotenv_values

env = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or env.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE}/api"
ADMIN = {"email": "admin@logistipro.id", "password": "admin123"}
USER = {"email": "user@logistipro.id", "password": "user123"}


def client(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def admin_c():
    return client(ADMIN)


@pytest.fixture(scope="module")
def user_c():
    return client(USER)


def make_request(user_c, admin_c, qty=2):
    wh = admin_c.get(f"{API}/warehouses", timeout=30).json()["items"][0]["id"]
    rid = admin_c.get(f"{API}/recipients", timeout=30).json()["items"][0]["id"]
    prods = [p for p in admin_c.get(f"{API}/products", timeout=30).json()["items"] if p["stock"] > 20]
    pid = prods[0]["id"]
    r = user_c.post(f"{API}/requests", json={"warehouse_id": wh, "recipient_id": rid,
                                             "destination": f"TEST_REG_{uuid.uuid4().hex[:6]}",
                                             "items": [{"product_id": pid, "quantity": qty}]}, timeout=30)
    assert r.status_code == 201, r.text[:300]
    body = r.json()
    assert body["number"].startswith("REQ-"), body
    rq = body["id"]
    a = admin_c.post(f"{API}/requests/{rq}/action", json={"action": "approve"}, timeout=30)
    assert a.status_code == 200, a.text[:300]
    return rq


# --- distribution number regression ---
class TestDistributionNumber:
    def test_create_distribution_with_eta(self, admin_c, user_c):
        """BUG: passing estimated_arrival string -> 500 AttributeError (str.isoformat) in distribution_json."""
        rq = make_request(user_c, admin_c)
        vid = admin_c.get(f"{API}/vehicles", timeout=30).json()["items"][0]["id"]
        d = admin_c.post(f"{API}/distributions", json={"request_id": rq, "vehicle_id": vid,
                                                       "delivery_number": "TEST-SJ-REG",
                                                       "estimated_arrival": "2026-08-01"}, timeout=30)
        assert d.status_code == 201, d.text[:300]
        body = d.json()
        assert body["number"].startswith("DST-"), body
        get = admin_c.get(f"{API}/distributions/{body['id']}", timeout=30)
        assert get.status_code == 200
        assert get.json()["number"] == body["number"]

    def test_create_distribution_without_eta(self, admin_c, user_c):
        rq = make_request(user_c, admin_c)
        d = admin_c.post(f"{API}/distributions", json={"request_id": rq}, timeout=30)
        assert d.status_code == 201, d.text[:300]
        num = d.json()["number"]
        # second distribution must get a unique new number
        rq2 = make_request(user_c, admin_c)
        d2 = admin_c.post(f"{API}/distributions", json={"request_id": rq2}, timeout=30)
        assert d2.status_code == 201, d2.text[:300]
        assert d2.json()["number"] != num


# --- status validation ---
class TestStatusValidation:
    def test_invalid_and_backward_status(self, admin_c, user_c):
        rq = make_request(user_c, admin_c)
        d = admin_c.post(f"{API}/distributions", json={"request_id": rq}, timeout=30)
        assert d.status_code == 201, d.text[:300]
        did = d.json()["id"]
        bad = admin_c.post(f"{API}/distributions/{did}/status", json={"status": "bogus"}, timeout=30)
        assert bad.status_code == 400, bad.text[:200]
        for st in ["in_transit", "arrived", "completed"]:
            r = admin_c.post(f"{API}/distributions/{did}/status", json={"status": st}, timeout=30)
            assert r.status_code == 200, r.text[:300]
            assert r.json()["status"] == st
        back = admin_c.post(f"{API}/distributions/{did}/status", json={"status": "prepared"}, timeout=30)
        assert back.status_code == 400, back.text[:200]
        final = admin_c.get(f"{API}/distributions/{did}", timeout=30).json()
        assert final["status"] == "completed"
        req = admin_c.get(f"{API}/requests/{rq}", timeout=30).json()
        assert req["status"] == "completed", req


# --- 404 handling ---
class TestNotFound:
    @pytest.mark.parametrize("path", ["products", "warehouses", "requests", "distributions"])
    def test_detail_404(self, admin_c, path):
        r = admin_c.get(f"{API}/{path}/999999", timeout=30)
        assert r.status_code == 404, f"{path}: {r.status_code} {r.text[:200]}"
        assert r.json().get("detail") == "Data tidak ditemukan", r.text[:200]


# --- 400 on incomplete payloads ---
class TestDateSerialization:
    """BUG regression: date fields sent as strings crash the JSON serializer after create."""

    def test_request_with_needed_date(self, user_c, admin_c):
        wh = admin_c.get(f"{API}/warehouses", timeout=30).json()["items"][0]["id"]
        rid = admin_c.get(f"{API}/recipients", timeout=30).json()["items"][0]["id"]
        pid = [p for p in admin_c.get(f"{API}/products", timeout=30).json()["items"] if p["stock"] > 20][0]["id"]
        r = user_c.post(f"{API}/requests", json={"warehouse_id": wh, "recipient_id": rid,
                                                 "destination": "TEST_REG_DATE", "needed_date": "2026-08-10",
                                                 "items": [{"product_id": pid, "quantity": 1}]}, timeout=30)
        assert r.status_code == 201, r.text[:200]


class TestBadPayloads:
    def test_post_product_missing_fields(self, admin_c):
        r = admin_c.post(f"{API}/products", json={}, timeout=30)
        assert r.status_code == 400, r.text[:200]

    def test_post_request_missing_fields(self, user_c):
        r = user_c.post(f"{API}/requests", json={}, timeout=30)
        assert r.status_code == 400, r.text[:200]

    def test_post_stock_transaction_missing_fields(self, admin_c):
        r = admin_c.post(f"{API}/stocks/transaction", json={}, timeout=30)
        assert r.status_code == 400, r.text[:200]

    def test_post_distribution_missing_request(self, admin_c):
        r = admin_c.post(f"{API}/distributions", json={}, timeout=30)
        assert r.status_code in (400, 404), r.text[:200]


# --- admin notification fan-out ---
class TestAdminNotify:
    def test_staff_admin_receives_request_notification(self, admin_c, user_c):
        before = admin_c.get(f"{API}/notifications", timeout=30).json()
        cnt_before = len(before["items"])
        make_request(user_c, admin_c)
        after = admin_c.get(f"{API}/notifications", timeout=30).json()
        assert len(after["items"]) > cnt_before, "admin got no notification for new request"


# --- exports ---
class TestExports:
    @pytest.mark.parametrize("res", ["stock", "requests", "distributions", "stock_transactions"])
    @pytest.mark.parametrize("fmt,ctype", [("csv", "csv"), ("excel", "spreadsheet"), ("pdf", "pdf")])
    def test_export(self, admin_c, res, fmt, ctype):
        r = admin_c.get(f"{API}/reports/{res}/export/{fmt}", timeout=60)
        assert r.status_code == 200, f"{res}/{fmt}: {r.status_code} {r.text[:200]}"
        assert ctype in r.headers.get("Content-Type", "").lower(), r.headers.get("Content-Type")
        assert len(r.content) > 100
