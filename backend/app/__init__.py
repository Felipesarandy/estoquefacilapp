"""Application Factory do EstoqueFácil (create_app).

Monta a aplicação a partir da configuração (config.py + .env), liga as
extensões (SQLAlchemy, Migrate, JWT, CORS), o logging, os blueprints da
API e o comando `flask seed`.
"""
import logging
import os

from flask import Flask
from flask_cors import CORS
from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import CHAVE_INSEGURA, config
from app.extensions import db, jwt, migrate


# O SQLite só verifica chaves estrangeiras com este PRAGMA ligado
@event.listens_for(Engine, "connect")
def _sqlite_foreign_keys(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


FORMATO_LOG = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def _configurar_logging(app):
    """Logs no console, no nível de LOG_LEVEL (padrão INFO)."""
    nome = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    nivel = getattr(logging, nome, logging.INFO)

    if not isinstance(nivel, int):
        nivel = logging.INFO

    logging.basicConfig(level=nivel, format=FORMATO_LOG)
    logging.getLogger().setLevel(nivel)
    app.logger.setLevel(nivel)

    return nivel


def _exigir_chaves_em_producao(app, config_name):
    """Em produção as chaves têm de vir do ambiente, nunca o valor padrão."""
    if app.testing or config_name != "production":
        return

    secret = os.getenv("SECRET_KEY")
    if not secret or secret == CHAVE_INSEGURA or not os.getenv("JWT_SECRET_KEY"):
        raise RuntimeError("Configure SECRET_KEY e JWT_SECRET_KEY em produção")


def create_app(config_name=None):
    config_name = config_name or os.getenv("FLASK_CONFIG", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    _configurar_logging(app)
    _exigir_chaves_em_producao(app, config_name)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from app import models  # noqa: F401  (registra os models para o Flask-Migrate)
    from app.api import register_blueprints
    register_blueprints(app)

    from app.seed import seed_command
    app.cli.add_command(seed_command)

    return app
