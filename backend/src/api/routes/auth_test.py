from fastapi import APIRouter, Depends
from middleware.auth_middleware import get_current_user

router = APIRouter()

@router.get("/auth/me")
async def read_users_me(current_user = Depends(get_current_user)):
    """
    Test endpoint to verify authentication token.
    Returns the authenticated user's information.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "app_metadata": current_user.app_metadata,
        "user_metadata": current_user.user_metadata
    }
