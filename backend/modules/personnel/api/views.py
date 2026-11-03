from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from shared.identity import CompanyUserDirectory
from shared.tenancy import company_id_from

from ..application.profiles import ChangeProfileState, SaveProfile
from ..domain.profiles import ProfileNotFound, ProfileValidationError
from ..infrastructure.django.repositories import DjangoProfileRepository
from .serializers import (
    ListFilterSerializer, ProfessionalInputSerializer, ProfessionalSerializer,
    SpecialtyInputSerializer, SpecialtySerializer,
    StrictInputSerializer,
)


class ProfilePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


def run(use_case, **kwargs):
    try:
        return use_case.execute(**kwargs)
    except ProfileNotFound as exc:
        raise NotFound('Registro no encontrado.') from exc
    except ProfileValidationError as exc:
        raise ValidationError(exc.errors) from exc


class ProfileView(APIView):
    required_modules = ('personnel',)
    kind = 'professionals'

    @property
    def output(self):
        return ProfessionalSerializer if self.kind == 'professionals' else SpecialtySerializer

    def repository(self, request):
        return DjangoProfileRepository(company_id_from(request))

    def get(self, request, profile_id=None):
        repo = self.repository(request)
        if profile_id:
            row = repo.rows(self.kind).filter(id=profile_id).first()
            if row is None:
                raise NotFound('Registro no encontrado.')
            return Response(self.output(row).data)
        filters = ListFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        values = filters.validated_data
        if 'active' in values:
            values['active'] = values['active'] == 'true'
        if self.kind == 'specialties':
            values.pop('specialty_id', None)
        rows = repo.list(self.kind, **values)
        paginator = ProfilePagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(self.output(page, many=True).data)

    def save(self, request, profile_id=None):
        input_class = ProfessionalInputSerializer if self.kind == 'professionals' else SpecialtyInputSerializer
        serializer = input_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = run(SaveProfile(self.repository(request), CompanyUserDirectory(company_id_from(request))),
                  kind=self.kind, values=serializer.validated_data, actor_id=request.user.id, profile_id=profile_id)
        return Response(self.output(row).data, status=200 if profile_id else 201)

class ProfileStateView(ProfileView):
    active = False

    def post(self, request, profile_id):
        serializer = StrictInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        row = run(ChangeProfileState(self.repository(request)), kind=self.kind, profile_id=profile_id,
                  active=self.active, actor_id=request.user.id)
        return Response(self.output(row).data)

    # State routes only accept POST; detail/list routes don't inherit this view's GET/PATCH handlers.
    http_method_names = ['post', 'options']


class ProfileListView(ProfileView):
    http_method_names = ['get', 'post', 'head', 'options']

    def post(self, request):
        return self.save(request)


class ProfileDetailView(ProfileView):
    http_method_names = ['get', 'patch', 'head', 'options']

    def patch(self, request, profile_id):
        return self.save(request, profile_id)


class UserOptionsView(APIView):
    required_modules = ('personnel',)

    def get(self, request):
        user_id = request.query_params.get('id')
        if user_id is not None:
            user_id = serializers.IntegerField(min_value=1).run_validation(user_id)
        rows = CompanyUserDirectory(company_id_from(request)).list(
            request.query_params.get('search', '').strip(), user_id)
        paginator = ProfilePagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(list(page))
