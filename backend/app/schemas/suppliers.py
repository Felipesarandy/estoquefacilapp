"""Schemas de fornecedor."""
from app.schemas.common import ValidationError, optional_string, required_string

CAMPOS_OPCIONAIS = (("phone", 20), ("email", 255))


def serialize_supplier(item):
    """Saída pública do fornecedor."""
    return {
        "id": item.id,
        "stable_id": item.stable_id,
        "name": item.name,
        "phone": item.phone,
        "email": item.email,
    }


def new_supplier_payload(data):
    """Dados aceitos na criação (POST /api/suppliers)."""
    dados = {"name": required_string(data, "name", 120)}

    for campo, limite in CAMPOS_OPCIONAIS:
        dados[campo] = optional_string(data, campo, limite)

    return dados


def supplier_update_payload(data):
    """Só os campos presentes no corpo (PATCH /api/suppliers/<id>)."""
    changes = {}

    if "name" in data:
        changes["name"] = required_string(data, "name", 120)

    for campo, limite in CAMPOS_OPCIONAIS:
        if campo in data:
            changes[campo] = optional_string(data, campo, limite)

    if not changes:
        raise ValidationError("Informe ao menos um campo para atualizar")

    return changes


__all__ = ["serialize_supplier", "new_supplier_payload", "supplier_update_payload"]
