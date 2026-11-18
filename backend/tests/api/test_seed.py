"""O `flask seed` deve montar uma demonstração com os quatro níveis."""
from datetime import timedelta

import pytest

from app.models import AuditLog, Incident, InventoryCount, Product, StockMovement
from app.seed import DIAS_DE_HISTORICO, seed_command
from app.services.alerts import hoje


@pytest.fixture
def banco_populado(app, db):
    """Roda o comando `flask seed` no banco de teste."""
    resultado = app.test_cli_runner().invoke(seed_command, ["--force"])

    assert resultado.exit_code == 0, resultado.output
    return resultado.output


@pytest.fixture
def headers(client, banco_populado):
    resposta = client.post("/api/auth/login",
                           json={"email": "admin@haras.com", "password": "admin123"})

    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.get_json()['access_token']}"}


def test_seed_cria_os_usuarios_da_demonstracao(banco_populado):
    assert "Banco populado!" in banco_populado
    assert "admin@haras.com" in banco_populado
    assert "tratador@haras.com" in banco_populado


def test_dashboard_tem_os_quatro_niveis(client, headers):
    corpo = client.get("/api/dashboard", headers=headers).get_json()
    por_nivel = corpo["por_nivel"]

    assert por_nivel["ruptura"] >= 1
    assert por_nivel["critico"] >= 1
    assert por_nivel["atencao"] >= 1
    assert por_nivel["ok"] >= 1
    assert corpo["produtos_ativos"] == sum(por_nivel.values())


def test_alertas_cobrem_os_tres_niveis_de_acao(client, headers):
    corpo = client.get("/api/alerts", headers=headers).get_json()
    niveis = {item["nivel"] for item in corpo["items"]}

    assert niveis == {"ruptura", "critico", "atencao"}
    assert corpo["total"] == len(corpo["items"])


def test_alerta_de_atencao_tem_cobertura_curta(client, headers):
    corpo = client.get("/api/alerts?nivel=atencao", headers=headers).get_json()

    assert corpo["total"] >= 1

    for item in corpo["items"]:
        assert float(item["cobertura_dias"]) <= corpo["dias_antecedencia"]
        assert item["data_prevista_ruptura"]
        assert item["min_stock_sugerido"]


def test_movimentacoes_espalhadas_pelos_ultimos_dias(client, db, headers):
    inicio = (hoje() - timedelta(days=DIAS_DE_HISTORICO - 1)).isoformat()
    corpo = client.get(f"/api/movements/daily?from={inicio}&to={hoje().isoformat()}",
                       headers=headers).get_json()

    dias_com_movimento = [d for d in corpo["dias"] if d["total_movimentacoes"] > 0]

    assert len(corpo["dias"]) == DIAS_DE_HISTORICO
    assert len(dias_com_movimento) >= 5
    assert db.session.query(StockMovement).count() > 20


def test_entradas_do_seed_tem_lote_e_validade(client, db, headers):
    com_lote = (
        db.session.query(StockMovement)
        .filter(StockMovement.batch.isnot(None),
                StockMovement.expiration_date.isnot(None))
        .count()
    )

    assert com_lote >= 3


def test_saldos_nunca_ficam_negativos(client, db, headers):
    saldos = [p.current_stock for p in db.session.query(Product).all()]

    assert saldos
    assert all(saldo >= 0 for saldo in saldos)


def test_seed_sem_force_pede_confirmacao_e_aborta(app, db):
    resultado = app.test_cli_runner().invoke(seed_command, input="n\n")

    assert resultado.exit_code == 1
    assert "APAGA" in resultado.output
    assert db.session.query(Product).count() == 0


def test_seed_sem_force_confirmado_popula(app, db):
    resultado = app.test_cli_runner().invoke(seed_command, input="y\n")

    assert resultado.exit_code == 0
    assert "Banco populado!" in resultado.output


def test_seed_cria_incidentes_e_inventario(client, db, headers):
    incidentes = {(i.type, i.status) for i in db.session.query(Incident).all()}

    assert ("ruptura", "aberto") in incidentes            # vitamínico zerou
    assert ("divergencia_inventario", "aberto") in incidentes
    assert ("avaria", "em_analise") in incidentes        # manual, atribuído
    assert db.session.query(InventoryCount).count() == 1

    em_analise = db.session.query(Incident).filter_by(status="em_analise").one()
    assert em_analise.assigned_to.email == "admin@haras.com"


def test_seed_tem_trilha_de_auditoria(client, db, headers):
    acoes = {log.action for log in db.session.query(AuditLog).all()}

    assert {"create", "movement", "inventory", "incident", "login"} <= acoes
