"""Alertas: estoque mínimo, dias de cobertura e capital imobilizado."""
from app.schemas.common import texto_dias
from app.services.alerts import resumo


def _texto(valor):
    """Decimal/Date como texto, para não perder casas no JSON."""
    if valor is None:
        return None

    return valor.isoformat() if hasattr(valor, "isoformat") else str(valor)


def serialize_alert(produto):
    """Insumo na lista de alertas, com a situação calculada em Python."""
    situacao = resumo(produto)

    return {
        "id": produto.id,
        "name": produto.name,
        "code": produto.code,
        "unit": produto.unit,
        "category_id": produto.category_id,
        "supplier_id": produto.supplier_id,
        "current_stock": _texto(produto.current_stock),
        "min_stock": _texto(produto.min_stock),
        "daily_consumption": _texto(produto.daily_consumption),
        "cobertura_dias": texto_dias(situacao["cobertura_dias"]),
        "data_prevista_ruptura": _texto(situacao["data_prevista_ruptura"]),
        "min_stock_sugerido": _texto(situacao["min_stock_sugerido"]),
        "nivel": situacao["nivel"],
    }


__all__ = ["serialize_alert"]
