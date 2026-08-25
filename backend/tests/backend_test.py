"""Backend API tests for LogistiPro (Django + SQLite) distribution system."""
import os
import time
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@logistipro.id", "password": "admin123"}
USER = {"email": "user@logistipro.id", "password": "user123"}


def new_session(creds=None):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    if creds:
        r = s.post(f"{API}/auth/login", json=creds, timeout=30)
        if r.status_code != 200:
            pytest.fail(f"Login failed for {creds['email']}: {r.status_code} {r.text[:300]}")
    return s


@pytest.fixture(scope="class")
def admin_c():
    return new_session(ADMIN)


@pytest.fixture(scope="class")
def user_c():
    return new_session(USER)


@pytest.fixture(scope="class")
def anon_c():
    return new_session()


# ---------- AUTH ----------
class TestAuth:
    def test_root(self, anon_c):
        r = anon_c.get(f"{API}/", timeout=30)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_login_admin(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json=ADMIN, timeout=30)
        assert r.status_code == 200, r.text[:300]
        u = r.json()["user"]
        assert u["role"] == "admin"
        assert u["email"] == ADMIN["email"]

    def test_login_user(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json=USER, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["user"]["role"] == "user"

    def test_login_wrong_password(self, anon_c):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": "bad"}, timeout=30)
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_me_unauthenticated(self):
        r = requests.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 401

    def test_me_authenticated(self, admin_c):
        r = admin_c.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "admin"

    def test_register_new_user(self):
        s = requests.Session()
        email = f"test_{uuid.uuid4().hex[:8]}@logistipro.id"
        r = s.post(f"{API}/auth/register", json={"email": email, "password": "secret123", "full_name": "TEST Regis Baru"}, timeout=30)
        assert r.status_code == 201, r.text[:300]
        data = r.json()["user"]
        assert data["email"] == email
        assert data["role"] == "user"
        # session established after register
        me = s.get(f"{API}/auth/me", timeout=30)
        assert me.status_code == 200
        assert me.json()["user"]["email"] == email
        # duplicate
        r2 = requests.post(f"{API}/auth/register", json={"email": email, "password": "secret123"}, timeout=30)
        assert r2.status_code == 400
        # short password
        r3 = requests.post(f"{API}/auth/register", json={"email": f"x{email}", "password": "123"}, timeout=30)
        assert r3.status_code == 400

    def test_change_password_wrong_current(self, admin_c):
        r = admin_c.post(f"{API}/auth/change-password", json={"current_password": "wrong", "new_password": "abcdef1"}, timeout=30)
        assert r.status_code == 400
        assert "Password saat ini salah" in r.json().get("detail", "")

    def test_change_password_flow_on_temp_user(self):
        s = requests.Session()
        email = f"test_{uuid.uuid4().hex[:8]}@logistipro.id"
        s.post(f"{API}/auth/register", json={"email": email, "password": "secret123", "full_name": "TEST Pwd"}, timeout=30)
        r = s.post(f"{API}/auth/change-password", json={"current_password": "secret123", "new_password": "newsecret123"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        r2 = requests.post(f"{API}/auth/login", json={"email": email, "password": "newsecret123"}, timeout=30)
        assert r2.status_code == 200

    def test_reset_password_flow(self):
        email = f"test_{uuid.uuid4().hex[:8]}@logistipro.id"
        requests.post(f"{API}/auth/register", json={"email": email, "password": "secret123", "full_name": "TEST Reset"}, timeout=30)
        r = requests.post(f"{API}/auth/reset-password", json={"email": email, "new_password": "resetpass1"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert requests.post(f"{API}/auth/login", json={"email": email, "password": "resetpass1"}, timeout=30).status_code == 200
        assert requests.post(f"{API}/auth/reset-password", json={"email": "nope@x.id", "new_password": "resetpass1"}, timeout=30).status_code == 404

    def test_profile_update(self):
        s = requests.Session()
        email = f"test_{uuid.uuid4().hex[:8]}@logistipro.id"
        s.post(f"{API}/auth/register", json={"email": email, "password": "secret123", "full_name": "TEST Awal"}, timeout=30)
        r = s.post(f"{API}/auth/profile", json={"full_name": "TEST Nama Baru", "phone": "0811222333"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        u = r.json()["user"]
        assert u["full_name"] == "TEST Nama Baru"
        assert u["phone"] == "0811222333"
        me = s.get(f"{API}/auth/me", timeout=30).json()["user"]
        assert me["full_name"] == "TEST Nama Baru"


# ---------- DASHBOARD ----------
class TestDashboard:
    def test_dashboard_admin(self, admin_c):
        r = admin_c.get(f"{API}/dashboard", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for k in ["stats", "distribution_chart", "category_chart", "top_products", "recent_requests", "recent_activities"]:
            assert k in d, f"missing {k}"
        for k in ["total_products", "total_users", "active_distributions", "total_stock", "pending_requests"]:
            assert k in d["stats"], f"missing stats.{k}"
        assert d["stats"]["total_users"] > 0
        assert isinstance(d["distribution_chart"], list) and len(d["distribution_chart"]) == 6
        assert len(d["recent_activities"]) > 0

    def test_dashboard_user_scoped(self, user_c):
        r = user_c.get(f"{API}/dashboard", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["stats"]["total_users"] == 0
        assert d["recent_activities"] == []
        # all recent requests belong to the logged-in user
        me = user_c.get(f"{API}/auth/me", timeout=30).json()["user"]["username"]
        for rq in d["recent_requests"]:
            assert rq["requester"] == me

    def test_dashboard_unauthenticated(self):
        assert requests.get(f"{API}/dashboard", timeout=30).status_code == 401


# ---------- MASTER DATA CRUD ----------
class TestMasterData:
    def test_categories_crud(self, admin_c):
        name = f"TEST_Kat_{uuid.uuid4().hex[:6]}"
        r = admin_c.post(f"{API}/categories", json={"name": name, "description": "desc"}, timeout=30)
        assert r.status_code == 201, r.text[:300]
        cid = r.json()["id"]
        items = admin_c.get(f"{API}/categories", timeout=30).json()["items"]
        assert any(c["id"] == cid and c["name"] == name for c in items)
        r = admin_c.put(f"{API}/categories/{cid}", json={"name": name + "_upd"}, timeout=30)
        assert r.status_code == 200 and r.json()["name"] == name + "_upd"
        assert admin_c.delete(f"{API}/categories/{cid}", timeout=30).status_code == 200
        items = admin_c.get(f"{API}/categories", timeout=30).json()["items"]
        assert [c for c in items if c["id"] == cid][0]["active"] is False

    def test_products_crud(self, admin_c):
        cats = admin_c.get(f"{API}/categories", timeout=30).json()["items"]
        cid = cats[0]["id"]
        sku = f"TEST-{uuid.uuid4().hex[:6].upper()}"
        r = admin_c.post(f"{API}/products", json={"sku": sku, "name": "TEST Barang", "category_id": cid,
                                                  "unit": "pcs", "minimum_stock": 5}, timeout=30)
        assert r.status_code == 201, r.text[:300]
        p = r.json()
        pid = p["id"]
        assert p["sku"] == sku and p["minimum_stock"] == 5 and p["stock"] == 0
        got = admin_c.get(f"{API}/products/{pid}", timeout=30)
        assert got.status_code == 200 and got.json()["name"] == "TEST Barang"
        r = admin_c.put(f"{API}/products/{pid}", json={"name": "TEST Barang Ubah", "minimum_stock": 9}, timeout=30)
        assert r.status_code == 200
        got = admin_c.get(f"{API}/products/{pid}", timeout=30).json()
        assert got["name"] == "TEST Barang Ubah" and got["minimum_stock"] == 9
        assert admin_c.delete(f"{API}/products/{pid}", timeout=30).status_code == 200
        assert admin_c.get(f"{API}/products/{pid}", timeout=30).json()["active"] is False
        # search filter
        r = admin_c.get(f"{API}/products?q={sku}", timeout=30)
        assert r.status_code == 200 and len(r.json()["items"]) == 1

    def test_warehouses_crud(self, admin_c):
        code = f"TW{uuid.uuid4().hex[:4].upper()}"
        r = admin_c.post(f"{API}/warehouses", json={"code": code, "name": "TEST Gudang", "city": "Bandung", "capacity": 100}, timeout=30)
        assert r.status_code == 201, r.text[:300]
        wid = r.json()["id"]
        assert any(w["id"] == wid for w in admin_c.get(f"{API}/warehouses", timeout=30).json()["items"])
        assert admin_c.put(f"{API}/warehouses/{wid}", json={"name": "TEST Gudang Ubah"}, timeout=30).status_code == 200
        w = [x for x in admin_c.get(f"{API}/warehouses", timeout=30).json()["items"] if x["id"] == wid][0]
        assert w["name"] == "TEST Gudang Ubah"
        assert admin_c.delete(f"{API}/warehouses/{wid}", timeout=30).status_code == 200

    def test_recipients_crud(self, admin_c):
        code = f"TR{uuid.uuid4().hex[:4].upper()}"
        r = admin_c.post(f"{API}/recipients", json={"code": code, "name": "TEST Penerima", "city": "Solo"}, timeout=30)
        assert r.status_code == 201, r.text[:300]
        rid = r.json()["id"]
        assert any(x["id"] == rid for x in admin_c.get(f"{API}/recipients", timeout=30).json()["items"])
        assert admin_c.put(f"{API}/recipients/{rid}", json={"name": "TEST Penerima Ubah"}, timeout=30).status_code == 200
        assert admin_c.delete(f"{API}/recipients/{rid}", timeout=30).status_code == 200
        assert not any(x["id"] == rid for x in admin_c.get(f"{API}/recipients", timeout=30).json()["items"])

    def test_vehicles_crud(self, admin_c):
        plate = f"TEST {uuid.uuid4().hex[:4].upper()}"
        r = admin_c.post(f"{API}/vehicles", json={"plate_number": plate, "vehicle_type": "Truk", "brand": "Hino"}, timeout=30)
        assert r.status_code == 201, r.text[:300]
        vid = r.json()["id"]
        assert admin_c.put(f"{API}/vehicles/{vid}", json={"brand": "Isuzu"}, timeout=30).status_code == 200
        v = [x for x in admin_c.get(f"{API}/vehicles", timeout=30).json()["items"] if x["id"] == vid][0]
        assert v["brand"] == "Isuzu"
        assert admin_c.delete(f"{API}/vehicles/{vid}", timeout=30).status_code == 200
        assert not any(x["id"] == vid for x in admin_c.get(f"{API}/vehicles", timeout=30).json()["items"])

    def test_users_list_and_create(self, admin_c):
        r = admin_c.get(f"{API}/users", timeout=30)
        assert r.status_code == 200
        assert any(u["email"] == ADMIN["email"] for u in r.json()["items"])
        email = f"test_{uuid.uuid4().hex[:8]}@logistipro.id"
        c = admin_c.post(f"{API}/users", json={"email": email, "password": "secret123", "full_name": "TEST Pengguna", "role": "user"}, timeout=30)
        assert c.status_code == 201, c.text[:300]
        assert c.json()["email"] == email
        assert admin_c.post(f"{API}/users", json={"email": email, "password": "secret123"}, timeout=30).status_code == 400


# ---------- STOCK ----------
class TestStock:
    def test_stock_in_out_and_insufficient(self, admin_c):
        wh = admin_c.get(f"{API}/warehouses", timeout=30).json()["items"][0]["id"]
        cid = admin_c.get(f"{API}/categories", timeout=30).json()["items"][0]["id"]
        sku = f"TEST-{uuid.uuid4().hex[:6].upper()}"
        pid = admin_c.post(f"{API}/products", json={"sku": sku, "name": "TEST Stok Item", "category_id": cid, "minimum_stock": 2}, timeout=30).json()["id"]

        r = admin_c.post(f"{API}/stocks/transaction", json={"product_id": pid, "warehouse_id": wh, "type": "in", "quantity": 50, "note": "TEST in"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["quantity"] == 50

        r = admin_c.post(f"{API}/stocks/transaction", json={"product_id": pid, "warehouse_id": wh, "type": "out", "quantity": 20}, timeout=30)
        assert r.status_code == 200 and r.json()["quantity"] == 30

        r = admin_c.post(f"{API}/stocks/transaction", json={"product_id": pid, "warehouse_id": wh, "type": "out", "quantity": 9999}, timeout=30)
        assert r.status_code == 400
        assert "Stok tidak mencukupi" in r.json()["detail"]

        r = admin_c.post(f"{API}/stocks/transaction", json={"product_id": pid, "warehouse_id": wh, "type": "in", "quantity": 0}, timeout=30)
        assert r.status_code == 400

        # persisted stock
        stocks = admin_c.get(f"{API}/stocks?warehouse={wh}", timeout=30).json()["items"]
        row = [s for s in stocks if s["product_id"] == pid][0]
        assert row["quantity"] == 30
        assert admin_c.get(f"{API}/products/{pid}", timeout=30).json()["stock"] == 30

        txs = admin_c.get(f"{API}/stocks/transactions", timeout=30).json()["items"]
        mine = [t for t in txs if t["sku"] == sku]
        assert len(mine) >= 2
        assert mine[0]["balance_after"] == 30

    def test_stock_transaction_requires_admin(self, user_c):
        r = user_c.post(f"{API}/stocks/transaction", json={"product_id": 1, "warehouse_id": 1, "type": "in", "quantity": 1}, timeout=30)
        assert r.status_code == 403


# ---------- WORKFLOW: request -> approve -> distribution ----------
class TestWorkflow:
    def _setup_product(self, admin_c, qty=100):
        wh = admin_c.get(f"{API}/warehouses", timeout=30).json()["items"][0]["id"]
        cid = admin_c.get(f"{API}/categories", timeout=30).json()["items"][0]["id"]
        sku = f"TEST-{uuid.uuid4().hex[:6].upper()}"
        pid = admin_c.post(f"{API}/products", json={"sku": sku, "name": f"TEST Flow {sku}", "category_id": cid, "minimum_stock": 1}, timeout=30).json()["id"]
        admin_c.post(f"{API}/stocks/transaction", json={"product_id": pid, "warehouse_id": wh, "type": "in", "quantity": qty}, timeout=30)
        rid = admin_c.get(f"{API}/recipients", timeout=30).json()["items"][0]["id"]
        return wh, pid, rid

    def test_full_happy_path(self, admin_c, user_c):
        wh, pid, rid = self._setup_product(admin_c, 100)
        body = {"warehouse_id": wh, "recipient_id": rid, "destination": "TEST Tujuan Kota",
                "items": [{"product_id": pid, "quantity": 10}], "note": "TEST request"}
        r = user_c.post(f"{API}/requests", json=body, timeout=30)
        assert r.status_code == 201, r.text[:400]
        req = r.json()
        assert req["number"].startswith("REQ-")
        assert req["status"] == "pending"
        assert req["total_quantity"] == 10
        req_id = req["id"]

        # iteration_5 behaviour change (anti-duplicate): requester must NOT get a self-notif
        notif = user_c.get(f"{API}/notifications", timeout=30).json()
        assert not any(req["number"] in n["message"] for n in notif["items"]), \
            "requester received a self-notif for its own new request"

        # request detail + timeline
        d = user_c.get(f"{API}/requests/{req_id}", timeout=30)
        assert d.status_code == 200
        assert isinstance(d.json()["timeline"], list) and len(d.json()["timeline"]) > 1

        # empty items rejected
        assert user_c.post(f"{API}/requests", json={"warehouse_id": wh, "recipient_id": rid, "destination": "x", "items": []}, timeout=30).status_code == 400

        before = admin_c.get(f"{API}/products/{pid}", timeout=30).json()["stock"]
        a = admin_c.post(f"{API}/requests/{req_id}/action", json={"action": "approve"}, timeout=30)
        assert a.status_code == 200, a.text[:300]
        assert a.json()["status"] == "approved"
        after = admin_c.get(f"{API}/products/{pid}", timeout=30).json()["stock"]
        assert after == before - 10, f"stock not deducted: {before}->{after}"

        # double approve blocked
        assert admin_c.post(f"{API}/requests/{req_id}/action", json={"action": "approve"}, timeout=30).status_code == 400

        # create distribution
        vid = admin_c.get(f"{API}/vehicles", timeout=30).json()["items"][0]["id"]
        dist = admin_c.post(f"{API}/distributions", json={"request_id": req_id, "vehicle_id": vid,
                                                          "delivery_number": "TEST-SJ-001",
                                                          "estimated_arrival": "2026-08-01"}, timeout=30)
        assert dist.status_code == 201, dist.text[:400]
        dj = dist.json()
        did = dj["id"]
        assert dj["number"].startswith("DST-")
        assert dj["status"] == "prepared"
        assert len(dj["history"]) == 1

        # duplicate distribution blocked
        assert admin_c.post(f"{API}/distributions", json={"request_id": req_id, "vehicle_id": vid}, timeout=30).status_code == 400

        # tracking shows it
        tr = admin_c.get(f"{API}/tracking", timeout=30).json()["items"]
        assert any(t["id"] == did for t in tr)

        for st in ["in_transit", "arrived", "completed"]:
            s = admin_c.post(f"{API}/distributions/{did}/status", json={"status": st, "note": f"TEST {st}"}, timeout=30)
            assert s.status_code == 200, s.text[:300]
            assert s.json()["status"] == st

        detail = admin_c.get(f"{API}/distributions/{did}", timeout=30).json()
        assert detail["status"] == "completed"
        assert len(detail["history"]) == 4
        assert detail["completed_at"]

        # vehicle back to available
        v = [x for x in admin_c.get(f"{API}/vehicles", timeout=30).json()["items"] if x["id"] == vid][0]
        assert v["status"] == "available", f"vehicle status={v['status']}"

        # request status completed
        assert user_c.get(f"{API}/requests/{req_id}", timeout=30).json()["status"] == "completed"

        # completed distribution not in tracking
        tr = admin_c.get(f"{API}/tracking", timeout=30).json()["items"]
        assert not any(t["id"] == did for t in tr)

    def test_reject_flow(self, admin_c, user_c):
        wh, pid, rid = self._setup_product(admin_c, 20)
        req_id = user_c.post(f"{API}/requests", json={"warehouse_id": wh, "recipient_id": rid,
                                                      "destination": "TEST Reject", "items": [{"product_id": pid, "quantity": 5}]}, timeout=30).json()["id"]
        r = admin_c.post(f"{API}/requests/{req_id}/action", json={"action": "reject", "reason": "TEST alasan tolak"}, timeout=30)
        assert r.status_code == 200 and r.json()["status"] == "rejected"
        d = admin_c.get(f"{API}/requests/{req_id}", timeout=30).json()
        assert d["rejection_reason"] == "TEST alasan tolak"
        # distribution for rejected request blocked
        assert admin_c.post(f"{API}/distributions", json={"request_id": req_id}, timeout=30).status_code == 400

    def test_approve_insufficient_stock(self, admin_c, user_c):
        wh, pid, rid = self._setup_product(admin_c, 3)
        req_id = user_c.post(f"{API}/requests", json={"warehouse_id": wh, "recipient_id": rid,
                                                      "destination": "TEST Kurang", "items": [{"product_id": pid, "quantity": 500}]}, timeout=30).json()["id"]
        r = admin_c.post(f"{API}/requests/{req_id}/action", json={"action": "approve"}, timeout=30)
        assert r.status_code == 400, r.text[:300]
        assert "tidak cukup" in r.json()["detail"]
        assert admin_c.get(f"{API}/products/{pid}", timeout=30).json()["stock"] == 3
        assert admin_c.get(f"{API}/requests/{req_id}", timeout=30).json()["status"] == "pending"

    def test_invalid_action(self, admin_c, user_c):
        wh, pid, rid = self._setup_product(admin_c, 10)
        req_id = user_c.post(f"{API}/requests", json={"warehouse_id": wh, "recipient_id": rid,
                                                      "destination": "TEST Aksi", "items": [{"product_id": pid, "quantity": 1}]}, timeout=30).json()["id"]
        assert admin_c.post(f"{API}/requests/{req_id}/action", json={"action": "bogus"}, timeout=30).status_code == 400
        # user cannot approve
        assert user_c.post(f"{API}/requests/{req_id}/action", json={"action": "approve"}, timeout=30).status_code == 403

    def test_user_cannot_see_others_request(self, admin_c, user_c):
        wh, pid, rid = self._setup_product(admin_c, 10)
        req_id = user_c.post(f"{API}/requests", json={"warehouse_id": wh, "recipient_id": rid,
                                                      "destination": "TEST Privasi", "items": [{"product_id": pid, "quantity": 1}]}, timeout=30).json()["id"]
        other = new_session({"email": "budi@logistipro.id", "password": "user123"})
        r = other.get(f"{API}/requests/{req_id}", timeout=30)
        assert r.status_code == 403, f"expected 403, got {r.status_code}"
        ids = [x["id"] for x in other.get(f"{API}/requests", timeout=30).json()["items"]]
        assert req_id not in ids


# ---------- NOTIFICATIONS / ACTIVITY ----------
class TestNotificationsActivity:
    def test_notifications_mark_all(self, user_c):
        r = user_c.get(f"{API}/notifications", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "unread" in d
        assert user_c.post(f"{API}/notifications", json={"mark_all": True}, timeout=30).status_code == 200
        assert user_c.get(f"{API}/notifications", timeout=30).json()["unread"] == 0

    def test_activities_admin_only(self, admin_c, user_c):
        r = admin_c.get(f"{API}/activities", timeout=30)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) > 0
        assert all("ip_address" in a and "detail" in a for a in items)
        assert any(a["ip_address"] not in ("", "-") for a in items), "no IP recorded in activity log"
        assert user_c.get(f"{API}/activities", timeout=30).status_code == 403


# ---------- REPORTS ----------
class TestReports:
    def test_summary(self, admin_c):
        r = admin_c.get(f"{API}/reports/summary", timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        for k in ["requests_total", "distributions_total", "stock_in", "stock_out", "top_products"]:
            assert k in d
        assert isinstance(d["top_products"], list)

    @pytest.mark.parametrize("kind", ["stock", "requests", "distributions", "stock_transactions"])
    @pytest.mark.parametrize("fmt,ctype", [("csv", "text/csv"), ("excel", "spreadsheetml"), ("pdf", "application/pdf")])
    def test_exports(self, admin_c, kind, fmt, ctype):
        r = admin_c.get(f"{API}/reports/{kind}/export/{fmt}", timeout=90)
        assert r.status_code == 200, r.text[:300]
        assert ctype in r.headers.get("Content-Type", ""), r.headers.get("Content-Type")
        assert len(r.content) > 100
        assert not r.headers.get("Content-Type", "").startswith("application/json")

    def test_export_bad_format(self, admin_c):
        assert admin_c.get(f"{API}/reports/stock/export/xml", timeout=30).status_code == 400

    def test_reports_forbidden_for_user(self, user_c):
        assert user_c.get(f"{API}/reports/summary", timeout=30).status_code == 403
        assert user_c.get(f"{API}/reports/stock/export/csv", timeout=30).status_code == 403


# ---------- RBAC ----------
class TestRBAC:
    def test_user_forbidden_on_admin_endpoints(self, user_c):
        checks = [
            ("post", "/products", {"sku": "X", "name": "X", "category_id": 1}),
            ("post", "/categories", {"name": "X"}),
            ("post", "/warehouses", {"code": "X", "name": "X"}),
            ("post", "/vehicles", {"plate_number": "X"}),
            ("post", "/recipients", {"code": "X", "name": "X"}),
            ("get", "/users", None),
            ("get", "/activities", None),
        ]
        failures = []
        for method, path, body in checks:
            fn = getattr(user_c, method)
            r = fn(f"{API}{path}", json=body, timeout=30) if body is not None else fn(f"{API}{path}", timeout=30)
            if r.status_code != 403:
                failures.append(f"{method.upper()} {path} -> {r.status_code}")
        assert not failures, f"expected 403: {failures}"

    def test_unauthenticated_blocked(self):
        for path in ["/products", "/categories", "/requests", "/distributions", "/tracking", "/notifications", "/stocks"]:
            assert requests.get(f"{API}{path}", timeout=30).status_code == 401, path

    def test_logout_invalidates_session(self):
        s = new_session(USER)
        assert s.get(f"{API}/auth/me", timeout=30).status_code == 200
        assert s.post(f"{API}/auth/logout", timeout=30).status_code == 200
        assert s.get(f"{API}/auth/me", timeout=30).status_code == 401


# ---------- EDGE / ERROR HANDLING ----------
class TestEdgeCases:
    def test_nonexistent_resources(self, admin_c):
        results = {}
        for path in ["/products/999999", "/requests/999999", "/distributions/999999", "/categories/999999"]:
            results[path] = admin_c.get(f"{API}{path}", timeout=30).status_code
        bad = {k: v for k, v in results.items() if v >= 500}
        assert not bad, f"server error (500) instead of 404 for missing objects: {bad}"

    def test_invalid_payloads(self, admin_c):
        bad = {}
        r = admin_c.post(f"{API}/products", json={"name": "no sku"}, timeout=30)
        if r.status_code >= 500:
            bad["POST /products missing sku"] = r.status_code
        r = admin_c.post(f"{API}/requests", json={"items": [{"product_id": 1, "quantity": 1}]}, timeout=30)
        if r.status_code >= 500:
            bad["POST /requests missing warehouse"] = r.status_code
        r = admin_c.post(f"{API}/stocks/transaction", json={"quantity": 5}, timeout=30)
        if r.status_code >= 500:
            bad["POST /stocks/transaction missing ids"] = r.status_code
        assert not bad, f"unhandled 500 on invalid payload: {bad}"
