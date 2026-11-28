from datetime import datetime

from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from modules.crm.application.inbox_services import InboxService
from modules.crm.application.opportunity_services import OpportunityService
from modules.crm.infrastructure.adapters import (
    ConversationInboxAdapter,
    CustomerDirectoryAdapter,
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

from .common import body, query_uuid, run
from .inbox_serializers import (
    ContactInputSerializer,
    MessageInputSerializer,
    OpportunityLinkInputSerializer,
    OpportunityNewInputSerializer,
    OwnerInputSerializer,
    conversation_data,
    message_data,
)
from .opportunity_serializers import opportunity_data
from .pagination import CrmListPagination


def inbox_service(company_id) -> InboxService:
    """La empresa sale siempre del usuario autenticado, nunca del cuerpo de la petición."""
    customers, opportunities = CustomerGatewayAdapter(company_id), DjangoOpportunityRepository(company_id)
    leads, users = DjangoLeadRepository(company_id), UserDirectoryAdapter(company_id)
    return InboxService(
        inbox=ConversationInboxAdapter(company_id), customers=customers,
        customer_directory=CustomerDirectoryAdapter(company_id), leads=leads, opportunities=opportunities,
        users=users, opportunity_service=OpportunityService(
            opportunities=opportunities, boards=DjangoBoardRepository(company_id), leads=leads,
            customers=customers, users=users, orders=OrderGatewayAdapter(company_id),
            availability=ModuleAvailabilityAdapter(company_id), clock=system_clock))


def _service(request) -> InboxService:
    return inbox_service(company_id_from(request))


class _Rows:
    """Filas paginables: cada rebanada pide solo su página al servicio (el conteo sale de la misma consulta)."""

    def __init__(self, fetch):
        self._fetch = fetch

    def count(self) -> int:
        return self._fetch(0, 1)[0]

    def __getitem__(self, index: slice):
        return self._fetch(index.start or 0, index.stop - (index.start or 0))[1]


def _after(request) -> datetime | None:
    raw = request.query_params.get('after', '').strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValidationError({'after': ['Fecha inválida.']}) from exc


class ConversationListView(APIView):
    required_modules = ('customers',)

    def get(self, request):
        service = _service(request)
        params = request.query_params
        filters = {'actor_id': request.user.id, 'scope': params.get('scope', 'all'),
                   'search': params.get('search'), 'opportunity_id': query_uuid(request, 'opportunity_id')}
        rows = _Rows(lambda offset, limit: service.list(offset=offset, limit=limit, **filters))

        def page(_):
            paginator = CrmListPagination()
            found = paginator.paginate_queryset(rows, request, view=self)
            return paginator.get_paginated_response([conversation_data(i) for i in found]).data

        return run(lambda: None, page)


class ConversationDetailView(APIView):
    required_modules = ('customers',)

    def get(self, request, conversation_id):
        service = _service(request)
        return run(lambda: service.get(conversation_id), conversation_data)


class MessageListCreateView(APIView):
    required_modules = ('customers',)

    def get(self, request, conversation_id):
        service, after = _service(request), _after(request)
        return run(lambda: service.messages(conversation_id, after),
                   lambda rows: {'results': [message_data(m) for m in rows]})

    def post(self, request, conversation_id):
        values = body(MessageInputSerializer, request)
        service = _service(request)
        if values['type'] == 'text':
            return run(lambda: service.send_text(conversation_id, values['body']), message_data, status=202)
        return run(lambda: service.send_template(conversation_id, values['template_id'], values.get('components')),
                   message_data, status=202)


class MessageRetryView(APIView):
    required_modules = ('customers',)

    def post(self, request, conversation_id, message_id):
        service = _service(request)
        return run(lambda: service.retry(conversation_id, message_id), message_data, status=202)


class ConversationOwnerView(APIView):
    required_modules = ('customers',)

    def put(self, request, conversation_id):
        values = body(OwnerInputSerializer, request)
        service = _service(request)
        return run(lambda: service.assign(conversation_id, values['owner_id']), conversation_data)


class ConversationContactView(APIView):
    required_modules = ('customers',)

    def put(self, request, conversation_id):
        values = body(ContactInputSerializer, request)
        service = _service(request)
        return run(lambda: service.set_contact(conversation_id, customer_id=values.get('customer_id'),
                                               lead_id=values.get('lead_id')), conversation_data)


class ConversationOpportunityView(APIView):
    required_modules = ('customers',)

    def put(self, request, conversation_id):
        values = body(OpportunityLinkInputSerializer, request)
        service = _service(request)
        return run(lambda: service.set_opportunity(conversation_id, values['opportunity_id']), conversation_data)

    def post(self, request, conversation_id):
        values = body(OpportunityNewInputSerializer, request)
        service = _service(request)
        return run(lambda: service.create_opportunity(conversation_id, actor_id=request.user.id, **values),
                   conversation_data, status=201)


class ConversationLinkableOpportunitiesView(APIView):
    required_modules = ('customers',)

    def get(self, request, conversation_id):
        service = _service(request)

        def render(rows):
            return {'results': [opportunity_data(card) for card in service.opportunity_service.describe(rows)]}

        return run(lambda: service.linkable_opportunities(conversation_id), render)
