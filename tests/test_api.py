from fastapi.testclient import TestClient
from uuid import uuid4
from api.main import app
from src.data_loader import load_baseline


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"


def test_ingest_and_report(tmp_path, monkeypatch):
    monkeypatch.setenv("DATAGUARD_API_KEY", "test-key")
    path = tmp_path / "batch.csv"; load_baseline().to_csv(path, index=False)
    client = TestClient(app)
    batch_id = f"test-batch-{uuid4().hex}"
    with TestClient(app) as client:
        response = client.post("/ingest", params={"batch_id": batch_id}, headers={"X-API-Key": "test-key"}, files={"file": ("batch.csv", path.read_bytes(), "text/csv")})
        assert response.status_code == 200
        assert client.get(f"/batches/{batch_id}/report").status_code == 200


def test_protected_endpoints_reject_missing_api_key(monkeypatch):
    monkeypatch.setenv("DATAGUARD_API_KEY", "test-key")
    with TestClient(app) as client:
        assert client.post("/ingest", params={"batch_id": "unauthorized"}).status_code == 401
        assert client.post("/ingest", params={"batch_id": "unauthorized"}, headers={"X-API-Key": "wrong"}).status_code == 401
        assert client.post("/validation/run", headers={"X-API-Key": "wrong-key"}).status_code == 401
        assert client.post("/validation/run").status_code == 401
        assert client.get("/evaluation").status_code == 401
        assert client.get("/evaluation", headers={"X-API-Key": "wrong-key"}).status_code == 401


def test_evaluation_authorized(monkeypatch):
    monkeypatch.setenv("DATAGUARD_API_KEY", "test-key")
    monkeypatch.setattr("api.main.run_evaluation", lambda baseline, trials: {"overall": {"precision": 1.0, "recall": 1.0}, "trials_per_type": trials})
    with TestClient(app) as client:
        res = client.get("/evaluation", headers={"X-API-Key": "test-key"})
        assert res.status_code == 200
        assert res.json()["overall"]["precision"] == 1.0


def test_open_endpoints_do_not_require_api_key():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        batches_res = client.get("/batches")
        assert batches_res.status_code == 200
        assert "items" in batches_res.json()
        assert "total" in batches_res.json()
        alerts_res = client.get("/alerts")
        assert alerts_res.status_code == 200
        assert "items" in alerts_res.json()
        assert "total" in alerts_res.json()


def test_pagination_batches_and_alerts():
    with TestClient(app) as client:
        batches_resp = client.get("/batches?limit=10&offset=0")
        assert batches_resp.status_code == 200
        data = batches_resp.json()
        assert "items" in data
        assert "total" in data
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert isinstance(data["items"], list)

        alerts_resp = client.get("/alerts?limit=5&offset=0")
        assert alerts_resp.status_code == 200
        alerts_data = alerts_resp.json()
        assert "items" in alerts_data
        assert "total" in alerts_data
        assert alerts_data["limit"] == 5
        assert alerts_data["offset"] == 0
        assert isinstance(alerts_data["items"], list)


def test_prometheus_metrics():
    with TestClient(app) as client:
        res = client.get("/metrics")
        assert res.status_code == 200
        text = res.text
        # Check custom gauge and counter are registered
        assert "dataguard_drift_score" in text
        assert "dataguard_alerts_total" in text
        # Check prometheus-fastapi-instrumentator metrics are present
        assert "http_request" in text or "http_requests" in text


def test_structured_logging_formatter():
    import json
    import logging
    from api.main import StructuredFormatter

    formatter = StructuredFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.batch_id = "test-batch-123"
    record.severity = "High"

    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["message"] == "Test message"
    assert parsed["level"] == "INFO"
    assert parsed["batch_id"] == "test-batch-123"
    assert parsed["severity"] == "High"
    assert "timestamp" in parsed


