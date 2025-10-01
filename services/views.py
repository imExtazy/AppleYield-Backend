from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.http import Http404, HttpResponseNotAllowed, HttpResponse
from django.db import connection
from django.contrib.auth.models import User
from .models import Months, Months_calculation, Month_indicators
from decimal import Decimal, ROUND_HALF_UP


def _get_or_create_demo_user() -> User:
    user, _ = User.objects.get_or_create(username="demo", defaults={"email": "demo@example.com"})
    return user


def _get_current_draft_order_for_demo():
    demo = _get_or_create_demo_user()
    return Months_calculation.objects.filter(created_by=demo, status="draft").first()


def _get_current_draft_order_for_request(request):
    user = request.user if getattr(request, "user", None) and request.user.is_authenticated else _get_or_create_demo_user()
    return Months_calculation.objects.filter(created_by=user, status="draft").first()


def calculate_application_yield_demo(order_id: int) -> Decimal:
    """
    Демонстрационный расчёт итоговой урожайности по заявке без интеграции.

    Алгоритм:
    - Для каждой позиции заявки берём базовую урожайность месяца (base_yield)
    - Считаем коэффициенты по температуре и осадкам как отношение фактических к идеальным
      (ограничивая сверху 1, нижняя граница не обрезается)
    - Вклад позиции = base_yield * temp_coef * precip_coef
    - Итог по заявке = сумма вкладов всех позиций
    - Возвращается Decimal, округлённый до 2 знаков (ROUND_HALF_UP)
    """
    order = Months_calculation.objects.get(pk=order_id)

    positions = Month_indicators.objects.select_related("service").filter(order=order)
    total = Decimal("0")
    has_positions = False

    for pos in positions:
        has_positions = True
        s = pos.service

        base = s.base_yield if s.base_yield is not None else Decimal("0")
        ideal_temp = s.ideal_temp
        ideal_precip = Decimal(s.ideal_precip)

        actual_temp = pos.avg_temp if pos.avg_temp is not None else ideal_temp
        actual_precip = pos.sum_precipitation if pos.sum_precipitation is not None else ideal_precip

        if ideal_temp == 0:
            if actual_temp == 0:
                temp_coef = Decimal("1")
            else:
                temp_coef = Decimal("1") / (Decimal(actual_temp) + 1)
        else:
            temp_coef = max(
                Decimal("0"), 
                Decimal("1") - abs(Decimal(actual_temp) - Decimal(ideal_temp)) / Decimal(ideal_temp))
            if temp_coef > 1:
                temp_coef = Decimal("1")

        if ideal_precip == 0:
            if actual_precip == 0:
                precip_coef = Decimal("1")
            else:
                precip_coef = Decimal("1") / (Decimal(actual_precip) + 1)
        else:
            precip_coef = max(
                Decimal("0"),
                Decimal("1") - abs(Decimal(actual_precip) - Decimal(ideal_precip)) / Decimal(ideal_precip)
            )
            if precip_coef > 1:
                precip_coef = Decimal("1")

        contribution = Decimal(base) * temp_coef * precip_coef
        total += contribution

    if not has_positions:
        return Decimal("0.00")

    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def months_list_view(request):
    q = (request.GET.get("q") or "").strip()
    qs = Months.objects.filter(status=True)
    if q:
        qs = qs.filter(month_name__istartswith=q)

    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "apple-media")
    base = getattr(settings, "AWS_S3_ENDPOINT_URL", "http://localhost:9000").rstrip("/")
    services = []
    for s in qs:
        image_key = s.month_image or "placeholder.png"
        services.append({
            "id": s.pk,
            "name": s.month_name,
            "main_value": s.main_value,
            "image_url": f"{base}/{bucket}/{image_key}",
        })

    # Корзина привязана к демо-пользователю (добавление идёт от demo)
    draft = _get_current_draft_order_for_demo()
    positions_count = Month_indicators.objects.filter(order=draft).count() if draft else 0

    context = {
        "services": services,
        "q": request.GET.get("q", ""),
        "calculation_positions_count": positions_count,
        "current_calculation_id": draft.id if draft else None,
    }
    return render(request, "services/months_list.html", context)


def month_detail_view(request, id: int):
    s = get_object_or_404(Months, pk=id, status=True)
    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "apple-media")
    base = getattr(settings, "AWS_S3_ENDPOINT_URL", "http://localhost:9000").rstrip("/")
    image_key = s.month_image or "placeholder.png"
    service = {
        "id": s.pk,
        "name": s.month_name,
        "description": s.description,
        "main_value": s.main_value,
        "stats": {
            "temperature": f"{s.temperature}",
            "precipitation": f"{s.precipitation} мм",
        },
        "image_url": f"{base}/{bucket}/{image_key}",
    }
    context = {
        "service": service,
    }
    return render(request, "services/month_detail.html", context)


def months_calculation_view(request, id: int):
    order = get_object_or_404(Months_calculation, pk=id)
    if order.status == "deleted":
        raise Http404("Application not found")

    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "apple-media")
    base = getattr(settings, "AWS_S3_ENDPOINT_URL", "http://localhost:9000").rstrip("/")
    positions = []
    for pos in Month_indicators.objects.select_related("service").filter(order=order):
        s = pos.service
        image_key = s.month_image or "placeholder.png"
        positions.append({
            "service": {
                "id": s.pk,
                "name": s.month_name,
                "main_value": s.main_value,
                "image_url": f"{base}/{bucket}/{image_key}",
            },
            "comment": pos.comment,
            "sum_precipitation": pos.sum_precipitation,
            "avg_temp": pos.avg_temp,
        })

    context = {
        "calculation": {
            "id": order.id,
            "result": "",
            "location_person": (order.location or "") + (", " + order.person if order.person else ""),
            "location": order.location,
            "person": order.person,
        },
        "positions": positions,
        "calculation_positions_count": len(positions),
        "locations": getattr(Months_calculation, "LOCATIONS", []),
        "persons": getattr(Months_calculation, "PERSONS", []),
    }
    return render(request, "services/months_calculation.html", context)


def add_to_calculation_view(request, id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    demo = _get_or_create_demo_user()
    order = Months_calculation.objects.filter(created_by=demo, status="draft").first()
    if not order:
        order = Months_calculation.objects.create(created_by=demo, status="draft")

    service = get_object_or_404(Months, pk=id, status=True)
    Month_indicators.objects.get_or_create(
        order=order,
        service=service,
        defaults={
            "avg_temp": 0,
            "sum_precipitation": 0,
            "comment": "",
        },
    )
    return redirect("months_list")


def delete_calculation_view(request, id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE services_months_calculation SET status=%s WHERE id=%s AND status <> %s",
            ["deleted", id, "deleted"],
        )
    return redirect("months_list")

# Create your views here.
