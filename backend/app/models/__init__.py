"""Models do EstoqueFácil Equihealth.

Um módulo por entidade; este pacote reexporta tudo, então
`from app.models import Product` continua funcionando.
"""
from app.models.constants import (
    AUDIT_ACTIONS,
    INCIDENT_SEVERITY,
    INCIDENT_STATUS,
    INCIDENT_TYPES,
    MOTIVOS_ENTRADA,
    MOTIVOS_PERDA,
    MOTIVOS_POR_TIPO,
    MOTIVOS_SAIDA,
    NIVEIS_ESTOQUE,
    ROLES,
    TIPOS_MOVIMENTACAO,
    UNIDADES,
)
from app.models.stable import Stable
from app.models.user import User
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.audit_log import AuditLog
from app.models.inventory_count import InventoryCount
from app.models.incident import Incident

__all__ = [
    # constantes de domínio
    "ROLES",
    "MOTIVOS_ENTRADA",
    "MOTIVOS_SAIDA",
    "MOTIVOS_PERDA",
    "TIPOS_MOVIMENTACAO",
    "MOTIVOS_POR_TIPO",
    "UNIDADES",
    "NIVEIS_ESTOQUE",
    "INCIDENT_TYPES",
    "INCIDENT_STATUS",
    "INCIDENT_SEVERITY",
    "AUDIT_ACTIONS",
    # entidades
    "Stable",
    "User",
    "Category",
    "Supplier",
    "Product",
    "StockMovement",
    "InventoryCount",
    "AuditLog",
    "Incident",
]
