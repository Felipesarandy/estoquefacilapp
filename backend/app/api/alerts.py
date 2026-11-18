"""Alertas de estoque mínimo e cobertura (/api/alerts).

Lista os insumos ATIVOS que não estão em "ok", do mais grave para o
menos grave. A regra de nível e de cobertura vive em
`app.services.alerts` — aqui só há paginação e filtro.
"""
from flask import Blueprint, jsonify, request

from app.api.security import login_required
from app.models import NIVEIS_ESTOQUE
from app.schemas.alerts import serialize_alert
from app.schemas.common import choice_field, pagination_args, paginated
from app.services.alerts import OK, dias_antecedencia, listar_em_alerta

bp = Blueprint("alerts", __name__, url_prefix="/alerts")

# "ok" não é alerta: só os três níveis que pedem ação
NIVEIS_DE_ALERTA = [nivel for nivel in NIVEIS_ESTOQUE if nivel != OK]


@bp.get("")
@login_required
def list_alerts(user):
    """Insumos que precisam de atenção, ordenados por gravidade."""
    page, per_page = pagination_args()

    filtro = request.args.get("nivel")
    if filtro:
        filtro = choice_field(filtro, NIVEIS_DE_ALERTA, "nivel")

    itens = listar_em_alerta(user.stable_id, filtro)
    total = len(itens)
    recorte = itens[(page - 1) * per_page : page * per_page]

    corpo = paginated(recorte, page, per_page, total, serialize_alert)
    corpo["dias_antecedencia"] = dias_antecedencia()

    return jsonify(corpo), 200
