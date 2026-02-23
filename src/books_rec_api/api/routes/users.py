from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from books_rec_api.dependencies.auth import get_external_idp_id
from books_rec_api.dependencies.users import get_user_service
from books_rec_api.schemas.user import UserPreferencesPatchRequest, UserRead
from books_rec_api.services.user_service import UserService

router = APIRouter(tags=["users"])


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get Current User Profile",
    description=(
        "Fetches the current user profile based on the external identity provider ID. "
        "If the user doesn't exist, it is created as a shadow user."
    ),
    responses={401: {"description": "Not authenticated"}},
)
def get_my_profile(
    external_idp_id: Annotated[str, Depends(get_external_idp_id)],
    svc: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    return svc.get_or_create_shadow_user(external_idp_id=external_idp_id)


@router.patch(
    "/me/preferences",
    response_model=UserRead,
    summary="Update Current User Preferences",
    description="Updates the preferences for the current user. Only provided fields are updated.",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "User not found"},
    },
)
def update_my_preferences(
    payload: UserPreferencesPatchRequest,
    external_idp_id: Annotated[str, Depends(get_external_idp_id)],
    svc: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    user = svc.get_or_create_shadow_user(external_idp_id=external_idp_id)
    updated_user = svc.update_preferences(user_id=user.id, patch=payload.domain_preferences)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated_user
