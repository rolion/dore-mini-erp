from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from modules.crm.application.services import BoardService
from modules.crm.domain.board import BoardConflict, BoardNotFound, BoardValidationError
from modules.crm.infrastructure.adapters import system_clock
from modules.crm.infrastructure.django.repositories import DjangoBoardRepository, DjangoStageCards
from shared.tenancy import company_id_from

from .board_serializers import NameInputSerializer, StageArchiveInputSerializer, StageOrderInputSerializer, board_data


def stage_cards(company_id):
    """Puerto de tarjetas de la empresa: sus oportunidades abiertas (PB-CRM-004)."""
    return DjangoStageCards(company_id, system_clock)


def _service(request) -> BoardService:
    company_id = company_id_from(request)
    return BoardService(DjangoBoardRepository(company_id), stage_cards(company_id))


def _run(request, callback, *, status=200):
    """Ejecuta un caso de uso en una transacción y traduce los errores de dominio a HTTP."""
    service = _service(request)
    try:
        with transaction.atomic():
            board = callback(service)
        return Response(board_data(board, service.cards), status=status)
    except BoardNotFound as exc:
        raise NotFound(str(exc) or 'No encontrado.') from exc
    except BoardValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except BoardConflict as exc:
        # Respuesta directa: DRF convertiría los números de una excepción en texto (`card_count`).
        return Response({'detail': exc.message, 'code': exc.code, **exc.extra}, status=409)


def _body(serializer_class, request) -> dict:
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class BoardListCreateView(APIView):
    required_modules = ('customers',)

    def get(self, request):
        active = request.query_params.get('active', '')
        if active not in ('', 'true', 'false'):
            raise ValidationError({'active': ['Usa true o false.']})
        service = _service(request)
        boards = service.list(active=None if not active else active == 'true')
        return Response([board_data(board, service.cards) for board in boards])

    def post(self, request):
        values = _body(NameInputSerializer, request)
        return _run(request, lambda s: s.create(values['name']), status=201)


class BoardDetailView(APIView):
    required_modules = ('customers',)

    def get(self, request, board_id):
        return _run(request, lambda s: s.get(board_id))

    def patch(self, request, board_id):
        values = _body(NameInputSerializer, request)
        return _run(request, lambda s: s.rename(board_id, values['name']))


class BoardArchiveView(APIView):
    required_modules = ('customers',)

    def post(self, request, board_id):
        return _run(request, lambda s: s.archive(board_id))


class BoardReactivateView(APIView):
    required_modules = ('customers',)

    def post(self, request, board_id):
        return _run(request, lambda s: s.reactivate(board_id))


class StageCreateView(APIView):
    required_modules = ('customers',)

    def post(self, request, board_id):
        values = _body(NameInputSerializer, request)
        return _run(request, lambda s: s.add_stage(board_id, values['name']), status=201)


class StageDetailView(APIView):
    required_modules = ('customers',)

    def patch(self, request, board_id, stage_id):
        values = _body(NameInputSerializer, request)
        return _run(request, lambda s: s.rename_stage(board_id, stage_id, values['name']))


class StageOrderView(APIView):
    required_modules = ('customers',)

    def put(self, request, board_id):
        values = _body(StageOrderInputSerializer, request)
        return _run(request, lambda s: s.reorder(board_id, values['stage_ids']))


class StageArchiveView(APIView):
    required_modules = ('customers',)

    def post(self, request, board_id, stage_id):
        values = _body(StageArchiveInputSerializer, request)
        return _run(request, lambda s: s.archive_stage(board_id, stage_id, values.get('target_stage_id')))
