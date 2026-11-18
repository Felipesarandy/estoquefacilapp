"""Fornecedores (/api/suppliers).

Leitura para qualquer usuário logado; criação e edição só para admin.
A tabela não tem coluna de ativação, então não há DELETE.
"""
from flask import Blueprint, jsonify

from app.api.errors import api_error
from app.api.security import admin_required, login_required
from app.extensions import db
from app.models import Supplier
from app.schemas.common import body, pagination_args, paginated, search_arg
from app.schemas.suppliers import (
    new_supplier_payload,
    serialize_supplier,
    supplier_update_payload,
)
from app.services.catalog import do_haras, listar_por_nome, nome_em_uso, pagina

bp = Blueprint("suppliers", __name__, url_prefix="/suppliers")


@bp.get("")
@login_required
def list_suppliers(user):
    """Lista paginada dos fornecedores do haras, com busca por nome."""
    page, per_page = pagination_args()

    query = listar_por_nome(Supplier, user.stable_id, search_arg())
    itens, total = pagina(query, page, per_page)

    return jsonify(paginated(itens, page, per_page, total, serialize_supplier)), 200


@bp.get("/<int:supplier_id>")
@login_required
def get_supplier(user, supplier_id):
    """Detalhe de um fornecedor do haras."""
    item = do_haras(Supplier, supplier_id, user.stable_id)

    if item is None:
        return api_error(404, "Fornecedor não encontrado")

    return jsonify(serialize_supplier(item)), 200


@bp.post("")
@admin_required
def create_supplier(user):
    """Cadastra um fornecedor no haras do admin."""
    dados = new_supplier_payload(body())

    if nome_em_uso(Supplier, user.stable_id, dados["name"]):
        return api_error(409, "Fornecedor já cadastrado")

    item = Supplier(stable_id=user.stable_id, **dados)
    db.session.add(item)
    db.session.commit()

    return jsonify(serialize_supplier(item)), 201


@bp.patch("/<int:supplier_id>")
@admin_required
def update_supplier(user, supplier_id):
    """Atualiza nome, telefone ou e-mail do fornecedor."""
    item = do_haras(Supplier, supplier_id, user.stable_id)

    if item is None:
        return api_error(404, "Fornecedor não encontrado")

    changes = supplier_update_payload(body())

    if "name" in changes and nome_em_uso(
        Supplier, user.stable_id, changes["name"], ignorar_id=item.id
    ):
        return api_error(409, "Fornecedor já cadastrado")

    for campo, valor in changes.items():
        setattr(item, campo, valor)

    db.session.commit()

    return jsonify(serialize_supplier(item)), 200
