"""Runner de pruebas con reloj estrictamente creciente.

En Windows `datetime.now()` avanza de a ~15,6 ms: varias filas creadas seguidas reciben el mismo
`auto_now_add` y el desempate cae en un UUID aleatorio (orden de ítems, historial, `updated_at >
created_at`). En Linux el reloj tiene resolución de microsegundos y esos empates casi no ocurren.
Aquí `timezone.now()` nunca repite ni retrocede un valor, así las pruebas no dependen de la plataforma.
"""
import threading
from datetime import timedelta

from django.test.runner import DiscoverRunner
from django.utils import timezone

_MICROSECOND = timedelta(microseconds=1)


def strictly_increasing(real_now):
    lock = threading.Lock()
    last = [None]

    def now():
        with lock:
            value = real_now()
            if last[0] is not None and value <= last[0]:
                value = last[0] + _MICROSECOND
            last[0] = value
            return value

    return now


class StrictClockRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._real_now = timezone.now
        timezone.now = strictly_increasing(self._real_now)

    def teardown_test_environment(self, **kwargs):
        timezone.now = self._real_now
        super().teardown_test_environment(**kwargs)
