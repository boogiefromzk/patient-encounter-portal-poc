"""Redis pub/sub utilities for real-time summary status notifications."""

import json
import logging
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

SUMMARY_CHANNEL_PREFIX = "patient:summary:"


def _redis_url() -> str:
    return settings.CELERY_BROKER_URL


def publish_summary_update(patient_id: str, status: str) -> None:
    """Publish a summary status change (sync — intended for Celery workers)."""
    channel = f"{SUMMARY_CHANNEL_PREFIX}{patient_id}"
    try:
        r = redis.from_url(_redis_url())
        r.publish(channel, json.dumps({"status": status}))
        r.close()
    except Exception:
        logger.exception(
            "Failed to publish summary update for patient %s", patient_id
        )


async def subscribe_summary(patient_id: str) -> tuple[Any, Any]:
    """Create an async Redis pub/sub subscription for a patient's summary channel.

    Returns ``(redis_client, pubsub)`` — caller must clean up both.
    """
    import redis.asyncio as aioredis

    channel = f"{SUMMARY_CHANNEL_PREFIX}{patient_id}"
    r = aioredis.from_url(_redis_url())
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)
    return r, pubsub
