"""Schemas de usuário: criação, atualização parcial e saída (sem a senha)."""
from app.models import ROLES
from app.schemas.common import (
    ValidationError,
    boolean_field,
    choice_field,
    required_string,
)

SENHA_MINIMA = 8
ROLE_PADRAO = "tratador"


def serialize_user(user):
    """Saída pública do usuário. Nunca inclui `password_hash`."""
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "stable_id": user.stable_id,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def email_field(data, field="email"):
    """E-mail em minúsculas, com uma checagem simples de formato."""
    email = required_string(data, field, 255).lower()

    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValidationError("Informe um e-mail válido", field=field)

    return email


def password_field(data, field="password"):
    """Senha com o mínimo de caracteres exigido."""
    password = required_string(data, field, 200)

    if len(password) < SENHA_MINIMA:
        raise ValidationError(
            f"{field} deve ter pelo menos {SENHA_MINIMA} caracteres", field=field
        )

    return password


def new_user_payload(data):
    """Dados aceitos na criação de um usuário (POST /users)."""
    return {
        "name": required_string(data, "name", 120),
        "email": email_field(data),
        "password": password_field(data),
        "role": choice_field(data.get("role", ROLE_PADRAO), ROLES, "role"),
    }


def user_update_payload(data):
    """Só os campos presentes no corpo (PATCH /users/<id>)."""
    changes = {}

    if "name" in data:
        changes["name"] = required_string(data, "name", 120)

    if "active" in data:
        changes["active"] = boolean_field(data, "active")

    if "role" in data:
        changes["role"] = choice_field(data.get("role"), ROLES, "role")

    if "password" in data:
        changes["password"] = password_field(data)

    if not changes:
        raise ValidationError("Informe ao menos um campo para atualizar")

    return changes


__all__ = [
    "SENHA_MINIMA",
    "ROLE_PADRAO",
    "serialize_user",
    "email_field",
    "password_field",
    "new_user_payload",
    "user_update_payload",
]
