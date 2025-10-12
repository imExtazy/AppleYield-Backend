import os
import uuid
import re
from django.core.files.storage import default_storage


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "file"


def generate_image_key(name: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    ext = ext or ".jpg"
    return f"{slugify(name)}-{uuid.uuid4().hex}{ext}"


def delete_object_if_exists(key: str) -> None:
    if not key:
        return
    try:
        if default_storage.exists(key):
            default_storage.delete(key)
    except Exception:
        # умышленно подавляем: удаление best-effort
        pass


