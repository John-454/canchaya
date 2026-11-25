"""URLs del módulo users_auth (§5.1)."""

from django.urls import path

from modules.users_auth.api.views import MeView, SyncView

urlpatterns = [
    path("sync/", SyncView.as_view(), name="auth-sync"),
    path("me/", MeView.as_view(), name="auth-me"),
]
