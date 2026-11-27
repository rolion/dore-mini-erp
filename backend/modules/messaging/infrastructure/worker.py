"""Worker: procesa los eventos de webhook verificados y entrega los mensajes salientes en cola."""
import logging
import time
from collections.abc import Callable

from django.db import close_old_connections

from .django.repositories import ConnectionDirectory, EventQueue, OutboxQueue
from .factory import SystemClock, event_processor, gateway_for, send_service

logger = logging.getLogger(__name__)


def process_next_event() -> bool:
    """`process_webhook_event`: aplica el siguiente evento en cola; False si no había."""
    now = SystemClock().now()
    claimed = EventQueue.claim_next(now)
    if claimed is None:
        return False
    event_id, connection_id, payload = claimed
    try:
        connection = ConnectionDirectory.by_id(connection_id)
        if connection is None:
            raise LookupError('connection_missing')
        event_processor(connection).run(payload)
        EventQueue.finish(event_id, SystemClock().now())
    except Exception as exc:
        logger.exception('Falló el evento de webhook %s', event_id)
        EventQueue.finish(event_id, SystemClock().now(), error=type(exc).__name__)
    return True


def deliver_next_message() -> bool:
    claimed = OutboxQueue.claim_next(SystemClock().now())
    if claimed is None:
        return False
    company_id, message_id = claimed
    try:
        send_service(company_id).deliver(message_id, gateway_for)
    except Exception:
        logger.exception('Falló la entrega del mensaje %s', message_id)
    return True


def process_all() -> int:
    done = 0
    while process_next_event() or deliver_next_message():
        done += 1
    return done


def run_forever(poll_seconds: float = 2.0, should_stop: Callable[[], bool] = lambda: False) -> None:
    while not should_stop():
        close_old_connections()
        try:
            worked = process_next_event() or deliver_next_message()
        except Exception:
            logger.exception('Error en el worker de mensajería')
            worked = False
        if not worked:
            time.sleep(poll_seconds)
