import pytest
from fastapi.testclient import TestClient
from main import app, collection


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    app.state.limiter.reset()


@pytest.fixture
def backup_and_restore_perfume():
    url = "https://perfumehub.pl/versace-eros-woda-perfumowana-dla-mezczyzn-200-ml"
    
    existing_document = collection.find_one({"url": url})
    
    yield 
    
    collection.delete_one({"url": url})
    
    if existing_document:
        collection.insert_one(existing_document)
    