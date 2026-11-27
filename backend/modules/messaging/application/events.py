"""Publicación en proceso de eventos de dominio: bandeja y asistente se suscriben (PB-CRM-012/018)."""
import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)
_subscribers: list[Callable] = []


def subscribe(handler: Callable) -> None:
    _subscribers.append(handler)


def unsubscribe(handler: Callable) -> None:
    if handler in _subscribers:
        _subscribers.remove(handler)


def publish(event) -> None:
    """Un suscriptor que falla no impide el resto ni deshace el mensaje ya guardado."""
    for handler in list(_subscribers):
        try:
            handler(event)
        except Exception:
            logger.exception('Falló un suscriptor de %s', type(event).__name__)
