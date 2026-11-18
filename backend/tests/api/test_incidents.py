"""Gestão de incidentes pela API (/api/incidents)."""
import pytest

INCIDENTS = "/api/incidents"


@pytest.fixture
def admin_headers(admin, auth_headers):
    return auth_headers("admin@teste.com", "admin12345")


@pytest.fixture
def tratador_headers(admin, tratador, auth_headers):
    return auth_headers("tratador@teste.com", "tratador123")


@pytest.fixture
def avaria(client, haras, admin_headers):
    return client.post(INCIDENTS, json={"product_id": haras["product"].id, "type": "avaria",
                                        "severity": "media",
                                        "description": "Saco rasgado"},
                       headers=admin_headers).get_json()


def test_abertura_manual(client, haras, avaria):
    assert avaria["type"] == "avaria"
    assert avaria["status"] == "aberto"
    assert avaria["severity"] == "media"
    assert avaria["product_id"] == haras["product"].id
    assert avaria["opened_by_id"] == haras["user"].id
    assert avaria["closed_at"] is None


def test_abertura_sem_insumo_e_sem_severidade(client, haras, admin_headers):
    resposta = client.post(INCIDENTS, json={"type": "outro", "description": "Cerca caída"},
                           headers=admin_headers)

    assert resposta.status_code == 201
    assert resposta.get_json()["product_id"] is None
    assert resposta.get_json()["severity"] == "media"


def test_tratador_abre_incidente(client, haras, tratador_headers):
    resposta = client.post(INCIDENTS, json={"type": "furto", "description": "Sumiu um fardo"},
                           headers=tratador_headers)

    assert resposta.status_code == 201


def test_duplicado_ativo_e_409(client, haras, avaria, admin_headers):
    resposta = client.post(INCIDENTS, json={"product_id": haras["product"].id,
                                            "type": "avaria", "description": "De novo"},
                           headers=admin_headers)

    assert resposta.status_code == 409
    assert resposta.get_json()["error"]["details"] == {"incident_id": avaria["id"]}


@pytest.mark.parametrize("dados, campo", [
    ({"type": "enchente", "description": "x"}, "type"),
    ({"type": "outro", "severity": "gravissima", "description": "x"}, "severity"),
    ({"type": "outro"}, "description"),
])
def test_validacao_da_abertura(client, haras, admin_headers, dados, campo):
    resposta = client.post(INCIDENTS, json=dados, headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": campo}


def test_insumo_de_outro_haras_e_422(client, haras, outro_haras, auth_headers):
    resposta = client.post(INCIDENTS, json={"product_id": haras["product"].id,
                                            "type": "avaria", "description": "x"},
                           headers=auth_headers("outro@teste.com", "outro12345"))

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "product_id"}


def test_ciclo_de_vida_completo(client, avaria, admin_headers):
    url = f"{INCIDENTS}/{avaria['id']}"

    em_analise = client.patch(url, json={"status": "em_analise"}, headers=admin_headers)
    resolvido = client.patch(url, json={"status": "resolvido", "resolution": "Trocado"},
                             headers=admin_headers)
    fechado = client.patch(url, json={"status": "fechado"}, headers=admin_headers)

    assert em_analise.get_json()["status"] == "em_analise"
    assert resolvido.get_json()["resolution"] == "Trocado"
    assert resolvido.get_json()["closed_at"] is not None
    assert fechado.status_code == 200
    assert fechado.get_json()["status"] == "fechado"


def test_transicao_invalida_e_409(client, avaria, admin_headers):
    resposta = client.patch(f"{INCIDENTS}/{avaria['id']}", json={"status": "fechado"},
                            headers=admin_headers)

    assert resposta.status_code == 409
    assert "aberto -> fechado" in resposta.get_json()["error"]["message"]


def test_fechado_e_final(client, avaria, admin_headers):
    url = f"{INCIDENTS}/{avaria['id']}"
    client.patch(url, json={"status": "resolvido", "resolution": "ok"}, headers=admin_headers)
    client.patch(url, json={"status": "fechado"}, headers=admin_headers)

    assert client.patch(url, json={"status": "em_analise"},
                        headers=admin_headers).status_code == 409


def test_resolver_sem_resolucao_e_422(client, avaria, admin_headers):
    resposta = client.patch(f"{INCIDENTS}/{avaria['id']}", json={"status": "resolvido"},
                            headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "resolution"}


def test_atribuicao(client, avaria, tratador, admin_headers):
    url = f"{INCIDENTS}/{avaria['id']}"

    atribuido = client.patch(url, json={"assigned_to_id": tratador.id}, headers=admin_headers)
    removido = client.patch(url, json={"assigned_to_id": None}, headers=admin_headers)

    assert atribuido.get_json()["assigned_to_id"] == tratador.id
    assert removido.get_json()["assigned_to_id"] is None


def test_atribuir_a_usuario_de_outro_haras_e_422(client, avaria, outro_haras, admin_headers):
    resposta = client.patch(f"{INCIDENTS}/{avaria['id']}",
                            json={"assigned_to_id": outro_haras["user"].id},
                            headers=admin_headers)

    assert resposta.status_code == 422
    assert resposta.get_json()["error"]["details"] == {"field": "assigned_to_id"}


def test_patch_sem_campos_e_422(client, avaria, admin_headers):
    assert client.patch(f"{INCIDENTS}/{avaria['id']}", json={},
                        headers=admin_headers).status_code == 422


def test_tratador_nao_altera_incidente(client, avaria, tratador_headers):
    resposta = client.patch(f"{INCIDENTS}/{avaria['id']}", json={"status": "em_analise"},
                            headers=tratador_headers)

    assert resposta.status_code == 403


def test_sem_delete(client, avaria, admin_headers):
    assert client.delete(f"{INCIDENTS}/{avaria['id']}",
                         headers=admin_headers).status_code == 405


def test_listagem_e_filtros(client, haras, avaria, tratador, admin_headers):
    client.post(INCIDENTS, json={"type": "furto", "description": "Sumiu"},
                headers=admin_headers)
    client.patch(f"{INCIDENTS}/{avaria['id']}",
                 json={"status": "em_analise", "assigned_to_id": tratador.id},
                 headers=admin_headers)

    def total(filtro):
        return client.get(f"{INCIDENTS}?{filtro}", headers=admin_headers).get_json()["total"]

    assert total("") == 2
    assert total("status=em_analise") == 1
    assert total("type=furto") == 1
    assert total(f"product_id={haras['product'].id}") == 1
    assert total(f"assigned_to_id={tratador.id}") == 1
    assert client.get(f"{INCIDENTS}?per_page=1",
                      headers=admin_headers).get_json()["per_page"] == 1
    assert client.get(f"{INCIDENTS}?status=pendente",
                      headers=admin_headers).status_code == 422


def test_detalhe_e_isolamento(client, avaria, outro_haras, admin_headers, auth_headers):
    outro = auth_headers("outro@teste.com", "outro12345")

    assert client.get(f"{INCIDENTS}/{avaria['id']}", headers=admin_headers).status_code == 200
    assert client.get(f"{INCIDENTS}/{avaria['id']}", headers=outro).status_code == 404
    assert client.get(INCIDENTS, headers=outro).get_json()["total"] == 0
    assert client.patch(f"{INCIDENTS}/{avaria['id']}", json={"status": "em_analise"},
                        headers=outro).status_code == 404


def test_summary(client, avaria, admin_headers):
    client.post(INCIDENTS, json={"type": "furto", "description": "Sumiu"},
                headers=admin_headers)
    client.patch(f"{INCIDENTS}/{avaria['id']}",
                 json={"status": "resolvido", "resolution": "Trocado"},
                 headers=admin_headers)

    corpo = client.get(f"{INCIDENTS}/summary", headers=admin_headers).get_json()

    assert corpo["total"] == 2
    assert corpo["por_status"] == {"aberto": 1, "resolvido": 1}
    assert corpo["por_tipo"] == {"avaria": 1, "furto": 1}
    assert corpo["encerrados"] == 1
    assert corpo["tempo_medio_resolucao_horas"] is not None


def test_ruptura_pela_api_de_movimentacao(client, haras, insumo, admin_headers):
    feno = insumo("Feno", saldo="0", minimo="5", consumo="1")
    mov = {"product_id": feno.id, "quantity": "10"}

    client.post("/api/movements", json={**mov, "type": "entrada", "reason": "compra"},
                headers=admin_headers)
    client.post("/api/movements", json={**mov, "type": "saida", "reason": "trato_manual"},
                headers=admin_headers)

    abertos = client.get(f"{INCIDENTS}?type=ruptura&status=aberto",
                         headers=admin_headers).get_json()
    assert abertos["total"] == 1

    client.post("/api/movements", json={**mov, "type": "entrada", "reason": "compra"},
                headers=admin_headers)

    resolvidos = client.get(f"{INCIDENTS}?type=ruptura&status=resolvido",
                            headers=admin_headers).get_json()
    assert resolvidos["total"] == 1
    assert resolvidos["items"][0]["resolution"] == "Reposição registrada"


def test_exige_token(client, haras):
    assert client.get(INCIDENTS).status_code == 401
    assert client.get(f"{INCIDENTS}/summary").status_code == 401
