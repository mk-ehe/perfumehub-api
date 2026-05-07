from email_sender import generate_auth_token, generate_unsubscribe_token
from main import collection


def test_unsubscribe_unsub_auth_token(client):
    url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    payload = {
        "url": url,
        "email": email,
        "token": token
    }
    
    client.post("/subscribe", json=payload)

    response = client.post("/unsubscribe", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == f"Success! Your e-mail has been unsubscribed from alerts for this product."


def test_unsubscribe_unsub_token(client):
    url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    email = "kontakt.mateusz.kudas@gmail.com"
    auth_token = generate_auth_token(email)
    client.post("/subscribe", json={"url": url, "email": email, "token": auth_token})

    unsub_token = generate_unsubscribe_token(email, url)
    payload = {
        "url": url,
        "email": email,
        "token": unsub_token
    }

    response = client.post("/unsubscribe", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Success! Your e-mail has been unsubscribed from alerts for this product."


def test_unsubscribe_unsub_not_existing(client):
    url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    payload = {
        "url": url,
        "email": email,
        "token": token
    }

    client.post("/unsubscribe", json=payload)

    response = client.post("/unsubscribe", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "You were not subscribed to this fragrance."
    assert email not in collection.find_one({"url": url})["subscribers"]


def test_unsubscribe_unauthorized(client):
    url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = "fake_token_iaF2gA63GasWr1"

    payload = {
        "url": url,
        "email": email,
        "token": token
    }

    response = client.post("/unsubscribe", json=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized."


def test_unsubscribe_invalid_url(client):
    url = "https://allegro.pl/fake/perfume/path"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    payload = {
        "url": url,
        "email": email,
        "token": token
    }
    
    response = client.post("/unsubscribe", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid domain. Only official Perfumehub URLs are allowed."


def test_unsubscribe_valid_url_invalid_path(client):
    url = "https://perfumehub.pl/?cat=perfumes&sort=best-deals-desc&showPromoCodes=false&showForeignShops=false&hideDecants=false"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    payload = {
        "url": url,
        "email": email,
        "token": token
    }
    
    response = client.post("/unsubscribe", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "You were not subscribed to this fragrance."


def test_unsubscribe_malformed_url(client):
    url = "https://[::1/some-perfumes"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    payload = {
        "url": url,
        "email": email,
        "token": token
    }
    
    response = client.post("/unsubscribe", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Malformed URL provided."


def test_unsubscribe_limit_exceeded(client):
    url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    payload = {
        "url": url,
        "email": email,
        "token": token
    }

    for _ in range(3):
        response = client.post("/unsubscribe", json=payload)
        assert response.status_code == 200

    limit_exceeded = client.post("/unsubscribe", json=payload)
    assert limit_exceeded.status_code == 429
    assert "rate limit exceeded".lower() in limit_exceeded.json()["error"].lower()
