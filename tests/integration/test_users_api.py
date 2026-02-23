from fastapi.testclient import TestClient


def test_get_me_returns_profile_and_defaults(
    client_with_overrides: TestClient,
    test_external_idp_id: str,
) -> None:
    response = client_with_overrides.get("/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("usr_")
    assert data["external_idp_id"] == test_external_idp_id
    assert data["domain_preferences"]["ui_theme"] == "dark"
    assert data["domain_preferences"]["preferred_genres"] == []


def test_patch_me_preferences_partial_update(client_with_overrides: TestClient) -> None:
    client_with_overrides.get("/me")

    response = client_with_overrides.patch(
        "/me/preferences",
        json={"domain_preferences": {"preferred_genres": ["scifi"]}},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["domain_preferences"]["preferred_genres"] == ["scifi"]
    assert data["domain_preferences"]["ui_theme"] == "dark"


def test_patch_me_preferences_invalid_payload_returns_422(
    client_with_overrides: TestClient,
) -> None:
    response = client_with_overrides.patch(
        "/me/preferences",
        json={"domain_preferences": {"preferred_genres": "not_a_list"}},
    )

    assert response.status_code == 422


def test_missing_user_header_returns_401(client: TestClient) -> None:
    response = client.get("/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing or empty X-User-Id header"
