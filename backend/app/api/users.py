"""Usuários do haras: admin e tratador (/api/users).

Todas as rotas exigem um admin e trabalham apenas dentro do
Stable (haras) desse admin. Não há DELETE: a baixa é lógica (`active`).
"""
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.api.errors import api_error
from app.api.security import admin_required
from app.extensions import db
from app.models import ROLES, User
from app.schemas.common import (
    bool_arg,
    body,
    choice_field,
    pagination_args,
    paginated,
)
from app.schemas.users import new_user_payload, serialize_user, user_update_payload

bp = Blueprint("users", __name__, url_prefix="/users")


def _do_haras(admin, user_id):
    """Usuário do mesmo haras do admin, ou None (vira 404)."""
    return (
        db.session.query(User)
        .filter_by(id=user_id, stable_id=admin.stable_id)
        .first()
    )


def _email_em_uso(email):
    return db.session.query(User).filter_by(email=email).first() is not None


@bp.get("")
@admin_required
def list_users(admin):
    """Lista paginada dos usuários do haras, ordenada por nome."""
    page, per_page = pagination_args()

    query = db.session.query(User).filter_by(stable_id=admin.stable_id)

    active = bool_arg("active")
    if active is not None:
        query = query.filter(User.active.is_(active))

    role = request.args.get("role")
    if role:
        query = query.filter(User.role == choice_field(role, ROLES, "role"))

    total = query.count()
    items = (
        query.order_by(User.name)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return jsonify(paginated(items, page, per_page, total, serialize_user)), 200


@bp.post("")
@admin_required
def create_user(admin):
    """Cadastra um usuário no haras do admin."""
    data = new_user_payload(body())

    if _email_em_uso(data["email"]):
        return api_error(409, "E-mail já cadastrado")

    novo = User(
        stable_id=admin.stable_id,
        name=data["name"],
        email=data["email"],
        role=data["role"],
        active=True,
    )
    novo.set_password(data["password"])

    db.session.add(novo)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error(409, "E-mail já cadastrado")

    return jsonify(serialize_user(novo)), 201


@bp.get("/<int:user_id>")
@admin_required
def get_user(admin, user_id):
    """Detalhe de um usuário do haras."""
    target = _do_haras(admin, user_id)

    if target is None:
        return api_error(404, "Usuário não encontrado")

    return jsonify(serialize_user(target)), 200


@bp.patch("/<int:user_id>")
@admin_required
def update_user(admin, user_id):
    """Atualiza nome, papel, senha ou ativa/desativa o usuário."""
    target = _do_haras(admin, user_id)

    if target is None:
        return api_error(404, "Usuário não encontrado")

    changes = user_update_payload(body())

    # O admin logado não pode se desativar nem deixar de ser admin
    if target.id == admin.id:
        if changes.get("active") is False:
            return api_error(409, "Você não pode desativar sua própria conta")

        if "role" in changes and changes["role"] != admin.role:
            return api_error(409, "Você não pode alterar seu próprio papel")

    if "name" in changes:
        target.name = changes["name"]

    if "active" in changes:
        target.active = changes["active"]

    if "role" in changes:
        target.role = changes["role"]

    if "password" in changes:
        target.set_password(changes["password"])

    db.session.commit()

    return jsonify(serialize_user(target)), 200
