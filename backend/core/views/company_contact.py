from core.models import CompanyContact
from core.serializers import CompanyContactSerializer

from .base import OwnedViewSet


class CompanyContactViewSet(OwnedViewSet[CompanyContact]):
    queryset = CompanyContact.objects.all()
    serializer_class = CompanyContactSerializer
    search_fields = ["first_name", "last_name", "role", "email"]
    ordering_fields = ["last_name", "first_name", "role", "created_at"]
