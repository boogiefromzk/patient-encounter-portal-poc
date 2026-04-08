import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlmodel import Session, col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    EncounterTranscript,
    EncounterTranscriptCreate,
    EncounterTranscriptPublic,
    EncounterTranscriptsPublic,
    EncounterTranscriptUpdate,
    Item,
    Message,
    User,
    UserPublic,
)

router = APIRouter(prefix="/items/{item_id}/transcripts", tags=["transcripts"])


def _get_item_or_403(
    session: Session, current_user: User, item_id: uuid.UUID
) -> Item:
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not current_user.is_superuser and item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return item


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
    item_id: uuid.UUID,
) -> Any:
    """List encounter transcripts for a patient."""
    _get_item_or_403(session, current_user, item_id)

    count_stmt = (
        select(func.count())
        .select_from(EncounterTranscript)
        .where(EncounterTranscript.item_id == item_id)
    )
    count = session.exec(count_stmt).one()

    stmt = (
        select(EncounterTranscript)
        .where(EncounterTranscript.item_id == item_id)
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
    item_id: uuid.UUID,
    transcript_in: EncounterTranscriptCreate,
) -> Any:
    """Add a new encounter transcript to a patient."""
    _get_item_or_403(session, current_user, item_id)

    transcript = EncounterTranscript.model_validate(
        transcript_in,
        update={"item_id": item_id, "created_by_id": current_user.id},
    )
    session.add(transcript)
    session.commit()
    session.refresh(transcript)
    return _transcript_to_public(transcript, is_editable=True)


@router.put("/{transcript_id}", response_model=EncounterTranscriptPublic)
def update_transcript(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    item_id: uuid.UUID,
    transcript_id: uuid.UUID,
    transcript_in: EncounterTranscriptUpdate,
) -> Any:
    """Update an encounter transcript (last only for non-admins)."""
    _get_item_or_403(session, current_user, item_id)

    transcript = session.get(EncounterTranscript, transcript_id)
    if not transcript or transcript.item_id != item_id:
        raise HTTPException(status_code=404, detail="Transcript not found")

    if not current_user.is_superuser:
        last_stmt = (
            select(EncounterTranscript.id)
            .where(EncounterTranscript.item_id == item_id)
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
    session.add(transcript)
    session.commit()
    session.refresh(transcript)
    return _transcript_to_public(transcript, is_editable=True)


@router.delete("/{transcript_id}")
def delete_transcript(
    session: SessionDep,
    current_user: CurrentUser,
    item_id: uuid.UUID,
    transcript_id: uuid.UUID,
) -> Message:
    """Delete an encounter transcript (last only for non-admins)."""
    _get_item_or_403(session, current_user, item_id)

    transcript = session.get(EncounterTranscript, transcript_id)
    if not transcript or transcript.item_id != item_id:
        raise HTTPException(status_code=404, detail="Transcript not found")

    if not current_user.is_superuser:
        last_stmt = (
            select(EncounterTranscript.id)
            .where(EncounterTranscript.item_id == item_id)
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
