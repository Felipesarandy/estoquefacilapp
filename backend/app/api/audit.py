"""Trilha de auditoria das operações (/api/audit)."""
from flask import Blueprint

bp = Blueprint("audit", __name__, url_prefix="/audit")
