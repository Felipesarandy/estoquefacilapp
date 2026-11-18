"""Trilha de auditoria: quem fez o quê, quando e com quais valores."""
from sqlalchemy import event

from app.extensions import db


class AuditLog(db.Model):
    """Registro imutável de uma ação no sistema (rastreabilidade ITIL).

    `stable_id` e `user_id` podem ser nulos: uma tentativa de login com
    e-mail desconhecido não pertence a nenhum haras nem usuário.
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        db.Index("ix_audit_logs_stable_created", "stable_id", "created_at"),
        db.Index("ix_audit_logs_entity", "entity", "entity_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    stable_id = db.Column(
        db.Integer, db.ForeignKey("stables.id", name="fk_audit_logs_stable_id")
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", name="fk_audit_logs_user_id")
    )
    action = db.Column(db.String(30), nullable=False)   # ver AUDIT_ACTIONS
    entity = db.Column(db.String(40), nullable=False)   # "product", "user", "movement"...
    entity_id = db.Column(db.Integer)
    before_json = db.Column(db.JSON)
    after_json = db.Column(db.JSON)
    ip = db.Column(db.String(45))                       # cabe IPv6
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User")


def _bloquear_alteracao(mapper, connection, target):
    raise RuntimeError(
        f"{type(target).__name__} é imutável: registros não podem ser alterados nem removidos"
    )


def tornar_imutavel(model):
    """Impede UPDATE e DELETE pelo ORM (o histórico só cresce)."""
    event.listen(model, "before_update", _bloquear_alteracao)
    event.listen(model, "before_delete", _bloquear_alteracao)
    return model


tornar_imutavel(AuditLog)

__all__ = ["AuditLog", "tornar_imutavel"]
