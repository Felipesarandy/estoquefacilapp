"""Inventário: contagens físicas x saldo do sistema (/api/inventory).

Admin e tratador registram contagens. A contagem é imutável (sem PUT,
PATCH ou DELETE); havendo diferença, o serviço lança o ajuste e abre o
incidente de divergência na mesma transação.
"""
from flask import Blueprint, jsonify

from app.api.errors import api_error
from app.api.security import login_required
from app.extensions import db
from app.models import InventoryCount, Product
from app.schemas.common import body, date_arg, int_arg, pagination_args, paginated
from app.schemas.incidents import serialize_incident
from app.schemas.inventory import new_count_payload, serialize_count
from app.schemas.movements import serialize_movement
from app.services import inventory
from app.services.alerts import nivel
from app.services.catalog import do_haras, pagina
from app.services.stock import intervalo_do_dia

bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@bp.post("")
@login_required
def create_count(user):
    """Registra a contagem física de um insumo."""
    dados = new_count_payload(body())

    produto = do_haras(Product, dados["product_id"], user.stable_id)

    if produto is None:
        return api_error(404, "Insumo não encontrado")

    contagem, ajuste, incidente = inventory.registrar_contagem(
        user, produto, dados["counted_quantity"], note=dados["note"]
    )
    db.session.commit()

    return jsonify({
        "count": serialize_count(contagem),
        "difference": str(contagem.difference),
        "adjustment": serialize_movement(ajuste) if ajuste else None,
        "incident": serialize_incident(incidente) if incidente else None,
        "current_stock": str(produto.current_stock),
        "nivel": nivel(produto),
    }), 201


@bp.get("")
@login_required
def list_counts(user):
    """Contagens do haras, mais recentes primeiro (?product_id=, ?from=, ?to=)."""
    page, per_page = pagination_args()

    inicio = date_arg("from")
    fim = date_arg("to")

    query = inventory.consultar(
        user.stable_id,
        product_id=int_arg("product_id"),
        inicio=intervalo_do_dia(inicio)[0] if inicio else None,
        fim=intervalo_do_dia(fim)[1] if fim else None,
    )
    itens, total = pagina(query, page, per_page)

    return jsonify(paginated(itens, page, per_page, total, serialize_count)), 200


@bp.get("/<int:count_id>")
@login_required
def get_count(user, count_id):
    """Detalhe de uma contagem do haras."""
    item = inventory.consultar(user.stable_id).filter(InventoryCount.id == count_id).first()

    if item is None:
        return api_error(404, "Contagem não encontrada")

    return jsonify(serialize_count(item)), 200
