"""Schemas de movimentação: tipo, motivo, quantidade, lote e validade."""
from app.models import MOTIVOS_POR_TIPO, TIPOS_MOVIMENTACAO
from app.schemas.common import (
    ValidationError,
    choice_field,
    date_arg,
    date_field,
    decimal_field,
    integer_field,
    optional_string,
    texto,
)

TIPOS = TIPOS_MOVIMENTACAO
MAX_DIAS_PERIODO = 31



def serialize_movement(item):
    """Saída pública da movimentação de estoque."""
    return {
        "id": item.id,
        "product_id": item.product_id,
        "user_id": item.user_id,
        "type": item.type,
        "reason": item.reason,
        "quantity": texto(item.quantity),
        "unit_cost": texto(item.unit_cost),
        "total_cost": texto(item.total_cost),
        "batch": item.batch,
        "expiration_date": texto(item.expiration_date),
        "note": item.note,
        "created_at": texto(item.created_at),
    }


def _totais(item):
    return {
        "entradas": texto(item["entradas"]),
        "saidas": texto(item["saidas"]),
        "saldo": texto(item["saldo"]),
        "total_movimentacoes": item["total_movimentacoes"],
    }


def serialize_daily(registro):
    """Registro diário de entradas e saídas.

    As chaves em português (data, entradas, saidas, saldo,
    total_movimentacoes) são as que o dashboard consome. As listas
    `produtos` e `usuarios` só aparecem quando o registro as traz.
    """
    corpo = {"data": texto(registro["data"]), **_totais(registro)}

    for lista in ("produtos", "usuarios"):
        if lista in registro:
            corpo[lista] = [
                {"id": item["id"], "name": item["name"], **_totais(item)}
                for item in registro[lista]
            ]

    return corpo


def new_movement_payload(data):
    """Dados aceitos no POST /api/movements (nomes iguais aos do model)."""
    tipo = choice_field(data.get("type"), TIPOS, "type")

    return {
        "product_id": integer_field(data, "product_id", required=True),
        "type": tipo,
        "reason": choice_field(data.get("reason"), MOTIVOS_POR_TIPO[tipo], "reason"),
        "quantity": decimal_field(data, "quantity", positive=True, scale=3),
        "batch": optional_string(data, "batch", 50),
        "expiration_date": date_field(data, "expiration_date"),
        "note": optional_string(data, "note", 5000),
    }


def periodo_do_registro(hoje):
    """Lê ?date= ou ?from=&to= do registro diário; no máximo 31 dias."""
    dia = date_arg("date")
    inicio = date_arg("from")
    fim = date_arg("to")

    if dia and (inicio or fim):
        raise ValidationError("Use date OU from/to, não os dois", field="date")

    if dia:
        return dia, dia

    if inicio or fim:
        inicio = inicio or fim
        fim = fim or inicio

        if fim < inicio:
            raise ValidationError("to não pode ser anterior a from", field="to")

        if (fim - inicio).days + 1 > MAX_DIAS_PERIODO:
            raise ValidationError(
                f"O intervalo não pode passar de {MAX_DIAS_PERIODO} dias", field="to"
            )

        return inicio, fim

    return hoje, hoje


__all__ = [
    "TIPOS",
    "MOTIVOS_POR_TIPO",
    "MAX_DIAS_PERIODO",
    "serialize_movement",
    "serialize_daily",
    "new_movement_payload",
    "periodo_do_registro",
]
