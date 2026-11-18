from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Category, InventoryCount, Product, StockMovement, User
from app.services.stock import ConflitoDeEstoque, registrar_movimentacao


def test_senha_com_hash(haras):
    user = haras["user"]
    assert user.password_hash != "123"
    assert user.check_password("123")
    assert not user.check_password("errada")


def test_entrada_aumenta_saldo(db, haras):
    p = haras["product"]
    registrar_movimentacao(haras["user"], p, "entrada", 10, "compra")
    db.session.commit()
    assert p.current_stock == 10
    assert len(p.movements) == 1


def test_entrada_guarda_lote_e_validade(db, haras):
    mov = registrar_movimentacao(haras["user"], haras["product"], "entrada", 25, "compra",
                                 batch="L01", expiration_date=date(2027, 1, 1))
    db.session.commit()
    assert mov.batch == "L01"
    assert mov.expiration_date == date(2027, 1, 1)


def test_abastecimento_do_alimentador_diminui_saldo(db, haras):
    p = haras["product"]
    registrar_movimentacao(haras["user"], p, "entrada", 50, "compra")
    registrar_movimentacao(haras["user"], p, "saida", 20, "abastecimento_alimentador")
    db.session.commit()
    assert p.current_stock == 30


def test_saida_maior_que_saldo_e_bloqueada(haras):
    with pytest.raises(ConflitoDeEstoque):
        registrar_movimentacao(haras["user"], haras["product"], "saida", 1, "trato_manual")


def test_alerta_estoque_minimo(db, haras):
    p = haras["product"]
    registrar_movimentacao(haras["user"], p, "entrada", 5, "compra")
    assert p.is_low_stock          # 5 <= 5
    registrar_movimentacao(haras["user"], p, "entrada", 1, "compra")
    assert not p.is_low_stock      # 6 > 5


def test_capital_imobilizado(db, haras):
    p = haras["product"]
    registrar_movimentacao(haras["user"], p, "entrada", 3, "compra")
    assert p.stock_value == Decimal("30")   # 3 kg x R$ 10


def test_dias_de_cobertura(db, haras):
    p = haras["product"]
    assert p.days_left is None              # consumo diário não informado
    p.daily_consumption = Decimal("4")
    registrar_movimentacao(haras["user"], p, "entrada", 20, "compra")
    assert p.days_left == 5                 # 20 kg / 4 kg por dia


def test_diferenca_inventario(db, haras):
    c = InventoryCount(product=haras["product"], user=haras["user"],
                       system_quantity=10, counted_quantity=8)
    db.session.add(c)
    db.session.commit()
    assert c.difference == -2


def test_email_unico(db, haras):
    db.session.add(User(stable=haras["stable"], name="X", email="admin@teste.com", password_hash="h"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_categoria_unica_por_haras(db, haras):
    db.session.add(Category(stable=haras["stable"], name="Ração"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_codigo_unico_por_haras(db, haras):
    db.session.add(Product(stable=haras["stable"], category=haras["category"], name="Outro", code="1"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_quantidade_deve_ser_positiva(db, haras):
    db.session.add(StockMovement(product=haras["product"], user=haras["user"], type="entrada",
                                 reason="compra", quantity=0, unit_cost=1))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_saldo_nao_pode_ser_negativo(db, haras):
    haras["product"].current_stock = -1
    with pytest.raises(IntegrityError):
        db.session.commit()
