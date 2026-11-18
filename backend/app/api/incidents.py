"""Ocorrências do estoque: avaria, vencimento, furto (/api/incidents)."""
from flask import Blueprint

bp = Blueprint("incidents", __name__, url_prefix="/incidents")
