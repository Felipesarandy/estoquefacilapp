"""Schemas de contagem de inventário (saldo do sistema x contado)."""
from app.schemas.common import decimal_field, integer_field, optional_string, texto



def serialize_count(item):
    """Saída pública da contagem (difference > 0 sobrou, < 0 faltou)."""
    return {
        "id": item.id,
        "product_id": item.product_id,
        "user_id": item.user_id,
        "system_quantity": texto(item.system_quantity),
        "counted_quantity": texto(item.counted_quantity),
        "difference": texto(item.difference),
        "created_at": texto(item.created_at),
    }


def new_count_payload(data):
    """Dados aceitos no POST /api/inventory."""
    return {
        "product_id": integer_field(data, "product_id", required=True),
        "counted_quantity": decimal_field(data, "counted_quantity", scale=3),
        "note": optional_string(data, "note", 1000),
    }


__all__ = ["serialize_count", "new_count_payload"]
