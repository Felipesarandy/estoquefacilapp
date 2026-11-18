"""Serviço de auditoria: snapshot sem senha e registro sem commit."""
from datetime import date, datetime
from decimal import Decimal

from app.models import AuditLog
from app.services import audit


def test_snapshot_nunca_inclui_senha(haras):
    foto = audit.snapshot(haras["user"])

    assert "password_hash" not in foto
    assert "password" not in foto
    assert foto["email"] == "admin@teste.com"
    assert foto["role"] == "admin"


def test_snapshot_converte_tipos_para_json(db, haras):
    produto = haras["product"]
    produto.daily_consumption = Decimal("2.500")
    db.session.commit()

    foto = audit.snapshot(produto)

    assert foto["cost_price"] == "10.00"
    assert foto["daily_consumption"] == "2.500"
    assert isinstance(foto["active"], bool)


def test_snapshot_de_datas(db, haras):
    from app.models import StockMovement

    mov = StockMovement(product=haras["product"], user=haras["user"], type="entrada",
                        reason="compra", quantity=1, unit_cost=1,
                        expiration_date=date(2027, 1, 31),
                        created_at=datetime(2026, 11, 1, 12, 30))
    db.session.add(mov)
    db.session.flush()

    foto = audit.snapshot(mov)

    assert foto["expiration_date"] == "2027-01-31"
    assert foto["created_at"] == "2026-11-01T12:30:00"


def test_snapshot_de_nada_e_none():
    assert audit.snapshot(None) is None


def test_record_nao_faz_commit(db, haras):
    audit.record(haras["user"], "login", "user", haras["user"].id)
    db.session.rollback()

    assert db.session.query(AuditLog).count() == 0


def test_record_herda_o_haras_do_usuario(db, haras):
    log = audit.record(haras["user"], "login", "user", haras["user"].id)
    db.session.commit()

    assert log.stable_id == haras["stable"].id
    assert log.user_id == haras["user"].id
    assert log.ip is None  # fora de uma requisição


def test_acao_de_alteracao():
    assert audit.acao_de_alteracao({"active": True}, {"active": False}) == "deactivate"
    assert audit.acao_de_alteracao({"active": False}, {"active": True}) == "update"
    assert audit.acao_de_alteracao({"name": "a"}, {"name": "b"}) == "update"


def test_consulta_filtra_por_haras_e_acao(db, haras, outro_haras):
    audit.record(haras["user"], "login", "user", haras["user"].id)
    audit.record(haras["user"], "create", "product", 1)
    audit.record(outro_haras["user"], "login", "user", outro_haras["user"].id)
    db.session.commit()

    do_haras = audit.consultar(haras["stable"].id).all()
    logins = audit.consultar(haras["stable"].id, action="login").all()

    assert len(do_haras) == 2
    assert [log.action for log in logins] == ["login"]
