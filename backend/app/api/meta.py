"""Metadados de domínio: unidades e motivos aceitos (/api/meta)."""
from flask import Blueprint, jsonify

from app.api.security import login_required
from app.schemas.meta import serialize_meta

bp = Blueprint("meta", __name__, url_prefix="/meta")


@bp.get("")
@login_required
def get_meta(user):
    """Constantes usadas nos formulários do front-end."""
    return jsonify(serialize_meta()), 200
