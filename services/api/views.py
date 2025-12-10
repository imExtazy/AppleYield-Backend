from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db.models import Q
from django.core.files.storage import default_storage
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from services.models import Months, Months_calculation, Month_indicators
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
    ChangePasswordSerializer,
    UserSerializer,
)
from .storage import generate_image_key, delete_object_if_exists
from .permissions import IsManager, IsAdmin
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie, csrf_exempt
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from drf_yasg.utils import swagger_auto_schema
import requests
from decimal import Decimal


class MonthsViewSet(viewsets.ModelViewSet):
    queryset = Months.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]

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

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy", "upload_image"):
            permission_classes = [IsManager | IsAdmin]
        else:
            permission_classes = [IsAuthenticatedOrReadOnly]
        return [perm() for perm in permission_classes]

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.month_image:
            delete_object_if_exists(obj.month_image)
        obj.status = False
        obj.month_image = None
        obj.save(update_fields=["status", "month_image"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="image", permission_classes=[IsManager|IsAdmin])
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

    @action(detail=True, methods=["post"], url_path="add", permission_classes=[IsAuthenticated])
    def add_to_calculation(self, request, pk=None):
        service = self.get_object()
        creator = request.user
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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        creator = request.user
        order = Months_calculation.objects.filter(created_by=creator, status="draft").first()
        count = Month_indicators.objects.filter(order=order).count() if order else 0
        data = {"order_id": order.id if order else None, "items_count": count}
        serializer = MonthsCartSerializer(data)
        return Response(serializer.data)


class MonthsCalculationViewSet(viewsets.GenericViewSet):
    queryset = Months_calculation.objects.all()
    permission_classes = [IsAuthenticated]

    def list(self, request):
        if request.user.is_staff or request.user.is_superuser:
            # Администратор/модератор видит все заявки, включая draft/deleted
            qs = Months_calculation.objects.select_related("created_by", "moderator")
        else:
            # Обычный пользователь видит только свои, без черновиков
            qs = (
                Months_calculation.objects
                .exclude(status__in=["deleted", "draft"]).select_related("created_by", "moderator")
                .filter(created_by=request.user)
            )
        if not (request.user.is_staff or request.user.is_superuser):
            qs = qs.filter(created_by=request.user)
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
        if not (request.user.is_staff or request.user.is_superuser or order.created_by_id == request.user.id):
            return Response(status=403)
        serializer = MonthsCalculationDetailSerializer(order)
        return Response(serializer.data)

    def update(self, request, pk=None):
        order = get_object_or_404(Months_calculation, pk=pk)
        if order.status not in ("draft", "submitted"):
            return Response({"detail": "Invalid status for update"}, status=409)
        if order.created_by_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
            return Response(status=403)
        serializer = MonthsCalculationUpdateSerializer(order, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MonthsCalculationDetailSerializer(order).data)

    def destroy(self, request, pk=None):
        order = get_object_or_404(Months_calculation, pk=pk)
        if order.created_by_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
            return Response(status=403)
        if order.status != "deleted":
            order.status = "deleted"
            order.save(update_fields=["status"])
        return Response(status=204)


class MonthsCalculationSubmitView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(operation_description="Submit draft order")
    def put(self, request, id: int):
        order = get_object_or_404(Months_calculation, pk=id)
        if order.status != "draft":
            return Response({"detail": "Only draft can be submitted"}, status=409)
        if order.created_by_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
            return Response(status=403)
        has_items = Month_indicators.objects.filter(order=order).exists()
        if not has_items or not order.location or not order.person:
            return Response({"detail": "Missing required fields or items"}, status=400)
        order.status = "submitted"
        order.submitted_at = timezone.now()
        order.save(update_fields=["status", "submitted_at"])
        return Response(MonthsCalculationDetailSerializer(order).data)


class MonthsCalculationFinishView(APIView):
    permission_classes = [IsAuthenticated, IsManager|IsAdmin]
    @swagger_auto_schema(operation_description="Finish submitted order (moderator)")
    def put(self, request, id: int):
        order = get_object_or_404(Months_calculation, pk=id)
        if order.status != "submitted":
            return Response({"detail": "Only submitted can be finished"}, status=409)
        moderator = request.user
        # Фиксируем модератора, но статус и результат будут установлены после колбэка
        if order.moderator_id != moderator.id:
            order.moderator = moderator
            order.save(update_fields=["moderator"])
        payload = {
            "order_id": order.id,
            "callback_url": getattr(settings, "ASYNC_CALLBACK_URL", "http://localhost:8000/api/async/result/"),
        }
        compute_url = (getattr(settings, "ASYNC_SERVICE_BASE_URL", "http://localhost:8081").rstrip("/") + "/compute")
        try:
            resp = requests.post(compute_url, json=payload, timeout=10)
            # Если удалённый сервис отвечает не 2xx — считаем как ошибка и сообщаем клиенту
            if resp.status_code >= 400:
                return Response({"detail": f"Async service error: {resp.status_code}"}, status=502)
        except requests.RequestException:
            return Response({"detail": "Async service unavailable"}, status=502)
        return Response(MonthsCalculationDetailSerializer(order).data, status=202)


class MonthsCalculationRejectView(APIView):
    permission_classes = [IsAuthenticated, IsManager|IsAdmin]
    @swagger_auto_schema(operation_description="Reject submitted order (moderator)")
    def put(self, request, id: int):
        order = get_object_or_404(Months_calculation, pk=id)
        if order.status != "submitted":
            return Response({"detail": "Only submitted can be rejected"}, status=409)
        moderator = request.user
        order.status = "rejected"
        order.moderator = moderator
        order.finished_at = timezone.now()
        order.save(update_fields=["status", "moderator", "finished_at"])
        return Response(MonthsCalculationDetailSerializer(order).data)


class MonthIndicatorsUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(operation_description="Update indicators for item in order", request_body=MonthIndicatorsSerializer)
    def put(self, request, order_id: int, service_id: int):
        order = get_object_or_404(Months_calculation, pk=order_id)
        if order.status not in ("draft", "submitted"):
            return Response({"detail": "Invalid status for item update"}, status=409)
        if order.created_by_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
            return Response(status=403)
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
    permission_classes = [IsAuthenticated]
    def delete(self, request, order_id: int, service_id: int):
        order = get_object_or_404(Months_calculation, pk=order_id)
        if order.status not in ("draft", "submitted"):
            return Response({"detail": "Invalid status for item delete"}, status=409)
        if order.created_by_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
            return Response(status=403)
        service = get_object_or_404(Months, pk=service_id)
        Month_indicators.objects.filter(order=order, service=service).delete()
        return Response(status=204)


class AsyncOrderPayloadView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(operation_description="Provide payload for async compute by token")
    def post(self, request):
        token = (request.data.get("token") or "").strip()
        if token != getattr(settings, "ASYNC_SHARED_TOKEN", ""):
            return Response(status=403)
        try:
            order_id = int(request.data.get("order_id"))
        except (TypeError, ValueError):
            return Response({"detail": "order_id must be int"}, status=400)
        order = get_object_or_404(Months_calculation, pk=order_id)
        if order.status != "submitted":
            return Response({"detail": "Only submitted orders are allowed"}, status=409)
        items_payload = []
        qs = Month_indicators.objects.select_related("service").filter(order=order)
        for item in qs:
            s = item.service
            # сериализуем Decimal как строки, int как int; null поддерживаем как None
            items_payload.append({
                "base_yield": str(s.base_yield) if s.base_yield is not None else None,
                "ideal_temp": str(s.ideal_temp) if s.ideal_temp is not None else None,
                "ideal_precip": int(s.ideal_precip) if s.ideal_precip is not None else None,
                "avg_temp": str(item.avg_temp) if item.avg_temp is not None else None,
                "sum_precipitation": str(item.sum_precipitation) if item.sum_precipitation is not None else None,
            })
        return Response({
            "order_id": order.id,
            "items": items_payload,
        })


class AsyncResultCallbackView(APIView):
    permission_classes = [AllowAny]
    @swagger_auto_schema(operation_description="Receive async compute result by token")
    def post(self, request):
        token = (request.data.get("token") or "").strip()
        if token != getattr(settings, "ASYNC_SHARED_TOKEN", ""):
            return Response(status=403)
        try:
            order_id = int(request.data.get("order_id"))
        except (TypeError, ValueError):
            return Response({"detail": "order_id must be int"}, status=400)
        result_value_raw = request.data.get("result_value")
        if result_value_raw is None:
            return Response({"detail": "result_value is required"}, status=400)
        try:
            result_value = Decimal(str(result_value_raw))
        except Exception:
            return Response({"detail": "result_value must be number/decimal"}, status=400)
        order = get_object_or_404(Months_calculation, pk=order_id)
        if order.status != "submitted":
            return Response({"detail": "Invalid order status for result"}, status=409)
        order.result_value = result_value
        order.finished_at = timezone.now()
        order.status = "finished"
        order.save(update_fields=["result_value", "finished_at", "status"])
        return Response(MonthsCalculationDetailSerializer(order).data)


from django.contrib.auth import authenticate, login, logout
from services.models import CustomUser


@swagger_auto_schema(method='post', request_body=LoginSerializer)
@csrf_exempt  # TEMP: отключаем CSRF для диагностики
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"]
    password = serializer.validated_data["password"]
    user = authenticate(request, email=email, password=password)
    if user is None:
        return Response({"detail": "Invalid credentials"}, status=400)
    login(request, user)
    return Response({"status": "ok"}, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@csrf_protect
def logout_view(request):
    logout(request._request)
    return Response({"status": "Success"})


class MeView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response(status=401)
        data = {
            "email": request.user.email or "",
            "first_name": getattr(request.user, "first_name", "") or "",
            "last_name": getattr(request.user, "last_name", "") or "",
            "is_staff": bool(getattr(request.user, "is_staff", False)),
            "is_superuser": bool(getattr(request.user, "is_superuser", False)),
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
            "email": request.user.email or "",
            "first_name": getattr(request.user, "first_name", "") or "",
            "last_name": getattr(request.user, "last_name", "") or "",
            "is_staff": bool(getattr(request.user, "is_staff", False)),
            "is_superuser": bool(getattr(request.user, "is_superuser", False)),
        })


@api_view(["GET"])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_view(request):
    return JsonResponse({"status": "ok"})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(request_body=ChangePasswordSerializer)
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]
        if not request.user.check_password(old_password):
            return Response({"detail": "Invalid old password"}, status=400)
        request.user.set_password(new_password)
        request.user.save()
        return Response({"status": "ok"}, status=200)
from rest_framework import viewsets
from .permissions import IsManager, IsAdmin

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if getattr(self, 'action', None) in ['create']:
            permission_classes = [AllowAny]
        elif getattr(self, 'action', None) in ['list']:
            permission_classes = [IsAdmin | IsManager]
        else:
            permission_classes = [IsAdmin]
        return [perm() for perm in permission_classes]

    @swagger_auto_schema(request_body=UserSerializer)
    def create(self, request):
        if CustomUser.objects.filter(email=request.data.get('email')).exists():
            return Response({'status': 'Exist'}, status=400)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            CustomUser.objects.create_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                is_superuser=serializer.validated_data.get('is_superuser', False),
                is_staff=serializer.validated_data.get('is_staff', False),
            )
            return Response({'status': 'Success'}, status=200)
        return Response({'status': 'Error', 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

