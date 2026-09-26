from rest_framework import viewsets


class OwnedViewSet(viewsets.ModelViewSet):
    """Scopes all queries to the requesting user."""

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)
