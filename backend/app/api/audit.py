"""Trilha de auditoria das operações (/api/audit).

Somente leitura e somente admin: a trilha é gravada pelos serviços e
não pode ser alterada nem removida (nem pela API, nem pelo ORM).
"""
from flask import Blueprint, jsonify, request

from app.api.errors import api_error
from app.api.security import admin_required
from app.models import AuditLog
from app.schemas.audit import action_filter, entity_filter, serialize_audit
from app.schemas.common import date_arg, int_arg, pagination_args, paginated
from app.services import audit
from app.services.catalog import pagina
from app.services.stock import intervalo_do_dia

bp = Blueprint("audit", __name__, url_prefix="/audit")


@bp.get("")
@admin_required
def list_audit(user):
    """Trilha do haras, mais recentes primeiro, com filtros."""
    page, per_page = pagination_args()

    inicio = date_arg("from")
    fim = date_arg("to")

    query = audit.consultar(
        user.stable_id,
        action=action_filter(request.args.get("action")),
        entity=entity_filter(request.args.get("entity")),
        entity_id=int_arg("entity_id"),
        user_id=int_arg("user_id"),
        inicio=intervalo_do_dia(inicio)[0] if inicio else None,
        fim=intervalo_do_dia(fim)[1] if fim else None,
    )
    itens, total = pagina(query, page, per_page)

    return jsonify(paginated(itens, page, per_page, total, serialize_audit)), 200


@bp.get("/<int:log_id>")
@admin_required
def get_audit(user, log_id):
    """Detalhe de um registro de auditoria do haras."""
    item = audit.consultar(user.stable_id).filter(AuditLog.id == log_id).first()

    if item is None:
        return api_error(404, "Registro de auditoria não encontrado")

    return jsonify(serialize_audit(item)), 200
