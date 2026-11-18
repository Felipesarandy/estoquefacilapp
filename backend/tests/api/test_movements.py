"""Movimentações de estoque pela API (/api/movements)."""
from datetime import timedelta

import pytest

from app.services.alerts import hoje
from app.services.stock import registrar_movimentacao

MOVEMENTS = "/api/movements"
DAILY = f"{MOVEMENTS}/daily"


@pytest.fixture
def admin_headers(admin, auth_headers):
    return auth_headers("admin@teste.com", "admin12345")


@pytest.fixture
def tratador_headers(admin, tratador, auth_headers):
    return auth_headers("tratador@teste.com", "tratador123")


@pytest.fixture
def produto(insumo):
    return insumo("Ração peletizada", saldo="0", minimo="10", consumo="4", code="EQ001")


def _entrada(product_id, quantity="100", **extra):
    dados = {"product_id": product_id, "type": "entrada",
             "quantity": quantity, "reason": "compra"}
    dados.update(extra)
    return dados


def _saida(product_id, quantity="10", reason="trato_manual", **extra):
    dados = {"product_id": product_id, "type": "saida",
             "quantity": quantity, "reason": reason}
    dados.update(extra)
    return dados


# --------------------------------------------------------------- registro

def test_entrada_atualiza_saldo(client, produto, admin_headers):
    resposta = client.post(MOVEMENTS,
                           json=_entrada(produto.id, "100.500", batch="L01",
                                         expiration_date="2027-01-31",
                                         note="20 sacos"),
                           headers=admin_headers)
    corpo = resposta.get_json()

    assert resposta.status_code == 201
    assert corpo["current_stock"] == "100.500"
    assert corpo["movement"]["type"] == "entrada"
    assert corpo["movement"]["reason"] == "compra"
    assert corpo["movement"]["quantity"] == "100.500"
    assert corpo["movement"]["unit_cost"] == "1.00"
    assert corpo["movement"]["batch"] == "L01"
    assert corpo["movement"]["expiration_date"] == "2027-01-31"
    assert corpo["movement"]["note"] == "20 sacos"
    assert corpo["movement"]["user_id"]
    assert corpo["nivel"] == "ok"
    assert corpo["is_low_stock"] is False


def test_saida_atualiza_saldo_e_nivel(client, produto, admin_headers):
    client.post(MOVEMENTS, json=_entrada(produto.id, "100"), headers=admin_headers)

    resposta = client.post(MOVEMENTS, json=_saida(produto.id, "92"),
                           headers=admin_headers)
    corpo = resposta.get_json()

    assert resposta.status_code == 201
    assert corpo["current_stock"] == "8.000"
    assert corpo["nivel"] == "critico"
    assert corpo["is_low_stock"] is True


def test_tratador_tambem_registra(client, produto, tratador_headers):
    resposta = client.post(MOVEMENTS, json=_entrada(produto.id, "10"),
                           headers=tratador_headers)

    assert resposta.status_code == 201


def test_saida_acima_do_saldo_e_409_com_saldo_intacto(client, db, produto, admin_headers):
    client.post(MOVEMENTS, json=_entrada(produto.id, "10"), headers=admin_headers)

    resposta = client.post(MOVEMENTS, json=_saida(produto.id, "10.001"),
                           headers=admin_headers)

    assert resposta.status_code == 409
    assert resposta.get_json()["error"]["message"] == "Estoque insuficiente"

    saldo = client.get(f"/api/products/{produto.id}", headers=admin_headers).get_json()
    assert saldo["current_stock"] == "10.000"
    assert client.get(MOVEMENTS, headers=admin_headers).get_json()["total"] == 1


def test_duas_saidas_a_segunda_e_409(client, produto, admin_headers):
    client.post(MOVEMENTS, json=_entrada(produto.id, "10"), headers=admin_headers)

    primeira = client.post(MOVEMENTS, json=_saida(produto.id, "6"), headers=admin_headers)
    segunda = client.post(MOVEMENTS, json=_saida(produto.id, "6"), headers=admin_headers)

    assert primeira.status_code == 201
    assert segunda.status_code == 409
    assert primeira.get_json()["current_stock"] == "4.000"

    detalhe = client.get(f"/api/products/{produto.id}", headers=admin_headers).get_json()
    assert detalhe["current_stock"] == "4.000"


def test_motivo_invalido_para_o_tipo_e_422(client, produto, admin_headers):
    resposta = client.post(MOVEMENTS,
                           json=_entrada(produto.id, "10", reason="trato_manual"),
                           headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "reason"}


def test_tipo_invalido_e_422(client, produto, admin_headers):
    resposta = client.post(MOVEMENTS,
                           json={"product_id": produto.id, "type": "devolucao",
                                 "quantity": "10", "reason": "compra"},
                           headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "type"}


@pytest.mark.parametrize("quantidade", ["0", "-3", "abc"])
def test_quantidade_invalida_e_422(client, produto, admin_headers, quantidade):
    resposta = client.post(MOVEMENTS, json=_entrada(produto.id, quantidade),
                           headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "quantity"}


def test_validade_invalida_e_422(client, produto, admin_headers):
    resposta = client.post(MOVEMENTS,
                           json=_entrada(produto.id, "10", expiration_date="31/01/2027"),
                           headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "expiration_date"}


def test_produto_inativo_e_409(client, insumo, admin_headers):
    inativo = insumo("Inativo", saldo="100", minimo="1", consumo="1", active=False)

    resposta = client.post(MOVEMENTS, json=_entrada(inativo.id, "10"),
                           headers=admin_headers)

    assert resposta.status_code == 409
    assert "inativo" in resposta.get_json()["error"]["message"]


def test_produto_de_outro_haras_e_404(client, produto, outro_haras, auth_headers):
    resposta = client.post(MOVEMENTS, json=_entrada(produto.id, "10"),
                           headers=auth_headers("outro@teste.com", "outro12345"))

    assert resposta.status_code == 404


def test_produto_inexistente_e_404(client, produto, admin_headers):
    resposta = client.post(MOVEMENTS, json=_entrada(99999, "10"), headers=admin_headers)

    assert resposta.status_code == 404


def test_movimentacao_e_imutavel(client, db, produto, admin, admin_headers):
    mov = registrar_movimentacao(admin, produto, "entrada", 10, "compra")
    db.session.commit()

    assert client.patch(f"{MOVEMENTS}/{mov.id}", json={"quantity": "1"},
                        headers=admin_headers).status_code == 405
    assert client.delete(f"{MOVEMENTS}/{mov.id}",
                         headers=admin_headers).status_code == 405
    assert client.put(f"{MOVEMENTS}/{mov.id}", json={},
                      headers=admin_headers).status_code == 405


def test_registro_exige_token(client, produto):
    assert client.post(MOVEMENTS, json=_entrada(produto.id)).status_code == 401


# ------------------------------------------------------------- histórico

@pytest.fixture
def historico(db, haras, admin, tratador, insumo, produto):
    """Duas entradas e duas saídas, uma delas de ontem."""
    outro = insumo("Feno", saldo="0", minimo="5", consumo="2", code="EQ100")
    ontem = hoje() - timedelta(days=1)

    from app.services.stock import intervalo_do_dia
    quando_ontem = intervalo_do_dia(ontem)[0] + timedelta(hours=12)

    registrar_movimentacao(admin, produto, "entrada", 100, "compra",
                           created_at=quando_ontem)
    registrar_movimentacao(admin, outro, "entrada", 40, "doacao")
    registrar_movimentacao(tratador, produto, "saida", 30, "abastecimento_alimentador")
    registrar_movimentacao(tratador, outro, "saida", 4, "avaria", note="Fardo molhado")
    db.session.commit()

    return {"produto": produto, "outro": outro, "ontem": ontem}


def test_listagem_mais_recentes_primeiro(client, historico, admin_headers):
    corpo = client.get(MOVEMENTS, headers=admin_headers).get_json()

    assert corpo["total"] == 4
    assert corpo["page"] == 1
    assert [m["reason"] for m in corpo["items"]][0] == "avaria"


def test_filtros_do_historico(client, historico, admin, tratador, admin_headers):
    produto = historico["produto"]
    outro = historico["outro"]

    por_produto = client.get(f"{MOVEMENTS}?product_id={outro.id}",
                             headers=admin_headers).get_json()
    assert por_produto["total"] == 2

    por_tipo = client.get(f"{MOVEMENTS}?type=saida", headers=admin_headers).get_json()
    assert {m["type"] for m in por_tipo["items"]} == {"saida"}
    assert por_tipo["total"] == 2

    por_motivo = client.get(f"{MOVEMENTS}?reason=avaria",
                            headers=admin_headers).get_json()
    assert por_motivo["total"] == 1

    por_usuario = client.get(f"{MOVEMENTS}?user_id={tratador.id}",
                             headers=admin_headers).get_json()
    assert por_usuario["total"] == 2

    de_hoje = client.get(f"{MOVEMENTS}?from={hoje().isoformat()}",
                         headers=admin_headers).get_json()
    assert de_hoje["total"] == 3

    ate_ontem = client.get(f"{MOVEMENTS}?to={historico['ontem'].isoformat()}",
                           headers=admin_headers).get_json()
    assert ate_ontem["total"] == 1
    assert ate_ontem["items"][0]["product_id"] == produto.id


def test_filtro_invalido_e_422(client, historico, admin_headers):
    assert client.get(f"{MOVEMENTS}?type=devolucao",
                      headers=admin_headers).status_code == 422
    assert client.get(f"{MOVEMENTS}?reason=venda",
                      headers=admin_headers).status_code == 422
    assert client.get(f"{MOVEMENTS}?from=31-01-2027",
                      headers=admin_headers).status_code == 422


def test_paginacao_do_historico(client, historico, admin_headers):
    pagina1 = client.get(f"{MOVEMENTS}?per_page=3", headers=admin_headers).get_json()
    pagina2 = client.get(f"{MOVEMENTS}?per_page=3&page=2",
                         headers=admin_headers).get_json()

    assert len(pagina1["items"]) == 3
    assert len(pagina2["items"]) == 1
    assert client.get(f"{MOVEMENTS}?per_page=500",
                      headers=admin_headers).get_json()["per_page"] == 100


def test_detalhe_da_movimentacao(client, historico, admin_headers):
    lista = client.get(MOVEMENTS, headers=admin_headers).get_json()
    movement_id = lista["items"][0]["id"]

    resposta = client.get(f"{MOVEMENTS}/{movement_id}", headers=admin_headers)

    assert resposta.status_code == 200
    assert resposta.get_json()["id"] == movement_id


def test_detalhe_de_outro_haras_e_404(client, historico, outro_haras, auth_headers):
    lista = client.get(
        MOVEMENTS, headers=auth_headers("outro@teste.com", "outro12345")
    ).get_json()
    assert lista["total"] == 0

    resposta = client.get(f"{MOVEMENTS}/1",
                          headers=auth_headers("outro@teste.com", "outro12345"))
    assert resposta.status_code == 404


def test_historico_exige_token(client, historico):
    assert client.get(MOVEMENTS).status_code == 401


# --------------------------------------------------------- registro diário

def test_daily_de_hoje(client, historico, admin_headers):
    corpo = client.get(DAILY, headers=admin_headers).get_json()

    assert corpo["from"] == corpo["to"] == hoje().isoformat()
    assert len(corpo["dias"]) == 1

    dia = corpo["dias"][0]
    assert dia["entradas"] == "40.000"
    assert dia["saidas"] == "34.000"
    assert dia["saldo"] == "6.000"
    assert dia["total_movimentacoes"] == 3

    nomes = {p["name"]: p for p in dia["produtos"]}
    assert nomes["Feno"]["entradas"] == "40.000"
    assert nomes["Feno"]["saidas"] == "4.000"
    assert nomes["Ração peletizada"]["saidas"] == "30.000"

    usuarios = {u["name"]: u for u in dia["usuarios"]}
    assert usuarios["Admin"]["entradas"] == "40.000"
    assert usuarios["João Tratador"]["saidas"] == "34.000"


def test_daily_de_um_dia_especifico(client, historico, admin_headers):
    ontem = historico["ontem"].isoformat()

    dia = client.get(f"{DAILY}?date={ontem}", headers=admin_headers).get_json()["dias"][0]

    assert dia["data"] == ontem
    assert dia["entradas"] == "100.000"
    assert dia["saidas"] == "0"
    assert dia["total_movimentacoes"] == 1


def test_daily_de_um_periodo(client, historico, admin_headers):
    ontem = historico["ontem"].isoformat()
    corpo = client.get(f"{DAILY}?from={ontem}&to={hoje().isoformat()}",
                       headers=admin_headers).get_json()

    assert [d["data"] for d in corpo["dias"]] == [ontem, hoje().isoformat()]
    assert corpo["dias"][0]["entradas"] == "100.000"
    assert corpo["dias"][1]["total_movimentacoes"] == 3


def test_daily_de_dia_sem_movimento(client, historico, admin_headers):
    futuro = (hoje() + timedelta(days=3)).isoformat()

    dia = client.get(f"{DAILY}?date={futuro}", headers=admin_headers).get_json()["dias"][0]

    assert dia["entradas"] == dia["saidas"] == dia["saldo"] == "0"
    assert dia["total_movimentacoes"] == 0
    assert dia["produtos"] == []
    assert dia["usuarios"] == []


def test_daily_conta_pelo_dia_local(client, db, haras, admin, insumo, admin_headers):
    """23h locais de hoje ainda são hoje, mesmo já sendo outro dia em UTC."""
    produto = insumo("Ração", saldo="0", minimo="1", consumo="1")

    from app.services.stock import intervalo_do_dia
    fim_do_dia = intervalo_do_dia(hoje())[1] - timedelta(minutes=30)  # 23h30 local

    registrar_movimentacao(admin, produto, "entrada", 7, "compra",
                           created_at=fim_do_dia)
    db.session.commit()

    hoje_local = client.get(DAILY, headers=admin_headers).get_json()["dias"][0]
    amanha = (hoje() + timedelta(days=1)).isoformat()
    outro_dia = client.get(f"{DAILY}?date={amanha}",
                           headers=admin_headers).get_json()["dias"][0]

    assert hoje_local["entradas"] == "7.000"
    assert outro_dia["entradas"] == "0"


def test_daily_periodo_longo_demais_e_422(client, historico, admin_headers):
    inicio = (hoje() - timedelta(days=40)).isoformat()
    resposta = client.get(f"{DAILY}?from={inicio}&to={hoje().isoformat()}",
                          headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "to"}


def test_daily_limite_de_31_dias_passa(client, historico, admin_headers):
    inicio = (hoje() - timedelta(days=30)).isoformat()
    resposta = client.get(f"{DAILY}?from={inicio}&to={hoje().isoformat()}",
                          headers=admin_headers)

    assert resposta.status_code == 200
    assert len(resposta.get_json()["dias"]) == 31


def test_daily_intervalo_invertido_e_422(client, historico, admin_headers):
    amanha = (hoje() + timedelta(days=1)).isoformat()
    resposta = client.get(f"{DAILY}?from={amanha}&to={hoje().isoformat()}",
                          headers=admin_headers)

    assert resposta.status_code == 422


def test_daily_date_com_from_e_422(client, historico, admin_headers):
    resposta = client.get(f"{DAILY}?date={hoje().isoformat()}&from={hoje().isoformat()}",
                          headers=admin_headers)

    assert resposta.status_code == 422


def test_daily_isolado_por_haras(client, historico, outro_haras, auth_headers):
    dia = client.get(
        DAILY, headers=auth_headers("outro@teste.com", "outro12345")
    ).get_json()["dias"][0]

    assert dia["total_movimentacoes"] == 0
    assert dia["produtos"] == []


def test_daily_exige_token(client, historico):
    assert client.get(DAILY).status_code == 401


def test_dashboard_continua_igual(client, historico, admin_headers):
    """O dashboard consome as mesmas chaves em português."""
    hoje_dashboard = client.get("/api/dashboard",
                                headers=admin_headers).get_json()["movimentacoes_hoje"]

    assert hoje_dashboard["entradas"] == "40.000"
    assert hoje_dashboard["saidas"] == "34.000"
    assert hoje_dashboard["saldo"] == "6.000"
    assert hoje_dashboard["total_movimentacoes"] == 3
    assert "produtos" not in hoje_dashboard
