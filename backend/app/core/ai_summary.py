"""Generate AI clinical summaries for patients using the Anthropic API."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlmodel import Session, col, select

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.db import engine
from app.core.redis import publish_summary_update
from app.models import EncounterTranscript, Patient

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = (
    "You are a clinical summarization assistant. Based on the patient "
    "information provided, produce a structured summary covering each of "
    "the required categories.\n\n"
    "Write in concise clinical language. Format each category with the "
    "category name as a bold Markdown header (e.g. **Category Name**), "
    "followed by the relevant findings as a short paragraph or bullet "
    "points.\n\n"
    "If no information is available for a category in the provided data, "
    'write "Not documented." for that category.'
)

SUMMARY_CATEGORIES = (
    "1. **Patient identity / demographics**\n"
    "2. **Body measurements**\n"
    "3. **Primary diagnoses / chief conditions**\n"
    "4. **Allergies**\n"
    "5. **Current medications / medication risk**\n"
    "6. **Vital signs**\n"
    "7. **Mobility / assistive devices / functional status**\n"
    "8. **Skin / wound status**\n"
    "9. **Risk factors / comorbidity context**\n"
    "10. **Active treatment plan / care needs**"
)


def _build_prompt(
    patient: Patient,
    transcripts: list[EncounterTranscript],
    *,
    include_medical_history: bool = True,
) -> str:
    sections: list[str] = [f"## Patient: {patient.title}"]

    if include_medical_history:
        sections.append(
            f"### Medical History\n{patient.description or 'Not recorded.'}"
        )

    if patient.summary:
        sections.append(f"### Previous Summary\n{patient.summary}")

    transcript_entries: list[str] = []
    for t in transcripts:
        transcript_entries.append(f"**Date: {t.encounter_date}**\n{t.text}")

    transcripts_text = (
        "\n\n---\n\n".join(transcript_entries)
        if transcript_entries
        else "No encounter transcripts recorded."
    )
    sections.append(f"### Encounter Transcripts\n{transcripts_text}")

    sections.append(
        "Based on ALL of the above information, generate a structured "
        "clinical summary covering EACH of these categories:\n\n"
        + SUMMARY_CATEGORIES
    )

    return "\n\n".join(sections)


def _set_summary_status_and_commit(
    session: Session, patient_id: uuid.UUID, status: str
) -> None:
    """Set summary_status and immediately commit, then notify via pub/sub."""
    patient = session.get(Patient, patient_id)
    if patient:
        patient.summary_status = status
        session.add(patient)
        session.commit()
        publish_summary_update(str(patient_id), status)


def mark_summary_processing(
    session: Session, patient_id: uuid.UUID
) -> None:
    """Set status to processing within the caller's transaction (does NOT commit)."""
    patient = session.get(Patient, patient_id)
    if patient:
        patient.summary_status = "processing"
        session.add(patient)


@celery_app.task(
    name="generate_summary",
    rate_limit="10/m",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    max_retries=3,
)
def generate_summary_task(
    patient_id: str,
    description_changed: bool = False,
) -> None:
    """Celery task: generate an AI clinical summary.

    Uses its own DB session.  On success the status is set to
    ``"completed"``; on final failure it becomes ``"failed"``.
    Celery serialises ``patient_id`` as a string (JSON), so we
    convert it back to a UUID here.
    """
    pid = uuid.UUID(patient_id)

    if not settings.ANTHROPIC_API_KEY or anthropic is None:
        return

    with Session(engine) as session:
        try:
            patient = session.get(Patient, pid)
            if not patient:
                return

            has_prior_summary = patient.summary_updated_at is not None

            stmt = select(EncounterTranscript).where(
                EncounterTranscript.patient_id == pid
            )
            if has_prior_summary:
                cutoff = patient.summary_updated_at
                stmt = stmt.where(
                    or_(
                        col(EncounterTranscript.created_at) > cutoff,
                        col(EncounterTranscript.updated_at) > cutoff,
                    )
                )
            stmt = stmt.order_by(col(EncounterTranscript.created_at).asc())
            transcripts = list(session.exec(stmt).all())

            if not has_prior_summary:
                if not transcripts and not patient.description:
                    _set_summary_status_and_commit(session, pid, "failed")
                    return
            elif not description_changed and not transcripts:
                _set_summary_status_and_commit(session, pid, "failed")
                return

            prompt = _build_prompt(
                patient,
                transcripts,
                include_medical_history=not has_prior_summary or description_changed,
            )

            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=2000,
                system=SUMMARY_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            summary_text: str = message.content[0].text  # type: ignore[union-attr]

            patient.summary = summary_text
            patient.summary_status = "completed"
            patient.summary_updated_at = datetime.now(timezone.utc)
            session.add(patient)
            session.commit()
            publish_summary_update(patient_id, "completed")
        except Exception:
            logger.exception(
                "Failed to generate AI summary for patient %s", pid
            )
            session.rollback()
            with Session(engine) as err_session:
                _set_summary_status_and_commit(err_session, pid, "failed")
            raise
