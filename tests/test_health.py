def test_guide(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["author"] == "mk-ehe"
    assert "routes" in response.json()


def test_ping(client):
    response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ping_limit_exceeded(client):
    for _ in range(20):
        response = client.get("/ping")
        assert response.status_code == 200

    limit_exceeded = client.get("/ping")
    assert limit_exceeded.status_code == 429
    assert "rate limit exceeded" in limit_exceeded.json()["error"].lower()
