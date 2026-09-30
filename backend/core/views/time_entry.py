from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Customer, TimeEntry, TimeEntryBreak
from core.serializers import TimeEntrySerializer

from .base import OwnedViewSet


class StartTimerSerializer(serializers.Serializer):
    customer = serializers.UUIDField(required=False, allow_null=True)
    project = serializers.UUIDField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)


class TimeEntryViewSet(OwnedViewSet):
    queryset = TimeEntry.objects.select_related(
        "customer", "project", "contract"
    ).prefetch_related("breaks")
    serializer_class = TimeEntrySerializer
    filterset_fields = {
        "customer": ["exact"],
        "project": ["exact"],
        "project__customer": ["exact"],
        "contract": ["exact", "isnull"],
        "invoice": ["exact", "isnull"],
        "billable": ["exact"],
        "start_datetime": ["gte", "lte", "exact"],
        "visit": ["exact"],
    }
    search_fields = ["description", "project__name", "customer__name"]
    ordering_fields = ["start_datetime", "duration_minutes"]

    @action(detail=False, methods=["get"])
    def active(self, request):
        """The running timer, if any."""
        entry = (
            self.get_queryset()
            .filter(end_datetime__isnull=True)
            .prefetch_related("breaks")
            .first()
        )
        return Response(
            TimeEntrySerializer(entry, context={"request": request}).data
            if entry
            else None
        )

    @action(detail=False, methods=["post"])
    def start(self, request):
        if self.get_queryset().filter(end_datetime__isnull=True).exists():
            return Response(
                {"detail": "A timer is already running."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = StartTimerSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        customer = None
        if ser.validated_data.get("customer"):
            customer = Customer.objects.filter(
                owner=request.user, pk=ser.validated_data["customer"]
            ).first()
            if not customer:
                return Response(
                    {"customer": ["Invalid customer."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        project = None
        if customer and ser.validated_data.get("project"):
            project = customer.projects.filter(
                pk=ser.validated_data["project"]
            ).first()
            if project is None:
                return Response(
                    {"project": ["Invalid project."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        entry = TimeEntry.objects.create(
            owner=request.user,
            customer=customer,
            project=project,
            start_datetime=timezone.localtime(),
            end_datetime=None,
            description=ser.validated_data.get("description", ""),
        )
        return Response(
            TimeEntrySerializer(entry, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def _active_entry(self):
        return self.get_queryset().filter(end_datetime__isnull=True).first()

    @action(detail=False, methods=["post"])
    def stop(self, request):
        entry = self._active_entry()
        if not entry:
            return Response(
                {"detail": "No timer is running."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # close any open break before stopping
        entry.breaks.filter(end_datetime__isnull=True).update(
            end_datetime=timezone.localtime()
        )
        entry.end_datetime = timezone.localtime()
        entry.save()
        entry = TimeEntry.objects.prefetch_related("breaks").get(pk=entry.pk)
        return Response(
            TimeEntrySerializer(entry, context={"request": request}).data
        )

    @action(detail=False, methods=["post"])
    def pause(self, request):
        entry = self._active_entry()
        if not entry:
            return Response(
                {"detail": "No timer is running."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        open_break = entry.breaks.filter(end_datetime__isnull=True).first()
        if open_break:
            return Response(
                {"detail": "Timer is already paused."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        TimeEntryBreak.objects.create(
            owner=request.user,
            time_entry=entry,
            start_datetime=timezone.localtime(),
            end_datetime=None,
        )
        entry.save()
        entry = TimeEntry.objects.prefetch_related("breaks").get(pk=entry.pk)
        return Response(
            TimeEntrySerializer(entry, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def resume(self, request):
        entry = self._active_entry()
        if not entry:
            return Response(
                {"detail": "No timer is running."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        open_break = entry.breaks.filter(end_datetime__isnull=True).first()
        if not open_break:
            return Response(
                {"detail": "Timer is not paused."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        open_break.end_datetime = timezone.localtime()
        open_break.save()
        entry.save()
        entry = TimeEntry.objects.prefetch_related("breaks").get(pk=entry.pk)
        return Response(
            TimeEntrySerializer(entry, context={"request": request}).data
        )
