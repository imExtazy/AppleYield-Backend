from django.shortcuts import render
from django.conf import settings
from django.http import Http404
from .data import SERVICES, APPLICATIONS


def _get_application_positions_count(application_id: int) -> int:
    application = APPLICATIONS.get(application_id)
    if not application:
        return 0
    items = application.get("items", [])
    return len(items)


def list_view(request):
    q = (request.GET.get("q") or "").strip().lower()
    services = SERVICES
    if q:
        def matches(s):
            return (s.get("name", "").lower()).startswith(q)
        services = [s for s in SERVICES if matches(s)]

    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "media")
    base = getattr(settings, "AWS_S3_ENDPOINT_URL", "http://localhost:9000").rstrip("/")
    def with_image_url(s):
        image_key = s.get("image_key") or "placeholder.png"
        s = dict(s)
        s["image_url"] = f"{base}/{bucket}/{image_key}"
        return s
    services = [with_image_url(s) for s in services]

    context = {
        "services": services,
        "q": request.GET.get("q", ""),
        "application_positions_count": _get_application_positions_count(1),
    }
    return render(request, "services/list.html", context)


def detail_view(request, id: int):
    service = next((s for s in SERVICES if s["id"] == id), None)
    if not service:
        raise Http404("Service not found")
    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "media")
    base = getattr(settings, "AWS_S3_ENDPOINT_URL", "http://localhost:9000").rstrip("/")
    image_key = service.get("image_key") or "placeholder.png"
    service = dict(service)
    service["image_url"] = f"{base}/{bucket}/{image_key}"
    context = {
        "service": service,
        "application_positions_count": _get_application_positions_count(1),
    }
    return render(request, "services/detail.html", context)


def application_view(request, id: int):
    application = APPLICATIONS.get(id)
    if not application:
        raise Http404("Application not found")
    positions = []
    for item in application.get("items", []):
        service = next((s for s in SERVICES if s["id"] == item["service_id"]), None)
        if not service:
            continue
        bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "apple-media")
        base = getattr(settings, "AWS_S3_ENDPOINT_URL", "http://localhost:9000").rstrip("/")
        image_key = (service.get("image_key") or "placeholder.png")
        service_with_image = dict(service)
        service_with_image["image_url"] = f"{base}/{bucket}/{image_key}"

        positions.append({
            "service": service_with_image,
            "comment": item.get("comment"),
            "sum_precipitation": item.get("sum_precipitation", ""),
            "avg_temp": item.get("avg_temp", ""),
        })

    context = {
        "application": {
            "id": application["id"],
            "result": application.get("result", ""),
            "location_person": application.get("location_person", ""),
        },
        "positions": positions,
        "application_positions_count": len(positions),
    }
    return render(request, "services/application.html", context)

# Create your views here.
