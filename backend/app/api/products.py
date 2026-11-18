"""Insumos do haras (/api/products).

Leitura para qualquer usuário logado; criação e edição só para admin.
`current_stock` não é editável aqui: o saldo muda por movimentação.
A baixa de um insumo é lógica — PATCH {"active": false}.
"""
from flask import Blueprint, jsonify
from sqlalchemy.exc import IntegrityError

from app.api.errors import api_error
from app.api.security import admin_required, login_required
from app.extensions import db
from app.models import Product
from app.schemas.common import (
    body,
    bool_arg,
    int_arg,
    pagination_args,
    paginated,
    search_arg,
)
from app.schemas.products import (
    new_product_payload,
    product_update_payload,
    serialize_product,
)
from app.services.catalog import (
    codigo_em_uso,
    do_haras,
    listar_produtos,
    pagina,
    validar_vinculos,
)

bp = Blueprint("products", __name__, url_prefix="/products")


@bp.get("")
@login_required
def list_products(user):
    """Lista paginada com busca por nome/código e filtros de categoria e situação."""
    page, per_page = pagination_args()

    query = listar_produtos(
        user.stable_id,
        busca=search_arg(),
        category_id=int_arg("category_id"),
        active=bool_arg("active"),
    )
    itens, total = pagina(query, page, per_page)

    return jsonify(paginated(itens, page, per_page, total, serialize_product)), 200


@bp.get("/<int:product_id>")
@login_required
def get_product(user, product_id):
    """Detalhe de um insumo do haras."""
    item = do_haras(Product, product_id, user.stable_id)

    if item is None:
        return api_error(404, "Insumo não encontrado")

    return jsonify(serialize_product(item)), 200


@bp.post("")
@admin_required
def create_product(user):
    """Cadastra um insumo no haras do admin (saldo começa em zero)."""
    dados = new_product_payload(body())

    validar_vinculos(
        user.stable_id,
        category_id=dados["category_id"],
        supplier_id=dados["supplier_id"],
    )

    if codigo_em_uso(user.stable_id, dados["code"]):
        return api_error(409, "Código de insumo já usado neste haras")

    item = Product(stable_id=user.stable_id, current_stock=0, **dados)
    db.session.add(item)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error(409, "Código de insumo já usado neste haras")

    return jsonify(serialize_product(item)), 201


@bp.patch("/<int:product_id>")
@admin_required
def update_product(user, product_id):
    """Atualiza os dados cadastrais do insumo (nunca o saldo)."""
    item = do_haras(Product, product_id, user.stable_id)

    if item is None:
        return api_error(404, "Insumo não encontrado")

    changes = product_update_payload(body(), item)

    validar_vinculos(
        user.stable_id,
        category_id=changes.get("category_id"),
        supplier_id=changes.get("supplier_id"),
    )

    if "code" in changes and codigo_em_uso(
        user.stable_id, changes["code"], ignorar_id=item.id
    ):
        return api_error(409, "Código de insumo já usado neste haras")

    for campo, valor in changes.items():
        setattr(item, campo, valor)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error(409, "Código de insumo já usado neste haras")

    return jsonify(serialize_product(item)), 200
