"""Schemas dos metadados de domínio (unidades, motivos, papéis e níveis)."""
from app.models import (
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
    }


__all__ = ["serialize_meta"]
