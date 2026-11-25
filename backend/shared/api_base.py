"""Clases base reutilizables para vistas de la API.

Contexto de DRF (verificado en `views.APIView.handle_exception`):

```python
auth_header = self.get_authenticate_header(self.request)  # auth_classes[0]
if auth_header:  exc.auth_header = auth_header
else:            exc.status_code = 403
```

Por eso una vista **sin autenticadores** convierte cualquier 401 en 403. Para los
endpoints públicos que igualmente deben devolver 401 (como `/auth/sync/` cuando
falta el token) se declara un autenticador que aporta el reto `Bearer`.
"""

from __future__ import annotations

from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from shared.auth.authentication import SupabaseJWTAuthentication


class SinAutenticacion(BaseAuthentication):
    """Autenticador nulo: deja `request.user` como `AnonymousUser`."""

    def authenticate(self, request):
        return None


class SoloRetoBearer(BaseAuthentication):
    """No autentica, pero aporta `WWW-Authenticate` para respuestas 401."""

    def authenticate(self, request):
        return None

    def authenticate_header(self, request) -> str:
        return 'Bearer realm="api"'


class PublicAPIView(APIView):
    """Endpoint público que puede responder 401 si falta el token."""

    authentication_classes = [SoloRetoBearer]
    permission_classes = [AllowAny]


class AutenticadoAPIView(APIView):
    """Endpoint que exige JWT de Supabase (401 si falta o es inválido)."""

    authentication_classes = [SupabaseJWTAuthentication]
