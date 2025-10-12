from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db.models import Q
from django.core.files.storage import default_storage
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from services.models import Months, Months_calculation, Month_indicators
from services.views import calculate_application_yield_demo
from .serializers import (
    MonthsListSerializer,
    MonthsCreateUpdateSerializer,
    MonthsCalculationListSerializer,
    MonthsCalculationDetailSerializer,
    MonthsCalculationUpdateSerializer,
    MonthsCartSerializer,
    MonthIndicatorsSerializer,
    RegisterSerializer,
    LoginSerializer,
    MeSerializer,
)
from .utils import _get_or_create_creator_user, _get_or_create_moderator_user
from .storage import generate_image_key, delete_object_if_exists


class MonthsViewSet(viewsets.ModelViewSet):
    queryset = Months.objects.all()

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return MonthsListSerializer
        return MonthsCreateUpdateSerializer

    def get_queryset(self):
        qs = Months.objects.filter(status=True)
        q = (self.request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(month_name__istartswith=q)
        return qs

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.month_image:
            delete_object_if_exists(obj.month_image)
        obj.status = False
        obj.month_image = None
        obj.save(update_fields=["status", "month_image"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="image")
    def upload_image(self, request, pk=None):
        month = self.get_object()
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "file is required"}, status=400)
        new_key = generate_image_key(month.month_name, file_obj.name)
        if month.month_image:
            delete_object_if_exists(month.month_image)
        saved_path = default_storage.save(new_key, file_obj)
        month.month_image = saved_path
        month.save(update_fields=["month_image"])
        return Response({"image_key": saved_path}, status=200)

    @action(detail=True, methods=["post"], url_path="add")
    def add_to_calculation(self, request, pk=None):
        service = self.get_object()
        creator = _get_or_create_creator_user()
        order = Months_calculation.objects.filter(created_by=creator, status="draft").first()
        if not order:
            order = Months_calculation.objects.create(created_by=creator, status="draft")
        Month_indicators.objects.get_or_create(
            order=order,
            service=service,
            defaults={
                "avg_temp": 0,
                "sum_precipitation": 0,
                "comment": "",
            },
        )
        return Response({"order_id": order.id}, status=200)


class MonthsCalculationCartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        creator = _get_or_create_creator_user()
        order = Months_calculation.objects.filter(created_by=creator, status="draft").first()
        count = Month_indicators.objects.filter(order=order).count() if order else 0
        data = {"order_id": order.id if order else None, "items_count": count}
        serializer = MonthsCartSerializer(data)
        return Response(serializer.data)


class MonthsCalculationViewSet(viewsets.GenericViewSet):
    queryset = Months_calculation.objects.all()

    def list(self, request):
        qs = Months_calculation.objects.exclude(status__in=["deleted", "draft"]).select_related("created_by", "moderator")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        submitted_from = request.query_params.get("submitted_from")
        submitted_to = request.query_params.get("submitted_to")
        if submitted_from:
            qs = qs.filter(submitted_at__gte=submitted_from)
        if submitted_to:
            qs = qs.filter(submitted_at__lte=submitted_to)
        serializer = MonthsCalculationListSerializer(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        order = get_object_or_404(Months_calculation, pk=pk)
        if order.status == "deleted":
            return Response(status=404)
        serializer = MonthsCalculationDetailSerializer(order)
        return Response(serializer.data)

    def update(self, request, pk=None):
        order = get_object_or_404(Months_calculation, pk=pk)
        if order.status not in ("draft", "submitted"):
            return Response({"detail": "Invalid status for update"}, status=409)
        serializer = MonthsCalculationUpdateSerializer(order, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MonthsCalculationDetailSerializer(order).data)

    def destroy(self, request, pk=None):
        order = get_object_or_404(Months_calculation, pk=pk)
        if order.status != "deleted":
            order.status = "deleted"
            order.save(update_fields=["status"])
        return Response(status=204)


class MonthsCalculationSubmitView(APIView):
    def put(self, request, id: int):
        order = get_object_or_404(Months_calculation, pk=id)
        if order.status != "draft":
            return Response({"detail": "Only draft can be submitted"}, status=409)
        has_items = Month_indicators.objects.filter(order=order).exists()
        if not has_items or not order.location or not order.person:
            return Response({"detail": "Missing required fields or items"}, status=400)
        order.status = "submitted"
        order.submitted_at = timezone.now()
        order.save(update_fields=["status", "submitted_at"])
        return Response(MonthsCalculationDetailSerializer(order).data)


class MonthsCalculationFinishView(APIView):
    def put(self, request, id: int):
        order = get_object_or_404(Months_calculation, pk=id)
        if order.status != "submitted":
            return Response({"detail": "Only submitted can be finished"}, status=409)
        moderator = _get_or_create_moderator_user()
        result = calculate_application_yield_demo(order.id)
        order.status = "finished"
        order.moderator = moderator
        order.finished_at = timezone.now()
        order.result_value = result
        order.save(update_fields=["status", "moderator", "finished_at", "result_value"])
        return Response(MonthsCalculationDetailSerializer(order).data)


class MonthsCalculationRejectView(APIView):
    def put(self, request, id: int):
        order = get_object_or_404(Months_calculation, pk=id)
        if order.status != "submitted":
            return Response({"detail": "Only submitted can be rejected"}, status=409)
        moderator = _get_or_create_moderator_user()
        order.status = "rejected"
        order.moderator = moderator
        order.finished_at = timezone.now()
        order.save(update_fields=["status", "moderator", "finished_at"])
        return Response(MonthsCalculationDetailSerializer(order).data)


class MonthIndicatorsUpdateView(APIView):
    def put(self, request, order_id: int, service_id: int):
        order = get_object_or_404(Months_calculation, pk=order_id)
        if order.status not in ("draft", "submitted"):
            return Response({"detail": "Invalid status for item update"}, status=409)
        service = get_object_or_404(Months, pk=service_id, status=True)
        item = get_object_or_404(Month_indicators, order=order, service=service)
        serializer = MonthIndicatorsSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # ручное обновление, так как serializer read_only для вложенного service
        for field in ["sum_precipitation", "avg_temp", "comment"]:
            if field in serializer.validated_data:
                setattr(item, field, serializer.validated_data[field])
        item.save()
        return Response(MonthIndicatorsSerializer(item).data)


class MonthIndicatorsDeleteView(APIView):
    def delete(self, request, order_id: int, service_id: int):
        order = get_object_or_404(Months_calculation, pk=order_id)
        if order.status not in ("draft", "submitted"):
            return Response({"detail": "Invalid status for item delete"}, status=409)
        service = get_object_or_404(Months, pk=service_id)
        Month_indicators.objects.filter(order=order, service=service).delete()
        return Response(status=204)


from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        email = serializer.validated_data.get("email")
        if User.objects.filter(username=username).exists():
            return Response({"detail": "Username already exists"}, status=400)
        User.objects.create_user(username=username, password=password, email=email)
        return Response(status=201)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": "Invalid credentials"}, status=400)
        login(request, user)
        return Response(status=200)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=200)


class MeView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response(status=401)
        data = {
            "username": request.user.username,
            "email": request.user.email or "",
            "first_name": request.user.first_name or "",
            "last_name": request.user.last_name or "",
        }
        return Response(data)

    def put(self, request):
        if not request.user.is_authenticated:
            return Response(status=401)
        serializer = MeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field in ["email", "first_name", "last_name"]:
            if field in serializer.validated_data:
                setattr(request.user, field, serializer.validated_data[field])
        request.user.save()
        return Response({
            "username": request.user.username,
            "email": request.user.email or "",
            "first_name": request.user.first_name or "",
            "last_name": request.user.last_name or "",
        })


