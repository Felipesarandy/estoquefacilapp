"""Haras / propriedade que usa o Equihealth."""
from app.extensions import db


class Stable(db.Model):
    """Haras / propriedade que usa o Equihealth."""
    __tablename__ = "stables"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    users = db.relationship("User", backref="stable")
    categories = db.relationship("Category", backref="stable")
    suppliers = db.relationship("Supplier", backref="stable")
    products = db.relationship("Product", backref="stable")


__all__ = ["Stable"]
