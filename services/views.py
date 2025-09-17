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


def list_view(request):
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

    draft = _get_current_draft_order_for_demo()
    positions_count = OrderService.objects.filter(order=draft).count() if draft else 0

    context = {
        "services": services,
        "q": request.GET.get("q", ""),
        "application_positions_count": positions_count,
        "current_application_id": draft.id if draft else None,
    }
    return render(request, "services/list.html", context)


def detail_view(request, id: int):
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
    draft = _get_current_draft_order_for_demo()
    positions_count = OrderService.objects.filter(order=draft).count() if draft else 0
    context = {
        "service": service,
        "application_positions_count": positions_count,
        "current_application_id": draft.id if draft else None,
    }
    return render(request, "services/detail.html", context)


def application_view(request, id: int):
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
        "application": {
            "id": order.id,
            "result": "",  # вычисление не требуется по ТЗ показа
            "location_person": (order.location or "") + (", " + order.person if order.person else ""),
            "location": order.location,
            "person": order.person,
        },
        "positions": positions,
        "application_positions_count": len(positions),
        "locations": getattr(Order, "LOCATIONS", []),
        "persons": getattr(Order, "PERSONS", []),
    }
    return render(request, "services/application.html", context)


def add_to_application_view(request, id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    demo = _get_or_create_demo_user()
    order = Order.objects.filter(created_by=demo, status="draft").first()
    if not order:
        order = Order.objects.create(created_by=demo, status="draft")

    # Возможное обновление полей заявки (селекты)
    location = request.POST.get("location")
    person = request.POST.get("person")
    updated_order = False
    if location:
        order.location = location
        updated_order = True
    if person:
        order.person = person
        updated_order = True
    if updated_order:
        order.save()

    # Detect batch fields like sum_precipitation_<service_id>, avg_temp_<service_id>, comment_<service_id>
    batch_ids = set()
    for key in request.POST.keys():
        if key.startswith("sum_precipitation_") or key.startswith("avg_temp_") or key.startswith("comment_"):
            try:
                sid = int(key.split("_", 1)[1])
                batch_ids.add(sid)
            except Exception:
                pass

    if batch_ids:
        for sid in batch_ids:
            service = get_object_or_404(Service, pk=sid, status="active")
            avg_temp = request.POST.get(f"avg_temp_{sid}")
            sum_precipitation = request.POST.get(f"sum_precipitation_{sid}")
            comment = request.POST.get(f"comment_{sid}")
            obj, created = OrderService.objects.get_or_create(order=order, service=service, defaults={
                "avg_temp": avg_temp or 0,
                "sum_precipitation": sum_precipitation or 0,
                "comment": comment or "",
            })
            if not created:
                if avg_temp is not None and avg_temp != "":
                    obj.avg_temp = avg_temp
                if sum_precipitation is not None and sum_precipitation != "":
                    obj.sum_precipitation = sum_precipitation
                if comment is not None:
                    obj.comment = comment
                obj.save()
    else:
        # Single-item mode (detail page button)
        service = get_object_or_404(Service, pk=id, status="active")
        avg_temp = request.POST.get("avg_temp")
        sum_precipitation = request.POST.get("sum_precipitation")
        comment = request.POST.get("comment")
        obj, created = OrderService.objects.get_or_create(order=order, service=service, defaults={
            "avg_temp": avg_temp or 0,
            "sum_precipitation": sum_precipitation or 0,
            "comment": comment or "",
        })
        if not created:
            obj.avg_temp = avg_temp or obj.avg_temp
            obj.sum_precipitation = sum_precipitation or obj.sum_precipitation
            obj.comment = comment or obj.comment
            obj.save()

    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("services_list")


def delete_application_view(request, id: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE services_order SET status=%s WHERE id=%s AND status <> %s",
            ["deleted", id, "deleted"],
        )
    return redirect("services_list")

# Create your views here.
