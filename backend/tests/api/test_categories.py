"""Categorias de insumo (/api/categories)."""
CATEGORIES = "/api/categories"


def test_listagem_do_proprio_haras(client, admin, haras, auth_headers):
    resposta = client.get(CATEGORIES, headers=auth_headers("admin@teste.com", "admin12345"))
    corpo = resposta.get_json()

    assert resposta.status_code == 200
    assert corpo["total"] == 1
    assert corpo["page"] == 1
    assert corpo["per_page"] == 20
    assert corpo["items"][0]["name"] == "Ração"
    assert corpo["items"][0]["stable_id"] == haras["stable"].id


def test_tratador_le_a_lista(client, admin, tratador, auth_headers):
    resposta = client.get(CATEGORIES, headers=auth_headers("tratador@teste.com", "tratador123"))

    assert resposta.status_code == 200


def test_tratador_nao_cria(client, admin, tratador, auth_headers):
    resposta = client.post(CATEGORIES, json={"name": "Volumoso"},
                           headers=auth_headers("tratador@teste.com", "tratador123"))

    assert resposta.status_code == 403


def test_criacao_e_detalhe(client, admin, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")

    criada = client.post(CATEGORIES, json={"name": "Volumoso"}, headers=headers)
    corpo = criada.get_json()

    assert criada.status_code == 201
    assert corpo["name"] == "Volumoso"

    detalhe = client.get(f"{CATEGORIES}/{corpo['id']}", headers=headers)
    assert detalhe.status_code == 200
    assert detalhe.get_json()["name"] == "Volumoso"


def test_nome_duplicado_e_409(client, admin, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")

    assert client.post(CATEGORIES, json={"name": "Ração"}, headers=headers).status_code == 409
    # a comparação ignora maiúsculas/minúsculas
    assert client.post(CATEGORIES, json={"name": "ração"}, headers=headers).status_code == 409


def test_nome_obrigatorio_e_422(client, admin, auth_headers):
    resposta = client.post(CATEGORIES, json={},
                           headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "name"}


def test_patch_renomeia(client, admin, haras, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")
    category_id = haras["category"].id

    resposta = client.patch(f"{CATEGORIES}/{category_id}",
                            json={"name": "Ração concentrada"}, headers=headers)

    assert resposta.status_code == 200
    assert resposta.get_json()["name"] == "Ração concentrada"


def test_patch_para_nome_existente_e_409(client, admin, haras, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")
    nova = client.post(CATEGORIES, json={"name": "Volumoso"}, headers=headers).get_json()

    resposta = client.patch(f"{CATEGORIES}/{nova['id']}", json={"name": "Ração"},
                            headers=headers)

    assert resposta.status_code == 409


def test_busca_por_nome(client, admin, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")
    client.post(CATEGORIES, json={"name": "Volumoso"}, headers=headers)

    corpo = client.get(f"{CATEGORIES}?search=volum", headers=headers).get_json()

    assert [c["name"] for c in corpo["items"]] == ["Volumoso"]
    assert corpo["total"] == 1


def test_isolamento_entre_haras(client, admin, haras, outro_haras, auth_headers):
    headers = auth_headers("outro@teste.com", "outro12345")

    lista = client.get(CATEGORIES, headers=headers).get_json()
    assert lista["total"] == 0

    detalhe = client.get(f"{CATEGORIES}/{haras['category'].id}", headers=headers)
    assert detalhe.status_code == 404

    patch = client.patch(f"{CATEGORIES}/{haras['category'].id}", json={"name": "X"},
                         headers=headers)
    assert patch.status_code == 404


def test_exige_token(client, admin, haras):
    assert client.get(CATEGORIES).status_code == 401
    assert client.get(f"{CATEGORIES}/{haras['category'].id}").status_code == 401


def test_nao_existe_delete(client, admin, haras, auth_headers):
    resposta = client.delete(f"{CATEGORIES}/{haras['category'].id}",
                             headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 405
