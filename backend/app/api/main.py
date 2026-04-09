from fastapi import APIRouter

from app.api.routes import login, patients, private, transcripts, users, utils, ws
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(patients.router)
api_router.include_router(transcripts.router)
api_router.include_router(ws.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
