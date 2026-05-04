def test_search(client):
    params = {"url": "https://perfumehub.pl/dior-sauvage-woda-toaletowa-dla-mezczyzn-100-ml"}
    response = client.get("/search", params=params)

    data = response.json()

    assert response.status_code == 200
    assert "subscribers" not in data
    assert "_id" not in data
    assert data["url"] != ""
    assert data["fragrance"] != ""


def test_search_invalid_domain(client):
    wrong_params = {"url": "https://allegro.pl/dior/sauvage"}
    response = client.get("/search", params=wrong_params)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid domain. Only official Perfumehub URLs are allowed."


def test_search_malformed_url(client):
    wrong_params = {"url": "https://[::1/some-perfumes"}
    response = client.get("/search", params=wrong_params)

    assert response.status_code == 400
    assert response.json()["detail"] == "Malformed URL provided."


def test_search_bad_path(client):
    wrong_params = {"url": "https://perfumehub.pl/fake/perfume/path"}
    response = client.get("/search", params=wrong_params)

    assert response.status_code == 500
    assert response.json()["detail"] == "An error occurred while fetching the price."


def test_search_valid_url_invalid_path(client):
    wrong_params = {"url": "https://perfumehub.pl/?cat=perfumes&sort=best-deals-desc&showPromoCodes=false&showForeignShops=false&hideDecants=false"}
    response = client.get("/search", params=wrong_params)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid URL or product not found."


def test_search_no_url(client):
    wrong_params = {"url": ""}
    response = client.get("/search", params=wrong_params)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid domain. Only official Perfumehub URLs are allowed."


def test_search_limit_exceeded(client):
    params = {"url": "https://perfumehub.pl/dior-sauvage-woda-toaletowa-dla-mezczyzn-100-ml"}
    response = client.get("/search", params=params)
    assert response.status_code == 200

    limit_exceeded = client.get("/search", params=params)
    assert limit_exceeded.status_code == 429
    assert "rate limit exceeded".lower() in limit_exceeded.json()["error"].lower()
