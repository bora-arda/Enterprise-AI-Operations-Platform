"""Integration tests for API endpoints, including authentication and RBAC."""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from procurement_ai.auth.security import hash_password
from procurement_ai.main import app

DEMO_PASSWORD = "demo123"
DEMO_USERS = [
    ("specialist@example.com", "Alice Specialist", "specialist"),
    ("manager@example.com", "Maya Manager", "manager"),
    ("finance@example.com", "Frank Finance", "finance"),
    ("director@example.com", "Diana Director", "director"),
    ("admin@example.com", "Adam Admin", "admin"),
]


def _sync_db_url() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/procurement")
    return url.replace("+asyncpg", "+psycopg2")


@pytest.fixture(scope="module")
def seeded_users():
    """Create/update demo users directly in the database."""
    engine = create_engine(_sync_db_url())
    password_hash = hash_password(DEMO_PASSWORD)
    users: dict[str, str] = {}

    with engine.begin() as conn:
        for email, name, role in DEMO_USERS:
            row = conn.execute(
                text(
                    """
                    INSERT INTO users (id, name, email, password_hash, role, created_at)
                    VALUES (:id, :name, :email, :password_hash, :role, now())
                    ON CONFLICT (email) DO UPDATE
                    SET name = EXCLUDED.name,
                        password_hash = EXCLUDED.password_hash,
                        role = EXCLUDED.role
                    RETURNING id
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "name": name,
                    "email": email,
                    "password_hash": password_hash,
                    "role": role,
                },
            ).fetchone()
            users[email] = str(row[0])

    return users


def _insert_approval(requested_by: str, request_type: str = "invoice_approval") -> str:
    engine = create_engine(_sync_db_url())
    approval_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO approval_requests
                    (id, approval_number, request_type, requested_by, status,
                     justification, requested_at, created_at)
                VALUES
                    (:id, :number, :request_type, :requested_by, 'pending',
                     'integration test approval', now(), now())
                """
            ),
            {
                "id": approval_id,
                "number": f"APPR-TEST-{approval_id.hex[:8].upper()}",
                "request_type": request_type,
                "requested_by": uuid.UUID(requested_by),
            },
        )
    return str(approval_id)


class TestAPI:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client, seeded_users):
        def _login(email: str) -> dict[str, str]:
            response = client.post(
                "/auth/login",
                json={"email": email, "password": DEMO_PASSWORD},
            )
            assert response.status_code == 200, response.text
            return {"Authorization": f"Bearer {response.json()['access_token']}"}

        return _login

    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "name" in response.json()

    def test_chat_requires_auth(self, client):
        response = client.post("/chat", json={"message": "hello"})
        assert response.status_code == 401

    def test_login_and_me(self, client, auth_headers):
        headers = auth_headers("manager@example.com")
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["role"] == "manager"

    def test_login_invalid_password(self, client, seeded_users):
        response = client.post(
            "/auth/login",
            json={"email": "manager@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_chat_endpoint(self, client, auth_headers):
        headers = auth_headers("specialist@example.com")
        response = client.post(
            "/chat",
            headers=headers,
            json={"message": "What is the status of invoice INV-001?"},
        )
        assert response.status_code == 200
        assert "response" in response.json()

    def test_chat_validation_error(self, client, auth_headers):
        headers = auth_headers("specialist@example.com")
        response = client.post("/chat", headers=headers, json={"message": ""})
        assert response.status_code == 422

    def test_anomalies_endpoint(self, client, auth_headers):
        headers = auth_headers("specialist@example.com")
        response = client.get("/anomalies", headers=headers)
        assert response.status_code == 200
        assert "anomalies" in response.json()

    def test_approvals_endpoint(self, client, auth_headers):
        headers = auth_headers("specialist@example.com")
        response = client.get("/approvals", headers=headers)
        assert response.status_code == 200
        assert "approvals" in response.json()

    def test_metrics_endpoint(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "agent_requests_total" in response.text

    def test_specialist_cannot_decide_approval(self, client, auth_headers):
        headers = auth_headers("specialist@example.com")
        response = client.post(
            f"/approvals/{uuid.uuid4()}/decide",
            headers=headers,
            json={"decision": "reject"},
        )
        assert response.status_code == 403

    def test_manager_cannot_self_approve(self, client, auth_headers, seeded_users):
        headers = auth_headers("manager@example.com")
        approval_id = _insert_approval(seeded_users["manager@example.com"])

        response = client.post(
            f"/approvals/{approval_id}/decide",
            headers=headers,
            json={"decision": "reject"},
        )
        assert response.status_code == 403
        assert "cannot decide" in response.json()["detail"].lower()

    def test_manager_can_reject_other_request(self, client, auth_headers, seeded_users):
        headers = auth_headers("manager@example.com")
        approval_id = _insert_approval(seeded_users["specialist@example.com"])

        response = client.post(
            f"/approvals/{approval_id}/decide",
            headers=headers,
            json={"decision": "reject", "comment": "integration test"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    def test_specialist_cannot_view_decisions(self, client, auth_headers):
        headers = auth_headers("specialist@example.com")
        response = client.get("/decisions", headers=headers)
        assert response.status_code == 403

    def test_planner_decision_audit(self, client, auth_headers):
        headers = auth_headers("manager@example.com")
        session_id = "test-decision-audit"
        response = client.post(
            "/chat",
            headers=headers,
            json={
                "message": "Show me PO-000001",
                "session_id": session_id,
            },
        )
        assert response.status_code == 200
        decision_id = response.json().get("decision_id")
        assert decision_id

        listing = client.get(f"/decisions?session_id={session_id}", headers=headers)
        assert listing.status_code == 200
        data = listing.json()
        assert data["total"] >= 1
        decision = data["decisions"][0]
        assert decision["planner_mode"] == "deterministic"
        assert decision["question"] == "Show me PO-000001"
        assert decision["workflow"] == "retrieval"

    def test_decisions_filter_validation(self, client, auth_headers):
        headers = auth_headers("manager@example.com")
        response = client.get("/decisions?planner_mode=invalid", headers=headers)
        assert response.status_code == 422
