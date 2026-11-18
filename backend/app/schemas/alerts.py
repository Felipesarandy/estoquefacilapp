"""Alertas: estoque mínimo, dias de cobertura e capital imobilizado."""
from app.schemas.common import texto, texto_dias
from app.services.alerts import resumo



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
        "current_stock": texto(produto.current_stock),
        "min_stock": texto(produto.min_stock),
        "daily_consumption": texto(produto.daily_consumption),
        "cobertura_dias": texto_dias(situacao["cobertura_dias"]),
        "data_prevista_ruptura": texto(situacao["data_prevista_ruptura"]),
        "min_stock_sugerido": texto(situacao["min_stock_sugerido"]),
        "nivel": situacao["nivel"],
    }


__all__ = ["serialize_alert"]
