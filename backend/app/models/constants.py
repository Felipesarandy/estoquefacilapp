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

TIPOS_MOVIMENTACAO = ["entrada", "saida"]
MOTIVOS_POR_TIPO = {"entrada": MOTIVOS_ENTRADA, "saida": MOTIVOS_SAIDA}

UNIDADES = ["kg", "g", "sc", "l", "ml", "un"]  # sc = saco | un = fardo, bisnaga, frasco...

# "Quebra de estoque" = colchão mínimo (min_stock); estes são os níveis de saldo,
# do mais grave para o mais tranquilo (ver app/services/alerts.py)
NIVEIS_ESTOQUE = ["ruptura", "critico", "atencao", "ok"]

# Gestão de incidentes (ITIL): tipo, ciclo de vida e severidade
INCIDENT_TYPES = [
    "ruptura",                 # saldo zerou (aberto automaticamente)
    "divergencia_inventario",  # contagem física diferente do sistema
    "avaria",
    "vencimento",
    "furto",
    "outro",
]
INCIDENT_STATUS = ["aberto", "em_analise", "resolvido", "fechado"]
INCIDENT_SEVERITY = ["baixa", "media", "alta", "critica"]

# Trilha de auditoria: o que foi feito
AUDIT_ACTIONS = [
    "login",
    "login_failed",
    "create",
    "update",
    "deactivate",
    "movement",
    "inventory",
    "incident",
]

__all__ = [
    "ROLES",
    "MOTIVOS_ENTRADA",
    "MOTIVOS_SAIDA",
    "MOTIVOS_PERDA",
    "TIPOS_MOVIMENTACAO",
    "MOTIVOS_POR_TIPO",
    "UNIDADES",
    "NIVEIS_ESTOQUE",
    "INCIDENT_TYPES",
    "INCIDENT_STATUS",
    "INCIDENT_SEVERITY",
    "AUDIT_ACTIONS",
]
