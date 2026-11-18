"""Auditoria: trilha imutável de quem fez o quê (rastreabilidade ITIL).

`record` só adiciona o registro à sessão: quem chama controla a
transação, então a ação e o seu registro de auditoria entram (ou
saem) juntos no mesmo commit.
"""
from datetime import date, datetime
from decimal import Decimal

from flask import has_request_context, request
from sqlalchemy import inspect

from app.extensions import db
from app.models import AuditLog

# Colunas que nunca vão para a trilha (nem com hash)
CAMPOS_SENSIVEIS = {"password", "password_hash", "senha"}


def _para_json(valor):
    """Converte valores do banco em algo que o JSON aceita."""
    if isinstance(valor, Decimal):
        return str(valor)

    if isinstance(valor, (date, datetime)):
        return valor.isoformat()

    return valor


def snapshot(model):
    """Fotografia das colunas do model em JSON, sem senha nem hash."""
    if model is None:
        return None

    colunas = inspect(model).mapper.column_attrs

    return {
        coluna.key: _para_json(getattr(model, coluna.key))
        for coluna in colunas
        if coluna.key not in CAMPOS_SENSIVEIS
    }


def _ip_da_requisicao():
    if not has_request_context():
        return None

    return request.remote_addr


def record(user, action, entity, entity_id=None, before=None, after=None,
           stable_id=None):
    """Adiciona um AuditLog à sessão (sem commit).

    `stable_id` vem do usuário quando não informado; fica nulo apenas
    quando não há haras conhecido (ex.: login com e-mail inexistente).
    """
    if stable_id is None and user is not None:
        stable_id = user.stable_id

    log = AuditLog(
        stable_id=stable_id,
        user_id=user.id if user is not None else None,
        action=action,
        entity=entity,
        entity_id=entity_id,
        before_json=before,
        after_json=after,
        ip=_ip_da_requisicao(),
    )
    db.session.add(log)

    return log


def acao_de_alteracao(antes, depois):
    """"deactivate" quando `active` passa de True para False; senão "update"."""
    if (antes or {}).get("active") is True and (depois or {}).get("active") is False:
        return "deactivate"

    return "update"


def registrar_criacao(user, entity, model):
    """Audita a criação (precisa do id: faz flush, não commit)."""
    db.session.flush()

    return record(user, "create", entity, model.id, after=snapshot(model))


def registrar_alteracao(user, entity, model, antes, extra=None):
    """Audita update/deactivate com o antes e o depois (flush, sem commit)."""
    db.session.flush()

    depois = snapshot(model)
    if extra:
        depois.update(extra)

    return record(user, acao_de_alteracao(antes, depois), entity, model.id,
                  before=antes, after=depois)


def registrar_exclusao(user, entity, entity_id, antes):
    """Audita a exclusão física: before = dados removidos, after = nulo (sem commit)."""
    return record(user, "delete", entity, entity_id, before=antes, after=None)


def consultar(stable_id, action=None, entity=None, entity_id=None,
              user_id=None, inicio=None, fim=None):
    """Query da trilha do haras, mais recentes primeiro.

    `inicio`/`fim` são instantes em UTC (como o banco grava created_at).
    """
    query = db.session.query(AuditLog).filter(AuditLog.stable_id == stable_id)

    if action:
        query = query.filter(AuditLog.action == action)

    if entity:
        query = query.filter(AuditLog.entity == entity)

    if entity_id is not None:
        query = query.filter(AuditLog.entity_id == entity_id)

    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)

    if inicio is not None:
        query = query.filter(AuditLog.created_at >= inicio)

    if fim is not None:
        query = query.filter(AuditLog.created_at < fim)

    return query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())


__all__ = [
    "CAMPOS_SENSIVEIS",
    "snapshot",
    "record",
    "acao_de_alteracao",
    "registrar_criacao",
    "registrar_alteracao",
    "registrar_exclusao",
    "consultar",
]
