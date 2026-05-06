from email_sender import generate_auth_token, generate_unsubscribe_token
from time import sleep
from main import collection


def test_subscribe_invalid_email_format(client):
    url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    email = "invalid-email-format"
    token = "fake-token"

    payload = {
        "url": url,
        "email": email,
        "token": token
    }
    
    response = client.post("/subscribe", json=payload)
    assert response.status_code == 422


def test_subscribe_case_insensitivity(client):
    url = "https://perfumehub.pl/test-case-insensitivity"
    email = "Kontakt.Mateusz.Kudas@gmail.com"
    expected_email_in_db = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(expected_email_in_db)

    collection.delete_one({"url": url})
    collection.insert_one({
        "fragrance": "Krystian Dijor",
        "price": "100 zł",
        "url": url,
        "subscribers": ["random.user@gmail.com"]
    })

    payload = {
        "url": url,
        "email": email,
        "token": token
    }

    response = client.post("/subscribe", json=payload)
    assert response.status_code == 200

    saved_product = collection.find_one({"url": url})
    assert expected_email_in_db in saved_product["subscribers"]
    assert email not in saved_product["subscribers"]
    
    collection.delete_one({"url": url})


def test_subscribe_added_no_scraper(client):
    url = "https://perfumehub.pl/no-scraper-test"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    collection.delete_one({"url": url})
    collection.insert_one({
        "fragrance": "Krystian Dijor",
        "price": "100 zł",
        "url": url,
        "subscribers": ["random.user@gmail.com"]
    })

    payload = {
        "url": url,
        "email": email,
        "token": token
    }

    response = client.post("/subscribe", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Fragrance successfully added to your alerts!"
    
    collection.delete_one({"url": url})


def test_subscribe_added_w_scraper(client, backup_and_restore_perfume):
    url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    payload = {
        "url": url,
        "email": email,
        "token": token
    }

    collection.delete_one({"url": url})

    response = client.post("/subscribe", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Fragrance successfully added to your alerts!"

    saved_product = collection.find_one({"url": url})
    assert saved_product is not None
    assert email in saved_product["subscribers"]
    assert "fragrance" in saved_product
    assert saved_product["price"] is not None


def test_subscribe_already_exists(client):
    url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    payload = {
        "url": url,
        "email": email,
        "token": token
    }
    client.post("/unsubscribe", json=payload)
    client.post("/subscribe", json=payload)

    sleep(1.1)

    response = client.post("/subscribe", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "You are already subscribed to this fragrance."


def test_subscribe_unauthorized(client):
    url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = "fake_token_iaF2gA63GasWr1"

    payload = {
        "url": url,
        "email": email,
        "token": token
    }

    response = client.post("/subscribe", json=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized."


def test_subscribe_invalid_url(client):
    url = "https://allegro.pl/fake/perfume/path"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    payload = {
        "url": url,
        "email": email,
        "token": token
    }
    
    response = client.post("/subscribe", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid domain. Only official Perfumehub URLs are allowed."


def test_subscribe_valid_url_invalid_path(client):
    url = "https://perfumehub.pl/?cat=perfumes&sort=best-deals-desc&showPromoCodes=false&showForeignShops=false&hideDecants=false"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    payload = {
        "url": url,
        "email": email,
        "token": token
    }
    
    response = client.post("/subscribe", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid URL or product not found."


def test_subscribe_malformed_url(client):
    url = "https://[::1/some-perfumes"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    payload = {
        "url": url,
        "email": email,
        "token": token
    }
    
    response = client.post("/subscribe", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Malformed URL provided."


def test_subscribe_limit_exceeded(client):
    url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(email)

    payload = {
        "url": url,
        "email": email,
        "token": token
    }

    response = client.post("/subscribe", json=payload)
    assert response.status_code == 200

    limit_exceeded = client.post("/subscribe", json=payload)
    assert limit_exceeded.status_code == 429
    assert "rate limit exceeded".lower() in limit_exceeded.json()["error"].lower()


def test_unsubscribe_auth_token(client):
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
    assert response.json()["message"] == f"Success! {email} has been unsubscribed from alerts for this product."


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
    assert response.json()["message"] == f"Success! {email} has been unsubscribed from alerts for this product."


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
