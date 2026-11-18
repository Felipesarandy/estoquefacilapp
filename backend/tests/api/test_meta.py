"""Metadados de domínio (/api/meta)."""
from app.models import (
    MOTIVOS_ENTRADA,
    MOTIVOS_PERDA,
    MOTIVOS_SAIDA,
    NIVEIS_ESTOQUE,
    ROLES,
    UNIDADES,
)

META = "/api/meta"


def test_meta_devolve_as_constantes(client, admin, auth_headers):
    resposta = client.get(META, headers=auth_headers("admin@teste.com", "admin12345"))
    corpo = resposta.get_json()

    assert resposta.status_code == 200
    assert corpo["motivos_entrada"] == MOTIVOS_ENTRADA
    assert corpo["motivos_saida"] == MOTIVOS_SAIDA
    assert corpo["motivos_perda"] == MOTIVOS_PERDA
    assert corpo["unidades"] == UNIDADES
    assert corpo["roles"] == ROLES
    assert corpo["niveis_estoque"] == NIVEIS_ESTOQUE


def test_meta_aberta_ao_tratador(client, admin, tratador, auth_headers):
    resposta = client.get(META, headers=auth_headers("tratador@teste.com", "tratador123"))

    assert resposta.status_code == 200


def test_meta_exige_token(client, admin):
    resposta = client.get(META)

    assert resposta.status_code == 401
    assert resposta.get_json()["error"]["message"] == "Token de acesso obrigatório"
