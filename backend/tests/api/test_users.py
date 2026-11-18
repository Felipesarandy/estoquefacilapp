"""Gestão de usuários pelo admin do haras (/api/users)."""
USERS = "/api/users"


def _novo(email="novo@teste.com", password="senha12345", **extra):
    dados = {"name": "Novo Tratador", "email": email, "password": password}
    dados.update(extra)
    return dados


def test_listagem_paginada_do_proprio_haras(client, admin, tratador, outro_haras, auth_headers):
    resposta = client.get(USERS, headers=auth_headers("admin@teste.com", "admin12345"))
    corpo = resposta.get_json()

    assert resposta.status_code == 200
    assert corpo["page"] == 1
    assert corpo["per_page"] == 20
    assert corpo["total"] == 2
    emails = [u["email"] for u in corpo["items"]]
    assert emails == ["admin@teste.com", "tratador@teste.com"]  # ordenado por nome
    assert "outro@teste.com" not in emails


def test_listagem_respeita_per_page_maximo(client, admin, auth_headers):
    resposta = client.get(f"{USERS}?per_page=500",
                          headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 200
    assert resposta.get_json()["per_page"] == 100


def test_listagem_filtra_por_role_e_active(client, db, admin, tratador, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")

    somente_tratador = client.get(f"{USERS}?role=tratador", headers=headers).get_json()
    assert [u["email"] for u in somente_tratador["items"]] == ["tratador@teste.com"]

    tratador.active = False
    db.session.commit()

    inativos = client.get(f"{USERS}?active=false", headers=headers).get_json()
    assert [u["email"] for u in inativos["items"]] == ["tratador@teste.com"]


def test_listagem_com_role_invalido_e_422(client, admin, auth_headers):
    resposta = client.get(f"{USERS}?role=veterinario",
                          headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "role"}


def test_admin_de_outro_haras_nao_enxerga_os_usuarios(client, admin, tratador,
                                                      outro_haras, auth_headers):
    headers = auth_headers("outro@teste.com", "outro12345")

    lista = client.get(USERS, headers=headers).get_json()
    assert [u["email"] for u in lista["items"]] == ["outro@teste.com"]

    detalhe = client.get(f"{USERS}/{tratador.id}", headers=headers)
    assert detalhe.status_code == 404

    patch = client.patch(f"{USERS}/{tratador.id}", json={"name": "Invasor"}, headers=headers)
    assert patch.status_code == 404


def test_tratador_nao_acessa_rota_de_admin(client, admin, tratador, auth_headers):
    resposta = client.get(USERS, headers=auth_headers("tratador@teste.com", "tratador123"))

    assert resposta.status_code == 403
    assert resposta.get_json()["error"]["status"] == 403


def test_criacao_de_usuario(client, admin, auth_headers):
    resposta = client.post(USERS, json=_novo(),
                           headers=auth_headers("admin@teste.com", "admin12345"))
    corpo = resposta.get_json()

    assert resposta.status_code == 201
    assert corpo["email"] == "novo@teste.com"
    assert corpo["role"] == "tratador"  # papel padrão
    assert corpo["active"] is True
    assert corpo["stable_id"] == admin.stable_id
    assert "password_hash" not in corpo
    assert "password" not in corpo


def test_usuario_criado_consegue_fazer_login(client, admin, auth_headers):
    client.post(USERS, json=_novo(), headers=auth_headers("admin@teste.com", "admin12345"))

    resposta = client.post("/api/auth/login",
                           json={"email": "novo@teste.com", "password": "senha12345"})

    assert resposta.status_code == 200


def test_criacao_com_email_duplicado_e_409(client, admin, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")

    resposta = client.post(USERS, json=_novo(email="admin@teste.com"), headers=headers)

    assert resposta.status_code == 409
    assert resposta.get_json()["error"]["message"] == "E-mail já cadastrado"


def test_criacao_com_senha_curta_e_422(client, admin, auth_headers):
    resposta = client.post(USERS, json=_novo(password="curta"),
                           headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "password"}


def test_criacao_com_email_invalido_e_422(client, admin, auth_headers):
    resposta = client.post(USERS, json=_novo(email="sem-arroba"),
                           headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "email"}


def test_criacao_com_role_invalido_e_422(client, admin, auth_headers):
    resposta = client.post(USERS, json=_novo(role="veterinario"),
                           headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 422


def test_detalhe_do_usuario(client, admin, tratador, auth_headers):
    resposta = client.get(f"{USERS}/{tratador.id}",
                          headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 200
    assert resposta.get_json()["email"] == "tratador@teste.com"


def test_patch_atualiza_nome_papel_e_desativa(client, admin, tratador, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")

    resposta = client.patch(f"{USERS}/{tratador.id}",
                            json={"name": "João da Silva", "role": "admin", "active": False},
                            headers=headers)
    corpo = resposta.get_json()

    assert resposta.status_code == 200
    assert corpo["name"] == "João da Silva"
    assert corpo["role"] == "admin"
    assert corpo["active"] is False


def test_patch_troca_a_senha(client, admin, tratador, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")

    client.patch(f"{USERS}/{tratador.id}", json={"password": "nova-senha-123"}, headers=headers)

    assert client.post("/api/auth/login",
                       json={"email": "tratador@teste.com",
                             "password": "nova-senha-123"}).status_code == 200


def test_admin_nao_pode_se_desativar(client, admin, auth_headers):
    resposta = client.patch(f"{USERS}/{admin.id}", json={"active": False},
                            headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 409
    assert resposta.get_json()["error"]["message"] == "Você não pode desativar sua própria conta"


def test_admin_nao_pode_se_rebaixar(client, admin, auth_headers):
    resposta = client.patch(f"{USERS}/{admin.id}", json={"role": "tratador"},
                            headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 409


def test_patch_sem_campos_e_422(client, admin, tratador, auth_headers):
    resposta = client.patch(f"{USERS}/{tratador.id}", json={},
                            headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 422


def test_usuarios_exige_token(client, admin):
    assert client.get(USERS).status_code == 401
    assert client.post(USERS, json=_novo()).status_code == 401


def test_nao_existe_delete_de_usuario(client, admin, tratador, auth_headers):
    resposta = client.delete(f"{USERS}/{tratador.id}",
                             headers=auth_headers("admin@teste.com", "admin12345"))

    assert resposta.status_code == 405
    assert resposta.get_json()["error"]["status"] == 405
