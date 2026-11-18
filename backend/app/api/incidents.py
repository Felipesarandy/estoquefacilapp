"""Gestão de incidentes do estoque (/api/incidents).

Qualquer usuário logado consulta e abre incidentes; só o admin muda
status, responsável e resolução (PATCH). Não há DELETE: o incidente é
encerrado pelo ciclo de vida (resolvido -> fechado).
"""
from flask import Blueprint, jsonify, request

from app.api.errors import api_error
from app.api.security import admin_required, login_required
from app.extensions import db
from app.models import Incident, Product, User
from app.schemas.common import ValidationError, body, int_arg, pagination_args, paginated
from app.schemas.incidents import (
    incident_update_payload,
    new_incident_payload,
    serialize_incident,
    status_filter,
    type_filter,
)
from app.services import incidents
from app.services.catalog import do_haras, pagina

bp = Blueprint("incidents", __name__, url_prefix="/incidents")


@bp.get("")
@login_required
def list_incidents(user):
    """Incidentes do haras (?status=, ?type=, ?product_id=, ?assigned_to_id=)."""
    page, per_page = pagination_args()

    query = incidents.consultar(
        user.stable_id,
        status=status_filter(request.args.get("status")),
        tipo=type_filter(request.args.get("type")),
        product_id=int_arg("product_id"),
        assigned_to_id=int_arg("assigned_to_id"),
    )
    itens, total = pagina(query, page, per_page)

    return jsonify(paginated(itens, page, per_page, total, serialize_incident)), 200


@bp.get("/summary")
@login_required
def summary(user):
    """Métricas: contagem por status/tipo e tempo médio de resolução."""
    return jsonify(incidents.resumo(user.stable_id)), 200


@bp.get("/<int:incident_id>")
@login_required
def get_incident(user, incident_id):
    """Detalhe de um incidente do haras."""
    item = do_haras(Incident, incident_id, user.stable_id)

    if item is None:
        return api_error(404, "Incidente não encontrado")

    return jsonify(serialize_incident(item)), 200


@bp.post("")
@login_required
def create_incident(user):
    """Abertura manual; não duplica incidente ativo do mesmo insumo e tipo."""
    dados = new_incident_payload(body())

    produto = None
    if dados["product_id"] is not None:
        produto = do_haras(Product, dados["product_id"], user.stable_id)
        if produto is None:
            raise ValidationError("product_id não pertence a este haras",
                                  field="product_id")

    incidente, criado = incidents.abrir_incidente(
        user.stable_id,
        dados["type"],
        dados["description"],
        severity=dados["severity"],
        product=produto,
        opened_by=user,
    )

    if not criado:
        db.session.rollback()
        return api_error(409, f"Já existe o incidente #{incidente.id} ativo para "
                              "este insumo e tipo",
                         {"incident_id": incidente.id})

    db.session.commit()

    return jsonify(serialize_incident(incidente)), 201


@bp.patch("/<int:incident_id>")
@admin_required
def update_incident(user, incident_id):
    """Muda status (ciclo de vida), responsável e/ou resolução."""
    item = do_haras(Incident, incident_id, user.stable_id)

    if item is None:
        return api_error(404, "Incidente não encontrado")

    changes = incident_update_payload(body())

    responsavel = None
    atribuir = "assigned_to_id" in changes

    if atribuir and changes["assigned_to_id"] is not None:
        responsavel = do_haras(User, changes["assigned_to_id"], user.stable_id)
        if responsavel is None:
            raise ValidationError("assigned_to_id não pertence a este haras",
                                  field="assigned_to_id")

    incidents.atualizar_incidente(
        item,
        user,
        status=changes.get("status"),
        assigned_to=responsavel,
        atribuir=atribuir,
        resolution=changes.get("resolution"),
    )
    db.session.commit()

    return jsonify(serialize_incident(item)), 200
