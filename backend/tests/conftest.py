from decimal import Decimal

import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Category, Product, Stable, User


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def haras(db):
    stable = Stable(name="Haras Teste")
    user = User(stable=stable, name="Admin", email="admin@teste.com", role="admin")
    user.set_password("123")
    category = Category(stable=stable, name="Ração")
    product = Product(stable=stable, category=category, name="Ração", code="1",
                      unit="kg", cost_price=10, min_stock=5)
    db.session.add_all([stable, user, category, product])
    db.session.commit()
    return {"stable": stable, "user": user, "category": category, "product": product}


@pytest.fixture
def admin(haras):
    """Admin do haras de teste, com a senha usada no login."""
    user = haras["user"]
    user.set_password("admin12345")
    from app.extensions import db as _db
    _db.session.commit()
    return user


@pytest.fixture
def tratador(db, haras):
    """Tratador do mesmo haras do admin."""
    user = User(stable=haras["stable"], name="João Tratador",
                email="tratador@teste.com", role="tratador")
    user.set_password("tratador123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def outro_haras(db):
    """Segundo Stable, com o próprio admin (teste de isolamento)."""
    stable = Stable(name="Outro Haras")
    user = User(stable=stable, name="Outro Admin", email="outro@teste.com", role="admin")
    user.set_password("outro12345")
    db.session.add_all([stable, user])
    db.session.commit()
    return {"stable": stable, "user": user}


@pytest.fixture
def auth_headers(client):
    """Faz login e devolve o cabeçalho Authorization com o token."""

    def _headers(email, password):
        resposta = client.post("/api/auth/login",
                               json={"email": email, "password": password})
        assert resposta.status_code == 200, resposta.get_json()
        return {"Authorization": f"Bearer {resposta.get_json()['access_token']}"}

    return _headers


@pytest.fixture
def insumo(db, haras):
    """Cria insumos com saldo, colchão mínimo e consumo controlados."""
    contador = {"n": 0}

    def _criar(name, saldo="0", minimo="0", consumo=None, active=True,
               code=None, stable=None, category=None):
        contador["n"] += 1
        stable = stable or haras["stable"]
        category = category or haras["category"]

        produto = Product(
            stable_id=stable.id,
            category_id=category.id,
            name=name,
            code=code or f"T{contador['n']:03d}",
            unit="kg",
            cost_price=Decimal("1.00"),
            min_stock=Decimal(str(minimo)),
            current_stock=Decimal(str(saldo)),
            daily_consumption=None if consumo is None else Decimal(str(consumo)),
            active=active,
        )
        db.session.add(produto)
        db.session.commit()
        return produto

    return _criar
