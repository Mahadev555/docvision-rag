"""Cloudinary storage — uploads extracted images and returns their CDN URL.

The Cloudinary SDK is synchronous, so calls are offloaded to a thread via
``asyncio.to_thread`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import cloudinary
import cloudinary.api
import cloudinary.uploader

from app.config import settings
from app.logger import get_logger
from app.utils.retry import async_retry

logger = get_logger("storage_service")


@dataclass(slots=True)
class UploadResult:
    public_id: str
    secure_url: str


class StorageService:
    """Upload/delete image assets on Cloudinary."""

    def __init__(self) -> None:
        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            secure=True,
        )
        self._folder = settings.cloudinary_folder

    @async_retry(max_attempts=4)
    async def upload_image(
        self, image_bytes: bytes, public_id: str, folder: str
    ) -> UploadResult | None:
        try:
            resp = await asyncio.to_thread(
                cloudinary.uploader.upload,
                image_bytes,
                public_id=public_id,
                folder=f"{self._folder}/{folder}",
                resource_type="image",
                overwrite=True,
                unique_filename=False,
            )
        except Exception as exc:  # noqa: BLE001 - never fail ingestion on a CDN error
            logger.warning("cloudinary upload failed for %s: %s", public_id, exc)
            return None
        return UploadResult(public_id=resp["public_id"], secure_url=resp["secure_url"])

    async def delete_folder(self, folder: str) -> None:
        prefix = f"{self._folder}/{folder}"
        try:
            await asyncio.to_thread(cloudinary.api.delete_resources_by_prefix, prefix)
            await asyncio.to_thread(cloudinary.api.delete_folder, prefix)
        except Exception as exc:  # noqa: BLE001
            logger.warning("cloudinary delete_folder failed for %s: %s", prefix, exc)
