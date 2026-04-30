from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_ping():
    response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ping_limit_exceeded():
    app.state.limiter.reset()

    for _ in range(20):
        response = client.get("/ping")
        assert response.status_code == 200

    limit_exceeded = client.get("/ping")
    assert limit_exceeded.status_code == 429
    assert "rate limit exceeded" in limit_exceeded.json()["error"].lower()


def test_guide():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["author"] == "mk-ehe"
    assert "routes" in response.json()