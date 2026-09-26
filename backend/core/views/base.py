from django.db import transaction
from rest_framework import viewsets


class OwnedViewSet(viewsets.ModelViewSet):
    """Scopes all queries to the requesting user."""

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)
