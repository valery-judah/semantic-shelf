from fastapi.testclient import TestClient


def test_get_recommendations_returns_expected_shape(
    client_with_overrides: TestClient,
) -> None:
    response = client_with_overrides.get("/me/recommendations")

    assert response.status_code == 200
    payload = response.json()

    assert "recommendations" in payload
    assert len(payload["recommendations"]) == 1

    recommendation = payload["recommendations"][0]
    assert recommendation["book_id"] == "123"
    assert recommendation["reason"] == "popular_in_sci_fi"
    assert recommendation["book"]["title"] == "Dune"
