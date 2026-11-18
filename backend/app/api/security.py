"""Controle de acesso das rotas: token válido + papel do usuário."""
from functools import wraps

from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.errors import api_error
from app.extensions import db
from app.models import User


def roles_required(*roles):
    """Exige token válido e um dos papéis informados.

    O usuário autenticado entra como primeiro argumento da rota.
    401 se o token não corresponde a um usuário ativo; 403 se o papel não serve.
    """

    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*args, **kwargs):
            try:
                user = db.session.get(User, int(get_jwt_identity()))
            except (TypeError, ValueError):
                user = None

            if user is None or not user.active:
                return api_error(401, "Usuário inativo ou inexistente")

            if roles and user.role not in roles:
                return api_error(403, f"Acesso permitido apenas para: {', '.join(roles)}")

            return fn(user, *args, **kwargs)

        return wrapped

    return decorator


admin_required = roles_required("admin")
login_required = roles_required("admin", "tratador")

__all__ = ["roles_required", "admin_required", "login_required"]
