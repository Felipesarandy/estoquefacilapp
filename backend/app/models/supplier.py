"""Fornecedores dos insumos."""
from app.extensions import db


class Supplier(db.Model):
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    stable_id = db.Column(db.Integer, db.ForeignKey("stables.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(255))

    products = db.relationship("Product", backref="supplier")


__all__ = ["Supplier"]
