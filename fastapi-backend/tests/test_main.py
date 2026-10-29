from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"Hello": "World"}


def test_read_item_without_query():
    r = client.get("/items/5")
    assert r.status_code == 200
    assert r.json() == {"item_id": 5, "q": None}


def test_read_item_with_query():
    r = client.get("/items/5", params={"q": "hi"})
    assert r.json() == {"item_id": 5, "q": "hi"}


def test_item_id_must_be_an_integer():
    assert client.get("/items/abc").status_code == 422


def test_item_id_must_be_positive():
    assert client.get("/items/0").status_code == 422
    assert client.get("/items/-1").status_code == 422


def test_item_id_upper_bound():
    assert client.get(f"/items/{2**31 - 1}").status_code == 200
    assert client.get(f"/items/{2**31}").status_code == 422


def test_query_length_limit():
    assert client.get("/items/1", params={"q": "a" * 100}).status_code == 200
    assert client.get("/items/1", params={"q": "a" * 101}).status_code == 422


def test_cors_allows_local_frontend():
    r = client.get("/", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_rejects_unknown_origin():
    r = client.get("/", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers
