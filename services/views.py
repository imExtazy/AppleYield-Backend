from django.shortcuts import render
from django.conf import settings
from django.http import Http404
from .data import MONTHS, MONTHS_CALCULATIONS


def _get_calculation_positions_count(calculation_id: int) -> int:
    calculation = MONTHS_CALCULATIONS.get(calculation_id)
    if not calculation:
        return 0
    items = calculation.get("items", [])
    return len(items)


def months_list_view(request):
    q = (request.GET.get("q") or "").strip().lower()
    services = MONTHS
    if q:
        def matches(s):
            return (s.get("name", "").lower()).startswith(q)
        services = [s for s in MONTHS if matches(s)]

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
        "calculation_positions_count": _get_calculation_positions_count(1),
        "current_calculation_id": 1,
    }
    return render(request, "services/months_list.html", context)


def month_detail_view(request, id: int):
    service = next((s for s in MONTHS if s["id"] == id), None)
    if not service:
        raise Http404("Service not found")
    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "media")
    base = getattr(settings, "AWS_S3_ENDPOINT_URL", "http://localhost:9000").rstrip("/")
    image_key = service.get("image_key") or "placeholder.png"
    service = dict(service)
    service["image_url"] = f"{base}/{bucket}/{image_key}"
    context = {
        "service": service,
        "calculation_positions_count": _get_calculation_positions_count(1),
    }
    return render(request, "services/month_detail.html", context)


def months_calculation_view(request, id: int):
    calculation = MONTHS_CALCULATIONS.get(id)
    if not calculation:
        raise Http404("Calculation not found")
    positions = []
    for item in calculation.get("items", []):
        service = next((s for s in MONTHS if s["id"] == item["service_id"]), None)
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
        "calculation": {
            "id": calculation["id"],
            "result": calculation.get("result", ""),
            "location_person": calculation.get("location_person", ""),
        },
        "positions": positions,
        "calculation_positions_count": len(positions),
    }
    return render(request, "services/months_calculation.html", context)

# Create your views here.
