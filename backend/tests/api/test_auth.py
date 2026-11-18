"""Login, usuário logado e falhas de token (/api/auth)."""
from datetime import timedelta

from flask_jwt_extended import create_access_token

LOGIN = "/api/auth/login"
ME = "/api/auth/me"


def test_login_devolve_token_e_usuario(client, admin):
    resposta = client.post(LOGIN, json={"email": "admin@teste.com", "password": "admin12345"})
    corpo = resposta.get_json()

    assert resposta.status_code == 200
    assert corpo["token_type"] == "Bearer"
    assert corpo["access_token"]
    assert corpo["expires_in"] == 3600
    assert corpo["user"]["email"] == "admin@teste.com"
    assert corpo["user"]["role"] == "admin"
    assert "password_hash" not in corpo["user"]


def test_login_aceita_email_em_maiusculas(client, admin):
    resposta = client.post(LOGIN, json={"email": "ADMIN@TESTE.COM", "password": "admin12345"})

    assert resposta.status_code == 200


def test_login_com_senha_errada(client, admin):
    resposta = client.post(LOGIN, json={"email": "admin@teste.com", "password": "errada123"})

    assert resposta.status_code == 401
    assert resposta.get_json()["error"]["message"] == "Credenciais inválidas"


def test_login_com_email_inexistente_tem_a_mesma_mensagem(client, admin):
    resposta = client.post(LOGIN, json={"email": "ninguem@teste.com", "password": "admin12345"})

    assert resposta.status_code == 401
    assert resposta.get_json()["error"]["message"] == "Credenciais inválidas"


def test_login_de_usuario_inativo(client, db, admin):
    admin.active = False
    db.session.commit()

    resposta = client.post(LOGIN, json={"email": "admin@teste.com", "password": "admin12345"})

    assert resposta.status_code == 401
    assert resposta.get_json()["error"]["message"] == "Credenciais inválidas"


def test_login_sem_senha_e_422(client, admin):
    resposta = client.post(LOGIN, json={"email": "admin@teste.com"})

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "password"}


def test_login_sem_corpo_json_e_400(client, admin):
    resposta = client.post(LOGIN, data="nao-e-json", content_type="text/plain")

    assert resposta.status_code == 400
    assert resposta.get_json()["error"]["status"] == 400


def test_me_com_token(client, admin, auth_headers):
    resposta = client.get(ME, headers=auth_headers("admin@teste.com", "admin12345"))
    corpo = resposta.get_json()

    assert resposta.status_code == 200
    assert corpo["email"] == "admin@teste.com"
    assert corpo["stable_id"] == admin.stable_id
    assert "password_hash" not in corpo


def test_me_sem_token(client, admin):
    resposta = client.get(ME)

    assert resposta.status_code == 401
    assert resposta.get_json()["error"]["message"] == "Token de acesso obrigatório"


def test_me_com_token_invalido(client, admin):
    resposta = client.get(ME, headers={"Authorization": "Bearer token.invalido.aqui"})

    assert resposta.status_code == 401
    assert resposta.get_json()["error"]["message"] == "Token inválido"


def test_me_com_token_expirado(client, app, admin):
    with app.app_context():
        token = create_access_token(identity=str(admin.id),
                                    expires_delta=timedelta(seconds=-10))

    resposta = client.get(ME, headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 401
    assert resposta.get_json()["error"]["message"] == "Token expirado"


def test_me_de_usuario_desativado_depois_do_login(client, db, admin, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")
    admin.active = False
    db.session.commit()

    resposta = client.get(ME, headers=headers)

    assert resposta.status_code == 401
    assert resposta.get_json()["error"]["message"] == "Usuário inativo ou inexistente"


def test_nao_existe_rota_de_registro(client, admin):
    resposta = client.post("/api/auth/register",
                           json={"email": "x@teste.com", "password": "12345678"})

    assert resposta.status_code == 404


def test_rota_inexistente_responde_json(client, admin):
    resposta = client.get("/api/nao-existe")
    corpo = resposta.get_json()

    assert resposta.status_code == 404
    assert resposta.headers["Content-Type"].startswith("application/json")
    assert corpo["error"]["status"] == 404
    assert corpo["error"]["message"]


def test_metodo_nao_permitido_responde_json(client, admin):
    resposta = client.delete(LOGIN)
    corpo = resposta.get_json()

    assert resposta.status_code == 405
    assert corpo["error"]["status"] == 405


def test_health_continua_publico(client):
    resposta = client.get("/api/health")

    assert resposta.status_code == 200
    assert resposta.get_json() == {"status": "ok"}
