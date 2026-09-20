from pathlib import Path

from fastapi.testclient import TestClient

import backend.main as main_module
from backend.config import ROOT, Settings
from backend.main import create_app


def test_authenticated_regular_user_gets_false_and_no_admin_insights(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(main_module, "initialize_firebase", lambda: None)
    monkeypatch.setattr("firebase_admin.auth.verify_id_token", lambda _token: {"uid": "regular-user"})
    settings = Settings(
        "mock", ("http://localhost:5173",), tmp_path / "admin.sqlite3",
        ROOT / "data" / "catalog" / "combined", 8, ("company-user",),
    )
    client = TestClient(create_app(settings))
    headers = {"Authorization": "Bearer regular-token"}

    assert client.get("/api/v1/admin/status", headers=headers).json() == {"is_admin": False}
    assert client.get("/api/v1/admin/insights", headers=headers).status_code == 403


def test_admin_status_accepts_configured_uid(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(main_module, "initialize_firebase", lambda: None)
    monkeypatch.setattr("firebase_admin.auth.verify_id_token", lambda _token: {"uid": "company-user"})
    settings = Settings(
        "mock", ("http://localhost:5173",), tmp_path / "admin.sqlite3",
        ROOT / "data" / "catalog" / "combined", 8, ("company-user",),
    )
    client = TestClient(create_app(settings))

    assert client.get(
        "/api/v1/admin/status", headers={"Authorization": "Bearer company-token"}
    ).json() == {"is_admin": True}
