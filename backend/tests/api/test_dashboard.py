"""Painel do haras (/api/dashboard)."""
import pytest

from app.services.stock import registrar_movimentacao

DASHBOARD = "/api/dashboard"


@pytest.fixture
def admin_headers(admin, auth_headers):
    return auth_headers("admin@teste.com", "admin12345")


def test_contagens_por_nivel(client, haras, insumo, admin_headers):
    insumo("Ok", saldo="100", minimo="1", consumo="1")
    insumo("Atenção", saldo="3", minimo="0", consumo="1")
    insumo("Crítico", saldo="5", minimo="10", consumo="1")
    insumo("Inativo", saldo="0", minimo="1", consumo="1", active=False)

    corpo = client.get(DASHBOARD, headers=admin_headers).get_json()

    assert corpo["produtos_ativos"] == 4  # 3 criados + a "Ração" da fixture
    assert corpo["por_nivel"] == {"ruptura": 1, "critico": 1, "atencao": 1, "ok": 1}
    assert corpo["em_alerta"] == 3
    assert corpo["dias_antecedencia"] == 5


def test_mais_urgentes_ordenados_e_limitados(client, haras, insumo, admin_headers):
    for i in range(12):
        insumo(f"Zerado {i:02d}", saldo="0", minimo="1", consumo="1")
    insumo("Atenção", saldo="3", minimo="0", consumo="1")

    corpo = client.get(DASHBOARD, headers=admin_headers).get_json()

    assert len(corpo["mais_urgentes"]) == 10
    assert {item["nivel"] for item in corpo["mais_urgentes"]} == {"ruptura"}
    assert corpo["em_alerta"] == 14


def test_movimentacoes_de_hoje(client, db, haras, admin, insumo, admin_headers):
    produto = insumo("Ração peletizada", saldo="0", minimo="10", consumo="5")

    registrar_movimentacao(admin, produto, "entrada", 100, "compra")
    registrar_movimentacao(admin, produto, "saida", 30, "trato_manual")
    db.session.commit()

    corpo = client.get(DASHBOARD, headers=admin_headers).get_json()
    hoje = corpo["movimentacoes_hoje"]

    assert hoje["entradas"] == "100.000"
    assert hoje["saidas"] == "30.000"
    assert hoje["saldo"] == "70.000"
    assert hoje["total_movimentacoes"] == 2
    assert hoje["data"]


def test_sem_movimentacoes_os_totais_sao_zero(client, haras, admin_headers):
    hoje = client.get(DASHBOARD, headers=admin_headers).get_json()["movimentacoes_hoje"]

    assert hoje["entradas"] == "0"
    assert hoje["saidas"] == "0"
    assert hoje["saldo"] == "0"
    assert hoje["total_movimentacoes"] == 0


def test_ultimas_movimentacoes(client, db, haras, admin, insumo, admin_headers):
    produto = insumo("Feno", saldo="0", minimo="5", consumo="2")

    registrar_movimentacao(admin, produto, "entrada", 50, "compra")
    for _ in range(11):
        registrar_movimentacao(admin, produto, "saida", 1, "trato_manual")
    db.session.commit()

    ultimas = client.get(DASHBOARD, headers=admin_headers).get_json()["ultimas_movimentacoes"]

    assert len(ultimas) == 10
    assert ultimas[0]["type"] == "saida"
    assert ultimas[0]["product_id"] == produto.id
    assert ultimas[0]["quantity"] == "1.000"
    assert ultimas[0]["total_cost"] == "1.00000"
    assert ultimas[0]["created_at"]


def test_isolamento_entre_haras(client, db, haras, outro_haras, admin, insumo,
                                auth_headers):
    produto = insumo("Ração", saldo="0", minimo="5", consumo="1")
    registrar_movimentacao(admin, produto, "entrada", 10, "compra")
    db.session.commit()

    corpo = client.get(
        DASHBOARD, headers=auth_headers("outro@teste.com", "outro12345")
    ).get_json()

    assert corpo["produtos_ativos"] == 0
    assert corpo["em_alerta"] == 0
    assert corpo["mais_urgentes"] == []
    assert corpo["ultimas_movimentacoes"] == []
    assert corpo["movimentacoes_hoje"]["total_movimentacoes"] == 0


def test_tratador_tambem_consulta(client, haras, tratador, auth_headers):
    resposta = client.get(DASHBOARD, headers=auth_headers("tratador@teste.com",
                                                          "tratador123"))

    assert resposta.status_code == 200


def test_exige_token(client, haras):
    resposta = client.get(DASHBOARD)

    assert resposta.status_code == 401
