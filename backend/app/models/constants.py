"""Valores aceitos nos campos de domínio (validar na API)."""

# Papéis de usuário
ROLES = ["admin", "tratador"]

# Motivos aceitos em cada tipo de movimentação
MOTIVOS_ENTRADA = ["compra", "doacao", "ajuste"]
MOTIVOS_SAIDA = [
    "abastecimento_alimentador",  # reposição do reservatório do alimentador Equihealth
    "trato_manual",               # ração/suplemento dado à mão pelo tratador
    "avaria",                     # saco rasgado, umidade, mofo, roedores
    "vencimento",
    "furto",
    "ajuste",
]
MOTIVOS_PERDA = ["avaria", "vencimento", "furto"]  # perdas registradas como saída

UNIDADES = ["kg", "g", "sc", "l", "ml", "un"]  # sc = saco | un = fardo, bisnaga, frasco...

# "Quebra de estoque" = colchão mínimo (min_stock); estes são os níveis de saldo,
# do mais grave para o mais tranquilo (ver app/services/alerts.py)
NIVEIS_ESTOQUE = ["ruptura", "critico", "atencao", "ok"]

__all__ = [
    "ROLES",
    "MOTIVOS_ENTRADA",
    "MOTIVOS_SAIDA",
    "MOTIVOS_PERDA",
    "UNIDADES",
    "NIVEIS_ESTOQUE",
]
