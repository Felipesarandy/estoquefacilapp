"""Inventário: contagens físicas x saldo do sistema (/api/inventory)."""
from flask import Blueprint

bp = Blueprint("inventory", __name__, url_prefix="/inventory")
