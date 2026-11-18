"""Registro atômico de movimentações (services/stock)."""
from datetime import date
from decimal import Decimal

import pytest

from app.models import StockMovement
from app.schemas.common import ValidationError
from app.services.stock import ConflitoDeEstoque, registrar_movimentacao


def test_entrada_aumenta_saldo_e_grava_custo(db, haras, insumo):
    produto = insumo("Ração", saldo="0", minimo="10", consumo="2")

    mov = registrar_movimentacao(haras["user"], produto, "entrada", "100.500", "compra",
                                 batch="L01", expiration_date=date(2027, 1, 1),
                                 note="10 sacos")
    db.session.commit()

    assert produto.current_stock == Decimal("100.500")
    assert mov.unit_cost == produto.cost_price
    assert mov.quantity == Decimal("100.500")
    assert mov.batch == "L01"
    assert mov.expiration_date == date(2027, 1, 1)
    assert mov.note == "10 sacos"
    assert mov.created_at is not None


def test_saida_diminui_saldo(db, haras, insumo):
    produto = insumo("Ração", saldo="100", minimo="10", consumo="2")

    registrar_movimentacao(haras["user"], produto, "saida", 40, "trato_manual")
    db.session.commit()

    assert produto.current_stock == Decimal("60.000")


def test_custo_gravado_e_o_do_momento(db, haras, insumo):
    produto = insumo("Ração", saldo="100", minimo="1", consumo="1")

    primeira = registrar_movimentacao(haras["user"], produto, "saida", 1, "trato_manual")
    produto.cost_price = Decimal("99.00")
    db.session.flush()
    segunda = registrar_movimentacao(haras["user"], produto, "saida", 1, "trato_manual")
    db.session.commit()

    assert primeira.unit_cost == Decimal("1.00")
    assert segunda.unit_cost == Decimal("99.00")


def test_saida_acima_do_saldo_e_recusada(db, haras, insumo):
    produto = insumo("Ração", saldo="10", minimo="1", consumo="1")

    with pytest.raises(ConflitoDeEstoque, match="Estoque insuficiente"):
        registrar_movimentacao(haras["user"], produto, "saida", "10.001", "trato_manual")

    db.session.rollback()
    assert produto.current_stock == Decimal("10.000")
    assert db.session.query(StockMovement).count() == 0


def test_saida_do_saldo_exato_e_permitida(db, haras, insumo):
    produto = insumo("Ração", saldo="10", minimo="1", consumo="1")

    registrar_movimentacao(haras["user"], produto, "saida", 10, "trato_manual")
    db.session.commit()

    assert produto.current_stock == Decimal("0.000")


def test_duas_saidas_a_segunda_estoura(db, haras, insumo):
    produto = insumo("Ração", saldo="10", minimo="1", consumo="1")

    registrar_movimentacao(haras["user"], produto, "saida", 6, "trato_manual")

    with pytest.raises(ConflitoDeEstoque):
        registrar_movimentacao(haras["user"], produto, "saida", 6, "trato_manual")

    db.session.rollback()
    assert produto.current_stock == Decimal("10.000")  # a transação inteira voltou


def test_produto_inativo_e_recusado(db, haras, insumo):
    produto = insumo("Inativo", saldo="100", minimo="1", consumo="1", active=False)

    with pytest.raises(ConflitoDeEstoque, match="inativo"):
        registrar_movimentacao(haras["user"], produto, "entrada", 10, "compra")


def test_motivo_invalido_para_o_tipo(db, haras, insumo):
    produto = insumo("Ração", saldo="100", minimo="1", consumo="1")

    with pytest.raises(ValidationError) as erro:
        registrar_movimentacao(haras["user"], produto, "entrada", 10, "trato_manual")

    assert erro.value.field == "reason"

    with pytest.raises(ValidationError):
        registrar_movimentacao(haras["user"], produto, "saida", 10, "compra")


def test_tipo_invalido(db, haras, insumo):
    produto = insumo("Ração", saldo="100", minimo="1", consumo="1")

    with pytest.raises(ValidationError) as erro:
        registrar_movimentacao(haras["user"], produto, "devolucao", 10, "compra")

    assert erro.value.field == "type"


@pytest.mark.parametrize("quantidade", ["0", "-5", "abc", None, True])
def test_quantidade_invalida(db, haras, insumo, quantidade):
    produto = insumo("Ração", saldo="100", minimo="1", consumo="1")

    with pytest.raises(ValidationError) as erro:
        registrar_movimentacao(haras["user"], produto, "entrada", quantidade, "compra")

    assert erro.value.field == "quantity"


def test_quantidade_com_casas_demais(db, haras, insumo):
    produto = insumo("Ração", saldo="100", minimo="1", consumo="1")

    with pytest.raises(ValidationError):
        registrar_movimentacao(haras["user"], produto, "entrada", "1.00001", "compra")


def test_estorno_por_ajuste(db, haras, insumo):
    produto = insumo("Ração", saldo="0", minimo="1", consumo="1")

    registrar_movimentacao(haras["user"], produto, "entrada", 10, "compra")
    registrar_movimentacao(haras["user"], produto, "saida", 10, "ajuste",
                           note="Estorno da entrada lançada errada")
    db.session.commit()

    assert produto.current_stock == Decimal("0.000")
    assert db.session.query(StockMovement).count() == 2
