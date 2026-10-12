from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from modules.accounts.registration import RegistrationError, register_company_admin

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer

INVALID_CREDENTIALS = 'Credenciales inválidas.'
REGISTRATION_DISABLED = 'El registro no está disponible por el momento.'


def _session(token: Token, user, http_status: int = status.HTTP_200_OK) -> Response:
    return Response({'token': token.key, 'user': UserSerializer(user).data}, status=http_status)


class LoginView(APIView):
    # Sin autenticación previa: un header Authorization vencido no debe romper el login.
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        # Usuario inexistente, inactivo o de una empresa inactiva: misma respuesta (no distingue casos).
        if user is None or (user.company is not None and not user.company.is_active):
            # Respuesta directa: sin authenticate header DRF degradaría un 401 lanzado a 403.
            return Response({'detail': INVALID_CREDENTIALS}, status=status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user=user)
        return _session(token, user)


class RegisterView(APIView):
    """Alta pública: crea la empresa y su primer usuario admin, y deja la sesión iniciada."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'register'

    def post(self, request):
        if not settings.REGISTRATION_ENABLED:
            raise PermissionDenied(REGISTRATION_DISABLED)
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = register_company_admin(**serializer.validated_data)
        except RegistrationError as exc:
            raise ValidationError(exc.errors) from exc
        token = Token.objects.create(user=user)
        return _session(token, user, status.HTTP_201_CREATED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
