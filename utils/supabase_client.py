import os
import uuid
from typing import Optional

import httpx
from slugify import slugify
from fastapi import UploadFile

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # <-- NUEVO
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "sleep-uploads")


def _build_public_url(path: str) -> str:
    # Para bucket Public
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{path}"


def _auth_key() -> str:
    # Prefiere Service Role si está disponible (permite escritura sin políticas extra)
    return SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY or ""


async def upload_file(file: UploadFile, path_prefix: Optional[str] = None) -> str:
    if not SUPABASE_URL or not _auth_key() or not SUPABASE_BUCKET:
        raise RuntimeError("Supabase storage no configurado (URL/KEY/BUCKET)")

    filename = file.filename or "upload"
    safe_name = slugify(filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    path = f"{path_prefix.rstrip('/')}/{unique_name}" if path_prefix else unique_name

    storage_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{path}"
    headers = {
        "Authorization": f"Bearer {_auth_key()}",
        "apikey": _auth_key(),
        "Content-Type": file.content_type or "application/octet-stream",
        "x-upsert": "true",
    }

    content = await file.read()

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.put(storage_url, headers=headers, content=content)

    if resp.status_code >= 400:
        # Mensaje explícito (403: permisos / 404: bucket / 413: tamaño)
        raise RuntimeError(f"Supabase error {resp.status_code}: {resp.text}")

    return _build_public_url(path)
