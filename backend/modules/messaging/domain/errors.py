"""Errores de dominio de la mensajería (puro: sin Django)."""


class MessagingError(Exception):
    """Base: `code` estable para que el cliente distinga el caso."""
    code = 'messaging_error'


class MessagingValidationError(MessagingError):
    code = 'validation_error'

    def __init__(self, errors: dict[str, list[str]]):
        super().__init__(errors)
        self.errors = errors


class MessagingNotFound(MessagingError):
    code = 'not_found'


class WindowClosed(MessagingError):
    code = 'window_closed'


class NotRetryable(MessagingError):
    code = 'not_retryable'


class TemplateNotApproved(MessagingError):
    code = 'template_not_approved'


class ConnectionNotActive(MessagingError):
    code = 'connection_not_active'


class SecretUnavailable(MessagingError):
    """La variable de entorno nombrada por `secret_ref` no existe o está vacía."""
    code = 'secret_unavailable'


class TransientGatewayError(MessagingError):
    """429/5xx/timeout del proveedor: se reintenta con backoff."""
    code = 'provider_unavailable'


class PermanentGatewayError(MessagingError):
    """Rechazo definitivo del proveedor (4xx): no se reintenta."""
    code = 'provider_rejected'

    def __init__(self, reason: str, *, provider_code: int | None = None, token_expired: bool = False):
        super().__init__(reason)
        self.reason, self.provider_code, self.token_expired = reason, provider_code, token_expired


class InvalidSignature(MessagingError):
    """Firma ausente/inválida o número desconocido: el webhook responde 401 y no persiste nada."""
    code = 'invalid_signature'


class PayloadTooLarge(MessagingError):
    code = 'payload_too_large'
