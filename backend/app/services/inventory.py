"""Inventário (gestão de ativos, ITIL): contagem física x saldo do sistema.

A contagem é imutável. Havendo diferença, o saldo é corrigido por uma
movimentação de ajuste (o mesmo caminho atômico das demais) e um
incidente de divergência é aberto com severidade proporcional.
"""
from app.extensions import db
from app.models import InventoryCount, Product
from app.schemas.common import decimal_field
from app.services import audit, incidents
from app.services.exceptions import ConflitoDeEstoque
from app.services.stock import ENTRADA, SAIDA, registrar_movimentacao


def registrar_contagem(user, product, counted_quantity, note=None):
    """Registra a contagem; devolve (contagem, ajuste ou None, incidente ou None).

    Não dá commit: quem chama fecha a transação.
    """
    contada = decimal_field({"counted_quantity": counted_quantity},
                            "counted_quantity", scale=3)

    if not product.active:
        raise ConflitoDeEstoque("Insumo inativo: reative antes de inventariar")

    sistema = product.current_stock

    contagem = InventoryCount(product=product, user=user,
                              system_quantity=sistema, counted_quantity=contada)
    db.session.add(contagem)
    db.session.flush()

    diferenca = contada - sistema
    ajuste = incidente = None

    if diferenca != 0:
        nota = f"Ajuste após inventário #{contagem.id}"
        if note:
            nota = f"{nota}: {note}"

        ajuste = registrar_movimentacao(
            user, product, ENTRADA if diferenca > 0 else SAIDA,
            abs(diferenca), "ajuste", note=nota,
        )

        sentido = "sobra" if diferenca > 0 else "falta"
        incidente, _ = incidents.abrir_incidente(
            product.stable_id,
            incidents.DIVERGENCIA,
            f"Divergência de inventário em {product.name}: {sentido} de "
            f"{abs(diferenca)} {product.unit} (sistema {sistema}, contado {contada}).",
            severity=incidents.severidade_divergencia(sistema, diferenca),
            product=product,
            opened_by=user,
        )

    depois = audit.snapshot(contagem)
    depois.update({
        "difference": str(diferenca),
        "note": note,
        "adjustment_id": ajuste.id if ajuste else None,
        "incident_id": incidente.id if incidente else None,
    })
    audit.record(user, "inventory", "inventory_count", contagem.id, after=depois)

    return contagem, ajuste, incidente


def consultar(stable_id, product_id=None, inicio=None, fim=None):
    """Query das contagens do haras, mais recentes primeiro (inicio/fim em UTC)."""
    query = (
        db.session.query(InventoryCount)
        .join(Product, InventoryCount.product_id == Product.id)
        .filter(Product.stable_id == stable_id)
    )

    if product_id is not None:
        query = query.filter(InventoryCount.product_id == product_id)

    if inicio is not None:
        query = query.filter(InventoryCount.created_at >= inicio)

    if fim is not None:
        query = query.filter(InventoryCount.created_at < fim)

    return query.order_by(InventoryCount.created_at.desc(), InventoryCount.id.desc())


__all__ = ["registrar_contagem", "consultar"]
