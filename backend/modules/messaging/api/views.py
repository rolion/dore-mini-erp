import json

from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ..application.services import ConnectionInput, ConnectionService, ReceiveWebhook
from ..domain.rules import secret_ref_prefix
from ..domain.errors import (
    InvalidSignature,
    MessagingError,
    MessagingNotFound,
    MessagingValidationError,
    PayloadTooLarge,
    PermanentGatewayError,
    SecretUnavailable,
    TransientGatewayError,
)
from ..infrastructure.django.repositories import (
    ConnectionDirectory,
    DjangoConnectionRepository,
    DjangoTemplateRepository,
    EventQueue,
)
from ..infrastructure.factory import SystemClock, gateway_for, send_service
from ..infrastructure.secrets import EnvSecretResolver
from shared.tenancy import company_id_from

from .serializers import (
    ConnectionInputSerializer,
    TestMessageInputSerializer,
    connection_data,
    message_data,
    template_data,
)


def _parse_json(body: bytes):
    try:
        return json.loads(body.decode() or 'null')
    except ValueError:
        return None


def _error(exc: Exception) -> Response:
    if isinstance(exc, MessagingValidationError):
        return Response(exc.errors, status=400)
    if isinstance(exc, MessagingNotFound):
        return Response({'detail': 'No encontrado.', 'code': exc.code}, status=404)
    if isinstance(exc, (PermanentGatewayError, TransientGatewayError)):
        return Response({'detail': 'El proveedor rechazó o no respondió la solicitud.', 'code': exc.code}, status=502)
    return Response({'detail': str(exc) or exc.code, 'code': exc.code}, status=409)


def _webhook_url(request) -> str:
    return request.build_absolute_uri(reverse('messaging-whatsapp-webhook'))


class WhatsAppWebhookView(APIView):
    """Público (lo llama Meta): sin sesión ni token; la autenticidad la da la firma HMAC del cuerpo."""
    authentication_classes: list = []
    permission_classes = [AllowAny]
    required_modules = ()

    def get(self, request):
        params = request.query_params
        if params.get('hub.mode') == 'subscribe' and ConnectionDirectory.verify_token_exists(
                params.get('hub.verify_token', '')):
            return HttpResponse(params.get('hub.challenge', ''), content_type='text/plain')
        return Response({'detail': 'Token de verificación inválido.'}, status=403)

    def post(self, request):
        use_case = ReceiveWebhook(ConnectionDirectory, EventQueue, EnvSecretResolver(), _parse_json)
        try:
            use_case.handle(request.body, request.headers.get('X-Hub-Signature-256'))
        except InvalidSignature:
            return Response({'detail': 'Firma inválida.'}, status=401)
        except PayloadTooLarge:
            return Response({'detail': 'Cuerpo demasiado grande.'}, status=413)
        except SecretUnavailable:
            return Response({'detail': 'Integración sin configurar.'}, status=503)  # Meta reintentará
        return Response({})


class ConnectionView(APIView):
    required_modules = ()

    def _service(self, request) -> ConnectionService:
        company_id = company_id_from(request)
        return ConnectionService(company_id, DjangoConnectionRepository(company_id), EnvSecretResolver(),
                                 settings.DEFAULT_PHONE_COUNTRY_CODE)

    def get(self, request):
        return Response(connection_data(self._service(request).get(), _webhook_url(request),
                                        secret_ref_prefix(company_id_from(request))))

    def put(self, request):
        serializer = ConnectionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            connection = self._service(request).save(ConnectionInput(**serializer.validated_data))
        except MessagingError as exc:
            return _error(exc)
        return Response(connection_data(connection, _webhook_url(request), secret_ref_prefix(company_id_from(request))))


class TestMessageView(APIView):
    required_modules = ()

    def post(self, request):
        serializer = TestMessageInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            message = send_service(company_id_from(request)).template(data['to'], data['template_id'])
        except MessagingError as exc:
            return _error(exc)
        return Response(message_data(message), status=202)


class TemplateListView(APIView):
    required_modules = ()

    def get(self, request):
        templates = DjangoTemplateRepository(company_id_from(request)).all()
        return Response({'results': [template_data(t) for t in templates]})


class TemplateSyncView(APIView):
    required_modules = ()

    def post(self, request):
        try:
            templates = send_service(company_id_from(request)).sync_templates(gateway_for, SystemClock().now())
        except (MessagingError, SecretUnavailable) as exc:
            return _error(exc)
        return Response({'results': [template_data(t) for t in templates]})
