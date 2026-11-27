"""Adaptador de la WhatsApp Cloud API de Meta (Graph API) con la biblioteca estándar.

El token solo vive en memoria durante la llamada; ningún mensaje de error ni log lo incluye.
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from ..application.ports import SendResult
from ..domain.errors import PermanentGatewayError, TransientGatewayError

logger = logging.getLogger(__name__)
TOKEN_EXPIRED_CODE = 190
TIMEOUT_SECONDS = 10


class WhatsAppCloudAdapter:
    def __init__(self, token: str, phone_number_id: str, waba_id: str, *, base_url: str, api_version: str,
                 opener=urllib.request.urlopen):
        self._token, self.phone_number_id, self.waba_id = token, phone_number_id, waba_id
        self._base, self._opener = f'{base_url.rstrip("/")}/{api_version}', opener

    def _call(self, method: str, path: str, payload: dict | None = None, query: dict | None = None) -> dict:
        url = f'{self._base}/{path}' + (f'?{urllib.parse.urlencode(query)}' if query else '')
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(url, data=data, method=method, headers={
            'Authorization': f'Bearer {self._token}', 'Content-Type': 'application/json'})
        try:
            with self._opener(request, timeout=TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode() or '{}')
        except urllib.error.HTTPError as exc:
            self._raise_for(exc.code, exc.read())
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TransientGatewayError(f'network:{type(exc).__name__}') from None
        except ValueError:
            raise TransientGatewayError('invalid_response') from None
        return {}

    @staticmethod
    def _raise_for(status: int, raw: bytes):
        try:
            error = (json.loads(raw.decode() or '{}') or {}).get('error') or {}
        except ValueError:
            error = {}
        code = error.get('code')
        reason = f'{status} {code or ""} {error.get("message", "")}'.strip()[:200]
        if status == 429 or status >= 500:
            raise TransientGatewayError(reason)
        raise PermanentGatewayError(reason, provider_code=code, token_expired=code == TOKEN_EXPIRED_CODE
                                    or status == 401)

    def _send(self, body: dict) -> SendResult:
        data = self._call('POST', f'{self.phone_number_id}/messages', {'messaging_product': 'whatsapp', **body})
        try:
            return SendResult(data['messages'][0]['id'])
        except (KeyError, IndexError, TypeError):
            raise TransientGatewayError('missing_message_id') from None

    def send_text(self, to, body):
        return self._send({'to': to, 'type': 'text', 'text': {'body': body}})

    def send_interactive(self, to, interactive):
        return self._send({'to': to, 'type': 'interactive', 'interactive': interactive})

    def send_template(self, to, name, language, components):
        template = {'name': name, 'language': {'code': language}}
        if components:
            template['components'] = components
        return self._send({'to': to, 'type': 'template', 'template': template})

    def list_templates(self) -> list[dict]:
        rows, after = [], None
        for _ in range(10):  # tope de páginas
            query = {'limit': 100, 'fields': 'name,language,category,status,components'}
            if after:
                query['after'] = after
            data = self._call('GET', f'{self.waba_id}/message_templates', query=query)
            rows += [{'name': t.get('name', ''), 'language': t.get('language', ''), 'category': t.get('category', ''),
                      'status': t.get('status', ''), 'components': t.get('components') or []}
                     for t in data.get('data', []) if t.get('name') and t.get('language')]
            paging = data.get('paging') or {}
            after = (paging.get('cursors') or {}).get('after') if paging.get('next') else None
            if not after:
                break
        return rows
