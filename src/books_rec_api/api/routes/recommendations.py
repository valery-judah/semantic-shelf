from typing import Annotated

from fastapi import APIRouter, Depends

from books_rec_api.dependencies.auth import get_external_idp_id
from books_rec_api.dependencies.users import get_user_service
from books_rec_api.schemas.recommendation import RecommendationsResponse
from books_rec_api.services.recommendation_service import get_recommendations
from books_rec_api.services.user_service import UserService

router = APIRouter(tags=["recommendations"])


@router.get("/me/recommendations", response_model=RecommendationsResponse)
def read_my_recommendations(
    external_idp_id: Annotated[str, Depends(get_external_idp_id)],
    svc: Annotated[UserService, Depends(get_user_service)],
) -> RecommendationsResponse:
    user = svc.get_or_create_shadow_user(external_idp_id=external_idp_id)
    recommendations = get_recommendations(user=user)
    return RecommendationsResponse(recommendations=recommendations)
