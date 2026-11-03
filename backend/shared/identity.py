"""Adaptador de identidad neutral: negocio recibe una interfaz, nunca el modelo de cuentas."""
from django.contrib.auth import get_user_model
from django.db.models import F, Value
from django.db.models.functions import Concat, Trim


class CompanyUserDirectory:
    def __init__(self, company_id):
        self.company_id = company_id

    def _users(self):
        return get_user_model().objects.filter(company_id=self.company_id)

    def exists(self, user_id: int) -> bool:
        return self._users().filter(id=user_id).exists()

    def list(self, search: str = '', user_id: int | None = None):
        from django.db.models import Q

        users = self._users()
        if user_id is not None:
            users = users.filter(id=user_id)
        return users.filter(
            Q(username__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search)
        ).annotate(name=Concat(Trim(Concat('first_name', Value(' '), 'last_name')),
                               Value(' ('), F('username'), Value(')'))).order_by('username', 'id').values('id', 'name')
