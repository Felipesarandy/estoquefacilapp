"""Formatos da resposta: datas com fuso e erros padrão em português."""
from datetime import datetime


def test_created_at_vem_no_fuso_do_haras_com_offset(client, admin, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")
    corpo = client.get("/api/auth/me", headers=headers).get_json()

    criado = datetime.fromisoformat(corpo["created_at"])
    assert criado.utcoffset() is not None          # tem fuso (o front converte certo)
    assert corpo["created_at"].endswith("-03:00")  # America/Sao_Paulo


def test_metodo_nao_permitido_em_portugues(client, admin, auth_headers):
    headers = auth_headers("admin@teste.com", "admin12345")
    resposta = client.delete("/api/movements/1", headers=headers)

    assert resposta.status_code == 405
    assert resposta.get_json()["error"]["message"] == "Método não permitido para este recurso."


def test_rota_inexistente_em_portugues(client):
    resposta = client.get("/api/nao-existe")

    assert resposta.status_code == 404
    assert resposta.get_json()["error"]["message"] == "Recurso não encontrado."
