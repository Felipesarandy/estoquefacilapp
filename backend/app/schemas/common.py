"""Helpers de validação compartilhados pelos schemas (campos, tipos, erros 422)."""
from datetime import date
from decimal import Decimal, InvalidOperation

from flask import request

PER_PAGE_PADRAO = 20
PER_PAGE_MAXIMO = 100


class ValidationError(ValueError):
    """Dado inválido enviado pelo cliente.

    `status` é 422 por padrão (corpo bem formado, conteúdo inválido) e
    400 quando o próprio corpo não é um JSON utilizável.
    """

    def __init__(self, message, field=None, status=422):
        super().__init__(message)
        self.message = message
        self.field = field
        self.status = status


def body():
    """Corpo da requisição como dicionário; 400 se não for JSON válido."""
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        raise ValidationError("Envie um objeto JSON válido", status=400)

    return data


def required_string(data, field, max_length=255):
    """Campo de texto obrigatório, sem espaços nas pontas."""
    value = data.get(field)

    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Campo obrigatório: {field}", field=field)

    value = value.strip()

    if len(value) > max_length:
        raise ValidationError(
            f"{field} deve ter no máximo {max_length} caracteres", field=field
        )

    return value


def optional_string(data, field, max_length=255):
    """Campo de texto opcional; devolve None quando ausente ou vazio."""
    value = data.get(field)

    if value is None or value == "":
        return None

    if not isinstance(value, str) or len(value.strip()) > max_length:
        raise ValidationError(f"{field} inválido", field=field)

    return value.strip()


def decimal_field(data, field, default=None, positive=False, scale=3):
    """Valor numérico decimal, com limite de casas e de grandeza da coluna."""
    value = data.get(field, default)

    if value is None or isinstance(value, bool):
        raise ValidationError(f"{field} deve ser numérico", field=field)

    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError(f"{field} deve ser numérico", field=field) from None

    if not number.is_finite():
        raise ValidationError(f"{field} inválido", field=field)

    if positive and number <= 0:
        raise ValidationError(f"{field} deve ser maior que zero", field=field)

    if not positive and number < 0:
        raise ValidationError(f"{field} não pode ser negativo", field=field)

    if number.as_tuple().exponent < -scale:
        raise ValidationError(f"{field} possui casas decimais demais", field=field)

    if number >= Decimal(10) ** (10 - scale):
        raise ValidationError(f"{field} fora do limite permitido", field=field)

    return number


def integer_field(data, field, required=False):
    """Identificador inteiro positivo."""
    value = data.get(field)

    if value is None and not required:
        return None

    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValidationError(f"{field} deve ser um ID inteiro positivo", field=field)

    return value


def boolean_field(data, field):
    """Booleano obrigatório (usado no PATCH de `active`)."""
    value = data.get(field)

    if not isinstance(value, bool):
        raise ValidationError(f"{field} deve ser booleano", field=field)

    return value


def choice_field(value, choices, field):
    """Valida um valor contra a lista de opções aceitas do domínio."""
    if value not in choices:
        raise ValidationError(
            f"{field} deve ser um destes: {', '.join(choices)}", field=field
        )

    return value


def pagination_args():
    """Lê ?page= e ?per_page= da query string (per_page no máximo 100)."""
    page = _inteiro_positivo("page", 1)
    per_page = _inteiro_positivo("per_page", PER_PAGE_PADRAO)

    return page, min(per_page, PER_PAGE_MAXIMO)


def paginated(items, page, per_page, total, serializer):
    """Envelope padrão das listagens da API."""
    return {
        "items": [serializer(item) for item in items],
        "page": page,
        "per_page": per_page,
        "total": total,
    }


def bool_arg(name):
    """Filtro booleano opcional vindo da query string (?active=true)."""
    raw = request.args.get(name)

    if raw is None or raw == "":
        return None

    valor = raw.strip().lower()

    if valor in ("true", "1", "sim"):
        return True

    if valor in ("false", "0", "nao", "não"):
        return False

    raise ValidationError(f"{name} deve ser true ou false", field=name)


def search_arg(name="search"):
    """Texto de busca da query string (?search=feno); None quando ausente."""
    raw = request.args.get(name)

    if raw is None or not raw.strip():
        return None

    return raw.strip()


ESCAPE_LIKE = "!"


def like_pattern(texto):
    """Padrão para ILIKE com os curingas do próprio texto escapados.

    Use junto com `ilike(..., escape=ESCAPE_LIKE)`.
    """
    seguro = (
        texto.replace(ESCAPE_LIKE, ESCAPE_LIKE * 2)
        .replace("%", f"{ESCAPE_LIKE}%")
        .replace("_", f"{ESCAPE_LIKE}_")
    )
    return f"%{seguro}%"


def int_arg(name):
    """Filtro numérico opcional da query string (?category_id=3)."""
    raw = request.args.get(name)

    if raw is None or raw == "":
        return None

    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} deve ser um ID inteiro positivo", field=name) from None

    if value < 1:
        raise ValidationError(f"{name} deve ser um ID inteiro positivo", field=name)

    return value


def texto_dias(valor):
    """Dias de cobertura como texto curto: 10, 5, 3.333 (3 casas, sem zeros à toa)."""
    if valor is None:
        return None

    numero = Decimal(valor).quantize(Decimal("0.001")).normalize()

    if numero == numero.to_integral_value():
        numero = numero.quantize(Decimal(1))

    return str(numero)


def date_field(data, field, required=False):
    """Data no formato ISO (YYYY-MM-DD) vinda do corpo da requisição."""
    valor = data.get(field)

    if valor is None or valor == "":
        if required:
            raise ValidationError(f"Campo obrigatório: {field}", field=field)
        return None

    if not isinstance(valor, str):
        raise ValidationError(f"{field} deve ser uma data YYYY-MM-DD", field=field)

    try:
        return date.fromisoformat(valor.strip())
    except ValueError:
        raise ValidationError(
            f"{field} deve ser uma data YYYY-MM-DD", field=field
        ) from None


def date_arg(name):
    """Data opcional vinda da query string (?from=2026-11-01)."""
    raw = request.args.get(name)

    if raw is None or raw == "":
        return None

    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        raise ValidationError(
            f"{name} deve ser uma data YYYY-MM-DD", field=name
        ) from None


def _inteiro_positivo(name, default):
    raw = request.args.get(name)

    if raw is None or raw == "":
        return default

    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} deve ser um inteiro positivo", field=name) from None

    if value < 1:
        raise ValidationError(f"{name} deve ser um inteiro positivo", field=name)

    return value
