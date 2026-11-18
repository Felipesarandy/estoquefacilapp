"""Atalhos de desenvolvimento (invoke).

Uso:  invoke --list
      invoke install upgrade seed run
"""
from invoke import task


@task
def install(c):
    """Instala o projeto com dependências de desenvolvimento e teste."""
    c.run('pip install -e ".[dev,test]"', echo=True)


@task
def migrate(c, msg="atualizacao"):
    """Gera uma nova migração a partir dos models (só uma pessoa do grupo)."""
    c.run(f'flask db migrate -m "{msg}"', echo=True)


@task
def upgrade(c):
    """Aplica as migrações no banco."""
    c.run("flask db upgrade", echo=True)


@task
def seed(c):
    """Recria o haras de demonstração (APAGA os dados, sem perguntar)."""
    c.run("flask seed --force", echo=True)


@task
def run(c, port=5000):
    """Sobe a API em modo de desenvolvimento."""
    c.run(f"flask run --port {port}", echo=True, pty=False)


@task
def test(c):
    """Executa os testes automatizados."""
    c.run("pytest -v", echo=True)
