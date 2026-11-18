"""Camada HTTP da API REST, servida sob /api.

Cada recurso tem seu módulo e seu Blueprint; aqui eles são agrupados
no blueprint `api`, junto com os handlers de erro e as mensagens de
falha de token.
"""
from flask import Blueprint

from app.api.errors import (
    MENSAGENS,
    api_error,
    register_error_handlers,
    register_jwt_handlers,
)
from app.api import (
    alerts,
    audit,
    auth,
    categories,
    dashboard,
    health,
    incidents,
    inventory,
    meta,
    movements,
    products,
    suppliers,
    users,
)
from app.extensions import jwt

api = Blueprint("api", __name__, url_prefix="/api")

# Ordem: infraestrutura, acesso, cadastros, operação, consultas
for _module in (
    health,
    auth,
    users,
    categories,
    suppliers,
    products,
    movements,
    inventory,
    incidents,
    alerts,
    dashboard,
    audit,
    meta,
):
    api.register_blueprint(_module.bp)


def register_blueprints(app):
    """Pendura a API na aplicação e liga os handlers."""
    app.register_blueprint(api)
    register_error_handlers(app)
    register_jwt_handlers(jwt)


__all__ = [
    "api",
    "register_blueprints",
    "register_error_handlers",
    "register_jwt_handlers",
    "api_error",
    "MENSAGENS",
]
