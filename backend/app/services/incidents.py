"""Gestão de incidentes (ITIL): abertura, severidade e ciclo de vida.

Ciclo de vida (qualquer outra mudança é 409):

    aberto      -> em_analise | resolvido
    em_analise  -> resolvido  | aberto
    resolvido   -> fechado    | em_analise
    fechado     (final)

`closed_at` marca o fim do atendimento: é preenchido quando o incidente
é resolvido, mantido ao fechar e limpo se ele for reaberto.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.extensions import db
from app.models import Incident
from app.schemas.common import ValidationError
from app.services import audit
from app.services.exceptions import TransicaoInvalida

logger = logging.getLogger(__name__)

ABERTO = "aberto"
EM_ANALISE = "em_analise"
RESOLVIDO = "resolvido"
FECHADO = "fechado"

# Incidentes que ainda pedem ação (não duplicamos estes)
ATIVOS = (ABERTO, EM_ANALISE)

TRANSICOES = {
    ABERTO: (EM_ANALISE, RESOLVIDO),
    EM_ANALISE: (RESOLVIDO, ABERTO),
    RESOLVIDO: (FECHADO, EM_ANALISE),
    FECHADO: (),
}

RUPTURA = "ruptura"
DIVERGENCIA = "divergencia_inventario"

RESOLUCAO_REPOSICAO = "Reposição registrada"


def _agora_utc():
    """Instante atual em UTC sem fuso e sem microssegundos (como o banco grava)."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


# --------------------------------------------------------------- severidade

def severidade_divergencia(system_quantity, difference):
    """|diferença| / saldo do sistema: >= 20% alta, >= 5% media, senão baixa.

    Sem saldo no sistema não há percentual: qualquer sobra é "alta".
    """
    diferenca = abs(Decimal(difference))

    if diferenca == 0:
        return "baixa"

    if Decimal(system_quantity) <= 0:
        return "alta"

    percentual = diferenca / Decimal(system_quantity)

    if percentual >= Decimal("0.20"):
        return "alta"

    if percentual >= Decimal("0.05"):
        return "media"

    return "baixa"


def severidade_padrao(tipo):
    """Severidade quando quem abre não informa: ruptura é sempre crítica."""
    return "critica" if tipo == RUPTURA else "media"


# -------------------------------------------------------------- abertura

def incidente_ativo(stable_id, product_id, tipo):
    """Incidente aberto/em análise do mesmo insumo e tipo, se houver."""
    if product_id is None:
        return None

    return (
        db.session.query(Incident)
        .filter(
            Incident.stable_id == stable_id,
            Incident.product_id == product_id,
            Incident.type == tipo,
            Incident.status.in_(ATIVOS),
        )
        .order_by(Incident.id)
        .first()
    )


def abrir_incidente(stable_id, tipo, description, severity=None, product=None,
                    opened_by=None, actor=None):
    """Abre um incidente sem duplicar um ativo do mesmo insumo e tipo.

    Devolve (incidente, criado). `opened_by` nulo = aberto pelo sistema;
    `actor` é quem disparou a ação, para a auditoria.
    """
    existente = incidente_ativo(stable_id, product.id if product else None, tipo)

    if existente is not None:
        return existente, False

    incidente = Incident(
        stable_id=stable_id,
        product_id=product.id if product else None,
        type=tipo,
        status=ABERTO,
        severity=severity or severidade_padrao(tipo),
        description=description,
        opened_by_id=opened_by.id if opened_by else None,
    )
    db.session.add(incidente)
    db.session.flush()

    audit.record(actor or opened_by, "incident", "incident", incidente.id,
                 after=audit.snapshot(incidente), stable_id=stable_id)

    logger.info(
        "incidente aberto | id=%s tipo=%s severidade=%s insumo=%s origem=%s",
        incidente.id, tipo, incidente.severity,
        incidente.product_id, "usuario" if opened_by else "sistema",
    )

    return incidente, True


# ----------------------------------------------------------- ciclo de vida

def mudar_status(incidente, novo_status, user, resolution=None):
    """Aplica uma transição válida; 409 se inválida, 422 sem resolução."""
    atual = incidente.status

    if novo_status == atual:
        return incidente

    if novo_status not in TRANSICOES.get(atual, ()):
        raise TransicaoInvalida(
            f"Transição inválida: {atual} -> {novo_status}"
        )

    if resolution is not None:
        incidente.resolution = resolution

    if novo_status == RESOLVIDO and not (incidente.resolution or "").strip():
        raise ValidationError(
            "Informe a resolução ao resolver o incidente", field="resolution"
        )

    if novo_status == RESOLVIDO:
        incidente.closed_at = _agora_utc()
    elif novo_status == FECHADO:
        incidente.closed_at = incidente.closed_at or _agora_utc()
    else:  # reaberto (aberto / em_analise)
        incidente.closed_at = None

    incidente.status = novo_status

    logger.info(
        "incidente mudou de status | id=%s %s -> %s usuario=%s",
        incidente.id, atual, novo_status, user.id if user else "sistema",
    )

    return incidente


def atualizar_incidente(incidente, user, status=None, assigned_to=None,
                        atribuir=False, resolution=None):
    """PATCH do incidente: status, responsável e/ou resolução, auditado."""
    antes = audit.snapshot(incidente)

    if atribuir:
        incidente.assigned_to_id = assigned_to.id if assigned_to else None

    if status is not None:
        mudar_status(incidente, status, user, resolution)
    elif resolution is not None:
        incidente.resolution = resolution

    db.session.flush()

    audit.record(user, "incident", "incident", incidente.id,
                 before=antes, after=audit.snapshot(incidente),
                 stable_id=incidente.stable_id)

    return incidente


# --------------------------------------------------------- automação

def sincronizar_ruptura(product, user=None):
    """Abre o incidente de ruptura ao zerar; resolve sozinho na reposição."""
    if product.current_stock is None:
        return None

    if product.current_stock <= 0:
        incidente, _ = abrir_incidente(
            product.stable_id,
            RUPTURA,
            f"Ruptura de estoque: {product.name} zerou.",
            product=product,
            actor=user,
        )
        return incidente

    ativo = incidente_ativo(product.stable_id, product.id, RUPTURA)

    if ativo is not None:
        atualizar_incidente(ativo, user, status=RESOLVIDO,
                            resolution=RESOLUCAO_REPOSICAO)

    return ativo


# ------------------------------------------------------------- consultas

def consultar(stable_id, status=None, tipo=None, product_id=None,
              assigned_to_id=None):
    """Query dos incidentes do haras, mais recentes primeiro."""
    query = db.session.query(Incident).filter(Incident.stable_id == stable_id)

    if status:
        query = query.filter(Incident.status == status)

    if tipo:
        query = query.filter(Incident.type == tipo)

    if product_id is not None:
        query = query.filter(Incident.product_id == product_id)

    if assigned_to_id is not None:
        query = query.filter(Incident.assigned_to_id == assigned_to_id)

    return query.order_by(Incident.opened_at.desc(), Incident.id.desc())


def contar_ativos(stable_id):
    """Quantos incidentes ainda pedem ação (aberto ou em análise)."""
    return (
        db.session.query(db.func.count(Incident.id))
        .filter(Incident.stable_id == stable_id, Incident.status.in_(ATIVOS))
        .scalar()
    )


def resumo(stable_id):
    """Contagem por status e por tipo e tempo médio de resolução (horas)."""
    por_status = dict(
        db.session.query(Incident.status, db.func.count(Incident.id))
        .filter(Incident.stable_id == stable_id)
        .group_by(Incident.status)
        .all()
    )
    por_tipo = dict(
        db.session.query(Incident.type, db.func.count(Incident.id))
        .filter(Incident.stable_id == stable_id)
        .group_by(Incident.type)
        .all()
    )

    encerrados = (
        db.session.query(Incident.opened_at, Incident.closed_at)
        .filter(
            Incident.stable_id == stable_id,
            Incident.status.in_((RESOLVIDO, FECHADO)),
            Incident.opened_at.isnot(None),
            Incident.closed_at.isnot(None),
        )
        .all()
    )

    horas = [
        max((fim - inicio).total_seconds(), 0) / 3600 for inicio, fim in encerrados
    ]

    return {
        "por_status": por_status,
        "por_tipo": por_tipo,
        "total": sum(por_status.values()),
        "encerrados": len(horas),
        "tempo_medio_resolucao_horas": round(sum(horas) / len(horas), 2) if horas else None,
    }


__all__ = [
    "ABERTO",
    "EM_ANALISE",
    "RESOLVIDO",
    "FECHADO",
    "ATIVOS",
    "TRANSICOES",
    "RUPTURA",
    "DIVERGENCIA",
    "RESOLUCAO_REPOSICAO",
    "severidade_divergencia",
    "severidade_padrao",
    "incidente_ativo",
    "abrir_incidente",
    "mudar_status",
    "atualizar_incidente",
    "sincronizar_ruptura",
    "consultar",
    "contar_ativos",
    "resumo",
]
