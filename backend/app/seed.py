"""Dados iniciais para desenvolvimento e demonstração.

Uso:  flask seed            (pede confirmação: APAGA os dados)
      flask seed --force    (sem perguntar; usado por `invoke seed`)

Monta um haras de demonstração com insumos nos quatro níveis de estoque
(ruptura, critico, atencao e ok), movimentações espalhadas pelos últimos
sete dias, uma contagem de inventário com divergência, incidentes e a
trilha de auditoria. Tudo passa pelos serviços (stock, inventory,
incidents, audit): o seed não reimplementa nenhuma regra.
"""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import click

from app.extensions import db
from app.models import Category, Product, Stable, Supplier, User
from app.services import audit, incidents, inventory
from app.services.alerts import fuso, hoje, nivel
from app.services.stock import registrar_movimentacao

DIAS_DE_HISTORICO = 7


def _quando(dias_atras, hora=8):
    """Instante de um dia atrás, no fuso do haras, convertido para UTC.

    O banco grava `created_at` em UTC (CURRENT_TIMESTAMP), então o seed
    guarda UTC para o registro diário cair no dia local certo.
    """
    dia = hoje() - timedelta(days=dias_atras)
    local = datetime.combine(dia, time(hour=hora), tzinfo=fuso())

    return local.astimezone(timezone.utc).replace(tzinfo=None)


@click.command("seed")
@click.option("--force", is_flag=True, help="Não pede confirmação antes de apagar os dados.")
def seed_command(force):
    """Apaga os dados e popula o banco com um haras de exemplo."""
    if not force:
        click.confirm(
            "Isto APAGA todos os dados do banco e cria o haras de exemplo. Continuar?",
            abort=True,
        )

    # limpa as tabelas (das "filhas" para as "mães"), mantendo a estrutura das migrações
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())

    haras = Stable(name="Haras Exemplo", city="Vila Velha")

    admin = User(stable=haras, name="Felipe Admin", email="admin@haras.com", role="admin")
    admin.set_password("admin123")
    tratador = User(stable=haras, name="João Tratador", email="tratador@haras.com", role="tratador")
    tratador.set_password("trat123")

    racao = Category(stable=haras, name="Ração")
    volumoso = Category(stable=haras, name="Volumoso")
    suplementos = Category(stable=haras, name="Suplementos")
    vitaminas = Category(stable=haras, name="Vitaminas")

    nutriequi = Supplier(stable=haras, name="Nutriequi Rações", phone="(27) 3333-0001",
                         email="vendas@nutriequi.com")
    agro = Supplier(stable=haras, name="Agropecuária Capixaba", phone="(27) 3333-0002")

    produtos = [
        Product(stable=haras, category=racao, supplier=nutriequi, name="Ração peletizada 14% PB",
                code="EQ001", unit="kg", cost_price=Decimal("3.20"),
                min_stock=Decimal("100"), max_stock=Decimal("600"), daily_consumption=Decimal("24")),
        Product(stable=haras, category=racao, supplier=nutriequi, name="Ração extrusada performance",
                code="EQ002", unit="kg", cost_price=Decimal("5.80"),
                min_stock=Decimal("50"), daily_consumption=Decimal("8")),
        Product(stable=haras, category=racao, supplier=nutriequi, name="Ração de potros (crescimento)",
                code="EQ003", unit="kg", cost_price=Decimal("4.50"),
                min_stock=Decimal("20"), max_stock=Decimal("400"), daily_consumption=Decimal("9")),
        Product(stable=haras, category=volumoso, supplier=agro, name="Feno de tifton (fardo)",
                code="EQ100", unit="un", cost_price=Decimal("35.00"),
                min_stock=Decimal("10"), daily_consumption=Decimal("2")),
        Product(stable=haras, category=suplementos, supplier=agro, name="Sal mineral",
                code="EQ200", unit="kg", cost_price=Decimal("6.00"),
                min_stock=Decimal("10"), daily_consumption=Decimal("0.4")),
        Product(stable=haras, category=suplementos, supplier=agro, name="Óleo de soja",
                code="EQ201", unit="l", cost_price=Decimal("9.00"),
                min_stock=Decimal("5"), daily_consumption=Decimal("0.5")),
        Product(stable=haras, category=vitaminas, supplier=nutriequi, name="Suplemento vitamínico em pó",
                code="EQ300", unit="kg", cost_price=Decimal("48.00"),
                min_stock=Decimal("2"), daily_consumption=Decimal("0.2")),
    ]
    db.session.add_all([haras, admin, tratador, racao, volumoso, suplementos, vitaminas,
                        nutriequi, agro, *produtos])
    db.session.flush()

    # Trilha de auditoria do cadastro: o primeiro admin nasce do seed
    # (sem autor); o resto foi cadastrado por ele
    audit.record(None, "create", "user", admin.id, after=audit.snapshot(admin),
                 stable_id=haras.id)
    audit.registrar_criacao(admin, "user", tratador)
    for categoria in (racao, volumoso, suplementos, vitaminas):
        audit.registrar_criacao(admin, "category", categoria)
    for fornecedor in (nutriequi, agro):
        audit.registrar_criacao(admin, "supplier", fornecedor)
    for produto in produtos:
        audit.registrar_criacao(admin, "product", produto)

    peletizada, extrusada, potros, feno, sal, oleo, vitamina = produtos

    def entrada(produto, quantidade, dias_atras, lote=None, validade=None, obs=None, hora=8):
        registrar_movimentacao(admin, produto, "entrada", quantidade, "compra",
                               batch=lote, expiration_date=validade, note=obs,
                               created_at=_quando(dias_atras, hora))

    def saida(produto, quantidade, motivo, dias_atras, obs=None, hora=17, usuario=None):
        registrar_movimentacao(usuario or tratador, produto, "saida", quantidade, motivo,
                               note=obs, created_at=_quando(dias_atras, hora))

    # ---------------------------------------------------------------- compras
    entrada(peletizada, 500, 7, lote="L2611A", validade=date(2027, 3, 1),
            obs="20 sacos de 25 kg")
    entrada(extrusada, 120, 7, lote="L2611B", validade=date(2027, 2, 15))
    entrada(feno, 40, 6)
    entrada(sal, 25, 6, lote="S1029", validade=date(2027, 10, 1))
    entrada(oleo, 20, 5)
    entrada(vitamina, 5, 5, lote="V0915", validade=date(2027, 1, 30))
    entrada(potros, 300, 4, lote="L2612C", validade=date(2027, 4, 20),
            obs="12 sacos de 25 kg")
    entrada(peletizada, 100, 2, lote="L2612A", validade=date(2027, 5, 10))

    # ------------------------------------------------- trato dos últimos dias
    for dias_atras in range(DIAS_DE_HISTORICO - 1, -1, -1):
        saida(peletizada, 70, "abastecimento_alimentador", dias_atras, hora=6)
        saida(extrusada, 5, "trato_manual", dias_atras, hora=7)
        saida(feno, 4, "trato_manual", dias_atras, hora=16)

    # Saídas pontuais que deixam cada insumo em um nível diferente:
    # vitamínico zera (ruptura), peletizada e feno ficam sob o mínimo (critico),
    # potros fica com ~4,4 dias de cobertura (atencao) e o resto segue em ok.
    saida(peletizada, 30, "trato_manual", 1, "Baias de recuperação")
    saida(potros, 200, "abastecimento_alimentador", 3)
    saida(potros, 60, "trato_manual", 1)
    saida(oleo, 10, "trato_manual", 4)
    saida(oleo, 2, "avaria", 3, "Galão furado")
    saida(sal, 12, "trato_manual", 2)
    saida(vitamina, 5, "trato_manual", 2, "Fim do lote V0915")   # zera: ruptura
    #   ^ o serviço de estoque abre sozinho o incidente de ruptura (crítico)
    saida(feno, 4, "trato_manual", 0, hora=18)                   # abaixo do mínimo: critico

    # ------------------------------ inventário com divergência (gestão de ativos)
    # Contagem física achou 1 kg de sal a menos: o serviço lança a saída de
    # ajuste e abre o incidente de divergência na mesma transação.
    inventory.registrar_contagem(admin, sal, sal.current_stock - Decimal("1"),
                                 note="Contagem semanal do depósito")

    # ------------------------------------------ incidente manual em análise
    umidade, _ = incidents.abrir_incidente(
        haras.id,
        "avaria",
        "Sacos de ração extrusada com sinais de umidade no depósito 2.",
        severity="media",
        product=extrusada,
        opened_by=tratador,
    )
    incidents.atualizar_incidente(umidade, admin, status=incidents.EM_ANALISE,
                                  assigned_to=admin, atribuir=True)

    db.session.commit()

    por_nivel = {}
    for produto in produtos:
        por_nivel.setdefault(nivel(produto), []).append(produto.name)

    click.echo("Banco populado!")
    click.echo("  admin@haras.com    / admin123  (admin)")
    click.echo("  tratador@haras.com / trat123   (tratador)")

    for situacao in ("ruptura", "critico", "atencao", "ok"):
        nomes = por_nivel.get(situacao, [])
        click.echo(f"  {situacao:<9} ({len(nomes)}): {', '.join(nomes) or '-'}")

    click.echo(f"  incidentes ativos: {incidents.contar_ativos(haras.id)}")
