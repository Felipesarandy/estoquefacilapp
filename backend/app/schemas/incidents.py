"""Schemas de incidente: abertura manual, atualização e saída."""
from app.models import INCIDENT_SEVERITY, INCIDENT_STATUS, INCIDENT_TYPES
from app.schemas.common import (
    ValidationError,
    choice_field,
    integer_field,
    optional_string,
    required_string,
    texto,
)



def serialize_incident(item):
    """Saída pública do incidente."""
    return {
        "id": item.id,
        "stable_id": item.stable_id,
        "product_id": item.product_id,
        "type": item.type,
        "status": item.status,
        "severity": item.severity,
        "description": item.description,
        "resolution": item.resolution,
        "opened_by_id": item.opened_by_id,
        "assigned_to_id": item.assigned_to_id,
        "opened_at": texto(item.opened_at),
        "closed_at": texto(item.closed_at),
    }


def new_incident_payload(data):
    """Abertura manual (POST /api/incidents); severity é opcional."""
    severidade = data.get("severity")

    return {
        "product_id": integer_field(data, "product_id"),
        "type": choice_field(data.get("type"), INCIDENT_TYPES, "type"),
        "severity": (choice_field(severidade, INCIDENT_SEVERITY, "severity")
                     if severidade is not None else None),
        "description": required_string(data, "description", 5000),
    }


def incident_update_payload(data):
    """Só os campos presentes (PATCH /api/incidents/<id>).

    `assigned_to_id: null` remove o responsável.
    """
    changes = {}

    if "status" in data:
        changes["status"] = choice_field(data.get("status"), INCIDENT_STATUS, "status")

    if "assigned_to_id" in data:
        changes["assigned_to_id"] = integer_field(data, "assigned_to_id")

    if "resolution" in data:
        changes["resolution"] = optional_string(data, "resolution", 5000)

    if not changes:
        raise ValidationError("Informe ao menos um campo para atualizar")

    return changes


def status_filter(valor):
    return choice_field(valor, INCIDENT_STATUS, "status") if valor else None


def type_filter(valor):
    return choice_field(valor, INCIDENT_TYPES, "type") if valor else None


__all__ = [
    "serialize_incident",
    "new_incident_payload",
    "incident_update_payload",
    "status_filter",
    "type_filter",
]
