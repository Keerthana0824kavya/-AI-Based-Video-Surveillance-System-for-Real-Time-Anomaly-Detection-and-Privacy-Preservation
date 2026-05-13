"""Backend API tests for Sentinel Surveillance."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://secureye-monitor.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@sentinel.io"
ADMIN_PASS = "admin123"


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    assert "access_token" in s.cookies, "access_token cookie not set"
    return s


# ---- Auth ----
class TestAuth:
    def test_login_success_sets_cookie(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == ADMIN_EMAIL
        assert d["role"] == "admin"
        assert "access_token" in s.cookies

    def test_login_invalid(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=15)
        assert r.status_code == 401

    def test_me_without_cookie_401(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 401

    def test_me_with_cookie(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_register_and_logout(self):
        import uuid
        s = requests.Session()
        email = f"test_{uuid.uuid4().hex[:8]}@test.io"
        r = s.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": "pass1234", "name": "T"}, timeout=15)
        assert r.status_code == 200
        assert "access_token" in s.cookies
        r2 = s.post(f"{BASE_URL}/api/auth/logout", timeout=15)
        assert r2.status_code == 200
        # after logout cookie should be cleared - calling /me should fail
        s.cookies.clear()
        r3 = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r3.status_code == 401


# ---- Cameras ----
class TestCameras:
    def test_list_unauth(self):
        r = requests.get(f"{BASE_URL}/api/cameras", timeout=15)
        assert r.status_code == 401

    def test_list_seeded(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/cameras", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 4
        names = " ".join(c["name"] for c in data)
        for code in ["CAM-01", "CAM-02", "CAM-03", "CAM-04"]:
            assert code in names

    def test_crud(self, admin_session):
        payload = {"name": "TEST_CAM", "location": "Test", "type": "mock", "status": "online"}
        r = admin_session.post(f"{BASE_URL}/api/cameras", json=payload, timeout=15)
        assert r.status_code == 200
        cam_id = r.json()["id"]
        # patch
        r2 = admin_session.patch(f"{BASE_URL}/api/cameras/{cam_id}", json={**payload, "name": "TEST_CAM_2"}, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["name"] == "TEST_CAM_2"
        # delete
        r3 = admin_session.delete(f"{BASE_URL}/api/cameras/{cam_id}", timeout=15)
        assert r3.status_code == 200
        # verify gone
        r4 = admin_session.delete(f"{BASE_URL}/api/cameras/{cam_id}", timeout=15)
        assert r4.status_code == 404


# ---- Incidents ----
class TestIncidents:
    def test_list_seeded(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/incidents", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 20
        # sorted desc
        ts = [d["detected_at"] for d in data]
        assert ts == sorted(ts, reverse=True)

    def test_create_resolve_and_notification(self, admin_session):
        cams = admin_session.get(f"{BASE_URL}/api/cameras", timeout=15).json()
        cam = cams[0]
        before = len(admin_session.get(f"{BASE_URL}/api/notifications", timeout=15).json())
        payload = {"camera_id": cam["id"], "camera_name": cam["name"], "type": "person",
                   "severity": "high", "confidence": 0.9, "description": "TEST_INC"}
        r = admin_session.post(f"{BASE_URL}/api/incidents", json=payload, timeout=15)
        assert r.status_code == 200
        inc_id = r.json()["id"]
        after = len(admin_session.get(f"{BASE_URL}/api/notifications", timeout=15).json())
        assert after >= before + 1
        r2 = admin_session.post(f"{BASE_URL}/api/incidents/{inc_id}/resolve", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["resolved"] is True


# ---- Recordings ----
class TestRecordings:
    def test_list(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/recordings", timeout=15)
        assert r.status_code == 200
        assert len(r.json()) >= 10


# ---- Notifications ----
class TestNotifications:
    def test_list_and_read_all(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/notifications", timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        if items:
            nid = items[0]["id"]
            r2 = admin_session.post(f"{BASE_URL}/api/notifications/{nid}/read", timeout=15)
            assert r2.status_code == 200
        r3 = admin_session.post(f"{BASE_URL}/api/notifications/read-all", timeout=15)
        assert r3.status_code == 200


# ---- Analytics ----
class TestAnalytics:
    def test_summary_shape(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/analytics/summary", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["total_incidents", "unresolved", "cameras_total", "cameras_online",
                  "by_severity", "by_type", "timeline_7d", "hourly"]:
            assert k in d
        assert len(d["timeline_7d"]) == 7
        assert len(d["hourly"]) == 24
        for s in ["low", "medium", "high", "critical"]:
            assert s in d["by_severity"]
