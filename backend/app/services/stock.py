"""Saldo de estoque: registrar entradas/saídas e manter o saldo consistente.

Regras aqui, não nas rotas:

* o saldo muda por UPDATE condicional (`WHERE ... AND current_stock >= :q`
  na saída), então duas saídas simultâneas nunca deixam o saldo negativo;
* a movimentação é gravada na mesma transação do UPDATE;
* movimentação é imutável: estorno é uma nova movimentação com
  reason "ajuste" e uma nota explicando.
"""
import logging
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import update

from app.extensions import db
from app.models import (
    MOTIVOS_POR_TIPO,
    TIPOS_MOVIMENTACAO,
    Product,
    StockMovement,
    User,
)
from app.schemas.common import choice_field, decimal_field
from app.services import audit, incidents
from app.services.alerts import fuso, hoje
from app.services.exceptions import ConflitoDeEstoque

logger = logging.getLogger(__name__)

ENTRADA, SAIDA = TIPOS_MOVIMENTACAO
TIPOS = TIPOS_MOVIMENTACAO


# --------------------------------------------------------------------------
# Registro de movimentação
# --------------------------------------------------------------------------

def registrar_movimentacao(user, product, type, quantity, reason, batch=None,
                           expiration_date=None, note=None, created_at=None):
    """Registra a entrada/saída e atualiza o saldo na mesma transação.

    `created_at` existe só para o seed montar um histórico de demonstração;
    no uso normal o banco carimba a hora.

    Levanta ValidationError (422) para dados inválidos e ConflitoDeEstoque
    (409) para saldo insuficiente ou insumo inativo. Também grava a
    auditoria ("movement") e sincroniza o incidente de ruptura. Não dá
    commit: quem chama decide a hora de fechar a transação.
    """
    tipo = choice_field(type, TIPOS, "type")
    motivo = choice_field(reason, MOTIVOS_POR_TIPO[tipo], "reason")
    quantidade = decimal_field({"quantity": quantity}, "quantity",
                               positive=True, scale=3)

    if not product.active:
        raise ConflitoDeEstoque("Insumo inativo: reative antes de movimentar")

    condicoes = [
        Product.id == product.id,
        Product.stable_id == product.stable_id,
        Product.active.is_(True),
    ]

    if tipo == SAIDA:
        condicoes.append(Product.current_stock >= quantidade)
        novo_saldo = Product.current_stock - quantidade
    else:
        novo_saldo = Product.current_stock + quantidade

    resultado = db.session.execute(
        update(Product).where(*condicoes).values(current_stock=novo_saldo)
    )

    if resultado.rowcount != 1:
        if tipo == SAIDA:
            logger.warning(
                "saida recusada por estoque insuficiente | usuario=%s insumo=%s "
                "quantidade=%s saldo=%s",
                user.id, product.id, quantidade, product.current_stock,
            )
            raise ConflitoDeEstoque("Estoque insuficiente")

        raise ConflitoDeEstoque("Insumo indisponível para movimentação")

    db.session.refresh(product)

    movimentacao = StockMovement(
        product=product,
        user=user,
        type=tipo,
        reason=motivo,
        quantity=quantidade,
        unit_cost=product.cost_price,  # custo no momento da movimentação
        batch=batch,
        expiration_date=expiration_date,
        note=note,
    )

    if created_at is not None:
        movimentacao.created_at = created_at

    db.session.add(movimentacao)
    db.session.flush()

    # Mesma transação: trilha de auditoria e incidente de ruptura (abre ao
    # zerar o saldo, resolve sozinho na reposição)
    audit.record(user, "movement", "movement", movimentacao.id,
                 after=audit.snapshot(movimentacao))
    incidents.sincronizar_ruptura(product, user)

    logger.info(
        "movimentacao registrada | usuario=%s insumo=%s tipo=%s motivo=%s "
        "quantidade=%s saldo=%s",
        user.id, product.id, tipo, motivo, quantidade, product.current_stock,
    )

    return movimentacao


# --------------------------------------------------------------------------
# Consultas
# --------------------------------------------------------------------------

def intervalo_do_dia(dia=None):
    """Começo e fim do dia local, em UTC (o banco grava created_at em UTC)."""
    dia = dia or hoje()
    tz = fuso()

    inicio_local = datetime.combine(dia, time.min, tzinfo=tz)
    fim_local = inicio_local + timedelta(days=1)

    return (
        inicio_local.astimezone(timezone.utc).replace(tzinfo=None),
        fim_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


def movimentacoes_do_haras(stable_id):
    """Query base: movimentações dos insumos deste haras."""
    return (
        db.session.query(StockMovement)
        .join(Product, StockMovement.product_id == Product.id)
        .filter(Product.stable_id == stable_id)
    )


def _agregado(stable_id, inicio, fim, *colunas, group_by, joins=()):
    """SUM/COUNT por tipo no período, agrupado no banco."""
    query = (
        db.session.query(
            *colunas,
            StockMovement.type,
            db.func.coalesce(db.func.sum(StockMovement.quantity), 0),
            db.func.count(StockMovement.id),
        )
        .join(Product, StockMovement.product_id == Product.id)
    )

    for alvo, condicao in joins:
        query = query.join(alvo, condicao)

    return (
        query.filter(
            Product.stable_id == stable_id,
            StockMovement.created_at >= inicio,
            StockMovement.created_at < fim,
        )
        .group_by(*group_by, StockMovement.type)
        .all()
    )


def _somar(linhas, chaves=0):
    """Transforma as linhas agrupadas em {chave: {entradas, saidas, ...}}."""
    resumo = {}

    for linha in linhas:
        chave = tuple(linha[:chaves]) if chaves else ()
        tipo, soma, contagem = linha[-3], Decimal(str(linha[-2])), linha[-1]

        item = resumo.setdefault(
            chave,
            {"entradas": Decimal("0"), "saidas": Decimal("0"),
             "total_movimentacoes": 0},
        )
        item["entradas" if tipo == ENTRADA else "saidas"] += soma
        item["total_movimentacoes"] += contagem

    for item in resumo.values():
        item["saldo"] = item["entradas"] - item["saidas"]

    return resumo


def movimentacoes_do_dia(stable_id, dia=None):
    """Totais de entrada, saída e saldo do dia (uma consulta agregada)."""
    dia = dia or hoje()
    inicio, fim = intervalo_do_dia(dia)

    totais = _somar(
        _agregado(stable_id, inicio, fim, group_by=()),
    ).get((), {"entradas": Decimal("0"), "saidas": Decimal("0"),
              "saldo": Decimal("0"), "total_movimentacoes": 0})

    return {"data": dia, **totais}


def registro_do_dia(stable_id, dia=None):
    """Registro diário completo: totais + quebra por insumo e por usuário."""
    dia = dia or hoje()
    inicio, fim = intervalo_do_dia(dia)

    registro = movimentacoes_do_dia(stable_id, dia)

    por_produto = _somar(
        _agregado(stable_id, inicio, fim, Product.id, Product.name,
                  group_by=(Product.id, Product.name)),
        chaves=2,
    )
    por_usuario = _somar(
        _agregado(stable_id, inicio, fim, User.id, User.name,
                  group_by=(User.id, User.name),
                  joins=((User, StockMovement.user_id == User.id),)),
        chaves=2,
    )

    registro["produtos"] = [
        {"id": chave[0], "name": chave[1], **valores}
        for chave, valores in sorted(por_produto.items(), key=lambda par: par[0][1])
    ]
    registro["usuarios"] = [
        {"id": chave[0], "name": chave[1], **valores}
        for chave, valores in sorted(por_usuario.items(), key=lambda par: par[0][1])
    ]

    return registro


def registro_por_periodo(stable_id, inicio, fim):
    """Um registro diário para cada dia do intervalo (inclusive)."""
    dias = (fim - inicio).days + 1

    return [registro_do_dia(stable_id, inicio + timedelta(days=i)) for i in range(dias)]


def ultimas_movimentacoes(stable_id, limite=10):
    """As movimentações mais recentes do haras."""
    return (
        movimentacoes_do_haras(stable_id)
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .limit(limite)
        .all()
    )


__all__ = [
    "ENTRADA",
    "SAIDA",
    "TIPOS",
    "MOTIVOS_POR_TIPO",
    "ConflitoDeEstoque",
    "registrar_movimentacao",
    "intervalo_do_dia",
    "movimentacoes_do_haras",
    "movimentacoes_do_dia",
    "registro_do_dia",
    "registro_por_periodo",
    "ultimas_movimentacoes",
]
