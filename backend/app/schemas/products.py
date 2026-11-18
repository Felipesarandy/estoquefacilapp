"""Schemas de insumo: unidades, custos, mínimo/máximo e saldo."""
from app.models import UNIDADES
from app.schemas.common import (
    ValidationError,
    boolean_field,
    choice_field,
    decimal_field,
    integer_field,
    optional_string,
    required_string,
    texto,
    texto_dias,
)
from app.services.alerts import resumo

UNIDADE_PADRAO = "kg"

# Campos numéricos editáveis e a escala de cada coluna
CAMPOS_DECIMAIS = (
    ("cost_price", 2),
    ("min_stock", 3),
    ("max_stock", 3),
    ("daily_consumption", 3),
)



def serialize_product(item):
    """Saída pública do insumo.

    A situação de estoque (`nivel`, `cobertura_dias`, `data_prevista_ruptura`,
    `min_stock_sugerido` e os antigos `days_left`/`is_low_stock`) vem de
    `app.services.alerts`: cálculo em Python sobre as colunas já carregadas,
    sem consulta extra por item.
    """
    situacao = resumo(item)

    return {
        "id": item.id,
        "stable_id": item.stable_id,
        "category_id": item.category_id,
        "supplier_id": item.supplier_id,
        "name": item.name,
        "code": item.code,
        "unit": item.unit,
        "cost_price": texto(item.cost_price),
        "min_stock": texto(item.min_stock),
        "max_stock": texto(item.max_stock),
        "current_stock": texto(item.current_stock),
        "daily_consumption": texto(item.daily_consumption),
        "stock_value": texto(item.stock_value),
        "nivel": situacao["nivel"],
        "cobertura_dias": texto_dias(situacao["cobertura_dias"]),
        "data_prevista_ruptura": texto(situacao["data_prevista_ruptura"]),
        "min_stock_sugerido": texto(situacao["min_stock_sugerido"]),
        "days_left": texto_dias(situacao["days_left"]),
        "is_low_stock": situacao["is_low_stock"],
        "active": item.active,
    }


def _recusar_saldo(data):
    """O saldo só muda por movimentação (Etapa 4)."""
    if "current_stock" in data:
        raise ValidationError(
            "current_stock só muda por movimentação de estoque",
            field="current_stock",
        )


def _decimais(data, obrigatorios):
    """Lê os campos numéricos presentes (ou todos, na criação)."""
    valores = {}

    for campo, escala in CAMPOS_DECIMAIS:
        if campo not in data:
            if obrigatorios and campo in ("cost_price", "min_stock"):
                valores[campo] = decimal_field({campo: 0}, campo, scale=escala)
            continue

        if data[campo] is None and campo in ("max_stock", "daily_consumption"):
            valores[campo] = None
            continue

        valores[campo] = decimal_field(data, campo, scale=escala)

    return valores


def _checar_maximo(min_stock, max_stock):
    if min_stock is not None and max_stock is not None and max_stock < min_stock:
        raise ValidationError(
            "max_stock não pode ser menor que min_stock", field="max_stock"
        )


def new_product_payload(data):
    """Dados aceitos na criação (POST /api/products)."""
    _recusar_saldo(data)

    dados = {
        "name": required_string(data, "name", 150),
        "code": optional_string(data, "code", 50),
        "category_id": integer_field(data, "category_id", required=True),
        "supplier_id": integer_field(data, "supplier_id"),
        "unit": choice_field(data.get("unit", UNIDADE_PADRAO), UNIDADES, "unit"),
        "active": boolean_field(data, "active") if "active" in data else True,
    }
    dados.update(_decimais(data, obrigatorios=True))

    _checar_maximo(dados.get("min_stock"), dados.get("max_stock"))

    return dados


def product_update_payload(data, atual):
    """Só os campos presentes no corpo (PATCH /api/products/<id>).

    `atual` é o produto em banco, usado para comparar min_stock x max_stock.
    """
    _recusar_saldo(data)

    changes = {}

    if "name" in data:
        changes["name"] = required_string(data, "name", 150)

    if "code" in data:
        changes["code"] = optional_string(data, "code", 50)

    if "category_id" in data:
        changes["category_id"] = integer_field(data, "category_id", required=True)

    if "supplier_id" in data:
        changes["supplier_id"] = integer_field(data, "supplier_id")

    if "unit" in data:
        changes["unit"] = choice_field(data.get("unit"), UNIDADES, "unit")

    if "active" in data:
        changes["active"] = boolean_field(data, "active")

    changes.update(_decimais(data, obrigatorios=False))

    if not changes:
        raise ValidationError("Informe ao menos um campo para atualizar")

    _checar_maximo(
        changes.get("min_stock", atual.min_stock),
        changes.get("max_stock", atual.max_stock),
    )

    return changes


__all__ = [
    "UNIDADE_PADRAO",
    "serialize_product",
    "new_product_payload",
    "product_update_payload",
]
