"""Movimentações de estoque: entradas e saídas (/api/movements).

Admin e tratador registram. A movimentação é imutável: não há PATCH
nem DELETE — um erro se corrige com uma nova movimentação de reason
"ajuste" e uma nota explicando.
"""
from flask import Blueprint, jsonify, request

from app.api.errors import api_error
from app.api.security import login_required
from app.extensions import db
from app.models import MOTIVOS_ENTRADA, MOTIVOS_SAIDA, Product, StockMovement
from app.schemas.common import (
    body,
    choice_field,
    date_arg,
    int_arg,
    pagination_args,
    paginated,
)
from app.schemas.movements import (
    TIPOS,
    new_movement_payload,
    periodo_do_registro,
    serialize_daily,
    serialize_movement,
)
from app.services.alerts import hoje, nivel
from app.services.catalog import do_haras
from app.services.stock import (
    intervalo_do_dia,
    movimentacoes_do_haras,
    registrar_movimentacao,
    registro_por_periodo,
)

bp = Blueprint("movements", __name__, url_prefix="/movements")

MOTIVOS = sorted(set(MOTIVOS_ENTRADA) | set(MOTIVOS_SAIDA))


@bp.post("")
@login_required
def create_movement(user):
    """Registra uma entrada ou saída e devolve o saldo novo do insumo."""
    dados = new_movement_payload(body())

    produto = do_haras(Product, dados.pop("product_id"), user.stable_id)

    if produto is None:
        return api_error(404, "Insumo não encontrado")

    movimentacao = registrar_movimentacao(user, produto, **dados)
    db.session.commit()

    return jsonify({
        "movement": serialize_movement(movimentacao),
        "current_stock": str(produto.current_stock),
        "nivel": nivel(produto),
        "is_low_stock": produto.is_low_stock,
    }), 201


def _filtrar(query, user):
    """Aplica os filtros da query string ao histórico."""
    product_id = int_arg("product_id")
    if product_id is not None:
        query = query.filter(StockMovement.product_id == product_id)

    tipo = request.args.get("type")
    if tipo:
        query = query.filter(StockMovement.type == choice_field(tipo, TIPOS, "type"))

    motivo = request.args.get("reason")
    if motivo:
        query = query.filter(
            StockMovement.reason == choice_field(motivo, MOTIVOS, "reason")
        )

    user_id = int_arg("user_id")
    if user_id is not None:
        query = query.filter(StockMovement.user_id == user_id)

    inicio = date_arg("from")
    if inicio is not None:
        query = query.filter(StockMovement.created_at >= intervalo_do_dia(inicio)[0])

    fim = date_arg("to")
    if fim is not None:
        query = query.filter(StockMovement.created_at < intervalo_do_dia(fim)[1])

    return query


@bp.get("")
@login_required
def list_movements(user):
    """Histórico paginado, das mais recentes para as mais antigas."""
    page, per_page = pagination_args()

    query = _filtrar(movimentacoes_do_haras(user.stable_id), user)

    total = query.order_by(None).count()
    itens = (
        query.order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return jsonify(paginated(itens, page, per_page, total, serialize_movement)), 200


@bp.get("/daily")
@login_required
def daily(user):
    """Registro diário: ?date=YYYY-MM-DD ou ?from=&to= (no máximo 31 dias)."""
    inicio, fim = periodo_do_registro(hoje())

    dias = registro_por_periodo(user.stable_id, inicio, fim)

    return jsonify({
        "from": inicio.isoformat(),
        "to": fim.isoformat(),
        "dias": [serialize_daily(registro) for registro in dias],
    }), 200


@bp.get("/<int:movement_id>")
@login_required
def get_movement(user, movement_id):
    """Detalhe de uma movimentação do haras."""
    item = (
        movimentacoes_do_haras(user.stable_id)
        .filter(StockMovement.id == movement_id)
        .first()
    )

    if item is None:
        return api_error(404, "Movimentação não encontrada")

    return jsonify(serialize_movement(item)), 200
