"""Movimentações de estoque (entradas e saídas)."""
from app.extensions import db


class StockMovement(db.Model):
    __tablename__ = "stock_movements"
    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="ck_movements_quantidade_positiva"),
    )

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    type = db.Column(db.String(10), nullable=False)    # entrada | saida
    reason = db.Column(db.String(30), nullable=False)  # ver MOTIVOS_ENTRADA / MOTIVOS_SAIDA
    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)  # custo unitário no momento
    batch = db.Column(db.String(50))         # lote (entradas)
    expiration_date = db.Column(db.Date)     # validade do lote (entradas)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost


__all__ = ["StockMovement"]
