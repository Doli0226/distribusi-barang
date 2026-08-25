"""Iteration 4 feature tests: arrival_photo on distribution status + selective export (?ids=)."""
import csv
import io
import os

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

ADMIN = {"email": "admin@logistipro.id", "password": "admin123"}
USER = {"email": "user@logistipro.id", "password": "user123"}

PNG_1x1 = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
           "z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==")


def _client(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _client(ADMIN)


@pytest.fixture(scope="module")
def user():
    return _client(USER)


# ---------- helpers ----------
def _new_distribution(admin):
    """Create a fresh request -> approve -> distribution, returns distribution id."""
    wh = admin.get(f"{BASE_URL}/api/warehouses", timeout=30).json()["items"][0]
    rc = admin.get(f"{BASE_URL}/api/recipients", timeout=30).json()["items"][0]
    prods = admin.get(f"{BASE_URL}/api/products", timeout=30).json()["items"]
    # pick product with stock in that warehouse
    stocks = admin.get(f"{BASE_URL}/api/stocks?warehouse={wh['id']}", timeout=30).json()["items"]
    stock = next((s for s in stocks if s["quantity"] >= 2), None)
    assert stock, "no warehouse stock available for test"
    r = admin.post(f"{BASE_URL}/api/requests", json={
        "warehouse_id": stock["warehouse_id"], "recipient_id": rc["id"],
        "destination": "TEST_ITER4 Depot", "needed_date": "2026-09-01",
        "items": [{"product_id": stock["product_id"], "quantity": 1}],
    }, timeout=30)
    assert r.status_code == 201, f"create request failed: {r.status_code} {r.text[:300]}"
    req_id = r.json()["id"]
    a = admin.post(f"{BASE_URL}/api/requests/{req_id}/action", json={"action": "approve"}, timeout=30)
    assert a.status_code == 200, f"approve failed: {a.status_code} {a.text[:300]}"
    d = admin.post(f"{BASE_URL}/api/distributions", json={"request_id": req_id,
                                                          "estimated_arrival": "2026-09-05"}, timeout=30)
    assert d.status_code == 201, f"create distribution failed: {d.status_code} {d.text[:300]}"
    return d.json()["id"]


# ---------- Feature 3: arrival photo ----------
class TestArrivalPhoto:
    def test_arrived_with_photo_persists(self, admin):
        did = _new_distribution(admin)
        r = admin.post(f"{BASE_URL}/api/distributions/{did}/status",
                       json={"status": "arrived", "photo": PNG_1x1}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["status"] == "arrived"
        g = admin.get(f"{BASE_URL}/api/distributions/{did}", timeout=30)
        assert g.status_code == 200
        data = g.json()
        assert isinstance(data["arrival_photo"], str)
        assert data["arrival_photo"] == PNG_1x1

    def test_arrived_without_photo_backward_compat(self, admin):
        did = _new_distribution(admin)
        r = admin.post(f"{BASE_URL}/api/distributions/{did}/status",
                       json={"status": "arrived"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        g = admin.get(f"{BASE_URL}/api/distributions/{did}", timeout=30).json()
        assert g["arrival_photo"] == ""
        assert isinstance(g["arrival_photo"], str)

    def test_photo_ignored_for_non_arrived_status(self, admin):
        did = _new_distribution(admin)
        r = admin.post(f"{BASE_URL}/api/distributions/{did}/status",
                       json={"status": "in_transit", "photo": PNG_1x1}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        g = admin.get(f"{BASE_URL}/api/distributions/{did}", timeout=30).json()
        assert g["arrival_photo"] == "", "photo must not be stored for in_transit"
        # completed also should not store
        r2 = admin.post(f"{BASE_URL}/api/distributions/{did}/status",
                        json={"status": "completed", "photo": PNG_1x1}, timeout=30)
        assert r2.status_code == 200, r2.text[:300]
        g2 = admin.get(f"{BASE_URL}/api/distributions/{did}", timeout=30).json()
        assert g2["arrival_photo"] == "", "photo must not be stored for completed"

    def test_photo_persists_after_further_transitions(self, admin):
        did = _new_distribution(admin)
        admin.post(f"{BASE_URL}/api/distributions/{did}/status",
                   json={"status": "arrived", "photo": PNG_1x1}, timeout=30)
        admin.post(f"{BASE_URL}/api/distributions/{did}/status",
                   json={"status": "completed"}, timeout=30)
        g = admin.get(f"{BASE_URL}/api/distributions/{did}", timeout=30).json()
        assert g["arrival_photo"] == PNG_1x1
        assert g["status"] == "completed"

    def test_user_cannot_set_status(self, user, admin):
        did = _new_distribution(admin)
        r = user.post(f"{BASE_URL}/api/distributions/{did}/status",
                      json={"status": "arrived", "photo": PNG_1x1}, timeout=30)
        assert r.status_code == 403


# ---------- Regression: status validation ----------
class TestStatusRegression:
    def test_invalid_status_400(self, admin):
        did = _new_distribution(admin)
        r = admin.post(f"{BASE_URL}/api/distributions/{did}/status",
                       json={"status": "banana"}, timeout=30)
        assert r.status_code == 400
        assert "detail" in r.json()

    def test_backward_transition_400(self, admin):
        did = _new_distribution(admin)
        admin.post(f"{BASE_URL}/api/distributions/{did}/status", json={"status": "arrived"}, timeout=30)
        r = admin.post(f"{BASE_URL}/api/distributions/{did}/status", json={"status": "in_transit"}, timeout=30)
        assert r.status_code == 400
        assert "mundur" in r.json()["detail"].lower()


# ---------- Feature 4: selective export ----------
KINDS = ["stock", "requests", "distributions", "stock_transactions"]


def _ids_for(admin, kind, n=3):
    if kind == "stock":
        items = admin.get(f"{BASE_URL}/api/stocks", timeout=30).json()["items"]
    elif kind == "requests":
        items = admin.get(f"{BASE_URL}/api/requests", timeout=30).json()["items"]
    elif kind == "distributions":
        items = admin.get(f"{BASE_URL}/api/distributions", timeout=30).json()["items"]
    else:
        items = admin.get(f"{BASE_URL}/api/stocks/transactions", timeout=30).json()["items"]
    return [i["id"] for i in items[:n]]


class TestSelectiveExport:
    @pytest.mark.parametrize("kind", KINDS)
    def test_csv_selected_ids_only(self, admin, kind):
        ids = _ids_for(admin, kind, 3)
        assert len(ids) == 3, f"need 3 {kind} rows, got {len(ids)}"
        r = admin.get(f"{BASE_URL}/api/reports/{kind}/export/csv?ids={','.join(map(str, ids))}", timeout=60)
        assert r.status_code == 200, r.text[:200]
        assert "text/csv" in r.headers["Content-Type"]
        rows = [row for row in csv.reader(io.StringIO(r.text)) if row]
        assert len(rows) == 4, f"expected header + 3 rows, got {len(rows)}"

    @pytest.mark.parametrize("kind", KINDS)
    def test_csv_all_rows_greater_than_selected(self, admin, kind):
        ids = _ids_for(admin, kind, 3)
        r_all = admin.get(f"{BASE_URL}/api/reports/{kind}/export/csv", timeout=60)
        rows_all = [row for row in csv.reader(io.StringIO(r_all.text)) if row]
        assert len(rows_all) >= 4

    @pytest.mark.parametrize("fmt,ctype", [("excel", "spreadsheetml"), ("pdf", "application/pdf")])
    def test_other_formats_with_ids(self, admin, fmt, ctype):
        ids = _ids_for(admin, "requests", 3)
        r = admin.get(f"{BASE_URL}/api/reports/requests/export/{fmt}?ids={','.join(map(str, ids))}", timeout=60)
        assert r.status_code == 200, r.text[:200]
        assert ctype in r.headers["Content-Type"]
        assert len(r.content) > 100

    def test_excel_row_count_matches_selection(self, admin):
        import openpyxl
        ids = _ids_for(admin, "requests", 3)
        r = admin.get(f"{BASE_URL}/api/reports/requests/export/excel?ids={','.join(map(str, ids))}", timeout=60)
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        assert wb.active.max_row == 4

    @pytest.mark.parametrize("kind", KINDS)
    def test_bad_ids_returns_header_only(self, admin, kind):
        r = admin.get(f"{BASE_URL}/api/reports/{kind}/export/csv?ids=abc,999999", timeout=60)
        assert r.status_code == 200, r.text[:300]
        rows = [row for row in csv.reader(io.StringIO(r.text)) if row]
        assert len(rows) == 1, f"expected header only, got {len(rows)}"

    def test_non_numeric_only_ids_no_500(self, admin):
        # KNOWN BUG (reported iteration_4): ids=abc parses to [] which is falsy in
        # _dataset.apply_ids, so the whole dataset is exported instead of an empty selection.
        r = admin.get(f"{BASE_URL}/api/reports/requests/export/csv?ids=abc", timeout=60)
        assert r.status_code == 200
        rows = [row for row in csv.reader(io.StringIO(r.text)) if row]
        assert len(rows) == 1, f"ids=abc should yield header only, got {len(rows)} rows"

    @pytest.mark.parametrize("kind", KINDS)
    def test_export_admin_only(self, user, kind):
        r = user.get(f"{BASE_URL}/api/reports/{kind}/export/csv?ids=1,2", timeout=60)
        assert r.status_code == 403

    def test_unsupported_format(self, admin):
        r = admin.get(f"{BASE_URL}/api/reports/requests/export/xml?ids=1", timeout=30)
        assert r.status_code == 400


# ---------- Feature 1: notifications endpoint shape (for polling) ----------
class TestNotificationsPolling:
    def test_notifications_shape(self, user):
        r = user.get(f"{BASE_URL}/api/notifications", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["items"], list)
        assert isinstance(d["unread"], int)
        if d["items"]:
            n = d["items"][0]
            for k in ["id", "title", "message", "kind", "read", "link", "created_at"]:
                assert k in n

    def test_new_notification_appears_for_user(self, admin, user):
        """Admin action on the user's request should surface a new notification to that user."""
        before = user.get(f"{BASE_URL}/api/notifications", timeout=30).json()
        before_ids = {n["id"] for n in before["items"]}
        # user creates a request -> admin rejects -> user gets notification
        wh = user.get(f"{BASE_URL}/api/warehouses", timeout=30).json()["items"][0]
        rc = user.get(f"{BASE_URL}/api/recipients", timeout=30).json()["items"][0]
        prod = user.get(f"{BASE_URL}/api/products", timeout=30).json()["items"][0]
        cr = user.post(f"{BASE_URL}/api/requests", json={
            "warehouse_id": wh["id"], "recipient_id": rc["id"], "destination": "TEST_ITER4 Notif",
            "items": [{"product_id": prod["id"], "quantity": 1}]}, timeout=30)
        assert cr.status_code == 201, cr.text[:300]
        req_id = cr.json()["id"]
        rj = admin.post(f"{BASE_URL}/api/requests/{req_id}/action",
                        json={"action": "reject", "reason": "TEST_ITER4"}, timeout=30)
        assert rj.status_code == 200, rj.text[:300]
        after = user.get(f"{BASE_URL}/api/notifications", timeout=30).json()
        new = [n for n in after["items"] if n["id"] not in before_ids]
        assert new, "no new notification produced for the requester"
        assert any("ditolak" in n["title"].lower() for n in new)
