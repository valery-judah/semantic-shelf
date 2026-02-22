# Recommendation Service MVP Requirements

## Overview
A simple recommendation service MVP.

## Tech Stack
- **API Service**: Python web app
- **Tools**: Python + FastAPI + Pydantic

## Features

### 1. Get Recommendations
The client calls `GET /me/recommendations` to retrieve a list of book recommendations.

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
