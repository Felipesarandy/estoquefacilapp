"""Indicadores consolidados do haras (/api/dashboard)."""
from flask import Blueprint, jsonify

from app.api.security import login_required
from app.schemas.alerts import serialize_alert
from app.schemas.movements import serialize_daily, serialize_movement
from app.services.alerts import (
    contagem_por_nivel,
    dias_antecedencia,
    ordenar_por_gravidade,
    produtos_ativos,
    nivel as nivel_do,
    OK,
)
from app.services.stock import movimentacoes_do_dia, ultimas_movimentacoes

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

URGENTES = 10
ULTIMAS = 10


@bp.get("")
@login_required
def get_dashboard(user):
    """Resumo do haras: situação do estoque e movimento do dia."""
    ativos = produtos_ativos(user.stable_id)

    em_alerta = ordenar_por_gravidade([p for p in ativos if nivel_do(p) != OK])

    return jsonify({
        "dias_antecedencia": dias_antecedencia(),
        "produtos_ativos": len(ativos),
        "por_nivel": contagem_por_nivel(ativos),
        "em_alerta": len(em_alerta),
        "mais_urgentes": [serialize_alert(p) for p in em_alerta[:URGENTES]],
        "movimentacoes_hoje": serialize_daily(movimentacoes_do_dia(user.stable_id)),
        "ultimas_movimentacoes": [
            serialize_movement(m) for m in ultimas_movimentacoes(user.stable_id, ULTIMAS)
        ],
    }), 200
