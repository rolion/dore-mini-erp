from rest_framework.views import APIView

from modules.crm.application.activity_services import ActivityService
from modules.crm.application.related import RelatedEntities
from modules.crm.application.task_services import STATUS_FILTERS, TaskService
from modules.crm.infrastructure.adapters import CustomerGatewayAdapter, UserDirectoryAdapter, system_clock
from modules.crm.infrastructure.django.repositories import (
    DjangoActivityRepository,
    DjangoOpportunityRepository,
    DjangoTaskRepository,
)
from shared.tenancy import company_id_from

from .common import body, query_choice, query_uuid, run
from .opportunity_views import _query_int
from .pagination import CrmListPagination
from .task_serializers import (
    ActivityCreateInputSerializer,
    TaskCompleteInputSerializer,
    TaskCreateInputSerializer,
    TaskEditInputSerializer,
    activity_data,
    task_data,
)


def _related(company_id) -> RelatedEntities:
    return RelatedEntities(customers=CustomerGatewayAdapter(company_id),
                           opportunities=DjangoOpportunityRepository(company_id))


def task_service(request) -> TaskService:
    """La empresa sale siempre del usuario autenticado, nunca del cuerpo de la petición."""
    company_id = company_id_from(request)
    return TaskService(tasks=DjangoTaskRepository(company_id), activities=DjangoActivityRepository(company_id),
                       related=_related(company_id), users=UserDirectoryAdapter(company_id), clock=system_clock)


def activity_service(request) -> ActivityService:
    company_id = company_id_from(request)
    return ActivityService(activities=DjangoActivityRepository(company_id), related=_related(company_id),
                           users=UserDirectoryAdapter(company_id), clock=system_clock)


class TaskListCreateView(APIView):
    required_modules = ('customers',)

    def get(self, request):
        filters = {
            'owner_id': _query_int(request, 'owner_id'),
            'status': query_choice(request, 'status', STATUS_FILTERS),
            'customer_id': query_uuid(request, 'customer_id'),
            'opportunity_id': query_uuid(request, 'opportunity_id'),
        }
        service = task_service(request)

        def page(rows):
            paginator = CrmListPagination()
            found = paginator.paginate_queryset(rows, request, view=self)
            return paginator.get_paginated_response([task_data(card) for card in found]).data

        return run(lambda: service.list(**filters), page)

    def post(self, request):
        values = body(TaskCreateInputSerializer, request)
        service = task_service(request)
        return run(lambda: service.create(actor_id=request.user.id, **values),
                   lambda t: task_data(service.card(t)), status=201)


class TaskDetailView(APIView):
    required_modules = ('customers',)

    def get(self, request, task_id):
        service = task_service(request)
        return run(lambda: service.get(task_id), lambda t: task_data(service.card(t)))

    def patch(self, request, task_id):
        values = body(TaskEditInputSerializer, request, partial=True)
        service = task_service(request)
        return run(lambda: service.edit(task_id, **values), lambda t: task_data(service.card(t)))


class TaskCompleteView(APIView):
    required_modules = ('customers',)

    def post(self, request, task_id):
        values = body(TaskCompleteInputSerializer, request)
        service = task_service(request)
        activities = activity_service(request)

        def render(result):
            task, activity = result
            return {**task_data(service.card(task)),
                    'activity': activity_data(activities.card(activity)) if activity else None}

        return run(lambda: service.complete(task_id, actor_id=request.user.id, activity=values.get('activity')),
                   render)


class _TaskActionView(APIView):
    required_modules = ('customers',)
    action = ''

    def post(self, request, task_id):
        service = task_service(request)
        return run(lambda: getattr(service, self.action)(task_id), lambda t: task_data(service.card(t)))


class TaskCancelView(_TaskActionView):
    action = 'cancel'


class TaskReopenView(_TaskActionView):
    action = 'reopen'


class TaskArchiveView(_TaskActionView):
    action = 'archive'


class ActivityListCreateView(APIView):
    required_modules = ('customers',)

    def get(self, request):
        filters = {'customer_id': query_uuid(request, 'customer_id'),
                   'opportunity_id': query_uuid(request, 'opportunity_id')}
        service = activity_service(request)

        def page(rows):
            paginator = CrmListPagination()
            found = paginator.paginate_queryset(rows, request, view=self)
            return paginator.get_paginated_response([activity_data(card) for card in found]).data

        return run(lambda: service.list(**filters), page)

    def post(self, request):
        values = body(ActivityCreateInputSerializer, request)
        service = activity_service(request)
        return run(lambda: service.create(actor_id=request.user.id, **values),
                   lambda a: activity_data(service.card(a)), status=201)
