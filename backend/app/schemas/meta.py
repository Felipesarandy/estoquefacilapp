"""Schemas dos metadados de domínio (unidades, motivos, papéis, níveis e ITIL)."""
from app.models import (
    AUDIT_ACTIONS,
    INCIDENT_SEVERITY,
    INCIDENT_STATUS,
    INCIDENT_TYPES,
    MOTIVOS_ENTRADA,
    MOTIVOS_PERDA,
    MOTIVOS_SAIDA,
    NIVEIS_ESTOQUE,
    ROLES,
    UNIDADES,
)


def serialize_meta():
    """Constantes do domínio que o front-end usa para montar os formulários."""
    return {
        "motivos_entrada": list(MOTIVOS_ENTRADA),
        "motivos_saida": list(MOTIVOS_SAIDA),
        "motivos_perda": list(MOTIVOS_PERDA),
        "unidades": list(UNIDADES),
        "roles": list(ROLES),
        "niveis_estoque": list(NIVEIS_ESTOQUE),
        "incident_types": list(INCIDENT_TYPES),
        "incident_status": list(INCIDENT_STATUS),
        "incident_severity": list(INCIDENT_SEVERITY),
        "audit_actions": list(AUDIT_ACTIONS),
    }


__all__ = ["serialize_meta"]
