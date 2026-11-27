"""Proveedor simulado: sin red. Para desarrollo mientras Meta verifica el negocio y para pruebas."""
from itertools import count

from ..application.ports import SendResult


class FakeMessagingGateway:
    sent: list[tuple] = []
    templates: list[dict] = []
    failures: list[Exception] = []  # se lanzan en orden, uno por envío
    _ids = count(1)

    @classmethod
    def reset(cls) -> None:
        cls.sent, cls.templates, cls.failures = [], [], []

    def _send(self, kind: str, to: str, payload) -> SendResult:
        if self.failures:
            raise self.failures.pop(0)
        self.sent.append((kind, to, payload))
        return SendResult(f'wamid.FAKE{next(self._ids)}')

    def send_text(self, to, body):
        return self._send('text', to, body)

    def send_interactive(self, to, interactive):
        return self._send('interactive', to, interactive)

    def send_template(self, to, name, language, components):
        return self._send('template', to, (name, language, components))

    def list_templates(self):
        return list(self.templates) or [
            {'name': 'hello_world', 'language': 'en_US', 'category': 'UTILITY', 'status': 'APPROVED', 'components': []}]
