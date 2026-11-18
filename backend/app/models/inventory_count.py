"""Inventário: contagem física de um insumo."""
from app.extensions import db


class InventoryCount(db.Model):
    """Auditoria de estoque: contagem física de um insumo."""
    __tablename__ = "inventory_counts"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    system_quantity = db.Column(db.Numeric(10, 3), nullable=False)   # saldo no sistema
    counted_quantity = db.Column(db.Numeric(10, 3), nullable=False)  # quantidade contada
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User")

    @property
    def difference(self):
        """Negativo = faltou insumo (divergência de inventário); positivo = sobrou."""
        return self.counted_quantity - self.system_quantity


__all__ = ["InventoryCount"]
