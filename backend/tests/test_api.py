"""End-to-end coverage for the tenant-aware API slice."""
from fastapi.testclient import TestClient


def test_registration_and_assistant_access_are_workspace_scoped(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    # Import after configuring the isolated test database.
    from app.main import app
    from app.database import Base, engine
    Base.metadata.create_all(engine)

    with TestClient(app) as client:
        registration = client.post("/api/v1/auth/register", json={
            "email": "owner@acme.example", "full_name": "Jordan Doe", "password": "correct-horse-battery-staple", "workspace_name": "Acme Inc",
        })
        assert registration.status_code == 201
        token = registration.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        workspaces = client.get("/api/v1/workspaces", headers=auth_headers)
        assert workspaces.status_code == 200
        workspace_id = workspaces.json()[0]["id"]
        tenant_headers = auth_headers | {"X-Workspace-Id": workspace_id}

        created = client.post("/api/v1/assistants", headers=tenant_headers, json={
            "name": "Aria", "role": "Executive Assistant", "department": "Leadership", "status": "active", "capabilities": ["Briefings"],
        })
        assert created.status_code == 201
        assert created.json()["workspace_id"] == workspace_id

        listing = client.get("/api/v1/assistants", headers=tenant_headers)
        assert listing.status_code == 200
        assert [assistant["name"] for assistant in listing.json()] == ["Aria"]
        assert client.get("/api/v1/assistants").status_code == 401
