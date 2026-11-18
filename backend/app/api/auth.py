"""Autenticação: login e consulta do usuário logado (/api/auth)."""
import logging
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
from app.services import audit

logger = logging.getLogger(__name__)

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _expires_in():
    """Validade do token em segundos, como está na configuração."""
    expires = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES")

    if isinstance(expires, timedelta):
        return int(expires.total_seconds())

    return int(expires or 0)


def _registrar_falha_de_login(email, conta):
    """Audita e loga a tentativa; e-mail desconhecido fica sem haras."""
    audit.record(
        None,
        "login_failed",
        "user",
        conta.id if conta else None,
        after={"email": email},
        stable_id=conta.stable_id if conta else None,
    )
    db.session.commit()

    logger.warning("login falhou | email=%s conta_existe=%s", email, conta is not None)


@bp.post("/login")
def login():
    """Troca e-mail e senha por um token de acesso."""
    email, password = login_credentials(body())

    conta = db.session.query(User).filter_by(email=email).first()

    # Mesma mensagem para e-mail inexistente, inativo e senha errada
    if conta is None or not conta.active or not conta.check_password(password):
        _registrar_falha_de_login(email, conta)
        return api_error(401, "Credenciais inválidas")

    user = conta
    audit.record(user, "login", "user", user.id)
    db.session.commit()

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
