from fastapi.testclient import TestClient

from api.main import app


def test_team_members_require_session():
    client = TestClient(app)
    response = client.get("/api/v1/crm/team/members")
    assert response.status_code == 401
    assert "session" in response.json()["detail"].lower()


def test_team_invite_requires_session():
    client = TestClient(app)
    response = client.post("/api/v1/crm/team/members", json={"email": "va@example.com"})
    assert response.status_code == 401
