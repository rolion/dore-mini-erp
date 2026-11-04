
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers
from rest_framework import status as http
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from config.permissions import CompanyClinicalPermission
from modules.dentistry.application.proformas import (
    DecisionInput, DentalProformaInput, DentalProformaService, LineInput, PriceEditNotAllowed, RectifyNotAllowed,
)
from modules.dentistry.domain.patient import PatientArchived, PatientNotFound
from modules.dentistry.domain.proforma import (
    ACCEPTED, CURRENCY, MAX_NAME, MAX_REASON, MAX_REFERENCE, STATUSES, DentalProformaNotFound,
    DentalProformaStateError, DentalProformaValidationError, money,
)
from modules.dentistry.infrastructure.adapters import CustomersAdapter, PatientGate, ServiceLookup
from modules.dentistry.infrastructure.proforma_repository import DjangoDentalProformaRepository, to_domain
from modules.dentistry.infrastructure.repository import DjangoPatientRepository
from rest_framework.views import APIView
from shared.tenancy import company_id_from

REQUIRED_MODULES = ('dentistry', 'customers', 'services')


class Conflict(APIException):
    status_code = http.HTTP_409_CONFLICT
    default_detail = 'La operación no es válida para el estado actual.'
    default_code = 'conflict'


def can_edit_price(user) -> bool:
    """Política de precios: hoy solo el administrador fija un precio distinto del catálogo.

    El módulo no importa `accounts`; lee el rol por nombre. Un rol futuro sin permiso recibe 403 sin cambiar la API.
    """
    return getattr(user, 'role', None) == 'admin'


class ProformaPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        for field in ('page', 'page_size'):
            raw = request.query_params.get(field)
            if raw is not None and (len(raw) > 10 or not raw.isascii() or not raw.isdigit() or int(raw) < 1):
                raise ValidationError({field: ['Ingresa un entero mayor que cero.']})
        try:
            return super().paginate_queryset(queryset, request, view=view)
        except NotFound as exc:
            raise ValidationError({'page': ['La página solicitada ya no está disponible.']}) from exc


class LineInputSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    service_id = serializers.UUIDField(required=False)
    quantity = serializers.DecimalField(max_digits=8, decimal_places=2)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    dental_piece = serializers.CharField(required=False, allow_blank=True, allow_null=True, trim_whitespace=False)
    # `description`, `subtotal` y `total` enviados por el navegador se ignoran: el servidor los calcula.


class ProformaInputSerializer(serializers.Serializer):
    date = serializers.DateField()
    valid_until = serializers.DateField(required=False, allow_null=True, default=None)
    notes = serializers.CharField(required=False, allow_blank=True, default='', max_length=2000)
    lines = LineInputSerializer(many=True, max_length=500)
    # El paciente sale de la URL: cualquier `customer_id` del cuerpo se ignora.

    def to_input(self) -> DentalProformaInput:
        data = self.validated_data
        lines = [LineInput(quantity=l['quantity'], id=l.get('id'), service_id=l.get('service_id'),
                           unit_price=l.get('unit_price'), dental_piece=l.get('dental_piece'))
                 for l in data['lines']]
        return DentalProformaInput(data['date'], data['valid_until'], data['notes'], lines)


class DecisionInputSerializer(serializers.Serializer):
    """Forma y tipos; las reglas de negocio las valida el agregado."""
    idempotency_key = serializers.UUIDField()
    decision = serializers.CharField(max_length=10)
    line_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list, max_length=200)
    accepted_by_name = serializers.CharField(required=False, allow_blank=True, default='', max_length=MAX_NAME)
    medium = serializers.CharField(required=False, allow_blank=True, default='', max_length=20)
    reference = serializers.CharField(required=False, allow_blank=True, default='', max_length=MAX_REFERENCE)
    reason = serializers.CharField(required=False, allow_blank=True, default='', max_length=MAX_REASON)

    def to_input(self, line_ids=None) -> DecisionInput:
        data = self.validated_data
        return DecisionInput(data['idempotency_key'], data['decision'],
                             list(line_ids) if line_ids is not None else data['line_ids'],
                             data['accepted_by_name'], data['medium'], data['reference'], data['reason'])


def decision_data(record) -> dict:
    return {'id': str(record.id), 'kind': record.kind, 'decision': record.decision,
            'decided_at': record.decided_at.isoformat(), 'recorded_by_name': record.recorded_by_name,
            'accepted_by_name': record.accepted_by_name, 'medium': record.medium, 'reference': record.reference,
            'reason': record.reason}


def line_data(line, *, proforma_status='presented') -> dict:
    current = line.current_decision
    return {'id': str(line.id), 'service_id': str(line.service_id), 'description': line.description,
            'quantity': f'{line.quantity:.2f}', 'unit_price': f'{line.unit_price:.2f}',
            'subtotal': f'{line.subtotal:.2f}', 'dental_piece': line.dental_piece,
            'line_kind': line.line_kind, 'origin_line_id': str(line.origin_line_id) if line.origin_line_id else None,
            'decision': line.decision, 'decided_at': current.decided_at.isoformat() if current else None,
            'decision_detail': decision_data(current) if current else None,
            'authorized': line.decision == ACCEPTED and proforma_status == 'presented'}


def summary_data(proforma) -> dict:
    return {'id': str(proforma.id), 'number': proforma.number, 'version': proforma.version,
            'status': proforma.status, 'customer_id': str(proforma.customer_id),
            'patient_name': proforma.patient_name, 'date': proforma.date.isoformat(),
            'valid_until': proforma.valid_until.isoformat() if proforma.valid_until else None,
            'currency': CURRENCY, 'total': f'{proforma.total:.2f}',
            'accepted_total': f"{proforma.totals['accepted']:.2f}", 'acceptance_status': proforma.acceptance_status}


def detail_data(proforma, *, allowed_actions, can_edit, versions, decision_actions=()) -> dict:
    previous = next((v for v in versions if v.version == proforma.version - 1), None)
    history = [{**decision_data(record), 'line_id': str(line.id), 'line_description': line.description}
               for line, record in proforma.decision_history()]
    return {**summary_data(proforma), 'notes': proforma.notes,
            'lines': [line_data(l, proforma_status=proforma.status) for l in proforma.lines],
            'allowed_actions': allowed_actions, 'can_edit_price': can_edit,
            'versions': [summary_data(v) for v in versions],
            'decision_actions': list(decision_actions),
            'totals': {key: f'{value:.2f}' for key, value in proforma.totals.items()},
            'decision_history': history, 'previous_version_id': str(previous.id) if previous else None}


def printable_data(proforma) -> dict:
    """Solo datos comerciales: sin referencia/evidencia, motivos, usuarios, ids internos ni historial."""
    return {'number': proforma.number, 'version': proforma.version, 'status': proforma.status,
            'patient_name': proforma.patient_name, 'date': proforma.date.isoformat(),
            'valid_until': proforma.valid_until.isoformat() if proforma.valid_until else None,
            'currency': CURRENCY, 'notes': proforma.notes, 'acceptance_status': proforma.acceptance_status,
            'totals': {k: f'{v:.2f}' for k, v in proforma.totals.items() if k != 'rejected'},
            'lines': [{'description': l.description, 'dental_piece': l.dental_piece,
                       'quantity': f'{l.quantity:.2f}', 'unit_price': f'{l.unit_price:.2f}',
                       'subtotal': f'{l.subtotal:.2f}', 'decision': l.decision,
                       'decided_at': l.current_decision.decided_at.date().isoformat() if l.current_decision else None}
                      for l in proforma.lines]}


def can_rectify(user) -> bool:
    """Política de rectificaciones: hoy solo el administrador; un rol futuro sin permiso recibe 403."""
    return getattr(user, 'role', None) == 'admin'


def _user_name(user) -> str:
    full = user.get_full_name() if hasattr(user, 'get_full_name') else ''
    return (full or user.get_username())[:150]


def _service(request) -> DentalProformaService:
    company_id = company_id_from(request)
    patients = PatientGate(DjangoPatientRepository(company_id), CustomersAdapter(company_id))
    return DentalProformaService(DjangoDentalProformaRepository(company_id), ServiceLookup(company_id), patients,
                                 can_edit_price=can_edit_price(request.user), user_id=request.user.pk,
                                 can_rectify=can_rectify(request.user), user_name=_user_name(request.user))


def _detail(service: DentalProformaService, proforma) -> dict:
    return detail_data(proforma, allowed_actions=service.allowed_actions(proforma),
                       can_edit=service.can_edit_price, versions=service.versions(proforma),
                       decision_actions=service.decision_actions(proforma))


def _run(callback):
    try:
        with transaction.atomic():
            return callback()
    except (DentalProformaNotFound, PatientNotFound) as exc:
        raise NotFound(str(exc) or 'Proforma no encontrada.') from exc
    except DentalProformaValidationError as exc:
        raise ValidationError(exc.errors) from exc
    except (DentalProformaStateError, PatientArchived) as exc:
        raise Conflict(str(exc)) from exc
    except PriceEditNotAllowed as exc:
        raise PermissionDenied('No tienes permiso para editar precios.') from exc
    except RectifyNotAllowed as exc:
        raise PermissionDenied('No tienes permiso para rectificar decisiones.') from exc


class ProformaView(APIView):
    required_modules = REQUIRED_MODULES
    permission_classes = [CompanyClinicalPermission]


class PatientProformaListCreateView(ProformaView):
    def get(self, request, customer_id):
        status = request.query_params.get('status', '')
        if status and status not in STATUSES:
            raise ValidationError({'status': ['Estado inválido.']})
        company_id = company_id_from(request)
        _run(lambda: DjangoPatientRepository(company_id).get(customer_id))  # 404 si no es paciente de la empresa
        rows = DjangoDentalProformaRepository(company_id).for_patient(customer_id, status=status)
        paginator = ProformaPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response([summary_data(to_domain(row)) for row in page])

    def post(self, request, customer_id):
        serializer = ProformaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _service(request)
        proforma = _run(lambda: service.create(customer_id, serializer.to_input()))
        return Response(_detail(service, proforma), status=201)


class ProformaDetailView(ProformaView):
    def get(self, request, proforma_id):
        service = _service(request)
        return Response(_detail(service, _run(lambda: service.get(proforma_id))))

    def put(self, request, proforma_id):
        serializer = ProformaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _service(request)
        proforma = _run(lambda: service.update(proforma_id, serializer.to_input()))
        return Response(_detail(service, proforma))


class ProformaActionView(ProformaView):
    action = ''

    def post(self, request, proforma_id):
        service = _service(request)
        method = {'present': service.present, 'new_version': service.new_version}[self.action]
        proforma = _run(lambda: method(proforma_id))
        return Response(_detail(service, proforma), status=201 if self.action == 'new_version' else 200)


class ProformaDecisionView(ProformaView):
    """Registra la aceptación o el rechazo de una o varias líneas (idempotente por `idempotency_key`)."""

    def post(self, request, proforma_id):
        serializer = DecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _service(request)
        result = _run(lambda: service.decide(proforma_id, serializer.to_input()))
        chosen = {str(i) for i in result.line_ids}
        amount = sum((l.subtotal for l in result.proforma.lines if str(l.id) in chosen), Decimal('0'))
        return Response({**_detail(service, result.proforma), 'replayed': result.replayed,
                         'summary': {'lines': len(chosen), 'amount': f'{money(amount):.2f}'}},
                        status=200 if result.replayed else 201)


class ProformaRectifyView(ProformaView):
    def post(self, request, proforma_id, line_id):
        serializer = DecisionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _service(request)
        result = _run(lambda: service.rectify(proforma_id, line_id, serializer.to_input([line_id])))
        return Response({**_detail(service, result.proforma), 'replayed': result.replayed},
                        status=200 if result.replayed else 201)


class ProformaPrintableView(ProformaView):
    def get(self, request, proforma_id):
        service = _service(request)
        return Response(printable_data(_run(lambda: service.printable(proforma_id))))
