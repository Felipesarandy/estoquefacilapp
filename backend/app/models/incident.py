"""Incidentes de estoque (Gestão de Incidentes, ITIL)."""
from app.extensions import db
from app.models.constants import INCIDENT_SEVERITY, INCIDENT_STATUS, INCIDENT_TYPES


def _valores_aceitos(coluna, valores):
    """CHECK (coluna IN (...)) montado a partir das constantes de domínio."""
    lista = ", ".join(f"'{valor}'" for valor in valores)
    return f"{coluna} IN ({lista})"


class Incident(db.Model):
    """Ocorrência que pede tratamento: ruptura, divergência, avaria...

    `opened_by_id` é nulo quando o próprio sistema abre o incidente
    (ex.: ruptura detectada numa saída).
    """
    __tablename__ = "incidents"
    __table_args__ = (
        db.CheckConstraint(_valores_aceitos("type", INCIDENT_TYPES),
                           name="ck_incidents_type"),
        db.CheckConstraint(_valores_aceitos("status", INCIDENT_STATUS),
                           name="ck_incidents_status"),
        db.CheckConstraint(_valores_aceitos("severity", INCIDENT_SEVERITY),
                           name="ck_incidents_severity"),
        db.Index("ix_incidents_stable_status", "stable_id", "status"),
        db.Index("ix_incidents_product_type", "product_id", "type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    stable_id = db.Column(
        db.Integer, db.ForeignKey("stables.id", name="fk_incidents_stable_id"),
        nullable=False,
    )
    product_id = db.Column(
        db.Integer, db.ForeignKey("products.id", name="fk_incidents_product_id")
    )
    type = db.Column(db.String(30), nullable=False)       # ver INCIDENT_TYPES
    status = db.Column(db.String(20), nullable=False, default="aberto",
                       server_default="aberto")           # ver INCIDENT_STATUS
    severity = db.Column(db.String(10), nullable=False)   # ver INCIDENT_SEVERITY
    description = db.Column(db.Text, nullable=False)
    resolution = db.Column(db.Text)
    opened_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", name="fk_incidents_opened_by_id")
    )
    assigned_to_id = db.Column(
        db.Integer, db.ForeignKey("users.id", name="fk_incidents_assigned_to_id")
    )
    opened_at = db.Column(db.DateTime, server_default=db.func.now())
    closed_at = db.Column(db.DateTime)

    product = db.relationship("Product")
    opened_by = db.relationship("User", foreign_keys=[opened_by_id])
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])


__all__ = ["Incident"]
