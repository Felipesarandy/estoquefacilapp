"""Regras do catálogo: escopo por haras e unicidade de nome/código.

Nenhuma rota consulta o banco direto: tudo passa por aqui, sempre
amarrado ao `stable_id` do usuário logado.
"""
from app.extensions import db
from app.models import Category, Product, Supplier
from app.schemas.common import ESCAPE_LIKE, ValidationError, like_pattern


def do_haras(model, entity_id, stable_id):
    """Registro do haras informado, ou None (a rota devolve 404)."""
    if entity_id is None:
        return None

    return (
        db.session.query(model)
        .filter_by(id=entity_id, stable_id=stable_id)
        .first()
    )


def nome_em_uso(model, stable_id, nome, ignorar_id=None):
    """Mesmo nome já cadastrado no haras (comparação sem diferenciar maiúsculas)."""
    query = db.session.query(model.id).filter(
        model.stable_id == stable_id,
        db.func.lower(model.name) == nome.lower(),
    )

    if ignorar_id is not None:
        query = query.filter(model.id != ignorar_id)

    return query.first() is not None


def codigo_em_uso(stable_id, code, ignorar_id=None):
    """Código de insumo já usado no haras (a tabela tem unique (stable_id, code))."""
    if not code:
        return False

    query = db.session.query(Product.id).filter(
        Product.stable_id == stable_id,
        Product.code == code,
    )

    if ignorar_id is not None:
        query = query.filter(Product.id != ignorar_id)

    return query.first() is not None


def validar_vinculos(stable_id, category_id=None, supplier_id=None):
    """Categoria e fornecedor têm de ser do mesmo haras (422 se não forem)."""
    if category_id is not None and do_haras(Category, category_id, stable_id) is None:
        raise ValidationError(
            "category_id não pertence a este haras", field="category_id"
        )

    if supplier_id is not None and do_haras(Supplier, supplier_id, stable_id) is None:
        raise ValidationError(
            "supplier_id não pertence a este haras", field="supplier_id"
        )


def listar_por_nome(model, stable_id, busca=None):
    """Query base das listagens simples (categorias e fornecedores)."""
    query = db.session.query(model).filter(model.stable_id == stable_id)

    if busca:
        query = query.filter(model.name.ilike(like_pattern(busca), escape=ESCAPE_LIKE))

    return query.order_by(model.name)


def listar_produtos(stable_id, busca=None, category_id=None, active=None):
    """Query de insumos com busca por nome/código e filtros opcionais."""
    query = db.session.query(Product).filter(Product.stable_id == stable_id)

    if busca:
        padrao = like_pattern(busca)
        query = query.filter(
            db.or_(
                Product.name.ilike(padrao, escape=ESCAPE_LIKE),
                Product.code.ilike(padrao, escape=ESCAPE_LIKE),
            )
        )

    if category_id is not None:
        query = query.filter(Product.category_id == category_id)

    if active is not None:
        query = query.filter(Product.active.is_(active))

    return query.order_by(Product.name)


def pagina(query, page, per_page):
    """Total e itens da página pedida (uma contagem + uma busca)."""
    total = query.order_by(None).count()
    itens = query.offset((page - 1) * per_page).limit(per_page).all()

    return itens, total


__all__ = [
    "do_haras",
    "nome_em_uso",
    "codigo_em_uso",
    "validar_vinculos",
    "listar_por_nome",
    "listar_produtos",
    "pagina",
]
