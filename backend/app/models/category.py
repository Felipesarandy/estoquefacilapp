"""Categorias de insumo do haras."""
from app.extensions import db


class Category(db.Model):
    """Ex.: Ração, Volumoso, Suplementos, Vitaminas."""
    __tablename__ = "categories"
    __table_args__ = (db.UniqueConstraint("stable_id", "name"),)

    id = db.Column(db.Integer, primary_key=True)
    stable_id = db.Column(db.Integer, db.ForeignKey("stables.id"), nullable=False)
    name = db.Column(db.String(80), nullable=False)

    products = db.relationship("Product", backref="category")


__all__ = ["Category"]
