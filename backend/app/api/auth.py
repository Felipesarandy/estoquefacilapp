"""Autenticação: login e consulta do usuário logado (/api/auth)."""
from datetime import timedelta

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import create_access_token

from app.api.errors import api_error
from app.api.security import login_required
from app.extensions import db
from app.models import User
from app.schemas.auth import login_credentials, token_response
from app.schemas.common import body
from app.schemas.users import serialize_user

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _expires_in():
    """Validade do token em segundos, como está na configuração."""
    expires = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES")

    if isinstance(expires, timedelta):
        return int(expires.total_seconds())

    return int(expires or 0)


@bp.post("/login")
def login():
    """Troca e-mail e senha por um token de acesso."""
    email, password = login_credentials(body())

    user = db.session.query(User).filter_by(email=email, active=True).first()

    # Mesma mensagem para e-mail inexistente, inativo e senha errada
    if user is None or not user.check_password(password):
        return api_error(401, "Credenciais inválidas")

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "stable_id": user.stable_id},
    )

    return jsonify(token_response(user, token, _expires_in())), 200


@bp.get("/me")
@login_required
def me(user):
    """Dados do usuário autenticado."""
    return jsonify(serialize_user(user)), 200
