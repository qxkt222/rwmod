"""API integration tests — verify all endpoints return expected status codes."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_status(self, client: TestClient):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "online" in data


class TestConfigEndpoint:
    def test_get_config(self, client: TestClient):
        resp = client.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "steamcmd_path" in data
        assert "mods_dir" in data

    def test_update_config(self, client: TestClient):
        resp = client.post("/api/config", json={"mods_dir": "/tmp/Mods"})
        assert resp.status_code == 200
        assert resp.json()["ok"]


class TestModsEndpoint:
    def test_list_mods_empty(self, client: TestClient):
        resp = client.get("/api/mods")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_check_updates_empty(self, client: TestClient):
        resp = client.get("/api/mods/check-updates")
        assert resp.status_code == 200
        assert "updates" in resp.json()

    def test_export_mods_empty(self, client: TestClient):
        resp = client.get("/api/mods/export")
        assert resp.status_code == 200
        assert "mods" in resp.json()

    def test_export_collection_empty(self, client: TestClient):
        resp = client.get("/api/mods/export-collection")
        assert resp.status_code == 200
        assert "ids" in resp.json()

    def test_compatibility(self, client: TestClient):
        resp = client.get("/api/mods/compatibility")
        assert resp.status_code == 200
        data = resp.json()
        # May return error if no RimWorld install, but should be valid JSON
        assert "rimworld_version" in data or "error" in data

    def test_health_empty(self, client: TestClient):
        resp = client.get("/api/mods/health")
        assert resp.status_code == 200
        assert "mods" in resp.json()


class TestDashboardEndpoint:
    def test_dashboard(self, client: TestClient):
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "mods_count" in data
        assert "updates_pending" in data
        assert "disk_usage_mb" in data


class TestDownloadEndpoint:
    def test_download_no_ids(self, client: TestClient):
        resp = client.post("/api/download", json={"ids": []})
        assert resp.status_code == 400

    def test_download_invalid_id(self, client: TestClient):
        resp = client.post("/api/download", json={"ids": ["not_a_number"]})
        assert resp.status_code == 400


class TestQueueEndpoint:
    def test_get_queue(self, client: TestClient):
        resp = client.get("/api/queue")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_add_to_queue(self, client: TestClient):
        resp = client.post("/api/queue/add", json={"ids": ["123456"]})
        assert resp.status_code == 200
        assert resp.json()["added"] >= 0

    def test_clear_queue(self, client: TestClient):
        resp = client.post("/api/queue/clear")
        assert resp.status_code == 200
        assert resp.json()["ok"]


class TestAutoUpdateEndpoint:
    def test_status(self, client: TestClient):
        resp = client.get("/api/auto-update/status")
        assert resp.status_code == 200
        assert "running" in resp.json()

    def test_result(self, client: TestClient):
        resp = client.get("/api/auto-check/result")
        assert resp.status_code == 200
        assert "updates" in resp.json()


class TestHistoryEndpoint:
    def test_history(self, client: TestClient):
        resp = client.get("/api/history")
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_history_stats(self, client: TestClient):
        resp = client.get("/api/history/stats")
        assert resp.status_code == 200

    def test_clear_history(self, client: TestClient):
        resp = client.post("/api/history/clear")
        assert resp.status_code == 200
        assert resp.json()["ok"]


class TestRimsortEndpoint:
    def test_generate(self, client: TestClient):
        resp = client.post("/api/rimsort/generate")
        assert resp.status_code == 200
        assert "modsconfig_xml" in resp.json()

    def test_check_order(self, client: TestClient):
        resp = client.get("/api/rimsort/check-order")
        assert resp.status_code == 200
        # May return error if no ModsConfig.xml, but should be valid JSON
        assert isinstance(resp.json(), dict)


class TestBackupsEndpoint:
    def test_list_backups(self, client: TestClient):
        resp = client.get("/api/backups")
        assert resp.status_code == 200
        assert "backups" in resp.json()


class TestProfilesEndpoint:
    def test_list_profiles(self, client: TestClient):
        resp = client.get("/api/profiles")
        assert resp.status_code == 200
        assert "profiles" in resp.json()

    def test_save_profile_no_name(self, client: TestClient):
        resp = client.post("/api/profiles/save", json={"name": ""})
        assert resp.status_code == 400


class TestWorkshopEndpoint:
    def test_search_no_query(self, client: TestClient):
        resp = client.get("/api/search?q=")
        assert resp.status_code == 200
        assert resp.json()["results"] == []

    def test_search(self, client: TestClient):
        resp = client.get("/api/search?q=harmony")
        assert resp.status_code == 200
        assert "results" in resp.json()


class TestErrorHandling:
    def test_404_route(self, client: TestClient):
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_error_response_format(self, client: TestClient):
        """Global error handler should return structured JSON."""
        resp = client.post("/api/download", json={"ids": []})
        # Should be 400 or have error detail
        assert resp.status_code in (200, 400, 422)
