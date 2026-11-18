"""Fornecedores (/api/suppliers)."""
SUPPLIERS = "/api/suppliers"

NUTRIEQUI = {"name": "Nutriequi Rações", "phone": "(27) 3333-0001",
             "email": "vendas@nutriequi.com"}


def test_crud_do_fornecedor(client, admin, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")

    criado = client.post(SUPPLIERS, json=NUTRIEQUI, headers=headers)
    corpo = criado.get_json()

    assert criado.status_code == 201
    assert corpo["name"] == "Nutriequi Rações"
    assert corpo["phone"] == "(27) 3333-0001"

    detalhe = client.get(f"{SUPPLIERS}/{corpo['id']}", headers=headers)
    assert detalhe.status_code == 200

    patch = client.patch(f"{SUPPLIERS}/{corpo['id']}",
                         json={"phone": None, "email": "novo@nutriequi.com"},
                         headers=headers)
    assert patch.status_code == 200
    assert patch.get_json()["phone"] is None
    assert patch.get_json()["email"] == "novo@nutriequi.com"

    lista = client.get(SUPPLIERS, headers=headers).get_json()
    assert lista["total"] == 1


def test_tratador_le_mas_nao_cria(client, admin, tratador, auth_headers):
    headers = auth_headers("tratador@teste.com", "tratador123")

    assert client.get(SUPPLIERS, headers=headers).status_code == 200
    assert client.post(SUPPLIERS, json=NUTRIEQUI, headers=headers).status_code == 403


def test_nome_duplicado_e_409(client, admin, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")
    client.post(SUPPLIERS, json=NUTRIEQUI, headers=headers)

    assert client.post(SUPPLIERS, json=NUTRIEQUI, headers=headers).status_code == 409


def test_nome_obrigatorio_e_422(client, admin, auth_headers):
    resposta = client.post(SUPPLIERS, json={"phone": "123"},
                           headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "name"}


def test_telefone_longo_demais_e_422(client, admin, auth_headers):
    resposta = client.post(SUPPLIERS, json={"name": "Agro", "phone": "x" * 30},
                           headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "phone"}


def test_patch_sem_campos_e_422(client, admin, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")
    criado = client.post(SUPPLIERS, json=NUTRIEQUI, headers=headers).get_json()

    resposta = client.patch(f"{SUPPLIERS}/{criado['id']}", json={}, headers=headers)

    assert resposta.status_code == 422


def test_busca_e_paginacao(client, admin, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")
    client.post(SUPPLIERS, json=NUTRIEQUI, headers=headers)
    client.post(SUPPLIERS, json={"name": "Agropecuária Capixaba"}, headers=headers)

    pagina1 = client.get(f"{SUPPLIERS}?per_page=1", headers=headers).get_json()
    assert pagina1["total"] == 2
    assert [s["name"] for s in pagina1["items"]] == ["Agropecuária Capixaba"]

    pagina2 = client.get(f"{SUPPLIERS}?per_page=1&page=2", headers=headers).get_json()
    assert [s["name"] for s in pagina2["items"]] == ["Nutriequi Rações"]

    busca = client.get(f"{SUPPLIERS}?search=capixaba", headers=headers).get_json()
    assert busca["total"] == 1


def test_isolamento_entre_haras(client, admin, outro_haras, auth_headers):
    criado = client.post(SUPPLIERS, json=NUTRIEQUI,
                         headers=auth_headers("admin@teste.com", "admin12345")).get_json()

    headers = auth_headers("outro@teste.com", "outro12345")

    assert client.get(SUPPLIERS, headers=headers).get_json()["total"] == 0
    assert client.get(f"{SUPPLIERS}/{criado['id']}", headers=headers).status_code == 404
    assert client.patch(f"{SUPPLIERS}/{criado['id']}", json={"name": "X"},
                        headers=headers).status_code == 404


def test_exige_token(client, admin):
    assert client.get(SUPPLIERS).status_code == 401
