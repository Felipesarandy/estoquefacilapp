"""AuditLog e InventoryCount são imutáveis; Incident valida seus domínios."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models import AuditLog, Incident, InventoryCount
from app.services import audit


def test_audit_log_nao_pode_ser_alterado(db, haras):
    log = audit.record(haras["user"], "login", "user", haras["user"].id)
    db.session.commit()

    log.action = "create"

    with pytest.raises(RuntimeError, match="imutável"):
        db.session.commit()

    db.session.rollback()
    assert db.session.get(AuditLog, log.id).action == "login"


def test_audit_log_nao_pode_ser_removido(db, haras):
    log = audit.record(haras["user"], "login", "user", haras["user"].id)
    db.session.commit()

    db.session.delete(log)

    with pytest.raises(RuntimeError, match="imutável"):
        db.session.commit()

    db.session.rollback()
    assert db.session.get(AuditLog, log.id) is not None


def test_audit_log_aceita_falha_sem_haras_nem_usuario(db):
    log = audit.record(None, "login_failed", "user", after={"email": "x@x.com"})
    db.session.commit()

    assert log.id is not None
    assert log.stable_id is None
    assert log.user_id is None
    assert log.created_at is not None


def test_contagem_de_inventario_e_imutavel(db, haras):
    contagem = InventoryCount(product=haras["product"], user=haras["user"],
                              system_quantity=5, counted_quantity=5)
    db.session.add(contagem)
    db.session.commit()

    contagem.counted_quantity = 99

    with pytest.raises(RuntimeError, match="imutável"):
        db.session.commit()

    db.session.rollback()


@pytest.mark.parametrize("campo, valor", [
    ("type", "enchente"),
    ("status", "pendente"),
    ("severity", "gravissima"),
])
def test_incidente_rejeita_valor_fora_do_dominio(db, haras, campo, valor):
    dados = {"stable_id": haras["stable"].id, "type": "outro", "status": "aberto",
             "severity": "baixa", "description": "teste"}
    dados[campo] = valor

    db.session.add(Incident(**dados))

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_incidente_nasce_aberto(db, haras):
    incidente = Incident(stable_id=haras["stable"].id, type="outro",
                         severity="baixa", description="teste")
    db.session.add(incidente)
    db.session.commit()

    assert incidente.status == "aberto"
    assert incidente.opened_at is not None
    assert incidente.closed_at is None
