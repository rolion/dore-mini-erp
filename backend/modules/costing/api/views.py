from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from modules.costing.application.use_cases import (
    AdoptionOutcome,
    AdoptValuation,
    GetProposal,
    GetValuation,
    ValuationView,
)
from modules.costing.domain.exceptions import (
    AdoptionIdReused,
    NegativeStock,
    StockChanged,
    ValuationAlreadyAdopted,
    ValuationValidationError,
)
from modules.costing.domain.valuation import ValuationAdoption
from modules.costing.infrastructure.adapters import InventoryCompanyStock
from modules.costing.infrastructure.django.repositories import DjangoAdoptionRepository
from shared.tenancy import company_id_from

from .serializers import AdoptionInputSerializer

REQUIRED_MODULES = ('costing',)


class Conflict(APIException):
    """409 con `{detail, code, ...}`."""

    status_code = status.HTTP_409_CONFLICT

    def __init__(self, detail: str, code: str, **extra):
        super().__init__({'detail': detail, 'code': code, **extra})


def _text(value) -> str | None:
    return None if value is None else str(value)


def _adoption_body(adoption: ValuationAdoption | None, names: dict) -> dict:
    if adoption is None:
        return {'status': 'not_adopted', 'adoption': None}
    return {'status': 'adopted', 'adoption': {
        'id': str(adoption.id), 'cutoff_at': adoption.cutoff_at.isoformat(), 'method': adoption.method,
        'user_name': adoption.user_name,
        'lines': [{
            'product_id': str(line.product_id), 'product_name': names.get(line.product_id, ('', None))[0],
            'unit_abbreviation': names.get(line.product_id, ('', None))[1],
            'reconciled_quantity': str(line.reconciled_quantity), 'total_value': str(line.total_value),
            'unit_cost': str(line.unit_cost), 'declared_zero': line.declared_zero, 'source': line.source,
        } for line in adoption.lines]}}


def _by_position(errors: dict, data) -> dict:
    """Los errores de líneas viajan como lista (un dict por línea), igual que los del dominio."""
    lines = errors.get('lines')
    sent = data.get('lines') if hasattr(data, 'get') else None
    if isinstance(lines, dict) and isinstance(sent, list) and all(str(key).isdigit() for key in lines):
        errors = {**errors, 'lines': [lines.get(index, {}) for index in range(len(sent))]}
    return errors




class CurrentValuationView(APIView):
    """Estado de la valoración y, si fue adoptada, el corte con sus líneas."""

    required_modules = REQUIRED_MODULES

    def get(self, request):
        company_id = company_id_from(request)
        view: ValuationView = GetValuation(DjangoAdoptionRepository(company_id), InventoryCompanyStock(company_id)).execute()
        return Response(_adoption_body(view.adoption, view.names))


class ProposalView(APIView):
    """Propuesta de conciliación: cantidades por producto y almacén, y bloqueos por stock negativo."""

    required_modules = REQUIRED_MODULES

    def get(self, request):
        proposal = GetProposal(InventoryCompanyStock(company_id_from(request))).execute()
        return Response({
            'lines': [{
                'product_id': str(s.product_id), 'product_name': s.product_name,
                'unit_abbreviation': s.unit_abbreviation, 'reconciled_quantity': str(s.quantity),
                'warehouses': [{'warehouse_id': str(w.warehouse_id), 'warehouse_name': w.warehouse_name,
                                'quantity': str(w.quantity)} for w in s.warehouses]} for s in proposal.lines],
            'blockers': [{
                'product_id': str(b.product_id), 'product_name': b.product_name,
                'warehouse_id': str(b.warehouse_id), 'warehouse_name': b.warehouse_name,
                'quantity': str(b.quantity)} for b in proposal.blockers]})


class AdoptView(APIView):
    required_modules = REQUIRED_MODULES

    def post(self, request):
        serializer = AdoptionInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise ValidationError(_by_position(serializer.errors, request.data))
        data = serializer.validated_data
        company_id = company_id_from(request)
        user = request.user
        use_case = AdoptValuation(DjangoAdoptionRepository(company_id), InventoryCompanyStock(company_id))
        try:
            outcome: AdoptionOutcome = use_case.execute(
                adoption_id=data['adoption_id'], raw_lines=[dict(line) for line in data['lines']],
                user_id=user.pk, user_name=user.get_full_name().strip() or user.get_username(),
                now=timezone.now())
        except ValuationValidationError as exc:
            raise ValidationError(exc.errors) from exc
        except NegativeStock as exc:
            raise Conflict(str(exc), exc.code, blockers=[{
                'product_id': str(b.product_id), 'product_name': b.product_name,
                'warehouse_id': str(b.warehouse_id), 'warehouse_name': b.warehouse_name,
                'quantity': str(b.quantity)} for b in exc.blockers]) from exc
        except StockChanged as exc:
            raise Conflict(str(exc), exc.code, lines=[{
                'product_id': str(pid), 'sent_quantity': _text(sent), 'current_quantity': _text(current)}
                for pid, sent, current in exc.differences]) from exc
        except (ValuationAlreadyAdopted, AdoptionIdReused) as exc:
            raise Conflict(str(exc), exc.code) from exc
        return Response(_adoption_body(outcome.adoption, outcome.names),
                        status=status.HTTP_200_OK if outcome.replayed else status.HTTP_201_CREATED)
