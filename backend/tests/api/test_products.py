"""Insumos do haras (/api/products)."""
import pytest

PRODUCTS = "/api/products"


@pytest.fixture
def admin_headers(admin, auth_headers):
    return auth_headers("admin@teste.com", "admin12345")


def _insumo(category_id, **extra):
    dados = {
        "name": "Ração peletizada 14% PB",
        "code": "EQ001",
        "category_id": category_id,
        "unit": "kg",
        "cost_price": "3.20",
        "min_stock": "100",
        "daily_consumption": "24",
    }
    dados.update(extra)
    return dados


def test_criacao_com_saldo_zerado(client, haras, admin_headers):
    resposta = client.post(PRODUCTS, json=_insumo(haras["category"].id),
                           headers=admin_headers)
    corpo = resposta.get_json()

    assert resposta.status_code == 201
    assert corpo["name"] == "Ração peletizada 14% PB"
    assert corpo["code"] == "EQ001"
    assert corpo["unit"] == "kg"
    assert corpo["current_stock"] == "0.000"
    assert corpo["cost_price"] == "3.20"
    assert corpo["min_stock"] == "100.000"
    assert corpo["supplier_id"] is None
    assert corpo["active"] is True
    assert corpo["stable_id"] == haras["stable"].id


def test_serializacao_traz_dias_e_alerta(client, haras, admin_headers):
    corpo = client.post(PRODUCTS, json=_insumo(haras["category"].id),
                        headers=admin_headers).get_json()

    # saldo zero com mínimo 100 => em alerta; 0 / 24 => 0 dias de cobertura
    assert corpo["is_low_stock"] is True
    assert corpo["days_left"] == "0"
    assert corpo["stock_value"] == "0.00000"  # saldo (3 casas) x custo (2 casas)


def test_dias_de_cobertura_nulo_sem_consumo(client, haras, admin_headers):
    corpo = client.post(PRODUCTS,
                        json=_insumo(haras["category"].id, code="EQ900",
                                     daily_consumption=None),
                        headers=admin_headers).get_json()

    assert corpo["daily_consumption"] is None
    assert corpo["days_left"] is None


def test_vinculo_com_fornecedor_do_haras(client, haras, admin_headers):
    fornecedor = client.post("/api/suppliers", json={"name": "Nutriequi"},
                             headers=admin_headers).get_json()

    corpo = client.post(PRODUCTS,
                        json=_insumo(haras["category"].id, supplier_id=fornecedor["id"]),
                        headers=admin_headers).get_json()

    assert corpo["supplier_id"] == fornecedor["id"]


def test_saldo_nao_e_editavel(client, haras, admin_headers):
    criado = client.post(PRODUCTS, json=_insumo(haras["category"].id),
                         headers=admin_headers).get_json()

    na_criacao = client.post(PRODUCTS,
                             json=_insumo(haras["category"].id, code="EQ002",
                                          current_stock="50"),
                             headers=admin_headers)
    assert na_criacao.status_code == 422
    assert na_criacao.get_json()["error"]["details"] == {"field": "current_stock"}

    no_patch = client.patch(f"{PRODUCTS}/{criado['id']}", json={"current_stock": "50"},
                            headers=admin_headers)
    assert no_patch.status_code == 422


def test_unidade_invalida_e_422(client, haras, admin_headers):
    resposta = client.post(PRODUCTS, json=_insumo(haras["category"].id, unit="arroba"),
                           headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "unit"}


def test_categoria_de_outro_haras_e_422(client, haras, outro_haras, admin_headers,
                                        auth_headers):
    categoria_alheia = client.post(
        "/api/categories", json={"name": "Ração do outro"},
        headers=auth_headers("outro@teste.com", "outro12345"),
    ).get_json()

    resposta = client.post(PRODUCTS, json=_insumo(categoria_alheia["id"]),
                           headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "category_id"}


def test_fornecedor_de_outro_haras_e_422(client, haras, outro_haras, admin_headers,
                                         auth_headers):
    fornecedor_alheio = client.post(
        "/api/suppliers", json={"name": "Agro do outro"},
        headers=auth_headers("outro@teste.com", "outro12345"),
    ).get_json()

    resposta = client.post(
        PRODUCTS,
        json=_insumo(haras["category"].id, supplier_id=fornecedor_alheio["id"]),
        headers=admin_headers,
    )

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "supplier_id"}


def test_categoria_obrigatoria_e_422(client, haras, admin_headers):
    dados = _insumo(haras["category"].id)
    dados.pop("category_id")

    resposta = client.post(PRODUCTS, json=dados, headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "category_id"}


def test_codigo_duplicado_e_409(client, haras, admin_headers):
    client.post(PRODUCTS, json=_insumo(haras["category"].id), headers=admin_headers)

    resposta = client.post(PRODUCTS, json=_insumo(haras["category"].id),
                           headers=admin_headers)

    assert resposta.status_code == 409
    assert resposta.get_json()["error"]["message"] == "Código de insumo já usado neste haras"


def test_maximo_menor_que_minimo_e_422(client, haras, admin_headers):
    resposta = client.post(PRODUCTS,
                           json=_insumo(haras["category"].id, min_stock="100",
                                        max_stock="50"),
                           headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "max_stock"}


def test_custo_negativo_e_422(client, haras, admin_headers):
    resposta = client.post(PRODUCTS, json=_insumo(haras["category"].id, cost_price="-1"),
                           headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "cost_price"}


def test_patch_atualiza_cadastro(client, haras, admin_headers):
    criado = client.post(PRODUCTS, json=_insumo(haras["category"].id),
                         headers=admin_headers).get_json()

    resposta = client.patch(f"{PRODUCTS}/{criado['id']}",
                            json={"name": "Ração 16% PB", "min_stock": "120",
                                  "unit": "sc"},
                            headers=admin_headers)
    corpo = resposta.get_json()

    assert resposta.status_code == 200
    assert corpo["name"] == "Ração 16% PB"
    assert corpo["min_stock"] == "120.000"
    assert corpo["unit"] == "sc"


def test_patch_desativa_o_insumo(client, haras, admin_headers):
    criado = client.post(PRODUCTS, json=_insumo(haras["category"].id),
                         headers=admin_headers).get_json()

    resposta = client.patch(f"{PRODUCTS}/{criado['id']}", json={"active": False},
                            headers=admin_headers)

    assert resposta.status_code == 200
    assert resposta.get_json()["active"] is False


def test_patch_sem_campos_e_422(client, haras, admin_headers):
    criado = client.post(PRODUCTS, json=_insumo(haras["category"].id),
                         headers=admin_headers).get_json()

    assert client.patch(f"{PRODUCTS}/{criado['id']}", json={},
                        headers=admin_headers).status_code == 422


def test_listagem_busca_e_filtros(client, haras, admin_headers):
    outra = client.post("/api/categories", json={"name": "Volumoso"},
                        headers=admin_headers).get_json()

    client.post(PRODUCTS, json=_insumo(haras["category"].id), headers=admin_headers)
    feno = client.post(PRODUCTS,
                       json=_insumo(outra["id"], name="Feno de tifton", code="EQ100",
                                    unit="un"),
                       headers=admin_headers).get_json()
    client.patch(f"{PRODUCTS}/{feno['id']}", json={"active": False},
                 headers=admin_headers)

    # a fixture `haras` já traz um insumo "Ração"
    todos = client.get(PRODUCTS, headers=admin_headers).get_json()
    assert todos["total"] == 3

    por_nome = client.get(f"{PRODUCTS}?search=feno", headers=admin_headers).get_json()
    assert [p["name"] for p in por_nome["items"]] == ["Feno de tifton"]

    por_codigo = client.get(f"{PRODUCTS}?search=EQ100", headers=admin_headers).get_json()
    assert por_codigo["total"] == 1

    por_categoria = client.get(f"{PRODUCTS}?category_id={outra['id']}",
                               headers=admin_headers).get_json()
    assert por_categoria["total"] == 1

    ativos = client.get(f"{PRODUCTS}?active=true", headers=admin_headers).get_json()
    assert ativos["total"] == 2

    inativos = client.get(f"{PRODUCTS}?active=false", headers=admin_headers).get_json()
    assert [p["name"] for p in inativos["items"]] == ["Feno de tifton"]


def test_paginacao_respeita_o_maximo(client, haras, admin_headers):
    corpo = client.get(f"{PRODUCTS}?per_page=500", headers=admin_headers).get_json()

    assert corpo["per_page"] == 100


def test_category_id_invalido_na_busca_e_422(client, haras, admin_headers):
    resposta = client.get(f"{PRODUCTS}?category_id=abc", headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "category_id"}


def test_tratador_le_mas_nao_cria_nem_edita(client, haras, tratador, admin_headers,
                                            auth_headers):
    criado = client.post(PRODUCTS, json=_insumo(haras["category"].id),
                         headers=admin_headers).get_json()
    headers = auth_headers("tratador@teste.com", "tratador123")

    assert client.get(PRODUCTS, headers=headers).status_code == 200
    assert client.get(f"{PRODUCTS}/{criado['id']}", headers=headers).status_code == 200
    assert client.post(PRODUCTS, json=_insumo(haras["category"].id, code="EQ777"),
                       headers=headers).status_code == 403
    assert client.patch(f"{PRODUCTS}/{criado['id']}", json={"name": "X"},
                        headers=headers).status_code == 403


def test_isolamento_entre_haras(client, haras, outro_haras, admin_headers, auth_headers):
    criado = client.post(PRODUCTS, json=_insumo(haras["category"].id),
                         headers=admin_headers).get_json()
    headers = auth_headers("outro@teste.com", "outro12345")

    assert client.get(PRODUCTS, headers=headers).get_json()["total"] == 0
    assert client.get(f"{PRODUCTS}/{criado['id']}", headers=headers).status_code == 404
    assert client.patch(f"{PRODUCTS}/{criado['id']}", json={"name": "X"},
                        headers=headers).status_code == 404


def test_exige_token(client, haras):
    assert client.get(PRODUCTS).status_code == 401
    assert client.post(PRODUCTS, json=_insumo(haras["category"].id)).status_code == 401
