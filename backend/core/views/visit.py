from types import SimpleNamespace
from typing import Any

from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from core.models import Customer, Invoice, OnSiteVisit, Project, TravelRate
from core.models.base import OwnedModel
from core.request_helpers import request_user
from core.serializers import OnSiteVisitSerializer
from core.services.numbering import next_number
from core.services.travel import billable_visits, resolve_travel_rate, travel_included

from .base import OwnedViewSet


class _TravelTermsQuerySerializer(serializers.Serializer[object]):
    customer = serializers.UUIDField()
    project = serializers.UUIDField(required=False)
    date = serializers.DateField()


class _TravelTermsRateSerializer(serializers.ModelSerializer[TravelRate]):
    class Meta:
        model = TravelRate
        fields = ["kind", "amount", "round_trip"]


class _TravelTermsSerializer(serializers.Serializer[object]):
    rate = _TravelTermsRateSerializer(allow_null=True)
    included = serializers.BooleanField()
    customer_distance_km = serializers.DecimalField(max_digits=7, decimal_places=1, allow_null=True)


class OnSiteVisitViewSet(OwnedViewSet[OnSiteVisit]):
    queryset = OnSiteVisit.objects.select_related("customer", "project")
    serializer_class = OnSiteVisitSerializer
    filterset_fields = ["customer", "project", "date"]
    search_fields = ["number", "customer__name", "location", "notes"]
    ordering_fields = [
        "number",
        "date",
        "customer__name",
        "project__name",
        "location",
        "arrival",
        "departure",
        "created_at",
    ]

    def perform_create(self, serializer: BaseSerializer[OnSiteVisit]) -> None:
        customer = serializer.validated_data["customer"]
        project = serializer.validated_data.get("project")
        visit = SimpleNamespace(**serializer.validated_data)
        serializer.save(
            number=next_number(
                request_user(self.request),
                "visit",
                {"customer": customer, "project": project, "visit": visit},
            )
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("customer", OpenApiTypes.UUID, required=True),
            OpenApiParameter("project", OpenApiTypes.UUID),
            OpenApiParameter("date_from", OpenApiTypes.DATE),
            OpenApiParameter("date_to", OpenApiTypes.DATE),
            OpenApiParameter("invoice", OpenApiTypes.UUID, description="A draft being edited"),
        ],
        responses=OnSiteVisitSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path="billable-travel")
    def billable_travel(self, request: Request) -> Response:
        """The customer's trips an invoice may bill: not billed yet, not covered by a
        contract."""
        params = _BillableTravelSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        p = params.validated_data
        owner = request_user(request)

        customer = _owned(Customer, owner, p, "customer")
        if customer is None:
            raise ValidationError({"customer": _("Invalid customer.")})
        visits = billable_visits(
            owner=owner,
            customer=customer,
            project=_owned(Project, owner, p, "project"),
            date_from=p.get("date_from"),
            date_to=p.get("date_to"),
            invoice=_owned(Invoice, owner, p, "invoice"),
        )
        return Response(OnSiteVisitSerializer(visits, many=True, context={"request": request}).data)

    @extend_schema(
        parameters=[
            OpenApiParameter("customer", OpenApiTypes.UUID, required=True),
            OpenApiParameter("project", OpenApiTypes.UUID),
            OpenApiParameter("date", OpenApiTypes.DATE, required=True),
        ],
        responses=_TravelTermsSerializer,
    )
    @action(detail=False, methods=["get"], url_path="travel-terms")
    def travel_terms(self, request: Request) -> Response:
        """The travel rate that applies to a visit, whether a contract includes the trip, and the
        customer's distance."""
        params = _TravelTermsQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        p = params.validated_data
        owner = request_user(request)
        customer = _owned(Customer, owner, p, "customer")
        if customer is None:
            raise ValidationError({"customer": _("Invalid customer.")})
        project = _owned(Project, owner, p, "project")
        scope = {"owner": owner, "customer": customer, "project": project, "on_date": p["date"]}
        terms = {
            "rate": resolve_travel_rate(**scope),
            "included": travel_included(**scope),
            "customer_distance_km": customer.travel_distance_km,
        }
        return Response(_TravelTermsSerializer(terms).data)


def _owned[M: OwnedModel](
    model: type[M], owner: User, params: dict[str, Any], key: str
) -> M | None:
    if not params.get(key):
        return None
    found = model._default_manager.filter(owner=owner, pk=params[key]).first()
    if found is None:
        raise ValidationError({key: _("Invalid object.")})
    return found


class _BillableTravelSerializer(serializers.Serializer[object]):
    customer = serializers.UUIDField()
    project = serializers.UUIDField(required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    invoice = serializers.UUIDField(required=False)
