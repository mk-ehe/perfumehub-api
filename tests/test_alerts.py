from email_sender import generate_auth_token, generate_unsubscribe_token
from time import sleep
from main import collection


def test_subscribe_added_no_scraper(client):
    test_url = "https://perfumehub.pl/no-scraper-test"
    test_email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(test_email)

    collection.delete_one({"url": test_url})
    
    collection.insert_one({
        "fragrance": "Krystian Dijor",
        "price": "100 zł",
        "url": test_url,
        "subscribers": ["random.user@gmail.com"]
    })

    payload = {
        "url": test_url,
        "email": test_email,
        "token": token
    }

    response = client.post("/subscribe", json=payload)
    
    assert response.status_code == 200
    assert response.json()["message"] == "Fragrance successfully added to your alerts!"
    
    collection.delete_one({"url": test_url})


def test_subscribe_added_w_scraper(client):
    test_url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    test_email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(test_email)

    payload = {
        "url": test_url,
        "email": test_email,
        "token": token
    }

    collection.delete_one({"url": test_url})

    response = client.post("/subscribe", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Fragrance successfully added to your alerts!"

    saved_product = collection.find_one({"url": test_url})
    assert saved_product is not None
    assert test_email in saved_product["subscribers"]
    assert "fragrance" in saved_product
    assert saved_product["price"] is not None


def test_subscribe_already_exists(client):
    test_url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    test_email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(test_email)

    payload = {
        "url": test_url,
        "email": test_email,
        "token": token
    }
    client.post("/unsubscribe", json=payload)
    client.post("/subscribe", json=payload)

    sleep(1.1)

    response = client.post("/subscribe", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "You are already subscribed to this fragrance."


def test_subscribe_unauthorized(client):
    test_url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    test_email = "kontakt.mateusz.kudas@gmail.com"
    token = "fake.mail@at.me"

    payload = {
        "url": test_url,
        "email": test_email,
        "token": token
    }

    response = client.post("/subscribe", json=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized."


def test_subscribe_invalid_url(client):
    test_url = "https://allegro.pl/fake/perfume/path"
    test_email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(test_email)

    payload = {
        "url": test_url,
        "email": test_email,
        "token": token
    }
    
    response = client.post("/subscribe", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid domain. Only official Perfumehub URLs are allowed."


def test_subscribe_valid_url_invalid_path(client):
    test_url = "https://perfumehub.pl/?cat=perfumes&sort=best-deals-desc&showPromoCodes=false&showForeignShops=false&hideDecants=false"
    test_email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(test_email)

    payload = {
        "url": test_url,
        "email": test_email,
        "token": token
    }
    
    response = client.post("/subscribe", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid URL or product not found."


def test_subscribe_malformed_url(client):
    test_url = "https://[::1/some-perfumes"
    test_email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(test_email)

    payload = {
        "url": test_url,
        "email": test_email,
        "token": token
    }
    
    response = client.post("/subscribe", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Malformed URL provided."


def test_subscribe_limit_exceeded(client):
    test_url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    test_email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(test_email)

    payload = {
        "url": test_url,
        "email": test_email,
        "token": token
    }

    response = client.post("/subscribe", json=payload)
    assert response.status_code == 200

    limit_exceeded = client.post("/subscribe", json=payload)
    assert limit_exceeded.status_code == 429
    assert "rate limit exceeded".lower() in limit_exceeded.json()["error"].lower()


def test_unsubscribe_existing(client):
    test_url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    test_email = "kontakt.mateusz.kudas@gmail.com"
    token = generate_auth_token(test_email)

    payload = {
        "url": test_url,
        "email": test_email,
        "token": token
    }
    
    client.post("/subscribe", json=payload)

    response = client.post("/unsubscribe", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == f"Success! {test_email} has been unsubscribed from alerts for this product."
