from fastapi.testclient import TestClient

from books_rec_api.main import app


def test_get_recommendations_returns_expected_shape() -> None:
    client = TestClient(app)

    response = client.get("/me/recommendations")

    assert response.status_code == 200
    payload = response.json()

    assert "recommendations" in payload
    assert len(payload["recommendations"]) == 1

    recommendation = payload["recommendations"][0]
    assert recommendation["book_id"] == "123"
    assert recommendation["reason"] == "popular_in_sci_fi"
    assert recommendation["book"]["title"] == "Dune"
