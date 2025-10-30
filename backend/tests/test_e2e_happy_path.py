import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

os.environ["BEDROCK_MOCK"] = "1"

client = TestClient(app)


def test_chat_happy_path():
    # Ensure health
    r = client.get("/healthz")
    assert r.status_code == 200

    # Send a question
    r = client.post("/chat", json={"message": "Show sales by region over time"})
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "sql" in data
    viz = data.get("viz")
    assert viz is not None
    assert viz.get("type") in ("line", "bar", "table")

