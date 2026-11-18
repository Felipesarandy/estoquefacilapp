"""Erros de regra de negócio levantados pelos serviços.

Ficam num módulo próprio para os serviços poderem usá-los sem importar
uns aos outros em círculo. A API converte todos em 409.
"""


class Conflito(Exception):
    """Operação válida, mas impossível no estado atual (vira 409 na API)."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class ConflitoDeEstoque(Conflito):
    """Saldo insuficiente ou insumo inativo."""


class TransicaoInvalida(Conflito):
    """Mudança de status de incidente fora do ciclo de vida permitido."""


__all__ = ["Conflito", "ConflitoDeEstoque", "TransicaoInvalida"]
