import os


def minio(request):
    base = (os.getenv("MINIO_PUBLIC_BASE_URL") or "http://localhost:9000").rstrip("/")
    media_bucket = os.getenv("MINIO_MEDIA_BUCKET") or os.getenv("MINIO_BUCKET") or "apple-media"
    static_bucket = os.getenv("MINIO_STATIC_BUCKET") or "apple-static"

    return {
        "MINIO_BASE_URL": base,
        "MINIO_MEDIA_BUCKET": media_bucket,
        "MINIO_STATIC_BUCKET": static_bucket,
        "MINIO_MEDIA_BASE": f"{base}/{media_bucket}",
        "MINIO_STATIC_BASE": f"{base}/{static_bucket}",
    }


