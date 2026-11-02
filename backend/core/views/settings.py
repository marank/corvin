from types import SimpleNamespace

from rest_framework import serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import CompanySettings, Customer, OnSiteVisit, Project, SupportContract, Task
from core.models.company_settings import NUMBERING_SCHEMES
from core.serializers import CompanySettingsSerializer
from core.services.numbering import preview_number


class CompanySettingsView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        obj, _ = CompanySettings.objects.get_or_create(user=request.user)
        return Response(CompanySettingsSerializer(obj).data)

    def put(self, request):
        obj, _ = CompanySettings.objects.get_or_create(user=request.user)
        ser = CompanySettingsSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class NumberPreviewSerializer(serializers.Serializer):
    entity = serializers.ChoiceField(choices=list(NUMBERING_SCHEMES))
    format = serializers.CharField(max_length=200)
    scope = serializers.ListField(
        child=serializers.ChoiceField(choices=["year", "customer", "project"]),
        required=False,
    )
    start = serializers.IntegerField(min_value=1)


class NumberPreviewView(APIView):
    def post(self, request):
        serializer = NumberPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        owner = request.user
        customer = Customer.objects.filter(owner=owner).order_by("-created_at").first()
        customer = customer or SimpleNamespace(
            number="1001", name="Musterkunde GmbH", vat_id="DE123456789"
        )
        project = Project.objects.filter(owner=owner).order_by("-created_at").first()
        project = project or SimpleNamespace(
            number="P-0001", name="Musterprojekt", customer=customer
        )
        contract = SupportContract.objects.filter(owner=owner).order_by(
            "-created_at"
        ).first() or SimpleNamespace(number="V-0001", name="Support", customer=customer)
        visit = OnSiteVisit.objects.filter(owner=owner).order_by("-created_at").first()
        task = Task.objects.filter(owner=owner).order_by("-created_at").first()
        values = {
            "customer": customer,
            "project": project,
            "contract": contract,
            "visit": visit,
            "task": task,
            "invoice": SimpleNamespace(customer=customer, project=project, issue_date=None),
        }
        return Response({"preview": preview_number(data["format"], data["start"], values)})
