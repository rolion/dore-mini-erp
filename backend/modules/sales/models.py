# Django descubre los modelos del app desde este módulo; la definición vive en infraestructura.
from modules.sales.infrastructure.django.models import OrderItemModel, OrderModel, PaymentModel  # noqa: F401
