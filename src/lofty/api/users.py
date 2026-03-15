"""User endpoints."""

from fastapi import APIRouter, Depends

from lofty.auth.clerk import get_current_user
from lofty.models.user import User
from lofty.schemas.auth import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user),
) -> UserResponse:
    """Get the current authenticated user's profile."""
    return UserResponse.model_validate(user)
