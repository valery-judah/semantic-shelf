from fastapi import APIRouter

from books_rec_api.schemas.recommendation import RecommendationsResponse
from books_rec_api.services.recommendation_service import get_recommendations

router = APIRouter(tags=["recommendations"])


@router.get("/me/recommendations", response_model=RecommendationsResponse)
def read_my_recommendations() -> RecommendationsResponse:
    recommendations = get_recommendations()
    return RecommendationsResponse(recommendations=recommendations)
