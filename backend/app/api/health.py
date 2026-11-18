"""Health check da API (GET /api/health)."""
from flask import Blueprint

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    """Responde 200 enquanto a API estiver de pé."""
    return {"status": "ok"}, 200
