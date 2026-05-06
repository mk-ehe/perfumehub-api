import os
from unittest.mock import patch


@patch("main.process_all_prices")
def test_cron_check_success(mock_process_all_prices, client):
    correct_secret = os.getenv("CRON_SECRET", "fake_cron_secret")

    headers = {"x-cron-secret": correct_secret}
    
    response = client.post("/cron-check", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Cron check started."
    
    mock_process_all_prices.assert_called_once()


@patch("main.process_all_prices")
def test_cron_check_missing_header(mock_process_all_prices, client):
    response = client.post("/cron-check")
    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"
    
    mock_process_all_prices.assert_not_called()


@patch("main.process_all_prices")
def test_cron_check_invalid_header(mock_process_all_prices, client):
    headers = {"x-cron-secret": "fake_token"}
    
    response = client.post("/cron-check", headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"
    
    mock_process_all_prices.assert_not_called()
    