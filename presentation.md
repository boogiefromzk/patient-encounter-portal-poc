# Patient Encounter Portal -- Code Walkthrough

## Architecture at a Glance

```
patient-encounter-portal-poc/
├── backend/          Python 3.10+ / FastAPI / SQLModel / Alembic
│   └── app/
│       ├── models.py              Data models (DB tables + API schemas)
│       ├── api/routes/items.py    Patient CRUD endpoints
│       ├── api/routes/transcripts.py  Encounter transcript endpoints
│       └── core/ai_summary.py     AI summary generation (Anthropic)
│
├── frontend/         React / Vite / TanStack Router + Query
│   └── src/
│       ├── routes/_layout/items_.$id.tsx   Patient detail page
│       ├── components/Items/EditItem.tsx    Edit patient dialog
│       └── components/Items/EncounterTranscripts.tsx  Transcript CRUD UI
│
└── compose.yml       Docker Compose (Postgres, backend, frontend, Traefik)
```

The frontend talks to the backend exclusively through a **generated OpenAPI client** (`frontend/src/client/sdk.gen.ts`), keeping the two sides in sync automatically.

---

## 1. Edit Simple Patient Data

A "patient" is an `Item` in the database. The core fields are **title** (patient name) and **description** (medical history).

### Data model

**`backend/app/models.py` lines 71--107**

```python
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)

class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, ...)
    description: str | None = Field(default=None, max_length=10000)

class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    description: str | None = Field(default=None, sa_type=Text())  # DB TEXT, no length cap
    owner_id: uuid.UUID = Field(foreign_key="user.id", ...)
    summary: str | None = Field(default=None, sa_type=Text())
    summary_updated_at: datetime | None = ...
    transcripts: list["EncounterTranscript"] = Relationship(...)
```

### API endpoint

**`backend/app/api/routes/items.py` lines 96--121** -- `PUT /api/v1/items/{id}`

```python
@router.put("/{id}", response_model=ItemPublic)
def update_item(*, session: SessionDep, current_user: CurrentUser,
                id: uuid.UUID, item_in: ItemUpdate) -> Any:
    item = session.get(Item, id)
    # ... 404 / 403 checks ...
    update_dict = item_in.model_dump(exclude_unset=True)
    item.sqlmodel_update(update_dict)
    session.add(item)
    session.commit()

    if "description" in update_dict:          # <-- triggers AI summary
        generate_and_save_summary(session, id)

    return item
```

Key behavior: `exclude_unset=True` means only the fields the client actually sends are updated -- partial updates are safe.

### Frontend form

**`frontend/src/components/Items/EditItem.tsx`**

A dialog form with two fields: **Full Name** (`title`) and **Medical History** (`description`). The form uses `react-hook-form` + Zod validation. On save it calls `ItemsService.updateItem` and invalidates the `["items"]` query cache so the UI refreshes.

---

## 2. Medical History -- Freeform Text, One Per Patient

The medical history is the `description` field on `Item`. It is stored as SQL `TEXT` (unlimited length at the DB level, validated to 10,000 chars at the API level).

### Where it lives

| Layer | File | What |
|-------|------|------|
| DB column | `backend/app/models.py:95` | `description: str \| None = Field(sa_type=Text())` |
| API validation | `backend/app/models.py:73` | `max_length=10000` on `ItemBase` |
| Migration | `alembic/versions/3f8a12c74b91_expand_item_description_to_text.py` | Altered column from `VARCHAR` to `TEXT` |
| Edit form | `frontend/src/components/Items/EditItem.tsx:117-133` | `<Textarea>` labeled "Medical History" |
| Detail view | `frontend/src/routes/_layout/items_.$id.tsx:111-126` | Card titled "Medical History" |

### How editing works

1. Admin clicks **Edit Patient** on the detail page (`items_.$id.tsx:79-84`) -- button only shown for superusers
2. Dialog opens with a `<Textarea>` pre-filled from `item.description`
3. On save: `PUT /api/v1/items/{id}` with `{ description: "..." }`
4. Backend saves to Postgres, then triggers AI summary regeneration

---

## 3. Encounter Transcripts -- Freeform Text, Many Per Patient

Transcripts are a **separate table** with a foreign key to the patient.

### Data model

**`backend/app/models.py` lines 131--174**

```python
class EncounterTranscript(EncounterTranscriptBase, table=True):
    __tablename__ = "encounter_transcript"
    id: uuid.UUID = ...
    text: str = Field(sa_type=Text())           # freeform encounter notes
    encounter_date: date = Field(sa_type=Date()) # when the visit happened
    item_id: uuid.UUID = Field(foreign_key="item.id", ...)
    created_by_id: uuid.UUID = Field(foreign_key="user.id", ...)
```

### API -- nested under the patient

**`backend/app/api/routes/transcripts.py`** -- prefix: `/api/v1/items/{item_id}/transcripts`

| Method | Path | What |
|--------|------|------|
| `GET /` | List all transcripts for a patient | Returns `is_editable` flag per transcript |
| `POST /` | Add a new transcript | Triggers AI summary regeneration |
| `PUT /{transcript_id}` | Update a transcript | Triggers AI summary regeneration |
| `DELETE /{transcript_id}` | Delete a transcript | Does **not** regenerate summary |

### Frontend

**`frontend/src/components/Items/EncounterTranscripts.tsx`**

- Renders a card with all transcripts, sorted newest-first
- Each transcript shows: date, author name, text, and an edit button (if `is_editable`)
- "Add Transcript" button opens a dialog with date picker + textarea
- After any mutation, invalidates both the transcript list and the patient detail (to pick up the new AI summary)

---

## 4. Preventing Users From Overriding Each Other's Data

The system uses **role-based access control** combined with **write-scope restrictions** on transcripts to prevent conflicts.

### Patient-level access (items)

**`backend/app/api/routes/items.py:110-111`**

```python
if not current_user.is_superuser and (item.owner_id != current_user.id):
    raise HTTPException(status_code=403, detail="Not enough permissions")
```

- Only **superusers** (admins) or the **assigned clinician** (`owner_id`) can edit a patient
- Only **superusers** can create patients or reassign ownership

### Transcript-level restrictions

**`backend/app/api/routes/transcripts.py:126-143`** (update) and **170-187** (delete):

```python
if not current_user.is_superuser:
    # Find the most recent transcript
    last_id = session.exec(
        select(EncounterTranscript.id)
        .where(EncounterTranscript.item_id == item_id)
        .order_by(col(EncounterTranscript.created_at).desc())
        .limit(1)
    ).first()

    if transcript.id != last_id:
        raise HTTPException(403, "Only the most recent transcript can be edited")
    if transcript.created_by_id != current_user.id:
        raise HTTPException(403, "Only the author can edit this transcript")
```

Three-layer protection:

1. **Patient ownership**: you must be the assigned clinician (or admin) to even see transcripts
2. **Recency rule**: non-admins can only edit/delete the **most recent** transcript -- older ones are locked
3. **Authorship rule**: only the person who wrote a transcript can modify it

The frontend reflects this with the `is_editable` flag computed server-side:

**`backend/app/api/routes/transcripts.py:72-77`**

```python
for i, t in enumerate(transcripts):
    is_editable = current_user.is_superuser or (
        i == 0 and t.created_by_id == current_user.id
    )
```

The edit button only appears in the UI when `is_editable` is `true` (`EncounterTranscripts.tsx:334`).

---

## 5. AI Summary Generation

When a clinician saves edits, the system generates a structured clinical summary using **Anthropic Claude** that can be read in the time it takes to walk from a car to a patient's front door.

### The generation pipeline

**`backend/app/core/ai_summary.py`**

```
       ┌─────────────────────────────────────────────────────┐
       │              generate_and_save_summary()             │
       │                                                      │
       │  1. Load patient (Item) from DB                      │
       │  2. Load all encounter transcripts, ordered by date  │
       │  3. Build prompt from:                               │
       │     - Patient name                                   │
       │     - Medical history (item.description)             │
       │     - Previous summary (if exists)                   │
       │     - All encounter transcripts (date + text)        │
       │  4. Call Anthropic API (claude-sonnet-4-20250514)    │
       │  5. Save summary + timestamp back to Item            │
       └─────────────────────────────────────────────────────┘
```

### The prompt structure

**`backend/app/core/ai_summary.py:45-72`** -- `_build_prompt()`

```
## Patient: {name}

### Medical History
{description or "Not recorded."}

### Previous Summary
{existing summary, if any}

### Encounter Transcripts
**Date: 2025-01-15**
{transcript text}
---
**Date: 2025-02-10**
{transcript text}

Generate a structured clinical summary covering EACH of these categories:
1. Patient identity / demographics
2. Body measurements
3. Primary diagnoses / chief conditions
4. Allergies
5. Current medications / medication risk
6. Vital signs
7. Mobility / assistive devices / functional status
8. Skin / wound status
9. Risk factors / comorbidity context
10. Active treatment plan / care needs
```

### System prompt

The model is instructed to write **concise clinical language** with bold Markdown headers for each category, and "Not documented." for missing information.

### Where summaries appear

**`frontend/src/routes/_layout/items_.$id.tsx:87-109`**

The patient detail page shows an **"AI Clinical Summary"** card at the top with the generated markdown and a "Last updated" timestamp. A custom `SimpleMarkdown` component renders bold text and line breaks.

---

## 6. When Summaries Are Triggered

Summary generation is **not** on-demand -- it fires **automatically after specific save operations**:

| Trigger | File | Line |
|---------|------|------|
| Patient description (medical history) updated | `items.py` | 118-119 |
| New transcript created | `transcripts.py` | 105 |
| Existing transcript updated | `transcripts.py` | 151 |
| Transcript deleted | `transcripts.py` | -- **not triggered** |

This means the summary is always up-to-date after any content change, without the user having to press a separate "generate" button.

---

## 7. Minimizing Costly Recomputation

AI API calls are expensive. The system avoids unnecessary calls through several mechanisms:

### a. Conditional triggering on item updates

**`backend/app/api/routes/items.py:118-119`**

```python
if "description" in update_dict:
    generate_and_save_summary(session, id)
```

The summary only regenerates when the `description` field is actually in the update payload. Changing just the patient name does not trigger a regeneration.

### b. Early exit when there is nothing to summarize

**`backend/app/core/ai_summary.py:97-98`**

```python
if not transcripts and not item.description:
    return
```

If a patient has no medical history and no transcripts, the API call is skipped entirely.

### c. Graceful degradation when no API key

**`backend/app/core/ai_summary.py:82-83`**

```python
if not settings.ANTHROPIC_API_KEY or anthropic is None:
    return
```

If the Anthropic key is not configured, summaries are silently skipped -- the rest of the application works normally.

### d. Persistent summary storage

The generated summary is stored directly on the `Item` table (`summary` + `summary_updated_at`). Subsequent reads of the patient detail page serve the **cached summary from Postgres** -- no AI call is needed to display it.

### e. Frontend query caching (TanStack Query)

The frontend caches API responses in-memory. After a mutation, only the affected query keys are invalidated:

```typescript
// After editing a transcript:
queryClient.invalidateQueries({ queryKey: ["items", itemId, "transcripts"] })
queryClient.invalidateQueries({ queryKey: ["items", itemId] })
```

This avoids refetching unrelated data.

### f. What is NOT yet implemented

- **Content hashing / dirty flags**: The system regenerates the summary on every qualifying save, even if the content did not actually change. A hash-based check could prevent redundant calls.
- **Optimistic concurrency control**: There is no row-version or ETag-based conflict detection. Two users editing simultaneously will result in last-write-wins. The role/authorship restrictions mitigate this in practice, but do not eliminate it.
- **Summary regeneration on transcript delete**: Deleting a transcript does not update the summary, which could leave stale information.

---

## Data Flow Summary

```
 Clinician                    Frontend                     Backend                    AI
    │                            │                            │                        │
    ├─ Edit medical history ────>│                            │                        │
    │                            ├── PUT /items/{id} ────────>│                        │
    │                            │   { description: "..." }   ├── save to Postgres     │
    │                            │                            ├── generate_and_save ──>│
    │                            │                            │   (medical history +    │
    │                            │                            │    all transcripts +    │
    │                            │                            │    previous summary)    │
    │                            │                            │<── structured summary ──┤
    │                            │                            ├── save summary to Item  │
    │                            │<── updated patient ────────┤                        │
    │<── UI refreshes ───────────┤                            │                        │
    │   (summary card updates)   │                            │                        │
    │                            │                            │                        │
    ├─ Add transcript ──────────>│                            │                        │
    │                            ├── POST /items/{id}/       >│                        │
    │                            │   transcripts              ├── save transcript      │
    │                            │                            ├── generate_and_save ──>│
    │                            │                            │<── structured summary ──┤
    │                            │                            ├── save summary to Item  │
    │                            │<── invalidate queries ─────┤                        │
    │<── UI refreshes ───────────┤                            │                        │
```

---

## Key Files Reference

| Feature | Backend | Frontend |
|---------|---------|----------|
| Data models | `backend/app/models.py` | `frontend/src/client/types.gen.ts` |
| Patient CRUD | `backend/app/api/routes/items.py` | `frontend/src/components/Items/EditItem.tsx` |
| Transcript CRUD | `backend/app/api/routes/transcripts.py` | `frontend/src/components/Items/EncounterTranscripts.tsx` |
| AI summaries | `backend/app/core/ai_summary.py` | `frontend/src/routes/_layout/items_.$id.tsx` |
| Auth / deps | `backend/app/api/deps.py` | `frontend/src/hooks/useAuth.ts` |
| Patient detail page | -- | `frontend/src/routes/_layout/items_.$id.tsx` |
| DB migrations | `backend/app/alembic/versions/` | -- |
| Generated API client | -- | `frontend/src/client/sdk.gen.ts` |
