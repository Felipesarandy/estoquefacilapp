"""Alertas: estoque mínimo, dias de cobertura e capital imobilizado.

Única fonte da verdade da "quebra de estoque": o colchão mínimo
(`min_stock`) e o aviso com alguns dias de antecedência.

    cobertura_dias = current_stock / daily_consumption   (None sem consumo)

Níveis, do mais grave para o menos grave (vale sempre o mais grave):

    ruptura  current_stock <= 0
    critico  current_stock <= min_stock          (o colchão foi rompido)
    atencao  cobertura_dias <= ALERTA_DIAS_ANTECEDENCIA
    ok       nenhum dos anteriores
"""
from datetime import datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app

from app.extensions import db
from app.models import Product

RUPTURA = "ruptura"
CRITICO = "critico"
ATENCAO = "atencao"
OK = "ok"

# Ordem de gravidade usada para ordenar as listagens
GRAVIDADE = {RUPTURA: 0, CRITICO: 1, ATENCAO: 2, OK: 3}

DIAS_ANTECEDENCIA_PADRAO = 5
TIMEZONE_PADRAO = "America/Sao_Paulo"


def dias_antecedencia():
    """Quantos dias antes da quebra o alerta começa (config/env)."""
    return int(current_app.config.get("ALERTA_DIAS_ANTECEDENCIA", DIAS_ANTECEDENCIA_PADRAO))


@lru_cache(maxsize=8)
def _zona(nome):
    """Fuso pelo nome; cai no fuso do sistema se o tzdata não estiver instalado."""
    try:
        return ZoneInfo(nome)
    except ZoneInfoNotFoundError:
        return datetime.now().astimezone().tzinfo


def fuso():
    """Fuso configurado para o haras."""
    return _zona(current_app.config.get("TIMEZONE", TIMEZONE_PADRAO))


def agora():
    """Agora no fuso do haras."""
    return datetime.now(fuso())


def hoje():
    """Data de hoje no fuso do haras."""
    return agora().date()


def cobertura_dias(produto):
    """Dias que o saldo ainda cobre; None quando não há consumo informado.

    É a mesma conta de `Product.days_left` (saldo ÷ consumo diário);
    reaproveitada daqui para não existirem duas fórmulas.
    """
    return produto.days_left


def nivel(produto, cobertura=None):
    """Nível do insumo; vale sempre o mais grave."""
    if produto.current_stock is not None and produto.current_stock <= 0:
        return RUPTURA

    if produto.is_low_stock:
        return CRITICO

    cobertura = cobertura_dias(produto) if cobertura is None else cobertura

    if cobertura is not None and cobertura <= dias_antecedencia():
        return ATENCAO

    return OK


def data_prevista_ruptura(produto, cobertura=None):
    """Dia em que o saldo deve zerar (hoje + cobertura); None sem consumo."""
    cobertura = cobertura_dias(produto) if cobertura is None else cobertura

    if cobertura is None:
        return None

    dias = int(cobertura) if cobertura > 0 else 0

    return hoje() + timedelta(days=dias)


def min_stock_sugerido(produto):
    """Colchão mínimo sugerido: consumo diário x dias de antecedência."""
    if not produto.daily_consumption:
        return None

    return produto.daily_consumption * Decimal(dias_antecedencia())


def resumo(produto):
    """Tudo o que a API mostra sobre a situação de estoque do insumo."""
    cobertura = cobertura_dias(produto)
    situacao = nivel(produto, cobertura)

    return {
        "nivel": situacao,
        "cobertura_dias": cobertura,
        "data_prevista_ruptura": data_prevista_ruptura(produto, cobertura),
        "min_stock_sugerido": min_stock_sugerido(produto),
        # compatibilidade: mesma regra, sem conta duplicada
        "days_left": cobertura,
        "is_low_stock": situacao in (RUPTURA, CRITICO),
    }


def em_alerta(produto):
    """O insumo precisa de atenção (qualquer nível diferente de "ok")."""
    return nivel(produto) != OK


def ordenar_por_gravidade(produtos):
    """Mais grave primeiro e, dentro do nível, menor cobertura primeiro."""

    def chave(produto):
        cobertura = cobertura_dias(produto)
        situacao = nivel(produto, cobertura)
        sem_cobertura = cobertura is None

        return (
            GRAVIDADE[situacao],
            sem_cobertura,
            cobertura if not sem_cobertura else 0,
            produto.name or "",
            produto.id or 0,
        )

    return sorted(produtos, key=chave)


def produtos_ativos(stable_id):
    """Insumos ativos do haras (uma única consulta, sem N+1)."""
    return (
        db.session.query(Product)
        .filter(Product.stable_id == stable_id, Product.active.is_(True))
        .order_by(Product.name)
        .all()
    )


def listar_em_alerta(stable_id, filtro_nivel=None):
    """Insumos ativos fora do "ok", já ordenados por gravidade.

    `filtro_nivel` restringe a um nível ("ruptura", "critico" ou "atencao").
    """
    selecionados = [
        produto
        for produto in produtos_ativos(stable_id)
        if nivel(produto) != OK
        and (filtro_nivel is None or nivel(produto) == filtro_nivel)
    ]

    return ordenar_por_gravidade(selecionados)


def contagem_por_nivel(produtos):
    """Quantos insumos há em cada nível (inclusive "ok")."""
    contagem = {RUPTURA: 0, CRITICO: 0, ATENCAO: 0, OK: 0}

    for produto in produtos:
        contagem[nivel(produto)] += 1

    return contagem


__all__ = [
    "RUPTURA",
    "CRITICO",
    "ATENCAO",
    "OK",
    "GRAVIDADE",
    "dias_antecedencia",
    "fuso",
    "agora",
    "hoje",
    "cobertura_dias",
    "nivel",
    "data_prevista_ruptura",
    "min_stock_sugerido",
    "resumo",
    "em_alerta",
    "ordenar_por_gravidade",
    "produtos_ativos",
    "listar_em_alerta",
    "contagem_por_nivel",
]
