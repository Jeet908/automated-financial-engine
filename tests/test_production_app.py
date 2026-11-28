from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_production_portal_is_served():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Make the numbers easier to act on." in response.text
    assert 'id="btn-live-scrape"' in response.text


def test_health_reports_service_status_without_claiming_an_unrun_audit():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "online"
    assert payload["domains_supported"]
    assert "accounting_invariants" not in payload
