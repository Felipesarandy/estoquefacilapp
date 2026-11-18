"""Lista de alertas de estoque (/api/alerts)."""
import pytest

ALERTS = "/api/alerts"


@pytest.fixture
def admin_headers(admin, auth_headers):
    return auth_headers("admin@teste.com", "admin12345")


def test_lista_so_o_que_precisa_de_atencao(client, haras, insumo, admin_headers):
    insumo("Tranquilo", saldo="100", minimo="1", consumo="1")
    insumo("Inativo zerado", saldo="0", minimo="5", consumo="1", active=False)
    insumo("Atenção", saldo="3", minimo="0", consumo="1")

    corpo = client.get(ALERTS, headers=admin_headers).get_json()
    nomes = [item["name"] for item in corpo["items"]]

    # "Ração" (saldo 0) vem da fixture `haras`
    assert set(nomes) == {"Ração", "Atenção"}
    assert corpo["total"] == 2
    assert corpo["dias_antecedencia"] == 5


def test_ordenacao_por_gravidade(client, haras, insumo, admin_headers):
    insumo("Crítico", saldo="5", minimo="10", consumo="1")
    insumo("Atenção 4", saldo="4", minimo="0", consumo="1")
    insumo("Atenção 2", saldo="2", minimo="0", consumo="1")

    corpo = client.get(ALERTS, headers=admin_headers).get_json()

    assert [item["nivel"] for item in corpo["items"]] == [
        "ruptura", "critico", "atencao", "atencao",
    ]
    assert [item["name"] for item in corpo["items"]] == [
        "Ração", "Crítico", "Atenção 2", "Atenção 4",
    ]


def test_item_traz_todos_os_campos(client, haras, insumo, admin_headers):
    insumo("Ração peletizada", saldo="10", minimo="0", consumo="2", code="EQ001")

    corpo = client.get(f"{ALERTS}?nivel=atencao", headers=admin_headers).get_json()
    item = corpo["items"][0]

    assert item["name"] == "Ração peletizada"
    assert item["code"] == "EQ001"
    assert item["current_stock"] == "10.000"
    assert item["min_stock"] == "0.000"
    assert item["daily_consumption"] == "2.000"
    assert item["cobertura_dias"] == "5"
    assert item["min_stock_sugerido"] == "10.000"
    assert item["data_prevista_ruptura"]
    assert item["nivel"] == "atencao"


def test_filtro_por_nivel(client, haras, insumo, admin_headers):
    insumo("Crítico", saldo="5", minimo="10", consumo="1")
    insumo("Atenção", saldo="3", minimo="0", consumo="1")

    for nivel, esperado in (("ruptura", ["Ração"]),
                            ("critico", ["Crítico"]),
                            ("atencao", ["Atenção"])):
        corpo = client.get(f"{ALERTS}?nivel={nivel}", headers=admin_headers).get_json()
        assert [i["name"] for i in corpo["items"]] == esperado
        assert corpo["total"] == 1


def test_filtro_ok_nao_e_aceito(client, haras, admin_headers):
    resposta = client.get(f"{ALERTS}?nivel=ok", headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "nivel"}


def test_nivel_invalido_e_422(client, haras, admin_headers):
    resposta = client.get(f"{ALERTS}?nivel=urgente", headers=admin_headers)

    assert resposta.status_code == 422


def test_paginacao(client, haras, insumo, admin_headers):
    for i in range(3):
        insumo(f"Zerado {i}", saldo="0", minimo="1", consumo="1")

    pagina1 = client.get(f"{ALERTS}?per_page=2", headers=admin_headers).get_json()
    pagina2 = client.get(f"{ALERTS}?per_page=2&page=2", headers=admin_headers).get_json()

    assert pagina1["total"] == 4  # 3 + a "Ração" da fixture
    assert len(pagina1["items"]) == 2
    assert len(pagina2["items"]) == 2
    assert client.get(f"{ALERTS}?per_page=500",
                      headers=admin_headers).get_json()["per_page"] == 100


def test_antecedencia_configuravel(client, app, haras, insumo, admin_headers):
    insumo("Dez dias", saldo="20", minimo="0", consumo="2")

    antes = client.get(f"{ALERTS}?nivel=atencao", headers=admin_headers).get_json()
    assert antes["total"] == 0

    app.config["ALERTA_DIAS_ANTECEDENCIA"] = 15

    depois = client.get(f"{ALERTS}?nivel=atencao", headers=admin_headers).get_json()
    assert [i["name"] for i in depois["items"]] == ["Dez dias"]
    assert depois["dias_antecedencia"] == 15


def test_tratador_tambem_consulta(client, haras, tratador, auth_headers):
    resposta = client.get(ALERTS, headers=auth_headers("tratador@teste.com", "tratador123"))

    assert resposta.status_code == 200


def test_isolamento_entre_haras(client, haras, outro_haras, insumo, auth_headers):
    insumo("Zerado", saldo="0", minimo="5", consumo="1")

    corpo = client.get(
        ALERTS, headers=auth_headers("outro@teste.com", "outro12345")
    ).get_json()

    assert corpo["total"] == 0
    assert corpo["items"] == []


def test_exige_token(client, haras):
    resposta = client.get(ALERTS)

    assert resposta.status_code == 401
    assert resposta.get_json()["error"]["message"] == "Token de acesso obrigatório"
