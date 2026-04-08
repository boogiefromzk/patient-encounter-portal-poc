"""Generate AI clinical summaries for patients using the Anthropic API."""

import logging
import uuid
from datetime import datetime, timezone

from sqlmodel import Session, col, select

from app.core.config import settings
from app.models import EncounterTranscript, Item

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


def _build_prompt(item: Item, transcripts: list[EncounterTranscript]) -> str:
    sections: list[str] = [f"## Patient: {item.title}"]

    sections.append(
        f"### Medical History\n{item.description or 'Not recorded.'}"
    )

    if item.summary:
        sections.append(f"### Previous Summary\n{item.summary}")

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


def generate_and_save_summary(session: Session, item_id: uuid.UUID) -> None:
    """Generate an AI clinical summary for a patient and persist it.

    Silently returns if the API key is missing or the call fails so that
    the caller's main transaction (e.g. saving a transcript) is never
    affected.
    """
    if not settings.ANTHROPIC_API_KEY or anthropic is None:
        return

    try:
        item = session.get(Item, item_id)
        if not item:
            return

        stmt = (
            select(EncounterTranscript)
            .where(EncounterTranscript.item_id == item_id)
            .order_by(col(EncounterTranscript.created_at).asc())
        )
        transcripts = list(session.exec(stmt).all())

        if not transcripts and not item.description:
            return

        prompt = _build_prompt(item, transcripts)

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=SUMMARY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        summary_text: str = message.content[0].text  # type: ignore[union-attr]

        item.summary = summary_text
        item.summary_updated_at = datetime.now(timezone.utc)
        session.add(item)
        session.commit()
    except Exception:
        logger.exception("Failed to generate AI summary for item %s", item_id)
        session.rollback()
