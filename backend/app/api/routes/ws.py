"""WebSocket endpoint for real-time summary status notifications."""

import asyncio
import json
import logging
import uuid

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jwt.exceptions import InvalidTokenError
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.db import engine
from app.core.redis import SUMMARY_CHANNEL_PREFIX, subscribe_summary
from app.models import Patient, TokenPayload, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


def _authenticate_ws(token: str) -> str | None:
    """Return the user-id string from *token*, or ``None`` on failure."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        return TokenPayload(**payload).sub
    except (InvalidTokenError, Exception):
        return None


def _can_access_patient(user_id: str, patient_id: uuid.UUID) -> bool:
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user or not user.is_active:
            return False
        patient = session.get(Patient, patient_id)
        if not patient:
            return False
        return bool(user.is_superuser or patient.owner_id == user.id)


def _get_summary_status(patient_id: uuid.UUID) -> str | None:
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        return patient.summary_status if patient else None


@router.websocket("/patients/{patient_id}/summary")
async def summary_ws(websocket: WebSocket, patient_id: uuid.UUID) -> None:
    """One-shot WebSocket: notifies the client when a patient's summary
    leaves the ``"processing"`` state, then closes."""

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = _authenticate_ws(token)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    can_access = await asyncio.to_thread(
        _can_access_patient, user_id, patient_id
    )
    if not can_access:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    r, pubsub = await subscribe_summary(str(patient_id))
    try:
        # Race-condition guard: check DB *after* subscribing so we never
        # miss a publish that happened between the client's last REST
        # response and the subscription being active.
        current = await asyncio.to_thread(_get_summary_status, patient_id)
        if current and current != "processing":
            await websocket.send_json({"status": current})
            return

        async def _listen_redis() -> None:
            while True:
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=5.0
                )
                if msg and msg["type"] == "message":
                    data = json.loads(msg["data"])
                    await websocket.send_json(data)
                    return

        async def _listen_disconnect() -> None:
            try:
                await websocket.receive()
            except WebSocketDisconnect:
                pass

        redis_task = asyncio.create_task(_listen_redis())
        disconnect_task = asyncio.create_task(_listen_disconnect())

        done, pending = await asyncio.wait(
            [redis_task, disconnect_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        for task in done:
            if task.exception():
                logger.error(
                    "summary_ws error for patient %s", patient_id,
                    exc_info=task.exception(),
                )
    except WebSocketDisconnect:
        pass
    finally:
        channel = f"{SUMMARY_CHANNEL_PREFIX}{patient_id}"
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await r.aclose()
