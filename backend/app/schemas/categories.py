"""Schemas de categoria de insumo."""
from app.schemas.common import ValidationError, required_string


def serialize_category(item):
    """Saída pública da categoria."""
    return {
        "id": item.id,
        "stable_id": item.stable_id,
        "name": item.name,
    }


def new_category_payload(data):
    """Dados aceitos na criação (POST /api/categories)."""
    return {"name": required_string(data, "name", 80)}


def category_update_payload(data):
    """Só os campos presentes no corpo (PATCH /api/categories/<id>)."""
    changes = {}

    if "name" in data:
        changes["name"] = required_string(data, "name", 80)

    if not changes:
        raise ValidationError("Informe ao menos um campo para atualizar")

    return changes


__all__ = ["serialize_category", "new_category_payload", "category_update_payload"]
