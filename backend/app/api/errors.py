"""Respostas de erro da API, sempre em JSON.

Formato: {"error": {"status": 404, "message": "...", "details": {...}}}

Este módulo não importa nada de `app.api` (evita import circular):
quem precisa de `api_error` importa daqui.
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException

from app.extensions import db
from app.schemas.common import ValidationError
from app.services.exceptions import Conflito

# Status usados pela API (REST): 200, 201, 204, 400, 401, 403, 404, 409, 422
MENSAGENS = {
    400: "Requisição inválida.",
    401: "Autenticação necessária.",
    403: "Acesso negado.",
    404: "Recurso não encontrado.",
    405: "Método não permitido para este recurso.",
    409: "Conflito com o estado atual do recurso.",
    415: "Formato de conteúdo não suportado (use application/json).",
    422: "Não foi possível processar os dados enviados.",
    500: "Erro interno no servidor.",
}


def api_error(status, message=None, details=None):
    """Monta a resposta de erro padronizada."""
    corpo = {"error": {"status": status, "message": message or MENSAGENS.get(status, "Erro.")}}

    if details:
        corpo["error"]["details"] = details

    return jsonify(corpo), status


def register_error_handlers(app):
    """Converte qualquer exceção em uma resposta JSON padronizada."""

    @app.errorhandler(ValidationError)
    def _dados_invalidos(e):
        details = {"field": e.field} if e.field else None
        return api_error(e.status, e.message, details)

    @app.errorhandler(Conflito)
    def _conflito(e):
        db.session.rollback()
        return api_error(409, e.message)

    @app.errorhandler(HTTPException)
    def _http_exception(e):
        return api_error(e.code, e.description or MENSAGENS.get(e.code))

    @app.errorhandler(Exception)
    def _erro_inesperado(e):
        if isinstance(e, ValidationError):
            return _dados_invalidos(e)
        if isinstance(e, Conflito):
            return _conflito(e)
        if isinstance(e, HTTPException):
            return _http_exception(e)
        app.logger.exception("Erro não tratado na API")
        return api_error(500)


def register_jwt_handlers(jwt):
    """Mensagens em português para as falhas de token do Flask-JWT-Extended."""

    @jwt.unauthorized_loader
    def _token_ausente(reason):
        return api_error(401, "Token de acesso obrigatório")

    @jwt.invalid_token_loader
    def _token_invalido(reason):
        return api_error(401, "Token inválido")

    @jwt.expired_token_loader
    def _token_expirado(jwt_header, jwt_payload):
        return api_error(401, "Token expirado")

    @jwt.revoked_token_loader
    def _token_revogado(jwt_header, jwt_payload):
        return api_error(401, "Token revogado")


__all__ = ["MENSAGENS", "api_error", "register_error_handlers", "register_jwt_handlers"]
