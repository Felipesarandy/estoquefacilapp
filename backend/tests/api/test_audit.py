"""Trilha de auditoria pela API e pontos de auditoria nas rotas."""
import pytest

from app.models import AuditLog

AUDIT = "/api/audit"


@pytest.fixture
def admin_headers(admin, auth_headers):
    return auth_headers("admin@teste.com", "admin12345")


def _ultimo(db, action, entity=None):
    query = db.session.query(AuditLog).filter_by(action=action)
    if entity:
        query = query.filter_by(entity=entity)
    return query.order_by(AuditLog.id.desc()).first()


# ------------------------------------------------------------------ login

def test_login_bem_sucedido_e_auditado(client, db, admin, admin_headers):
    log = _ultimo(db, "login")

    assert log.user_id == admin.id
    assert log.stable_id == admin.stable_id
    assert log.entity == "user"
    assert log.ip == "127.0.0.1"


def test_senha_errada_e_auditada(client, db, admin):
    client.post("/api/auth/login", json={"email": "admin@teste.com", "password": "errada123"})

    log = _ultimo(db, "login_failed")

    assert log.user_id is None
    assert log.entity_id == admin.id
    assert log.stable_id == admin.stable_id
    assert log.after_json == {"email": "admin@teste.com"}


def test_email_desconhecido_fica_sem_haras(client, db, admin):
    client.post("/api/auth/login", json={"email": "ninguem@x.com", "password": "12345678"})

    log = _ultimo(db, "login_failed")

    assert log.stable_id is None
    assert log.entity_id is None
    assert log.after_json == {"email": "ninguem@x.com"}


def test_usuario_inativo_e_auditado_como_falha(client, db, admin):
    admin.active = False
    db.session.commit()

    client.post("/api/auth/login", json={"email": "admin@teste.com", "password": "admin12345"})

    assert _ultimo(db, "login_failed").entity_id == admin.id


# --------------------------------------------------- create/update/deactivate

def test_produto_create_update_deactivate(client, db, haras, admin_headers):
    criado = client.post("/api/products",
                         json={"name": "Feno", "code": "F1",
                               "category_id": haras["category"].id},
                         headers=admin_headers).get_json()
    client.patch(f"/api/products/{criado['id']}", json={"name": "Feno tifton"},
                 headers=admin_headers)
    client.patch(f"/api/products/{criado['id']}", json={"active": False},
                 headers=admin_headers)

    create = _ultimo(db, "create", "product")
    update = _ultimo(db, "update", "product")
    deactivate = _ultimo(db, "deactivate", "product")

    assert create.entity_id == criado["id"]
    assert create.before_json is None
    assert create.after_json["name"] == "Feno"
    assert update.before_json["name"] == "Feno"
    assert update.after_json["name"] == "Feno tifton"
    assert deactivate.before_json["active"] is True
    assert deactivate.after_json["active"] is False


def test_categoria_e_fornecedor_auditados(client, db, haras, admin_headers):
    categoria = client.post("/api/categories", json={"name": "Volumoso"},
                            headers=admin_headers).get_json()
    client.patch(f"/api/categories/{categoria['id']}", json={"name": "Volumosos"},
                 headers=admin_headers)
    fornecedor = client.post("/api/suppliers", json={"name": "Agro"},
                             headers=admin_headers).get_json()
    client.patch(f"/api/suppliers/{fornecedor['id']}", json={"phone": "123"},
                 headers=admin_headers)

    assert _ultimo(db, "create", "category").entity_id == categoria["id"]
    assert _ultimo(db, "update", "category").after_json["name"] == "Volumosos"
    assert _ultimo(db, "create", "supplier").entity_id == fornecedor["id"]
    assert _ultimo(db, "update", "supplier").after_json["phone"] == "123"


def test_usuario_auditado_sem_senha(client, db, admin, admin_headers):
    novo = client.post("/api/users", json={"name": "Maria", "email": "maria@teste.com",
                                           "password": "maria12345"},
                       headers=admin_headers).get_json()
    client.patch(f"/api/users/{novo['id']}", json={"password": "outra-senha-1"},
                 headers=admin_headers)
    client.patch(f"/api/users/{novo['id']}", json={"active": False}, headers=admin_headers)

    logs = db.session.query(AuditLog).filter_by(entity="user", entity_id=novo["id"]).all()
    texto = str([(log.before_json, log.after_json) for log in logs])

    assert [log.action for log in logs] == ["create", "update", "deactivate"]
    assert logs[1].after_json["password_changed"] is True
    assert "password_hash" not in texto
    assert "maria12345" not in texto
    assert "outra-senha-1" not in texto


def test_conflito_nao_deixa_auditoria(client, db, haras, admin_headers):
    antes = db.session.query(AuditLog).count()

    resposta = client.post("/api/categories", json={"name": "Ração"}, headers=admin_headers)

    assert resposta.status_code == 409
    assert db.session.query(AuditLog).count() == antes


# ---------------------------------------------------------------- /api/audit

def test_lista_filtros_e_detalhe(client, db, haras, admin_headers):
    client.post("/api/categories", json={"name": "Volumoso"}, headers=admin_headers)

    todos = client.get(AUDIT, headers=admin_headers).get_json()
    creates = client.get(f"{AUDIT}?action=create", headers=admin_headers).get_json()
    categorias = client.get(f"{AUDIT}?entity=category", headers=admin_headers).get_json()
    do_admin = client.get(f"{AUDIT}?user_id={haras['user'].id}",
                          headers=admin_headers).get_json()
    futuro = client.get(f"{AUDIT}?from=2099-01-01", headers=admin_headers).get_json()

    assert todos["items"][0]["action"] == "create"  # mais recente primeiro
    assert creates["total"] == 1
    assert categorias["total"] == 1
    assert do_admin["total"] == todos["total"]
    assert futuro["total"] == 0

    item = categorias["items"][0]
    por_id = client.get(f"{AUDIT}?entity=category&entity_id={item['entity_id']}",
                        headers=admin_headers).get_json()
    detalhe = client.get(f"{AUDIT}/{item['id']}", headers=admin_headers)

    assert por_id["total"] == 1
    assert detalhe.status_code == 200
    assert detalhe.get_json()["after_json"]["name"] == "Volumoso"


def test_filtro_invalido_e_422(client, admin_headers):
    assert client.get(f"{AUDIT}?action=hack", headers=admin_headers).status_code == 422
    assert client.get(f"{AUDIT}?entity=senha", headers=admin_headers).status_code == 422


def test_paginacao(client, admin_headers):
    corpo = client.get(f"{AUDIT}?per_page=1", headers=admin_headers).get_json()

    assert corpo["per_page"] == 1
    assert len(corpo["items"]) == 1


def test_tratador_nao_ve_auditoria(client, tratador, admin, auth_headers):
    resposta = client.get(AUDIT, headers=auth_headers("tratador@teste.com", "tratador123"))

    assert resposta.status_code == 403


def test_isolamento(client, admin_headers, outro_haras, auth_headers):
    outro = auth_headers("outro@teste.com", "outro12345")
    do_outro = client.get(AUDIT, headers=outro).get_json()
    meu_log = client.get(AUDIT, headers=admin_headers).get_json()["items"][0]

    assert {log["stable_id"] for log in do_outro["items"]} == {outro_haras["stable"].id}
    assert client.get(f"{AUDIT}/{meu_log['id']}", headers=outro).status_code == 404


def test_sem_escrita_pela_api(client, admin_headers):
    log_id = client.get(AUDIT, headers=admin_headers).get_json()["items"][0]["id"]

    assert client.post(AUDIT, json={}, headers=admin_headers).status_code == 405
    assert client.patch(f"{AUDIT}/{log_id}", json={}, headers=admin_headers).status_code == 405
    assert client.put(f"{AUDIT}/{log_id}", json={}, headers=admin_headers).status_code == 405
    assert client.delete(f"{AUDIT}/{log_id}", headers=admin_headers).status_code == 405


def test_exige_token(client, admin):
    assert client.get(AUDIT).status_code == 401


# ------------------------------------------------------ meta e dashboard

def test_meta_traz_dominios_itil(client, admin_headers):
    corpo = client.get("/api/meta", headers=admin_headers).get_json()

    assert corpo["incident_types"][0] == "ruptura"
    assert corpo["incident_status"] == ["aberto", "em_analise", "resolvido", "fechado"]
    assert corpo["incident_severity"] == ["baixa", "media", "alta", "critica"]
    assert "login_failed" in corpo["audit_actions"]
    assert corpo["niveis_estoque"] == ["ruptura", "critico", "atencao", "ok"]


def test_dashboard_conta_incidentes_ativos(client, haras, admin_headers):
    antes = client.get("/api/dashboard", headers=admin_headers).get_json()
    criado = client.post("/api/incidents", json={"type": "outro", "description": "x"},
                         headers=admin_headers).get_json()
    client.post("/api/incidents", json={"type": "furto", "description": "y"},
                headers=admin_headers)
    client.patch(f"/api/incidents/{criado['id']}",
                 json={"status": "resolvido", "resolution": "ok"}, headers=admin_headers)

    depois = client.get("/api/dashboard", headers=admin_headers).get_json()

    assert antes["incidentes_abertos"] == 0
    assert depois["incidentes_abertos"] == 1
    assert set(antes) - {"incidentes_abertos"} <= set(depois)
