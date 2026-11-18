"""Schemas de autenticação: credenciais de login e token devolvido."""
from app.schemas.common import required_string
from app.schemas.users import serialize_user


def login_credentials(data):
    """E-mail (em minúsculas) e senha enviados no login."""
    return (
        required_string(data, "email", 255).lower(),
        required_string(data, "password", 200),
    )


def token_response(user, access_token, expires_in):
    """Corpo de sucesso do login."""
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "user": serialize_user(user),
    }


__all__ = ["login_credentials", "token_response"]
