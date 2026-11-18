"""Regra da quebra de estoque: níveis, cobertura e previsão (services/alerts)."""
from datetime import timedelta
from decimal import Decimal

from app.services import alerts


def test_ruptura_quando_o_saldo_zera(app, insumo):
    produto = insumo("Sem saldo", saldo="0", minimo="10", consumo="2")

    assert alerts.nivel(produto) == alerts.RUPTURA


def test_ruptura_vale_mesmo_sem_colchao(app, insumo):
    produto = insumo("Sem saldo nem mínimo", saldo="0", minimo="0", consumo="2")

    assert alerts.nivel(produto) == alerts.RUPTURA


def test_critico_no_limite_exato_do_minimo(app, insumo):
    produto = insumo("No mínimo", saldo="10", minimo="10", consumo="1")

    assert alerts.nivel(produto) == alerts.CRITICO


def test_critico_abaixo_do_minimo(app, insumo):
    produto = insumo("Abaixo", saldo="9", minimo="10", consumo="1")

    assert alerts.nivel(produto) == alerts.CRITICO


def test_atencao_no_limite_de_cinco_dias(app, insumo):
    # 10 / 2 = exatamente 5 dias de cobertura
    produto = insumo("Cinco dias", saldo="10", minimo="0", consumo="2")

    assert alerts.cobertura_dias(produto) == Decimal("5")
    assert alerts.nivel(produto) == alerts.ATENCAO


def test_ok_com_mais_de_cinco_dias(app, insumo):
    # 12 / 2 = 6 dias
    produto = insumo("Seis dias", saldo="12", minimo="0", consumo="2")

    assert alerts.nivel(produto) == alerts.OK


def test_critico_vence_atencao(app, insumo):
    # 4 dias de cobertura e saldo abaixo do mínimo: vale o mais grave
    produto = insumo("Pior caso", saldo="8", minimo="10", consumo="2")

    assert alerts.nivel(produto) == alerts.CRITICO


def test_consumo_nulo_nao_gera_cobertura(app, insumo):
    produto = insumo("Sem consumo", saldo="20", minimo="5", consumo=None)

    assert alerts.cobertura_dias(produto) is None
    assert alerts.nivel(produto) == alerts.OK
    assert alerts.data_prevista_ruptura(produto) is None
    assert alerts.min_stock_sugerido(produto) is None


def test_consumo_zero_nao_gera_cobertura(app, insumo):
    produto = insumo("Consumo zero", saldo="20", minimo="5", consumo="0")

    assert alerts.cobertura_dias(produto) is None
    assert alerts.nivel(produto) == alerts.OK


def test_data_prevista_de_ruptura(app, insumo):
    produto = insumo("Cinco dias", saldo="10", minimo="0", consumo="2")

    assert alerts.data_prevista_ruptura(produto) == alerts.hoje() + timedelta(days=5)


def test_data_prevista_arredonda_para_baixo(app, insumo):
    # 11 / 2 = 5,5 dias => zera no quinto dia completo
    produto = insumo("Cinco dias e meio", saldo="11", minimo="0", consumo="2")

    assert alerts.data_prevista_ruptura(produto) == alerts.hoje() + timedelta(days=5)


def test_data_prevista_na_ruptura_e_hoje(app, insumo):
    produto = insumo("Zerado", saldo="0", minimo="0", consumo="2")

    assert alerts.data_prevista_ruptura(produto) == alerts.hoje()


def test_min_stock_sugerido_e_o_colchao_de_cinco_dias(app, insumo):
    produto = insumo("Com consumo", saldo="100", minimo="0", consumo="24")

    assert alerts.min_stock_sugerido(produto) == Decimal("120")


def test_resumo_mantem_days_left_e_is_low_stock(app, insumo):
    produto = insumo("No mínimo", saldo="10", minimo="10", consumo="2")
    situacao = alerts.resumo(produto)

    assert situacao["nivel"] == alerts.CRITICO
    assert situacao["days_left"] == situacao["cobertura_dias"] == Decimal("5")
    assert situacao["is_low_stock"] is True
    assert situacao["is_low_stock"] == produto.is_low_stock


def test_config_muda_a_antecedencia(app, insumo):
    produto = insumo("Dez dias", saldo="20", minimo="0", consumo="2")
    assert alerts.nivel(produto) == alerts.OK

    app.config["ALERTA_DIAS_ANTECEDENCIA"] = 15

    assert alerts.dias_antecedencia() == 15
    assert alerts.nivel(produto) == alerts.ATENCAO
    assert alerts.min_stock_sugerido(produto) == Decimal("30")


def test_ordenacao_por_gravidade_e_cobertura(app, insumo):
    ok = insumo("D ok", saldo="100", minimo="1", consumo="1")
    atencao_4 = insumo("C atenção 4", saldo="4", minimo="0", consumo="1")
    atencao_2 = insumo("B atenção 2", saldo="2", minimo="0", consumo="1")
    critico = insumo("A crítico", saldo="5", minimo="10", consumo="1")
    ruptura = insumo("E ruptura", saldo="0", minimo="1", consumo="1")

    ordenados = alerts.ordenar_por_gravidade([ok, atencao_4, atencao_2, critico, ruptura])

    assert [p.name for p in ordenados] == [
        "E ruptura", "A crítico", "B atenção 2", "C atenção 4", "D ok",
    ]


def test_listar_em_alerta_ignora_ok_e_inativos(app, haras, insumo):
    insumo("Tranquilo", saldo="100", minimo="1", consumo="1")
    insumo("Inativo zerado", saldo="0", minimo="5", consumo="1", active=False)
    insumo("Zerado", saldo="0", minimo="5", consumo="1")

    # a fixture `haras` já traz "Ração" com saldo 0 (ruptura)
    nomes = [p.name for p in alerts.listar_em_alerta(haras["stable"].id)]

    assert "Inativo zerado" not in nomes
    assert "Tranquilo" not in nomes
    assert set(nomes) == {"Ração", "Zerado"}


def test_contagem_por_nivel(app, haras, insumo):
    insumo("Ok", saldo="100", minimo="1", consumo="1")
    insumo("Atenção", saldo="3", minimo="0", consumo="1")
    insumo("Crítico", saldo="5", minimo="10", consumo="1")

    contagem = alerts.contagem_por_nivel(alerts.produtos_ativos(haras["stable"].id))

    assert contagem == {
        alerts.RUPTURA: 1,  # a "Ração" da fixture
        alerts.CRITICO: 1,
        alerts.ATENCAO: 1,
        alerts.OK: 1,
    }
