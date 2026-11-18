"""Schemas da trilha de auditoria (somente leitura)."""
from app.models import AUDIT_ACTIONS
from app.schemas.common import choice_field, texto

# Entidades que aparecem na trilha
ENTIDADES = [
    "user",
    "category",
    "supplier",
    "product",
    "movement",
    "inventory_count",
    "incident",
]



def serialize_audit(log):
    """Saída pública do registro de auditoria."""
    return {
        "id": log.id,
        "stable_id": log.stable_id,
        "user_id": log.user_id,
        "action": log.action,
        "entity": log.entity,
        "entity_id": log.entity_id,
        "before_json": log.before_json,
        "after_json": log.after_json,
        "ip": log.ip,
        "created_at": texto(log.created_at),
    }


def action_filter(valor):
    """?action= validado pelas ações conhecidas."""
    return choice_field(valor, AUDIT_ACTIONS, "action") if valor else None


def entity_filter(valor):
    """?entity= validado pelas entidades auditadas."""
    return choice_field(valor, ENTIDADES, "entity") if valor else None


__all__ = ["ENTIDADES", "serialize_audit", "action_filter", "entity_filter"]
