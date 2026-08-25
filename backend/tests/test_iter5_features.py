"""Iteration 5: (1) Anti-duplicate self notifications, (2) Report schedules + report inbox."""
import os
import re

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/") + "/api"

ADMIN = {"email": "admin@logistipro.id", "password": "admin123"}
USER = {"email": "user@logistipro.id", "password": "user123"}
BUDI = {"email": "budi@logistipro.id", "password": "user123"}


def login(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"Login failed for {creds['email']}: {r.status_code} {r.text[:300]}")
    return s


@pytest.fixture(scope="session")
def admin():
    return login(ADMIN)


@pytest.fixture(scope="session")
def user():
    return login(USER)


@pytest.fixture(scope="session")
def budi():
    return login(BUDI)


def unread(session):
    r = session.get(f"{BASE_URL}/notifications", timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()["unread"]


@pytest.fixture(scope="session")
def refs(user):
    """warehouse/recipient/product ids usable for creating a request."""
    wh = user.get(f"{BASE_URL}/warehouses", timeout=30).json()["items"]
    rc = user.get(f"{BASE_URL}/recipients", timeout=30).json()["items"]
    pr = user.get(f"{BASE_URL}/products", timeout=30).json()["items"]
    assert wh and rc and pr
    return {"warehouse_id": wh[0]["id"], "recipient_id": rc[0]["id"], "product_id": pr[0]["id"]}


# ---------- FEATURE 1: anti-duplicate self notifications ----------
class TestSelfNotifications:
    def test_user_request_creation_no_self_notif_admin_notified(self, user, admin, refs):
        before_user = unread(user)
        before_admin = unread(admin)
        payload = {"warehouse_id": refs["warehouse_id"], "recipient_id": refs["recipient_id"],
                   "destination": "TEST_ Jl. Anti Ganda 1", "note": "TEST_selfnotif",
                   "items": [{"product_id": refs["product_id"], "quantity": 1}]}
        r = user.post(f"{BASE_URL}/requests", json=payload, timeout=30)
        assert r.status_code == 201, r.text[:400]
        req = r.json()
        assert req["number"].startswith("REQ-")
        after_user = unread(user)
        after_admin = unread(admin)
        assert after_user == before_user, f"requester got a self-notif ({before_user} -> {after_user})"
        assert after_admin > before_admin, "admin did not receive 'Permintaan baru' fan-out"
        titles = [n["title"] for n in admin.get(f"{BASE_URL}/notifications", timeout=30).json()["items"][:5]]
        assert "Permintaan baru" in titles, titles
        pytest.request_id = req["id"]
        pytest.request_number = req["number"]

    def test_admin_action_no_self_notif_requester_notified(self, admin, user, refs):
        payload = {"warehouse_id": refs["warehouse_id"], "recipient_id": refs["recipient_id"],
                   "destination": "TEST_ Jl. Anti Ganda 2",
                   "items": [{"product_id": refs["product_id"], "quantity": 1}]}
        rid = user.post(f"{BASE_URL}/requests", json=payload, timeout=30).json()["id"]
        before_admin = unread(admin)
        before_user = unread(user)
        r = admin.post(f"{BASE_URL}/requests/{rid}/action", json={"action": "reject", "reason": "TEST_reason"},
                       timeout=30)
        assert r.status_code == 200, r.text[:400]
        assert r.json()["status"] == "rejected"
        assert unread(admin) == before_admin, "admin got a self-notif for its own reject"
        assert unread(user) > before_user, "requester did not get 'Permintaan ditolak'"

    def test_admin_own_request_action_no_self_notif(self, admin, refs):
        """Admin creates a request for itself then approves it -> should get zero notifications."""
        payload = {"warehouse_id": refs["warehouse_id"], "recipient_id": refs["recipient_id"],
                   "destination": "TEST_ Jl. Admin Sendiri",
                   "items": [{"product_id": refs["product_id"], "quantity": 1}]}
        r = admin.post(f"{BASE_URL}/requests", json=payload, timeout=30)
        assert r.status_code == 201, r.text[:400]
        rid = r.json()["id"]
        before = unread(admin)
        act = admin.post(f"{BASE_URL}/requests/{rid}/action", json={"action": "process"}, timeout=30)
        assert act.status_code == 200, act.text[:400]
        after = unread(admin)
        assert after == before, (
            f"admin received a self-notif when acting on its own request ({before} -> {after}); "
            "notify(req.requester, ...) is missing an actor guard")

    def test_admin_stock_transaction_low_stock_no_self_notif(self, admin):
        stocks = admin.get(f"{BASE_URL}/stocks", timeout=30).json()["items"]
        target = next((s for s in stocks if s["quantity"] > 0), None)
        assert target, "no stock row with quantity > 0"
        before = unread(admin)
        original = target["quantity"]
        base = {"product_id": target["product_id"], "warehouse_id": target["warehouse_id"]}
        # drive quantity to 1 so it is (almost surely) below minimum_stock
        r = admin.post(f"{BASE_URL}/stocks/transaction",
                       json={**base, "type": "adjust", "quantity": 1, "note": "TEST_lowstock"}, timeout=30)
        assert r.status_code == 200, r.text[:400]
        assert r.json()["quantity"] == 1
        after = unread(admin)
        assert after == before, f"admin got its own 'Stok rendah' notif ({before} -> {after})"
        # restore
        admin.post(f"{BASE_URL}/stocks/transaction",
                   json={**base, "type": "adjust", "quantity": original, "note": "TEST_restore"}, timeout=30)

    def test_admin_distribution_flow_notifies_requester_only(self, admin, user, refs):
        payload = {"warehouse_id": refs["warehouse_id"], "recipient_id": refs["recipient_id"],
                   "destination": "TEST_ Jl. Distribusi",
                   "items": [{"product_id": refs["product_id"], "quantity": 1}]}
        rid = user.post(f"{BASE_URL}/requests", json=payload, timeout=30).json()["id"]
        assert admin.post(f"{BASE_URL}/requests/{rid}/action",
                          json={"action": "approve"}, timeout=30).status_code == 200
        before_admin, before_user = unread(admin), unread(user)
        d = admin.post(f"{BASE_URL}/distributions",
                       json={"request_id": rid, "destination": "TEST_ Jl. Distribusi"}, timeout=30)
        assert d.status_code == 201, d.text[:400]
        did = d.json()["id"]
        assert unread(admin) == before_admin, "admin got self-notif on distribution create"
        assert unread(user) > before_user, "requester not notified on distribution create"
        before_admin, before_user = unread(admin), unread(user)
        st = admin.post(f"{BASE_URL}/distributions/{did}/status", json={"status": "in_transit"}, timeout=30)
        assert st.status_code == 200, st.text[:400]
        assert unread(admin) == before_admin, "admin got self-notif on distribution status update"
        assert unread(user) > before_user, "requester not notified on distribution status update"


# ---------- FEATURE 2: report schedules ----------
class TestReportSchedules:
    created = []

    def test_create_schedule_sets_next_run(self, admin):
        r = admin.post(f"{BASE_URL}/report-schedules",
                       json={"name": "TEST_ Jadwal Stok", "kind": "stock", "format": "csv",
                             "frequency": "monthly", "day_of_month": 5}, timeout=30)
        assert r.status_code == 201, r.text[:400]
        d = r.json()
        assert d["name"] == "TEST_ Jadwal Stok"
        assert d["kind"] == "stock" and d["format"] == "csv"
        assert d["frequency"] == "monthly" and d["day_of_month"] == 5
        assert d["active"] is True
        assert d["next_run_at"], "next_run_at not set"
        assert d["last_run_at"] == ""
        TestReportSchedules.created.append(d["id"])

    def test_list_schedules_includes_created(self, admin):
        r = admin.get(f"{BASE_URL}/report-schedules", timeout=30)
        assert r.status_code == 200, r.text[:400]
        items = r.json()["items"]
        found = [i for i in items if i["id"] in TestReportSchedules.created]
        assert found, "created schedule not in list"
        for i in items:
            assert "next_run_at" in i and "_id" not in i

    def test_run_schedule_creates_report_and_notifies(self, admin):
        sid = TestReportSchedules.created[0]
        before = unread(admin)
        r = admin.post(f"{BASE_URL}/report-schedules/{sid}/run", timeout=60)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["generated_report_id"]
        assert d["filename"].endswith(".csv")
        assert d["next_run_at"]
        # owner notified (this is intentional per spec)
        assert unread(admin) > before, "owner not notified about ready report"
        sched = [s for s in admin.get(f"{BASE_URL}/report-schedules", timeout=30).json()["items"]
                 if s["id"] == sid][0]
        assert sched["last_run_at"] != "", "last_run_at not updated"
        TestReportSchedules.report_id = d["generated_report_id"]
        TestReportSchedules.report_name = d["filename"]

    def test_generated_reports_list_and_unread(self, admin):
        r = admin.get(f"{BASE_URL}/generated-reports", timeout=30)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        ids = [i["id"] for i in body["items"]]
        assert TestReportSchedules.report_id in ids
        item = [i for i in body["items"] if i["id"] == TestReportSchedules.report_id][0]
        assert item["format"] == "csv" and item["kind"] == "stock"
        assert item["size"] > 0
        assert item["schedule_name"] == "TEST_ Jadwal Stok"
        assert item["downloaded"] is False
        assert body["unread"] == sum(1 for i in body["items"] if not i["downloaded"])

    def test_download_marks_read(self, admin):
        rid = TestReportSchedules.report_id
        r = admin.get(f"{BASE_URL}/generated-reports/{rid}/download", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert "text/csv" in r.headers.get("Content-Type", ""), r.headers.get("Content-Type")
        assert TestReportSchedules.report_name in r.headers.get("Content-Disposition", "")
        assert len(r.content) > 0
        item = [i for i in admin.get(f"{BASE_URL}/generated-reports", timeout=30).json()["items"]
                if i["id"] == rid][0]
        assert item["downloaded"] is True, "downloaded_at not set after download"

    @pytest.mark.parametrize("fmt,ctype,ext", [
        ("excel", "spreadsheetml", "xlsx"),
        ("pdf", "pdf", "pdf"),
    ])
    def test_run_other_formats(self, admin, fmt, ctype, ext):
        s = admin.post(f"{BASE_URL}/report-schedules",
                       json={"name": f"TEST_ Fmt {fmt}", "kind": "requests", "format": fmt,
                             "frequency": "weekly", "day_of_week": 2}, timeout=30).json()
        TestReportSchedules.created.append(s["id"])
        run = admin.post(f"{BASE_URL}/report-schedules/{s['id']}/run", timeout=60)
        assert run.status_code == 200, run.text[:400]
        gid = run.json()["generated_report_id"]
        assert run.json()["filename"].endswith("." + ext)
        dl = admin.get(f"{BASE_URL}/generated-reports/{gid}/download", timeout=60)
        assert dl.status_code == 200
        assert ctype in dl.headers.get("Content-Type", ""), dl.headers.get("Content-Type")
        assert f'.{ext}"' in dl.headers.get("Content-Disposition", "")

    def test_update_schedule_recomputes_next_run(self, admin):
        sid = TestReportSchedules.created[0]
        old = [s for s in admin.get(f"{BASE_URL}/report-schedules", timeout=30).json()["items"]
               if s["id"] == sid][0]
        r = admin.put(f"{BASE_URL}/report-schedules/{sid}",
                      json={"kind": "distributions", "format": "pdf", "frequency": "daily"}, timeout=30)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["kind"] == "distributions" and d["format"] == "pdf" and d["frequency"] == "daily"
        assert d["next_run_at"] != old["next_run_at"], "next_run_at not recomputed"
        get = [s for s in admin.get(f"{BASE_URL}/report-schedules", timeout=30).json()["items"]
               if s["id"] == sid][0]
        assert get["kind"] == "distributions" and get["frequency"] == "daily"

    def test_toggle_active(self, admin):
        sid = TestReportSchedules.created[0]
        assert admin.put(f"{BASE_URL}/report-schedules/{sid}", json={"active": False},
                         timeout=30).json()["active"] is False
        assert admin.put(f"{BASE_URL}/report-schedules/{sid}", json={"active": True},
                         timeout=30).json()["active"] is True

    def test_report_isolation_other_user(self, user, admin):
        r = user.get(f"{BASE_URL}/generated-reports", timeout=30)
        assert r.status_code == 200, r.text[:300]
        ids = [i["id"] for i in r.json()["items"]]
        assert TestReportSchedules.report_id not in ids, "user can see admin's generated report"
        # cross-user download must not leak
        dl = user.get(f"{BASE_URL}/generated-reports/{TestReportSchedules.report_id}/download", timeout=30)
        assert dl.status_code in (403, 404), f"cross-user download returned {dl.status_code}"

    def test_user_forbidden_on_schedules(self, user):
        assert user.get(f"{BASE_URL}/report-schedules", timeout=30).status_code == 403
        assert user.post(f"{BASE_URL}/report-schedules",
                         json={"name": "TEST_x", "kind": "stock"}, timeout=30).status_code == 403
        sid = TestReportSchedules.created[0]
        assert user.post(f"{BASE_URL}/report-schedules/{sid}/run", timeout=30).status_code == 403
        assert user.put(f"{BASE_URL}/report-schedules/{sid}", json={"name": "TEST_y"},
                        timeout=30).status_code == 403
        assert user.delete(f"{BASE_URL}/report-schedules/{sid}", timeout=30).status_code == 403

    def test_unauthenticated_blocked(self):
        anon = requests.Session()
        assert anon.get(f"{BASE_URL}/report-schedules", timeout=30).status_code in (401, 403)
        assert anon.get(f"{BASE_URL}/generated-reports", timeout=30).status_code in (401, 403)

    def test_invalid_schedule_payload(self, admin):
        r = admin.post(f"{BASE_URL}/report-schedules", json={"kind": "stock"}, timeout=30)
        assert r.status_code in (400, 422), f"missing name returned {r.status_code}: {r.text[:200]}"

    def test_missing_ids_return_404_not_500(self, admin):
        assert admin.post(f"{BASE_URL}/report-schedules/999999/run", timeout=30).status_code == 404
        assert admin.put(f"{BASE_URL}/report-schedules/999999", json={"name": "x"},
                         timeout=30).status_code == 404
        assert admin.delete(f"{BASE_URL}/report-schedules/999999", timeout=30).status_code == 404
        assert admin.get(f"{BASE_URL}/generated-reports/999999/download", timeout=30).status_code == 404

    def test_zz_delete_schedules(self, admin):
        for sid in list(TestReportSchedules.created):
            r = admin.delete(f"{BASE_URL}/report-schedules/{sid}", timeout=30)
            assert r.status_code == 200, r.text[:300]
        remaining = [s["id"] for s in admin.get(f"{BASE_URL}/report-schedules", timeout=30).json()["items"]]
        for sid in TestReportSchedules.created:
            assert sid not in remaining
