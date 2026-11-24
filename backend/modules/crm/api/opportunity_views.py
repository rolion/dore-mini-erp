from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from modules.crm.application.opportunity_services import OpportunityService
from modules.crm.domain.opportunity import STATUSES
from modules.crm.infrastructure.adapters import (
    CustomerGatewayAdapter,
    ModuleAvailabilityAdapter,
    OrderGatewayAdapter,
    UserDirectoryAdapter,
    system_clock,
)
from modules.crm.infrastructure.django.repositories import (
    DjangoBoardRepository,
    DjangoLeadRepository,
    DjangoOpportunityRepository,
)
from shared.tenancy import company_id_from

from .common import body, query_choice, query_uuid, run
from .opportunity_serializers import (
    CloseInputSerializer,
    MoveInputSerializer,
    OpportunityCreateInputSerializer,
    OpportunityEditInputSerializer,
    OrderLinkInputSerializer,
    opportunity_data,
    order_data,
    stage_change_data,
)
from .pagination import CrmListPagination


def opportunity_service(request) -> OpportunityService:
    """La empresa sale siempre del usuario autenticado, nunca del cuerpo de la petición."""
    company_id = company_id_from(request)
    return OpportunityService(
        opportunities=DjangoOpportunityRepository(company_id), boards=DjangoBoardRepository(company_id),
        leads=DjangoLeadRepository(company_id), customers=CustomerGatewayAdapter(company_id),
        users=UserDirectoryAdapter(company_id), orders=OrderGatewayAdapter(company_id),
        availability=ModuleAvailabilityAdapter(company_id), clock=system_clock)


def _query_int(request, name: str) -> int | None:
    raw = request.query_params.get(name, '').strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise ValidationError({name: ['Identificador inválido.']}) from exc


class OpportunityListCreateView(APIView):
    required_modules = ('customers',)

    def get(self, request):
        filters = {
            'board_id': query_uuid(request, 'board_id', required=True),
            'owner_id': _query_int(request, 'owner_id'),
            'lead_id': query_uuid(request, 'lead_id'),
            'customer_id': query_uuid(request, 'customer_id'),
            'status': query_choice(request, 'status', STATUSES),
        }
        service = opportunity_service(request)

        def page(rows):
            paginator = CrmListPagination()
            found = paginator.paginate_queryset(rows, request, view=self)
            return paginator.get_paginated_response([opportunity_data(card) for card in found]).data

        return run(lambda: service.list(**filters), page)

    def post(self, request):
        values = body(OpportunityCreateInputSerializer, request)
        service = opportunity_service(request)
        return run(lambda: service.create(actor_id=request.user.id, **values),
                   lambda o: opportunity_data(service.card(o)), status=201)


class OpportunityDetailView(APIView):
    required_modules = ('customers',)

    def get(self, request, opportunity_id):
        service = opportunity_service(request)
        return run(lambda: service.get(opportunity_id), lambda o: opportunity_data(service.card(o)))

    def patch(self, request, opportunity_id):
        values = body(OpportunityEditInputSerializer, request)
        service = opportunity_service(request)
        return run(lambda: service.edit(opportunity_id, actor_id=request.user.id, **values),
                   lambda o: opportunity_data(service.card(o)))


class OpportunityMoveView(APIView):
    required_modules = ('customers',)

    def post(self, request, opportunity_id):
        values = body(MoveInputSerializer, request)
        service = opportunity_service(request)
        return run(lambda: service.move(opportunity_id, values['stage_id'], actor_id=request.user.id),
                   lambda o: opportunity_data(service.card(o)))


class OpportunityCloseView(APIView):
    required_modules = ('customers',)

    def post(self, request, opportunity_id):
        values = body(CloseInputSerializer, request)
        service = opportunity_service(request)
        return run(lambda: service.close(opportunity_id, values['result'], lost_reason=values.get('lost_reason') or '',
                                         order_id=values.get('order_id')),
                   lambda o: opportunity_data(service.card(o)))


class OpportunityOrderView(APIView):
    required_modules = ('customers',)

    def put(self, request, opportunity_id):
        values = body(OrderLinkInputSerializer, request)
        service = opportunity_service(request)
        return run(lambda: service.link_order(opportunity_id, values['order_id']),
                   lambda o: opportunity_data(service.card(o)))


class OpportunityLinkableOrdersView(APIView):
    required_modules = ('customers',)

    def get(self, request, opportunity_id):
        service = opportunity_service(request)
        return run(lambda: service.linkable_orders(opportunity_id), lambda orders: [order_data(o) for o in orders])


class OpportunityHistoryView(APIView):
    required_modules = ('customers',)

    def get(self, request, opportunity_id):
        service = opportunity_service(request)
        return run(lambda: service.history(opportunity_id), lambda changes: [stage_change_data(c) for c in changes])
