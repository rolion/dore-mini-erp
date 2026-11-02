# Django descubre los modelos del app desde este módulo; la definición vive en infraestructura.
from modules.customers.infrastructure.django.models import CustomerModel  # noqa: F401
from modules.customers.infrastructure.django.demographics import (  # noqa: F401
    CustomerDemographicsModel, CustomerDemographicsHistoryModel,
)
