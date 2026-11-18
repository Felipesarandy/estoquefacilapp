import os

CHAVE_INSEGURA = "chave-padrao-insegura"
CORS_ORIGINS_PADRAO = "http://localhost:5173,http://127.0.0.1:5173"


def _lista_de_origens(valor):
    """Quebra a variável CORS_ORIGINS ("a,b,c") em lista, ignorando vazios."""
    return [origem.strip() for origem in valor.split(",") if origem.strip()]


class DefaultConfig:
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv("SECRET_KEY", CHAVE_INSEGURA)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Autenticação por token (Flask-JWT-Extended)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_EXPIRES_SECONDS", 3600))

    # Origens liberadas para o front-end
    CORS_ORIGINS = _lista_de_origens(os.getenv("CORS_ORIGINS", CORS_ORIGINS_PADRAO))

    # Fuso usado para "hoje" (registro diário e previsão de ruptura)
    TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")

    # Quantos dias antes da quebra de estoque o alerta começa
    ALERTA_DIAS_ANTECEDENCIA = int(os.getenv("ALERTA_DIAS_ANTECEDENCIA", 5))

    # Nível dos logs no console (DEBUG, INFO, WARNING, ERROR)
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class DevelopmentConfig(DefaultConfig):
    DEBUG = True


class TestingConfig(DefaultConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(DefaultConfig):
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
