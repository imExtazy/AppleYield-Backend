from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.http import Http404, HttpResponseNotAllowed
from django.db import connection
from django.contrib.auth.models import User
from .models import Service, Order, OrderService


def _get_or_create_demo_user() -> User:
    user, _ = User.objects.get_or_create(username="demo", defaults={"email": "demo@example.com"})
    return user


def _get_current_draft_order_for_demo():
    demo = _get_or_create_demo_user()
    return Order.objects.filter(created_by=demo, status="draft").first()


def _get_current_draft_order_for_request(request):
    user = request.user if getattr(request, "user", None) and request.user.is_authenticated else _get_or_create_demo_user()
    return Order.objects.filter(created_by=user, status="draft").first()


def months_list_view(request):
    q = (request.GET.get("q") or "").strip()
    qs = Service.objects.filter(status="active")
    if q:
        qs = qs.filter(name__istartswith=q)

    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "apple-media")
    base = getattr(settings, "AWS_S3_ENDPOINT_URL", "http://localhost:9000").rstrip("/")
    services = []
    for s in qs:
        image_key = s.image_key or "placeholder.png"
        services.append({
            "id": s.id,
            "name": s.name,
            "main_value": s.main_value,
            "image_url": f"{base}/{bucket}/{image_key}",
        })

    draft = _get_current_draft_order_for_request(request)
    positions_count = OrderService.objects.filter(order=draft).count() if draft else 0

    context = {
        "services": services,
        "q": request.GET.get("q", ""),
        "calculation_positions_count": positions_count,
        "current_calculation_id": draft.id if draft else None,
    }
    return render(request, "services/months_list.html", context)


def month_detail_view(request, id: int):
    s = get_object_or_404(Service, pk=id, status="active")
    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "apple-media")
    base = getattr(settings, "AWS_S3_ENDPOINT_URL", "http://localhost:9000").rstrip("/")
    image_key = s.image_key or "placeholder.png"
    service = {
        "id": s.id,
        "name": s.name,
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
    order = get_object_or_404(Order, pk=id)
    if order.status == "deleted":
        raise Http404("Application not found")

    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "apple-media")
    base = getattr(settings, "AWS_S3_ENDPOINT_URL", "http://localhost:9000").rstrip("/")
    positions = []
    for pos in OrderService.objects.select_related("service").filter(order=order):
        s = pos.service
        image_key = s.image_key or "placeholder.png"
        positions.append({
            "service": {
                "id": s.id,
                "name": s.name,
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
        "locations": getattr(Order, "LOCATIONS", []),
        "persons": getattr(Order, "PERSONS", []),
    }
    return render(request, "services/months_calculation.html", context)


def add_to_calculation_view(request, id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    demo = _get_or_create_demo_user()
    order = Order.objects.filter(created_by=demo, status="draft").first()
    if not order:
        order = Order.objects.create(created_by=demo, status="draft")

    service = get_object_or_404(Service, pk=id, status="active")
    OrderService.objects.get_or_create(
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
            "UPDATE services_order SET status=%s WHERE id=%s AND status <> %s",
            ["deleted", id, "deleted"],
        )
    return redirect("months_list")

# Create your views here.
