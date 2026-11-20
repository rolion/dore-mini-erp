"""Worker de la importación: toma corridas en cola y las ejecuta con la empresa y el usuario guardados en ellas."""
import logging
import time
from collections.abc import Callable

from django.db import close_old_connections

from modules.data_import.application.use_cases import ExecuteSalesImport
from modules.data_import.infrastructure.adapters import SalesImportAdapter, SystemClock
from modules.data_import.infrastructure.django.repositories import DjangoImportQueue, DjangoImportRepository

logger = logging.getLogger(__name__)

STALE_CHECK_EVERY = 60  # segundos entre revisiones de corridas caídas


def process_next(queue: DjangoImportQueue | None = None) -> bool:
    """Ejecuta la siguiente corrida en cola; devuelve False si no había ninguna."""
    queue = queue or DjangoImportQueue()
    clock = SystemClock()
    queue.fail_stale(clock.now())
    claimed = queue.claim_next(clock.now())
    if claimed is None:
        return False
    try:
        ExecuteSalesImport(DjangoImportRepository(claimed.company_id),
                           SalesImportAdapter(claimed.company_id, claimed.user_id, claimed.user_name),
                           clock).run_claimed(claimed.run_id)
    except Exception:  # run_claimed ya registra los fallos; esto protege el bucle de uno que no pudo registrarse
        logger.exception('La importación %s falló fuera de su caso de uso', claimed.run_id)
    return True


def run_forever(poll_seconds: float = 2.0, should_stop: Callable[[], bool] = lambda: False) -> None:
    queue = DjangoImportQueue()
    last_stale_check = 0.0
    while not should_stop():
        close_old_connections()  # reabre la conexión si la base la cerró mientras el worker esperaba
        if time.monotonic() - last_stale_check >= STALE_CHECK_EVERY:
            queue.fail_stale(SystemClock().now())
            last_stale_check = time.monotonic()
        try:
            worked = process_next(queue)
        except Exception:
            logger.exception('Error al consultar la cola de importaciones')
            worked = False
        if not worked:
            time.sleep(poll_seconds)
