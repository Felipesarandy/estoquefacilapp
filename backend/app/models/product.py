"""Insumos do haras (ração, volumoso, suplementos, vitaminas)."""
from app.extensions import db


class Product(db.Model):
    """Insumo do haras: ração, feno, suplemento, vitamina..."""
    __tablename__ = "products"
    __table_args__ = (
        db.UniqueConstraint("stable_id", "code"),
        db.CheckConstraint("current_stock >= 0", name="ck_products_saldo_positivo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    stable_id = db.Column(db.Integer, db.ForeignKey("stables.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"))  # opcional
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(50))  # código interno / de barras (opcional)
    unit = db.Column(db.String(10), nullable=False, default="kg")  # ver UNIDADES
    cost_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # custo por unidade
    min_stock = db.Column(db.Numeric(10, 3), nullable=False, default=0)  # estoque de segurança
    max_stock = db.Column(db.Numeric(10, 3))  # opcional: evita comprar demais (vencimento)
    current_stock = db.Column(db.Numeric(10, 3), nullable=False, default=0)
    daily_consumption = db.Column(db.Numeric(10, 3))  # consumo médio por dia (opcional)
    active = db.Column(db.Boolean, default=True)

    movements = db.relationship("StockMovement", backref="product")
    inventory_counts = db.relationship("InventoryCount", backref="product")

    @property
    def is_low_stock(self):
        return self.current_stock <= self.min_stock

    @property
    def stock_value(self):
        """Capital imobilizado no insumo (saldo x custo)."""
        return self.current_stock * self.cost_price

    @property
    def days_left(self):
        """Quantos dias o saldo atual dura no consumo médio (None se não informado)."""
        if not self.daily_consumption:
            return None
        return self.current_stock / self.daily_consumption


__all__ = ["Product"]
