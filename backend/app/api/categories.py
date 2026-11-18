"""Categorias de insumo (/api/categories).

Leitura para qualquer usuário logado; criação, edição e exclusão só para admin.
A tabela não tem coluna de ativação: a categoria é excluída de verdade,
mas só quando não tem nenhum insumo (ativo ou inativo) vinculado.
"""
from flask import Blueprint, jsonify
from sqlalchemy.exc import IntegrityError

from app.api.errors import api_error
from app.api.security import admin_required, login_required
from app.extensions import db
from app.models import Category
from app.schemas.categories import (
    category_update_payload,
    new_category_payload,
    serialize_category,
)
from app.schemas.common import body, pagination_args, paginated, search_arg
from app.services import audit
from app.services.catalog import (
    contar_produtos_da_categoria,
    do_haras,
    listar_por_nome,
    nome_em_uso,
    pagina,
)
from app.services.exceptions import Conflito

bp = Blueprint("categories", __name__, url_prefix="/categories")


@bp.get("")
@login_required
def list_categories(user):
    """Lista paginada das categorias do haras, com busca por nome."""
    page, per_page = pagination_args()

    query = listar_por_nome(Category, user.stable_id, search_arg())
    itens, total = pagina(query, page, per_page)

    return jsonify(paginated(itens, page, per_page, total, serialize_category)), 200


@bp.get("/<int:category_id>")
@login_required
def get_category(user, category_id):
    """Detalhe de uma categoria do haras."""
    item = do_haras(Category, category_id, user.stable_id)

    if item is None:
        return api_error(404, "Categoria não encontrada")

    return jsonify(serialize_category(item)), 200


@bp.post("")
@admin_required
def create_category(user):
    """Cadastra uma categoria no haras do admin."""
    dados = new_category_payload(body())

    if nome_em_uso(Category, user.stable_id, dados["name"]):
        return api_error(409, "Categoria já cadastrada")

    item = Category(stable_id=user.stable_id, name=dados["name"])
    db.session.add(item)

    try:
        audit.registrar_criacao(user, "category", item)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error(409, "Categoria já cadastrada")

    return jsonify(serialize_category(item)), 201


@bp.patch("/<int:category_id>")
@admin_required
def update_category(user, category_id):
    """Renomeia uma categoria do haras."""
    item = do_haras(Category, category_id, user.stable_id)

    if item is None:
        return api_error(404, "Categoria não encontrada")

    changes = category_update_payload(body())

    if nome_em_uso(Category, user.stable_id, changes["name"], ignorar_id=item.id):
        return api_error(409, "Categoria já cadastrada")

    antes = audit.snapshot(item)
    item.name = changes["name"]

    try:
        audit.registrar_alteracao(user, "category", item, antes)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error(409, "Categoria já cadastrada")

    return jsonify(serialize_category(item)), 200


def _produtos_vinculados(quantidade):
    return Conflito(
        f"Categoria possui {quantidade} produto(s) vinculado(s) e não pode ser excluída.",
        details={"product_count": quantidade},
    )


@bp.delete("/<int:category_id>")
@admin_required
def delete_category(user, category_id):
    """Exclui a categoria, desde que nenhum produto (ativo ou inativo) a use."""
    item = do_haras(Category, category_id, user.stable_id)

    if item is None:
        return api_error(404, "Categoria não encontrada")

    # Checagem explícita: não depende de o banco aplicar chaves estrangeiras.
    vinculados = contar_produtos_da_categoria(item.id)
    if vinculados:
        raise _produtos_vinculados(vinculados)

    antes = audit.snapshot(item)
    db.session.delete(item)
    audit.registrar_exclusao(user, "category", category_id, antes)

    try:
        db.session.commit()
    except IntegrityError:
        # Um produto foi vinculado entre a checagem e o commit.
        db.session.rollback()
        raise _produtos_vinculados(contar_produtos_da_categoria(category_id)) from None

    return "", 204
