# Recommendation Service MVP Requirements

## Overview
A simple recommendation service MVP.

## Tech Stack
- **API Service**: Python web app
- **Tools**: Python + FastAPI + Pydantic

## Features

### 1. Get Recommendations
The client calls `GET /me/recommendations` to retrieve a list of book recommendations.
This endpoint requires the `X-User-Id` header in v0.

#### Response Format
```json
{
  "recommendations": [
    {
      "book_id": "123",
      "score": 0.95,
      "reason": "popular_in_sci_fi",
      "book": {
        "title": "Dune",
        "author": "Frank Herbert",
        "cover_url": "https://..."
      }
    }
  ]
}
```

### 2. Get Current User
The client calls `GET /me` to retrieve the shadow user profile.
This endpoint requires the `X-User-Id` header in v0.

#### Response Format
```json
{
  "id": "usr_18fd5dbf-eec2-4c55-bd09-2f26d6ec299f",
  "external_idp_id": "auth0|abc123",
  "domain_preferences": {
    "preferred_genres": ["scifi"],
    "ui_theme": "dark"
  }
}
```

### 3. Update Current User Preferences
The client calls `PATCH /me/preferences` to partially update recommendation preferences.
This endpoint requires the `X-User-Id` header in v0.

#### Request Format
```json
{
  "domain_preferences": {
    "ui_theme": "light"
  }
}
```

#### Notes
- Patch semantics are top-level merge for `domain_preferences`.
- Omitted keys remain unchanged.
