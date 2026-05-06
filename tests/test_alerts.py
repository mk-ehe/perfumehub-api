from unittest.mock import patch
from main import collection, generate_auth_token


@patch("main.send_auth_email")
def test_request_access_link_sent(mock_send_email, client):
    payload = {"email": "kontakt.matuesz.kudas@gmail.com"}

    response = client.post("/request-access", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Access link has been sent to your e-mail."

    mock_send_email.assert_called_once()
    

def test_request_access_missing_email(client):
    payload = {}

    response = client.post("/request-access", json=payload)
    assert response.status_code == 422


def test_request_access_invalid_email(client):
    payload = {"email": "invalid-email-format"}
    
    response = client.post("/request-access", json=payload)
    assert response.status_code == 422


@patch("main.send_auth_email")
def test_request_access_limit_exceeded(mock_send_email, client):
    payload = {
        "email": "kontakt.matuesz.kudas@gmail.com"
    }

    response = client.post("/request-access", json=payload)
    response.status_code == 200

    limit_exceeded = client.post("/request-access", json=payload)
    assert limit_exceeded.status_code == 429
    assert "rate limit exceeded".lower() in limit_exceeded.json()["error"].lower()




def test_get_my_alerts_success_and_sorted(client):
    email = "alerts.test@gmail.com"
    token = generate_auth_token(email)
    params = {"email": email, "token": token}

    collection.delete_many({"subscribers": email})
    
    collection.insert_many([
        {
            "fragrance": "Zebra",
            "price": "200 zł",
            "url": "https://perfumehub.pl/zebra",
            "picture": "zebra.png",
            "low_30d": "150 zł",
            "shop": {"name": "Notino"},
            "subscribers": [email, "other.email@gmail.com"]
        },
        {
            "fragrance": "Aventus",
            "price": "100 zł",
            "url": "https://perfumehub.pl/aventus",
            "picture": "aventus.png",
            "low_30d": "90 zł",
            "shop": {"name": "Sephora"},
            "subscribers": [email]
        }
    ])

    response = client.get(f"/my-alerts", params=params)
    assert response.status_code == 200

    alerts = response.json()["alerts"]
    assert len(alerts) == 2
    
    assert alerts[0]["fragrance"] == "Aventus"
    assert alerts[1]["fragrance"] == "Zebra"

    assert "subscribers" not in alerts[0]
    assert "shop" not in alerts[0]
    assert "price" in alerts[0]

    collection.delete_many({"subscribers": email})


def test_get_my_alerts_empty_list(client):
    email = "empty.alerts@gmail.com"
    token = generate_auth_token(email)
    params = {"email": email, "token": token}

    collection.delete_many({"subscribers": email})

    response = client.get(f"/my-alerts", params=params)
    assert response.status_code == 200
    assert response.json()["alerts"] == []


def test_get_my_alerts_unauthorized(client):
    email = "unauthorized.alerts@gmail.com"
    wrong_token = "fake_token"
    params = {"email": email, "token": wrong_token}

    response = client.get(f"/my-alerts", params=params)

    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized."


def test_get_my_alerts_missing_parameters(client):
    response = client.get("/my-alerts")
    assert response.status_code == 422


def test_get_my_alerts_rate_limit(client):
    email = "limit.alerts@gmail.com"
    token = generate_auth_token(email)
    params = {"email": email, "token": token}

    for _ in range(30):
        res = client.get("/my-alerts", params=params)
        assert res.status_code == 200

    limit_exceeded = client.get("/my-alerts", params=params)
    assert limit_exceeded.status_code == 429
    assert "rate limit exceeded".lower() in limit_exceeded.json()["error"].lower()
    