"""Reglas puras: ventana de 24 h, normalización de teléfono, firma del webhook, backoff, referencias de secretos."""
import hashlib
import hmac
import re
from datetime import datetime, timedelta

from .errors import MessagingValidationError

WINDOW = timedelta(hours=24)
MAX_ATTEMPTS = 5
BACKOFF_BASE = timedelta(minutes=1)
SECRET_REF_PATTERN = re.compile(r'^WHATSAPP_[A-Z0-9_]{1,56}$')


def window_open(last_inbound_at: datetime | None, now: datetime) -> bool:
    """Abierta ⇔ hubo mensaje entrante y pasaron como máximo 24 h (límite exacto inclusivo)."""
    return last_inbound_at is not None and now - last_inbound_at <= WINDOW


def normalize_phone(raw: str, default_country_code: str) -> str:
    """Solo dígitos con código de país. «+…» y «00…» ya traen país; los locales (≤ 9 dígitos) usan el por defecto."""
    text = (raw or '').strip()
    digits = re.sub(r'\D', '', text)
    if not digits:
        raise MessagingValidationError({'to': ['Teléfono inválido.']})
    if text.startswith('+'):
        result = digits
    elif digits.startswith('00'):
        result = digits[2:]
    elif len(digits) <= 9:
        result = default_country_code + digits.lstrip('0')
    else:
        result = digits
    if not 8 <= len(result) <= 15:
        raise MessagingValidationError({'to': ['Teléfono inválido.']})
    return result


def valid_signature(body: bytes, header: str | None, app_secret: str) -> bool:
    """`X-Hub-Signature-256` = «sha256=» + HMAC-SHA256 del cuerpo crudo; comparación en tiempo constante."""
    if not header or not header.startswith('sha256=') or not app_secret:
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[len('sha256='):])


def backoff_delay(attempt: int) -> timedelta:
    """1, 2, 4, 8… minutos para el intento fallido número `attempt` (1-based)."""
    return BACKOFF_BASE * (2 ** (attempt - 1))


def secret_ref_prefix(company_id) -> str:
    """Prefijo propio de cada empresa para sus variables (`WHATSAPP_<12 hex del id>_`): no se adivina y evita que
    una empresa apunte al token de otra o a `SECRET_KEY`/`DATABASE_URL` (REV-01)."""
    return f'WHATSAPP_{company_id.hex[:12].upper()}_'


def clean_secret_ref(value: str, field: str, prefix: str) -> str:
    text = (value or '').strip()
    valid = (SECRET_REF_PATTERN.match(text) and text.startswith(prefix) and len(text) > len(prefix)
             and len(text) <= 64)
    if not valid:
        message = f'Usa un nombre de variable que empiece con {prefix} (mayúsculas, números y _).'
        raise MessagingValidationError({field: [message]})
    return text
