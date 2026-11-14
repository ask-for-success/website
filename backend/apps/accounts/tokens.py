from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


def issue_token_pair(user: User) -> dict[str, str]:
    refresh_token = RefreshToken.for_user(user)
    return {
        "access_token": str(refresh_token.access_token),
        "refresh_token": str(refresh_token),
    }
