"""Contagens de inventário pela API (/api/inventory)."""
import pytest

INVENTORY = "/api/inventory"


@pytest.fixture
def admin_headers(admin, auth_headers):
    return auth_headers("admin@teste.com", "admin12345")


@pytest.fixture
def sal(insumo):
    return insumo("Sal mineral", saldo="100", minimo="10", consumo="1", code="EQ200")


def test_contagem_com_falta(client, sal, admin_headers):
    resposta = client.post(INVENTORY, json={"product_id": sal.id, "counted_quantity": "90",
                                            "note": "Contagem semanal"},
                           headers=admin_headers)
    corpo = resposta.get_json()

    assert resposta.status_code == 201
    assert corpo["count"]["system_quantity"] == "100.000"
    assert corpo["count"]["counted_quantity"] == "90.000"
    assert corpo["difference"] == "-10.000"
    assert corpo["adjustment"]["type"] == "saida"
    assert corpo["adjustment"]["reason"] == "ajuste"
    assert corpo["incident"]["type"] == "divergencia_inventario"
    assert corpo["incident"]["severity"] == "media"
    assert corpo["current_stock"] == "90.000"


def test_contagem_com_sobra(client, sal, admin_headers):
    corpo = client.post(INVENTORY, json={"product_id": sal.id, "counted_quantity": "125"},
                        headers=admin_headers).get_json()

    assert corpo["adjustment"]["type"] == "entrada"
    assert corpo["incident"]["severity"] == "alta"
    assert corpo["current_stock"] == "125.000"


def test_contagem_sem_divergencia(client, sal, admin_headers):
    corpo = client.post(INVENTORY, json={"product_id": sal.id, "counted_quantity": "100"},
                        headers=admin_headers).get_json()

    assert corpo["difference"] == "0.000"
    assert corpo["adjustment"] is None
    assert corpo["incident"] is None


def test_tratador_tambem_conta(client, sal, tratador, auth_headers):
    resposta = client.post(INVENTORY, json={"product_id": sal.id, "counted_quantity": "100"},
                           headers=auth_headers("tratador@teste.com", "tratador123"))

    assert resposta.status_code == 201


def test_validacao(client, sal, admin_headers):
    negativo = client.post(INVENTORY, json={"product_id": sal.id, "counted_quantity": "-1"},
                           headers=admin_headers)
    sem_produto = client.post(INVENTORY, json={"counted_quantity": "1"},
                              headers=admin_headers)

    assert negativo.status_code == 422
    assert negativo.get_json()["error"]["details"] == {"field": "counted_quantity"}
    assert sem_produto.status_code == 422


def test_insumo_de_outro_haras_e_404(client, sal, outro_haras, auth_headers):
    resposta = client.post(INVENTORY, json={"product_id": sal.id, "counted_quantity": "1"},
                           headers=auth_headers("outro@teste.com", "outro12345"))

    assert resposta.status_code == 404


def test_insumo_inativo_e_409(client, insumo, admin_headers):
    inativo = insumo("Inativo", saldo="10", minimo="1", consumo="1", active=False)

    resposta = client.post(INVENTORY, json={"product_id": inativo.id, "counted_quantity": "5"},
                           headers=admin_headers)

    assert resposta.status_code == 409


def test_listagem_filtros_e_detalhe(client, sal, insumo, admin_headers):
    feno = insumo("Feno", saldo="10", minimo="1", consumo="1")
    client.post(INVENTORY, json={"product_id": sal.id, "counted_quantity": "99"},
                headers=admin_headers)
    client.post(INVENTORY, json={"product_id": feno.id, "counted_quantity": "10"},
                headers=admin_headers)

    todas = client.get(INVENTORY, headers=admin_headers).get_json()
    do_sal = client.get(f"{INVENTORY}?product_id={sal.id}", headers=admin_headers).get_json()
    futuro = client.get(f"{INVENTORY}?from=2099-01-01", headers=admin_headers).get_json()
    pagina = client.get(f"{INVENTORY}?per_page=1", headers=admin_headers).get_json()

    assert todas["total"] == 2
    assert todas["items"][0]["product_id"] == feno.id  # mais recente primeiro
    assert do_sal["total"] == 1
    assert futuro["total"] == 0
    assert len(pagina["items"]) == 1

    detalhe = client.get(f"{INVENTORY}/{todas['items'][0]['id']}", headers=admin_headers)
    assert detalhe.status_code == 200


def test_isolamento(client, sal, outro_haras, admin_headers, auth_headers):
    criada = client.post(INVENTORY, json={"product_id": sal.id, "counted_quantity": "99"},
                         headers=admin_headers).get_json()
    outro = auth_headers("outro@teste.com", "outro12345")

    assert client.get(INVENTORY, headers=outro).get_json()["total"] == 0
    assert client.get(f"{INVENTORY}/{criada['count']['id']}", headers=outro).status_code == 404


def test_contagem_e_imutavel(client, sal, admin_headers):
    criada = client.post(INVENTORY, json={"product_id": sal.id, "counted_quantity": "99"},
                         headers=admin_headers).get_json()
    url = f"{INVENTORY}/{criada['count']['id']}"

    assert client.patch(url, json={}, headers=admin_headers).status_code == 405
    assert client.put(url, json={}, headers=admin_headers).status_code == 405
    assert client.delete(url, headers=admin_headers).status_code == 405


def test_exige_token(client, sal):
    assert client.get(INVENTORY).status_code == 401
    assert client.post(INVENTORY, json={}).status_code == 401
