import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlmodel import Session, col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.ai_summary import generate_summary_task, mark_summary_processing

logger = logging.getLogger(__name__)
from app.models import (
    EncounterTranscript,
    EncounterTranscriptCreate,
    EncounterTranscriptPublic,
    EncounterTranscriptsPublic,
    EncounterTranscriptUpdate,
    Message,
    Patient,
    User,
    UserPublic,
)

router = APIRouter(prefix="/patients/{patient_id}/transcripts", tags=["transcripts"])


def _get_patient_or_403(
    session: Session, current_user: User, patient_id: uuid.UUID
) -> Patient:
    patient = session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not current_user.is_superuser and patient.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return patient


def _transcript_to_public(
    transcript: EncounterTranscript,
    *,
    is_editable: bool = False,
) -> EncounterTranscriptPublic:
    created_by_public: UserPublic | None = None
    if transcript.created_by:
        created_by_public = UserPublic.model_validate(transcript.created_by)
    return EncounterTranscriptPublic.model_validate(
        transcript,
        update={"created_by": created_by_public, "is_editable": is_editable},
    )


@router.get("/", response_model=EncounterTranscriptsPublic)
def read_transcripts(
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID,
) -> Any:
    """List encounter transcripts for a patient."""
    _get_patient_or_403(session, current_user, patient_id)

    count_stmt = (
        select(func.count())
        .select_from(EncounterTranscript)
        .where(EncounterTranscript.patient_id == patient_id)
    )
    count = session.exec(count_stmt).one()

    stmt = (
        select(EncounterTranscript)
        .where(EncounterTranscript.patient_id == patient_id)
        .order_by(col(EncounterTranscript.created_at).desc())
    )
    transcripts = session.exec(stmt).all()

    result = []
    for i, t in enumerate(transcripts):
        is_editable = current_user.is_superuser or (
            i == 0 and t.created_by_id == current_user.id
        )
        result.append(_transcript_to_public(t, is_editable=is_editable))

    return EncounterTranscriptsPublic(data=result, count=count)


@router.post(
    "/",
    response_model=EncounterTranscriptPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_transcript(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID,
    transcript_in: EncounterTranscriptCreate,
) -> Any:
    """Add a new encounter transcript to a patient."""
    _get_patient_or_403(session, current_user, patient_id)

    transcript = EncounterTranscript.model_validate(
        transcript_in,
        update={"patient_id": patient_id, "created_by_id": current_user.id},
    )
    session.add(transcript)

    mark_summary_processing(session, patient_id)

    session.commit()
    session.refresh(transcript)

    try:
        generate_summary_task.delay(str(patient_id))
    except Exception:
        logger.exception("Failed to enqueue summary task for patient %s", patient_id)

    return _transcript_to_public(transcript, is_editable=True)


@router.put("/{transcript_id}", response_model=EncounterTranscriptPublic)
def update_transcript(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID,
    transcript_id: uuid.UUID,
    transcript_in: EncounterTranscriptUpdate,
) -> Any:
    """Update an encounter transcript (last only for non-admins)."""
    _get_patient_or_403(session, current_user, patient_id)

    transcript = session.get(EncounterTranscript, transcript_id)
    if not transcript or transcript.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Transcript not found")

    if not current_user.is_superuser:
        last_stmt = (
            select(EncounterTranscript.id)
            .where(EncounterTranscript.patient_id == patient_id)
            .order_by(col(EncounterTranscript.created_at).desc())
            .limit(1)
        )
        last_id = session.exec(last_stmt).first()
        if transcript.id != last_id:
            raise HTTPException(
                status_code=403,
                detail="Only the most recent transcript can be edited",
            )
        if transcript.created_by_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only the author can edit this transcript",
            )

    update_dict = transcript_in.model_dump(exclude_unset=True)
    transcript.sqlmodel_update(update_dict)
    transcript.updated_at = datetime.now(timezone.utc)
    session.add(transcript)

    mark_summary_processing(session, patient_id)

    session.commit()
    session.refresh(transcript)

    try:
        generate_summary_task.delay(str(patient_id))
    except Exception:
        logger.exception("Failed to enqueue summary task for patient %s", patient_id)

    return _transcript_to_public(transcript, is_editable=True)


@router.delete("/{transcript_id}")
def delete_transcript(
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID,
    transcript_id: uuid.UUID,
) -> Message:
    """Delete an encounter transcript (last only for non-admins)."""
    _get_patient_or_403(session, current_user, patient_id)

    transcript = session.get(EncounterTranscript, transcript_id)
    if not transcript or transcript.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Transcript not found")

    if not current_user.is_superuser:
        last_stmt = (
            select(EncounterTranscript.id)
            .where(EncounterTranscript.patient_id == patient_id)
            .order_by(col(EncounterTranscript.created_at).desc())
            .limit(1)
        )
        last_id = session.exec(last_stmt).first()
        if transcript.id != last_id:
            raise HTTPException(
                status_code=403,
                detail="Only the most recent transcript can be deleted",
            )
        if transcript.created_by_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only the author can delete this transcript",
            )

    session.delete(transcript)
    session.commit()
    return Message(message="Transcript deleted successfully")
