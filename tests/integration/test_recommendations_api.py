from fastapi.testclient import TestClient

from books_rec_api.services.user_service import UserService


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


def test_get_recommendations_with_custom_header(
    client: TestClient, mock_user_service: UserService
) -> None:
    from books_rec_api.dependencies.users import get_user_service
    from books_rec_api.main import app

    app.dependency_overrides[get_user_service] = lambda: mock_user_service

    # Test that the standard client without dependency overrides correctly
    # accepts the header and processes the request.
    response = client.get("/me/recommendations", headers={"X-User-Id": "real-header-user"})

    assert response.status_code == 200
    payload = response.json()
    assert "recommendations" in payload
    assert len(payload["recommendations"]) == 1
