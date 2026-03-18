from fastapi.testclient import TestClient

from services.pet_app.app import app
from services.pet_app.domain import compute_dashboard_metrics


def test_dashboard_metrics_have_expected_shape() -> None:
    metrics = compute_dashboard_metrics()
    assert metrics["gross_revenue"] > 0
    assert metrics["net_revenue"] > 0
    assert metrics["order_count"] == 6
    assert len(metrics["low_stock"]) >= 1


def test_dashboard_page_renders() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Seller Desk" in response.text
    assert "Low stock products" in response.text
