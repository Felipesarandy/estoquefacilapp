# Trechos de código para o PDF

Trechos copiados automaticamente do código atual (arquivo e linhas conferem com o repositório na data da geração). Cada um traz uma explicação curta para o relatório.

## 1. Application Factory (`create_app`)

**Arquivo:** `backend/app/__init__.py` — linhas 56 a 77

```python
def create_app(config_name=None):
    config_name = config_name or os.getenv("FLASK_CONFIG", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    _configurar_logging(app)
    _exigir_chaves_em_producao(app, config_name)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from app import models  # noqa: F401  (registra os models para o Flask-Migrate)
    from app.api import register_blueprints
    register_blueprints(app)

    from app.seed import seed_command
    app.cli.add_command(seed_command)

    return app
```

A aplicação é montada por uma função fábrica: carrega a configuração do ambiente (development, testing ou production), configura o logging, recusa chaves inseguras em produção e só então liga as extensões (SQLAlchemy, Migrate, JWT, CORS). Os testes usam `create_app("testing")` com banco em memória, sem tocar no banco de desenvolvimento.

## 2. Registro dos blueprints sob `/api`

**Arquivo:** `backend/app/api/__init__.py` — linhas 32 a 57

```python
api = Blueprint("api", __name__, url_prefix="/api")

# Ordem: infraestrutura, acesso, cadastros, operação, consultas
for _module in (
    health,
    auth,
    users,
    categories,
    suppliers,
    products,
    movements,
    inventory,
    incidents,
    alerts,
    dashboard,
    audit,
    meta,
):
    api.register_blueprint(_module.bp)


def register_blueprints(app):
    """Pendura a API na aplicação e liga os handlers."""
    app.register_blueprint(api)
    register_error_handlers(app)
    register_jwt_handlers(jwt)
```

Cada recurso tem seu próprio módulo e Blueprint; aqui eles são agrupados no blueprint `api` com prefixo `/api`. `register_blueprints` também liga os handlers que transformam qualquer erro em JSON no formato padrão e as mensagens de falha de token em português.

## 3. Controle de acesso por papel (`roles_required`)

**Arquivo:** `backend/app/api/security.py` — linhas 11 a 41

```python
def roles_required(*roles):
    """Exige token válido e um dos papéis informados.

    O usuário autenticado entra como primeiro argumento da rota.
    401 se o token não corresponde a um usuário ativo; 403 se o papel não serve.
    """

    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*args, **kwargs):
            try:
                user = db.session.get(User, int(get_jwt_identity()))
            except (TypeError, ValueError):
                user = None

            if user is None or not user.active:
                return api_error(401, "Usuário inativo ou inexistente")

            if roles and user.role not in roles:
                return api_error(403, f"Acesso permitido apenas para: {', '.join(roles)}")

            return fn(user, *args, **kwargs)

        return wrapped

    return decorator


admin_required = roles_required("admin")
login_required = roles_required("admin", "tratador")
```

Um único decorator valida o JWT, carrega o usuário do banco e confere o papel. Token de usuário inexistente ou desativado vira 401; papel insuficiente vira 403. O usuário entra como primeiro argumento da rota, então nenhuma rota consulta o token sozinha.

## 4. Validação no servidor com helpers (`new_movement_payload`)

**Arquivo:** `backend/app/schemas/movements.py` — linhas 65 a 77

```python
def new_movement_payload(data):
    """Dados aceitos no POST /api/movements (nomes iguais aos do model)."""
    tipo = choice_field(data.get("type"), TIPOS, "type")

    return {
        "product_id": integer_field(data, "product_id", required=True),
        "type": tipo,
        "reason": choice_field(data.get("reason"), MOTIVOS_POR_TIPO[tipo], "reason"),
        "quantity": decimal_field(data, "quantity", positive=True, scale=3),
        "batch": optional_string(data, "batch", 50),
        "expiration_date": date_field(data, "expiration_date"),
        "note": optional_string(data, "note", 5000),
    }
```

Os schemas validam o corpo da requisição com helpers reutilizáveis (`choice_field`, `decimal_field`, `integer_field`, `date_field`). O motivo aceito depende do tipo (entrada/saída). Qualquer falha levanta `ValidationError`, convertida em 422 com o campo em `details.field`.

## 5. Baixa atômica de estoque (`registrar_movimentacao`)

**Arquivo:** `backend/app/services/stock.py` — linhas 40 a 119

```python
def registrar_movimentacao(user, product, type, quantity, reason, batch=None,
                           expiration_date=None, note=None, created_at=None):
    """Registra a entrada/saída e atualiza o saldo na mesma transação.

    `created_at` existe só para o seed montar um histórico de demonstração;
    no uso normal o banco carimba a hora.

    Levanta ValidationError (422) para dados inválidos e ConflitoDeEstoque
    (409) para saldo insuficiente ou insumo inativo. Também grava a
    auditoria ("movement") e sincroniza o incidente de ruptura. Não dá
    commit: quem chama decide a hora de fechar a transação.
    """
    tipo = choice_field(type, TIPOS, "type")
    motivo = choice_field(reason, MOTIVOS_POR_TIPO[tipo], "reason")
    quantidade = decimal_field({"quantity": quantity}, "quantity",
                               positive=True, scale=3)

    if not product.active:
        raise ConflitoDeEstoque("Insumo inativo: reative antes de movimentar")

    condicoes = [
        Product.id == product.id,
        Product.stable_id == product.stable_id,
        Product.active.is_(True),
    ]

    if tipo == SAIDA:
        condicoes.append(Product.current_stock >= quantidade)
        novo_saldo = Product.current_stock - quantidade
    else:
        novo_saldo = Product.current_stock + quantidade

    resultado = db.session.execute(
        update(Product).where(*condicoes).values(current_stock=novo_saldo)
    )

    if resultado.rowcount != 1:
        if tipo == SAIDA:
            logger.warning(
                "saida recusada por estoque insuficiente | usuario=%s insumo=%s "
                "quantidade=%s saldo=%s",
                user.id, product.id, quantidade, product.current_stock,
            )
            raise ConflitoDeEstoque("Estoque insuficiente")

        raise ConflitoDeEstoque("Insumo indisponível para movimentação")

    db.session.refresh(product)

    movimentacao = StockMovement(
        product=product,
        user=user,
        type=tipo,
        reason=motivo,
        quantity=quantidade,
        unit_cost=product.cost_price,  # custo no momento da movimentação
        batch=batch,
        expiration_date=expiration_date,
        note=note,
    )

    if created_at is not None:
        movimentacao.created_at = created_at

    db.session.add(movimentacao)
    db.session.flush()

    # Mesma transação: trilha de auditoria e incidente de ruptura (abre ao
    # zerar o saldo, resolve sozinho na reposição)
    audit.record(user, "movement", "movement", movimentacao.id,
                 after=audit.snapshot(movimentacao))
    incidents.sincronizar_ruptura(product, user)

    logger.info(
        "movimentacao registrada | usuario=%s insumo=%s tipo=%s motivo=%s "
        "quantidade=%s saldo=%s",
        user.id, product.id, tipo, motivo, quantidade, product.current_stock,
    )

    return movimentacao
```

O saldo muda por um único `UPDATE ... WHERE current_stock >= :q`: se duas saídas concorrentes disputarem o mesmo saldo, só uma afeta a linha e a outra recebe 409, sem saldo negativo. A movimentação, a auditoria e o incidente de ruptura entram na mesma transação; quem chama decide o commit.

## 6. Regra de nível e cobertura (quebra de estoque)

**Arquivo:** `backend/app/services/alerts.py` — linhas 66 a 88

```python
def cobertura_dias(produto):
    """Dias que o saldo ainda cobre; None quando não há consumo informado.

    É a mesma conta de `Product.days_left` (saldo ÷ consumo diário);
    reaproveitada daqui para não existirem duas fórmulas.
    """
    return produto.days_left


def nivel(produto, cobertura=None):
    """Nível do insumo; vale sempre o mais grave."""
    if produto.current_stock is not None and produto.current_stock <= 0:
        return RUPTURA

    if produto.is_low_stock:
        return CRITICO

    cobertura = cobertura_dias(produto) if cobertura is None else cobertura

    if cobertura is not None and cobertura <= dias_antecedencia():
        return ATENCAO

    return OK
```

Única fonte da regra de alertas: cobertura = saldo ÷ consumo diário e o nível mais grave vence (ruptura, crítico = abaixo do colchão mínimo, atenção = cobertura de até `ALERTA_DIAS_ANTECEDENCIA` dias). Produtos, alertas e dashboard usam estas funções, em Python e sem consultas extras por item.

## 7. Auditoria: `snapshot` e `record`

**Arquivo:** `backend/app/services/audit.py` — linhas 31 a 74

```python
def snapshot(model):
    """Fotografia das colunas do model em JSON, sem senha nem hash."""
    if model is None:
        return None

    colunas = inspect(model).mapper.column_attrs

    return {
        coluna.key: _para_json(getattr(model, coluna.key))
        for coluna in colunas
        if coluna.key not in CAMPOS_SENSIVEIS
    }


def _ip_da_requisicao():
    if not has_request_context():
        return None

    return request.remote_addr


def record(user, action, entity, entity_id=None, before=None, after=None,
           stable_id=None):
    """Adiciona um AuditLog à sessão (sem commit).

    `stable_id` vem do usuário quando não informado; fica nulo apenas
    quando não há haras conhecido (ex.: login com e-mail inexistente).
    """
    if stable_id is None and user is not None:
        stable_id = user.stable_id

    log = AuditLog(
        stable_id=stable_id,
        user_id=user.id if user is not None else None,
        action=action,
        entity=entity,
        entity_id=entity_id,
        before_json=before,
        after_json=after,
        ip=_ip_da_requisicao(),
    )
    db.session.add(log)

    return log
```

`snapshot` fotografa as colunas do registro em JSON e descarta senha e hash; `record` só adiciona o `AuditLog` à sessão, então a ação e sua trilha são gravadas (ou desfeitas) juntas. O IP vem da requisição quando houver.

## 8. Imutabilidade da trilha de auditoria

**Arquivo:** `backend/app/models/audit_log.py` — linhas 37 a 50

```python
def _bloquear_alteracao(mapper, connection, target):
    raise RuntimeError(
        f"{type(target).__name__} é imutável: registros não podem ser alterados nem removidos"
    )


def tornar_imutavel(model):
    """Impede UPDATE e DELETE pelo ORM (o histórico só cresce)."""
    event.listen(model, "before_update", _bloquear_alteracao)
    event.listen(model, "before_delete", _bloquear_alteracao)
    return model


tornar_imutavel(AuditLog)
```

Listeners do SQLAlchemy (`before_update` e `before_delete`) impedem que um registro de auditoria seja alterado ou removido pelo ORM. A mesma proteção vale para as contagens de inventário; e a API não expõe nenhuma rota de escrita para a trilha (405).

## 9. Ciclo de vida do incidente

**Arquivo:** `backend/app/services/incidents.py` — linhas 140 a 174

```python
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
```

As transições permitidas ficam na tabela `TRANSICOES`; qualquer outra vira 409. Resolver exige a descrição da resolução (422 sem ela) e `closed_at` marca o fim do atendimento, sendo limpo se o incidente for reaberto. Toda transição é logada.

## 10. Teste automatizado: concorrência de saídas

**Arquivo:** `backend/tests/api/test_movements.py` — linhas 100 a 111

```python
def test_duas_saidas_a_segunda_e_409(client, produto, admin_headers):
    client.post(MOVEMENTS, json=_entrada(produto.id, "10"), headers=admin_headers)

    primeira = client.post(MOVEMENTS, json=_saida(produto.id, "6"), headers=admin_headers)
    segunda = client.post(MOVEMENTS, json=_saida(produto.id, "6"), headers=admin_headers)

    assert primeira.status_code == 201
    assert segunda.status_code == 409
    assert primeira.get_json()["current_stock"] == "4.000"

    detalhe = client.get(f"/api/products/{produto.id}", headers=admin_headers).get_json()
    assert detalhe["current_stock"] == "4.000"
```

Teste de API com o cliente do Flask: duas saídas de 6 sobre um saldo de 10. A primeira passa (201) e a segunda recebe 409, e o saldo continua consistente em 4. É um dos 302 testes executados com `pytest`.
