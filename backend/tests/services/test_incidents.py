"""Gestão de incidentes: severidade, ciclo de vida e ruptura automática."""
from decimal import Decimal

import pytest

from app.models import AuditLog, Incident
from app.schemas.common import ValidationError
from app.services import incidents
from app.services.exceptions import TransicaoInvalida
from app.services.stock import registrar_movimentacao


@pytest.fixture
def incidente(db, haras):
    item, _ = incidents.abrir_incidente(haras["stable"].id, "avaria", "Saco rasgado",
                                        severity="baixa", product=haras["product"],
                                        opened_by=haras["user"])
    db.session.commit()
    return item


# ---------------------------------------------------------------- severidade

@pytest.mark.parametrize("sistema, diferenca, esperado", [
    ("100", "-20", "alta"),    # 20% exatos
    ("100", "25", "alta"),
    ("100", "-19.999", "media"),
    ("100", "5", "media"),     # 5% exatos
    ("100", "-4.999", "baixa"),
    ("100", "0", "baixa"),
    ("0", "3", "alta"),        # sem saldo no sistema não há percentual
])
def test_severidade_da_divergencia(sistema, diferenca, esperado):
    assert incidents.severidade_divergencia(Decimal(sistema), Decimal(diferenca)) == esperado


def test_ruptura_e_sempre_critica(db, haras):
    item, _ = incidents.abrir_incidente(haras["stable"].id, "ruptura", "zerou",
                                        product=haras["product"])

    assert item.severity == "critica"


# ------------------------------------------------------------------ abertura

def test_nao_duplica_incidente_ativo(db, haras, incidente):
    repetido, criado = incidents.abrir_incidente(
        haras["stable"].id, "avaria", "De novo", product=haras["product"])

    assert criado is False
    assert repetido.id == incidente.id
    assert db.session.query(Incident).count() == 1


def test_abre_novo_depois_de_resolvido(db, haras, incidente):
    incidents.mudar_status(incidente, "resolvido", haras["user"], "Trocado")
    novo, criado = incidents.abrir_incidente(
        haras["stable"].id, "avaria", "Outro saco", product=haras["product"])

    assert criado is True
    assert novo.id != incidente.id


def test_abertura_e_auditada(db, haras, incidente):
    log = db.session.query(AuditLog).filter_by(action="incident").one()

    assert log.entity == "incident"
    assert log.entity_id == incidente.id
    assert log.after_json["status"] == "aberto"


# ------------------------------------------------------------- ciclo de vida

@pytest.mark.parametrize("caminho", [
    ["em_analise"],
    ["resolvido"],
    ["em_analise", "resolvido"],
    ["em_analise", "aberto"],
    ["resolvido", "fechado"],
    ["resolvido", "em_analise"],
    ["em_analise", "resolvido", "fechado"],
])
def test_transicoes_validas(db, haras, incidente, caminho):
    for status in caminho:
        incidents.mudar_status(incidente, status, haras["user"], resolution="Feito")

    assert incidente.status == caminho[-1]


@pytest.mark.parametrize("caminho", [
    ["fechado"],                              # aberto -> fechado
    ["em_analise", "fechado"],                # em_analise -> fechado
    ["resolvido", "aberto"],                  # resolvido -> aberto
    ["resolvido", "fechado", "em_analise"],   # fechado é final
    ["resolvido", "fechado", "aberto"],
])
def test_transicoes_invalidas(db, haras, incidente, caminho):
    with pytest.raises(TransicaoInvalida, match="Transição inválida"):
        for status in caminho:
            incidents.mudar_status(incidente, status, haras["user"], resolution="Feito")


def test_resolver_exige_resolucao(db, haras, incidente):
    with pytest.raises(ValidationError) as erro:
        incidents.mudar_status(incidente, "resolvido", haras["user"])

    assert erro.value.field == "resolution"
    assert incidente.status == "aberto"


def test_resolucao_em_branco_nao_vale(db, haras, incidente):
    with pytest.raises(ValidationError):
        incidents.mudar_status(incidente, "resolvido", haras["user"], resolution="   ")


def test_closed_at_ao_resolver_fechar_e_reabrir(db, haras, incidente):
    incidents.mudar_status(incidente, "resolvido", haras["user"], "Trocado")
    resolvido_em = incidente.closed_at
    assert resolvido_em is not None

    incidents.mudar_status(incidente, "fechado", haras["user"])
    assert incidente.closed_at == resolvido_em

    outro, _ = incidents.abrir_incidente(haras["stable"].id, "furto", "Sumiu")
    incidents.mudar_status(outro, "resolvido", haras["user"], "Achado")
    incidents.mudar_status(outro, "em_analise", haras["user"])
    assert outro.closed_at is None


def test_atualizacao_e_auditada_com_antes_e_depois(db, haras, incidente):
    incidents.atualizar_incidente(incidente, haras["user"], status="em_analise",
                                  assigned_to=haras["user"], atribuir=True)
    db.session.commit()

    log = (db.session.query(AuditLog).filter_by(action="incident")
           .order_by(AuditLog.id.desc()).first())

    assert log.before_json["status"] == "aberto"
    assert log.after_json["status"] == "em_analise"
    assert log.after_json["assigned_to_id"] == haras["user"].id


# --------------------------------------------------------- ruptura automática

def test_saida_que_zera_abre_ruptura(db, haras, insumo):
    produto = insumo("Feno", saldo="0", minimo="5", consumo="1")
    registrar_movimentacao(haras["user"], produto, "entrada", 10, "compra")
    registrar_movimentacao(haras["user"], produto, "saida", 10, "trato_manual")
    db.session.commit()

    ruptura = db.session.query(Incident).filter_by(product_id=produto.id).one()

    assert ruptura.type == "ruptura"
    assert ruptura.status == "aberto"
    assert ruptura.severity == "critica"
    assert ruptura.opened_by_id is None  # aberto pelo sistema


def test_ruptura_nao_duplica(db, haras, insumo):
    produto = insumo("Feno", saldo="0", minimo="5", consumo="1")
    registrar_movimentacao(haras["user"], produto, "entrada", 10, "compra")
    registrar_movimentacao(haras["user"], produto, "saida", 10, "trato_manual")
    incidents.sincronizar_ruptura(produto, haras["user"])
    incidents.sincronizar_ruptura(produto, haras["user"])
    db.session.commit()

    assert db.session.query(Incident).filter_by(product_id=produto.id).count() == 1


def test_reposicao_resolve_ruptura_sozinha(db, haras, insumo):
    produto = insumo("Feno", saldo="0", minimo="5", consumo="1")
    registrar_movimentacao(haras["user"], produto, "entrada", 10, "compra")
    registrar_movimentacao(haras["user"], produto, "saida", 10, "trato_manual")
    registrar_movimentacao(haras["user"], produto, "entrada", 3, "compra")
    db.session.commit()

    ruptura = db.session.query(Incident).filter_by(product_id=produto.id).one()

    assert ruptura.status == "resolvido"
    assert ruptura.resolution == incidents.RESOLUCAO_REPOSICAO
    assert ruptura.closed_at is not None


def test_entrada_sem_ruptura_nao_cria_incidente(db, haras, insumo):
    produto = insumo("Feno", saldo="0", minimo="5", consumo="1")
    registrar_movimentacao(haras["user"], produto, "entrada", 10, "compra")
    db.session.commit()

    assert db.session.query(Incident).count() == 0


def test_movimentacao_gera_auditoria(db, haras, insumo):
    produto = insumo("Feno", saldo="0", minimo="5", consumo="1")
    mov = registrar_movimentacao(haras["user"], produto, "entrada", 10, "compra")
    db.session.commit()

    log = db.session.query(AuditLog).filter_by(action="movement").one()

    assert log.entity == "movement"
    assert log.entity_id == mov.id
    assert Decimal(log.after_json["quantity"]) == 10
    assert log.user_id == haras["user"].id


# ----------------------------------------------------------------- resumo

def test_resumo_conta_e_mede_resolucao(db, haras, incidente):
    outro, _ = incidents.abrir_incidente(haras["stable"].id, "furto", "Sumiu")
    incidents.mudar_status(outro, "resolvido", haras["user"], "Achado")
    db.session.commit()

    resumo = incidents.resumo(haras["stable"].id)

    assert resumo["total"] == 2
    assert resumo["por_status"] == {"aberto": 1, "resolvido": 1}
    assert resumo["por_tipo"] == {"avaria": 1, "furto": 1}
    assert resumo["encerrados"] == 1
    assert resumo["tempo_medio_resolucao_horas"] >= 0


def test_resumo_sem_encerrados(db, haras, incidente):
    assert incidents.resumo(haras["stable"].id)["tempo_medio_resolucao_horas"] is None
