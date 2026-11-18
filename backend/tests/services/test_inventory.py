"""Inventário: contagem, ajuste automático e incidente de divergência."""
from decimal import Decimal

import pytest

from app.models import AuditLog, Incident, StockMovement
from app.schemas.common import ValidationError
from app.services.exceptions import ConflitoDeEstoque
from app.services.inventory import registrar_contagem


@pytest.fixture
def sal(insumo):
    return insumo("Sal mineral", saldo="100", minimo="10", consumo="1")


def test_falta_gera_saida_de_ajuste_e_incidente(db, haras, sal):
    contagem, ajuste, incidente = registrar_contagem(haras["user"], sal, "90")
    db.session.commit()

    assert contagem.system_quantity == Decimal("100.000")
    assert contagem.difference == Decimal("-10.000")
    assert sal.current_stock == Decimal("90.000")

    assert ajuste.type == "saida"
    assert ajuste.reason == "ajuste"
    assert ajuste.quantity == Decimal("10.000")
    assert ajuste.note == f"Ajuste após inventário #{contagem.id}"

    assert incidente.type == "divergencia_inventario"
    assert incidente.severity == "media"  # 10%
    assert incidente.opened_by_id == haras["user"].id


def test_sobra_gera_entrada_de_ajuste(db, haras, sal):
    _, ajuste, incidente = registrar_contagem(haras["user"], sal, "130",
                                              note="Achados no depósito 2")
    db.session.commit()

    assert sal.current_stock == Decimal("130.000")
    assert ajuste.type == "entrada"
    assert ajuste.note.endswith(": Achados no depósito 2")
    assert incidente.severity == "alta"  # 30%


def test_pequena_divergencia_e_baixa(db, haras, sal):
    _, _, incidente = registrar_contagem(haras["user"], sal, "98")

    assert incidente.severity == "baixa"  # 2%


def test_sem_divergencia_nao_ajusta_nem_abre_incidente(db, haras, sal):
    contagem, ajuste, incidente = registrar_contagem(haras["user"], sal, "100")
    db.session.commit()

    assert contagem.difference == 0
    assert ajuste is None
    assert incidente is None
    assert db.session.query(StockMovement).count() == 0
    assert db.session.query(Incident).count() == 0


def test_contagem_e_auditada(db, haras, sal):
    contagem, ajuste, incidente = registrar_contagem(haras["user"], sal, "95",
                                                     note="Contagem semanal")
    db.session.commit()

    log = db.session.query(AuditLog).filter_by(action="inventory").one()

    assert log.entity == "inventory_count"
    assert log.entity_id == contagem.id
    assert log.after_json["difference"] == "-5.000"
    assert log.after_json["note"] == "Contagem semanal"
    assert log.after_json["adjustment_id"] == ajuste.id
    assert log.after_json["incident_id"] == incidente.id


def test_contagem_zerada_tambem_abre_ruptura(db, haras, sal):
    registrar_contagem(haras["user"], sal, "0")
    db.session.commit()

    tipos = {i.type for i in db.session.query(Incident).all()}

    assert tipos == {"divergencia_inventario", "ruptura"}


def test_quantidade_negativa_e_invalida(db, haras, sal):
    with pytest.raises(ValidationError) as erro:
        registrar_contagem(haras["user"], sal, "-1")

    assert erro.value.field == "counted_quantity"


def test_insumo_inativo_nao_e_inventariado(db, haras, insumo):
    inativo = insumo("Inativo", saldo="10", minimo="1", consumo="1", active=False)

    with pytest.raises(ConflitoDeEstoque):
        registrar_contagem(haras["user"], inativo, "5")
