from rest_framework.views import APIView

from modules.crm.application.lead_services import LeadService
from modules.crm.infrastructure.adapters import CustomerGatewayAdapter
from modules.crm.infrastructure.django.repositories import DjangoLeadRepository, DjangoOpportunityRepository
from shared.tenancy import company_id_from

from .common import body, query_choice, run
from .lead_serializers import ConvertInputSerializer, LeadInputSerializer, conversion_data, lead_data
from .pagination import CrmListPagination


def lead_service(request) -> LeadService:
    """La empresa sale siempre del usuario autenticado, nunca del cuerpo de la petición."""
    company_id = company_id_from(request)
    return LeadService(DjangoLeadRepository(company_id), DjangoOpportunityRepository(company_id),
                       CustomerGatewayAdapter(company_id))


class LeadListCreateView(APIView):
    required_modules = ('customers',)

    def get(self, request):
        converted = query_choice(request, 'converted', ('true', 'false'))
        search = request.query_params.get('search', '').strip() or None
        rows = lead_service(request).list(search=search, converted=None if converted is None else converted == 'true')
        paginator = CrmListPagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response([lead_data(lead) for lead in page])

    def post(self, request):
        values = body(LeadInputSerializer, request)
        service = lead_service(request)
        return run(lambda: service.create(values['name'], values.get('phone') or '', values.get('email') or ''),
                   lead_data, status=201)


class LeadDetailView(APIView):
    required_modules = ('customers',)

    def get(self, request, lead_id):
        service = lead_service(request)
        return run(lambda: service.get(lead_id), lead_data)

    def patch(self, request, lead_id):
        values = body(LeadInputSerializer, request, partial=True)
        service = lead_service(request)
        fields = {key: values[key] or '' for key in ('name', 'phone', 'email') if key in values}
        return run(lambda: service.edit(lead_id, **fields), lead_data)


class LeadConvertView(APIView):
    required_modules = ('customers',)

    def post(self, request, lead_id):
        values = body(ConvertInputSerializer, request)
        service = lead_service(request)
        return run(lambda: service.convert(lead_id, values.get('customer_id')), conversion_data)
