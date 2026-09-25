"""End-to-end coverage for the tenant-aware API slice."""
from fastapi.testclient import TestClient


def test_registration_and_assistant_access_are_workspace_scoped(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("JWT_SECRET", "test-only-secret-that-is-longer-than-thirty-two-characters")

    # Import after configuring the isolated test database.
    from app.main import app
    from app.database import Base, SessionLocal, engine
    from app import knowledge_processing, routers
    from app.models import TaskMessage, WorkTask
    monkeypatch.setattr(routers, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(knowledge_processing, "UPLOAD_DIR", tmp_path / "uploads")
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
            "name": "Aria", "role": "Data Analyst", "department": "data", "role_template_id": "data-analyst", "status": "active", "access_level": "admins_only", "capabilities": [],
        })
        assert created.status_code == 201
        assert created.json()["workspace_id"] == workspace_id
        assert created.json()["department"] == "Data & Analytics"
        assistant_id = created.json()["id"]

        updated = client.patch(f"/api/v1/assistants/{assistant_id}", headers=tenant_headers, json={
            "name": "Aria", "department": "data", "role_template_id": "data-analyst", "status": "draft", "access_level": "admins_only", "instructions": "Escalate uncertain analysis.",
        })
        assert updated.status_code == 200
        assert updated.json()["status"] == "draft"
        assert updated.json()["instructions"] == "Escalate uncertain analysis."

        reactivated = client.patch(f"/api/v1/assistants/{assistant_id}", headers=tenant_headers, json={
            "name": "Aria", "department": "data", "role_template_id": "data-analyst", "status": "active", "access_level": "admins_only", "instructions": "Escalate uncertain analysis.",
        })
        assert reactivated.status_code == 200

        def complete_task(task_id: str):
            with SessionLocal() as task_session:
                task = task_session.get(WorkTask, task_id)
                task.status = "awaiting_review"
                task.stage = "Ready for supervisor review"
                task.progress = 90
                task.result = "Grounded analysis result"
                task_session.add(TaskMessage(task_id=task.id, workspace_id=task.workspace_id, author_type="assistant", author_name="Aria", kind="result", content=task.result))
                task_session.commit()

        monkeypatch.setattr(routers, "process_work_task", complete_task)
        assigned = client.post("/api/v1/work/tasks", headers=tenant_headers, json={
            "assistant_id": assistant_id, "title": "Analyse monthly costs", "instructions": "Review the monthly costs and explain the largest changes.", "expected_output": "A concise management summary", "priority": "high",
        })
        assert assigned.status_code == 201
        task_id = assigned.json()["id"]
        assert client.get("/api/v1/work/tasks", headers=tenant_headers).json()[0]["status"] == "awaiting_review"
        task_messages = client.get(f"/api/v1/work/tasks/{task_id}/messages", headers=tenant_headers)
        assert task_messages.status_code == 200
        assert len(task_messages.json()) == 3
        comment = client.post(f"/api/v1/work/tasks/{task_id}/messages", headers=tenant_headers, json={"content": "Please confirm the figures."})
        assert comment.status_code == 201
        approved = client.post(f"/api/v1/work/tasks/{task_id}/approve", headers=tenant_headers)
        assert approved.status_code == 200
        assert approved.json()["status"] == "completed"
        assert approved.json()["progress"] == 100

        listing = client.get("/api/v1/assistants", headers=tenant_headers)
        assert listing.status_code == 200
        assert [assistant["name"] for assistant in listing.json()] == ["Aria"]
        assert client.get("/api/v1/assistants").status_code == 401

        mismatch = client.post("/api/v1/assistants", headers=tenant_headers, json={
            "name": "Wrong role", "role": "Data Analyst", "department": "sales", "role_template_id": "data-analyst", "status": "draft", "access_level": "admins_only", "capabilities": [],
        })
        assert mismatch.status_code == 422

        uploaded = client.post(
            f"/api/v1/assistants/{assistant_id}/knowledge",
            headers=tenant_headers,
            files={"file": ("handbook.txt", b"Approved company process", "text/plain")},
        )
        assert uploaded.status_code == 201
        assert uploaded.json()["status"] == "queued"
        assert "review" in uploaded.json()["feedback"].lower()
        processed = client.get(f"/api/v1/assistants/{assistant_id}/knowledge", headers=tenant_headers)
        assert processed.status_code == 200
        assert processed.json()[0]["status"] == "ready"
        assert processed.json()[0]["progress"] == 100
        assert processed.json()[0]["chunk_count"] >= 1
        assert "training complete" in processed.json()[0]["feedback"].lower()

        disguised_file = client.post(
            f"/api/v1/assistants/{assistant_id}/knowledge",
            headers=tenant_headers,
            files={"file": ("malware.pdf", b"not a pdf", "application/octet-stream")},
        )
        assert disguised_file.status_code == 415

        spoofed_pdf = client.post(
            f"/api/v1/assistants/{assistant_id}/knowledge",
            headers=tenant_headers,
            files={"file": ("malware.pdf", b"not actually a pdf", "application/pdf")},
        )
        assert spoofed_pdf.status_code == 415

        other_registration = client.post("/api/v1/auth/register", json={
            "email": "owner@other.example", "full_name": "Other Owner", "password": "another-correct-horse-password", "workspace_name": "Other Inc",
        })
        other_auth = {"Authorization": f"Bearer {other_registration.json()['access_token']}"}
        other_workspace_id = client.get("/api/v1/workspaces", headers=other_auth).json()[0]["id"]
        other_headers = other_auth | {"X-Workspace-Id": other_workspace_id}
        assert client.get(f"/api/v1/work/tasks/{task_id}/messages", headers=other_headers).status_code == 404
        added_member = client.post("/api/v1/members", headers=tenant_headers, json={"email": "owner@other.example", "role": "member"})
        assert added_member.status_code == 201
        employee_company_headers = other_auth | {"X-Workspace-Id": workspace_id}
        assert client.get("/api/v1/work/tasks", headers=employee_company_headers).status_code == 200
        assert client.post("/api/v1/members", headers=employee_company_headers, json={"email": "nobody@example.com", "role": "admin"}).status_code == 403
        assert client.get(f"/api/v1/assistants/{assistant_id}/knowledge", headers=other_headers).status_code == 404
        assert client.patch(f"/api/v1/assistants/{assistant_id}", headers=other_headers, json={
            "name": "Stolen", "department": "data", "role_template_id": "data-analyst", "status": "active", "access_level": "workspace", "instructions": None,
        }).status_code == 404
