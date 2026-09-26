from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Customer, TimeEntry
from core.serializers import TimeEntrySerializer

from .base import OwnedViewSet


class StartTimerSerializer(serializers.Serializer):
    customer = serializers.UUIDField()
    project = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)


class TimeEntryViewSet(OwnedViewSet):
    queryset = TimeEntry.objects.select_related(
        "customer", "project", "contract"
    )
    serializer_class = TimeEntrySerializer
    filterset_fields = {
        "customer": ["exact"],
        "project": ["exact"],
        "project__customer": ["exact"],
        "contract": ["exact", "isnull"],
        "invoice": ["exact", "isnull"],
        "billable": ["exact"],
        "date": ["gte", "lte", "exact"],
        "visit": ["exact"],
    }
    search_fields = ["description", "project__name", "customer__name"]
    ordering_fields = ["date", "start_time", "duration_minutes"]

    @action(detail=False, methods=["get"])
    def active(self, request):
        """The running timer, if any."""
        entry = self.get_queryset().filter(end_time__isnull=True).first()
        return Response(
            TimeEntrySerializer(entry, context={"request": request}).data
            if entry
            else None
        )

    @action(detail=False, methods=["post"])
    def start_timer(self, request):
        if self.get_queryset().filter(end_time__isnull=True).exists():
            return Response(
                {"detail": "A timer is already running."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = StartTimerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        customer = Customer.objects.filter(
            owner=request.user, pk=ser.validated_data["customer"]
        ).first()
        if not customer:
            return Response(
                {"customer": ["Invalid customer."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        project = None
        if ser.validated_data.get("project"):
            project = customer.projects.filter(
                pk=ser.validated_data["project"]
            ).first()
            if project is None:
                return Response(
                    {"project": ["Invalid project."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        now = timezone.localtime()
        entry = TimeEntry.objects.create(
            owner=request.user,
            customer=customer,
            project=project,
            date=now.date(),
            start_time=now.time(),
            end_time=None,
            description=ser.validated_data.get("description", ""),
        )
        return Response(
            TimeEntrySerializer(entry, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        entry = self.get_object()
        if entry.end_time is not None:
            return Response(
                {"detail": "Timer is not running."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        now = timezone.localtime()
        entry.end_time = now.time()
        if entry.date < now.date():
            entry.end_time = now.time().replace(hour=23, minute=59, second=59)
        entry.save()
        return Response(
            TimeEntrySerializer(entry, context={"request": request}).data
        )
