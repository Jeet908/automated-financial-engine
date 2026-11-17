import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import app
from src.portal import auth, database, jobs
from src.portal.database import Job, User, utc_now
from src.portal.plans import reserve_job
from src.portal.security import hash_password


@pytest.fixture
def client(tmp_path, monkeypatch):
    database.configure_database(f"sqlite:///{(tmp_path / 'marketlens-test.sqlite3').as_posix()}")
    database.init_database()
    monkeypatch.setattr(jobs, "DATA_DIR", tmp_path / "private-data")
    monkeypatch.setenv("PUBLIC_APP_URL", "https://marketlens.example")
    monkeypatch.setattr(auth, "email_delivery_configured", lambda: True)
    monkeypatch.setattr(auth, "send_email", lambda *_args, **_kwargs: None)
    with TestClient(app) as test_client:
        yield test_client


def register_and_sign_in(client: TestClient, email: str) -> tuple[str, str]:
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Long-enough-password-742!",
            "accepted_terms": True,
        },
    )
    assert registration.status_code == 202

    with database.SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        user.email_verified = True
        db.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Long-enough-password-742!"},
    )
    assert login.status_code == 200
    return login.json()["csrf_token"], login.json()["user"]["id"]


def test_registration_requires_terms_and_password_strength(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "short", "accepted_terms": False},
    )
    assert response.status_code == 422


def test_monthly_free_quota_is_reserved_atomically(client):
    _, user_id = register_and_sign_in(client, "quota@example.com")
    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        first = reserve_job(db, user, "live_scrape", Path("private/job-one"))
        assert first.status == "pending"
        with pytest.raises(HTTPException) as error:
            reserve_job(db, user, "file_upload", Path("private/job-two"))
    assert error.value.status_code == 429


def test_reports_are_private_and_not_mounted_as_public_static_files(client, tmp_path):
    _, user_id = register_and_sign_in(client, "owner@example.com")
    workspace = tmp_path / "accounts" / user_id / "jobs" / "report"
    workspace.mkdir(parents=True)
    report_path = workspace / "model.txt"
    report_path.write_text("owner-only", encoding="utf-8")
    job_id = "private-report-job"
    with database.SessionLocal() as db:
        db.add(
            Job(
                id=job_id,
                user_id=user_id,
                kind="file_upload",
                status="succeeded",
                workspace_path=str(workspace),
                result_json=json.dumps(
                    {
                        "files": {"zip_pack": f"/api/v1/jobs/{job_id}/files/zip_pack"},
                        "_private_files": {"zip_pack": str(report_path)},
                    }
                ),
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        db.commit()

    response = client.get(f"/api/v1/jobs/{job_id}/files/zip_pack")
    assert response.status_code == 200
    assert response.content == b"owner-only"
    assert response.headers["cache-control"] == "private, no-store"
    assert client.get("/client_outbox/model.txt").status_code == 404
    assert client.get("/artifacts/model.html").status_code == 404

    other = TestClient(app)
    with database.SessionLocal() as db:
        second_user = User(
            email="other@example.com",
            password_hash=hash_password("Long-enough-password-881!"),
            email_verified=True,
        )
        db.add(second_user)
        db.commit()
        second_email = second_user.email
    assert other.post(
        "/api/v1/auth/login",
        json={"email": second_email, "password": "Long-enough-password-881!"},
    ).status_code == 200
    assert other.get(f"/api/v1/jobs/{job_id}/files/zip_pack").status_code == 404
    assert other.get("/api/v1/jobs").json()["jobs"] == []


def test_model_endpoints_require_verified_session_and_csrf(client):
    unauthenticated = client.post(
        "/api/v1/model/live-scrape",
        json={"domain": "Any Random Domain", "market": "random"},
    )
    assert unauthenticated.status_code == 401

    csrf, _ = register_and_sign_in(client, "csrf@example.com")
    missing_token = client.post(
        "/api/v1/model/live-scrape",
        json={"domain": "Any Random Domain", "market": "random"},
    )
    assert missing_token.status_code == 403
    assert client.cookies.get("marketlens_csrf") == csrf


def test_upload_job_completes_and_serves_private_pack(client, monkeypatch):
    csrf, _ = register_and_sign_in(client, "upload@example.com")

    def fake_process_file(file_path: str, output_dir: str) -> dict[str, str]:
        output = Path(output_dir)
        output.mkdir(parents=True)
        pack_path = output / "result.zip"
        pack_path.write_bytes(Path(file_path).read_bytes())
        return {"zip_path": str(pack_path)}

    monkeypatch.setattr(jobs, "process_file", fake_process_file)
    response = client.post(
        "/api/v1/model/generate-pack",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("sample.xlsx", b"workbook-data", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    result = client.get(f"/api/v1/jobs/{job_id}")
    assert result.status_code == 200
    assert result.json()["status"] == "succeeded"
    assert result.json()["result"]["company"]["name"] == "sample.xlsx"
    pack = client.get(f"/api/v1/jobs/{job_id}/files/zip_pack")
    assert pack.status_code == 200
    assert pack.content == b"workbook-data"
    history = client.get("/api/v1/jobs")
    assert history.status_code == 200
    assert history.json()["jobs"][0]["company"] == "sample.xlsx"


def test_public_plans_and_health_are_non_sensitive(client):
    plans = client.get("/api/v1/billing/plans")
    assert plans.status_code == 200
    by_key = {plan["key"]: plan for plan in plans.json()["plans"]}
    assert by_key["free"]["monthly_valuations"] == 1
    assert by_key["pro"]["price_paise"] == 149900
    assert by_key["business"]["monthly_valuations"] == 100

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "online"
    assert "DATABASE_URL" not in health.text


def test_invalid_razorpay_webhook_signature_is_rejected(client, monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "test-webhook-secret")
    response = client.post(
        "/api/v1/billing/webhook",
        content='{"event":"subscription.activated"}',
        headers={"X-Razorpay-Signature": "invalid"},
    )
    assert response.status_code == 400
