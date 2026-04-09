import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.ai_summary import generate_summary_task

logger = logging.getLogger(__name__)
from app.models import (
    Message,
    Patient,
    PatientAssignOwner,
    PatientCreate,
    PatientPublic,
    PatientsPublic,
    PatientUpdate,
    User,
    UserPublic,
)

router = APIRouter(prefix="/patients", tags=["patients"])


def _patient_to_public(patient: Patient, include_owner: bool = False) -> PatientPublic:
    owner_public: UserPublic | None = None
    if include_owner and patient.owner:
        owner_public = UserPublic.model_validate(patient.owner)
    return PatientPublic.model_validate(patient, update={"owner": owner_public})


@router.get("/", response_model=PatientsPublic)
def read_patients(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve patients. Superusers see all patients with owner info.
    """

    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(Patient)
        count = session.exec(count_statement).one()
        statement = (
            select(Patient).order_by(col(Patient.created_at).desc()).offset(skip).limit(limit)
        )
        patients = session.exec(statement).all()
        patients_public = [_patient_to_public(p, include_owner=True) for p in patients]
    else:
        count_statement = (
            select(func.count())
            .select_from(Patient)
            .where(Patient.owner_id == current_user.id)
        )
        count = session.exec(count_statement).one()
        statement = (
            select(Patient)
            .where(Patient.owner_id == current_user.id)
            .order_by(col(Patient.created_at).desc())
            .offset(skip)
            .limit(limit)
        )
        patients = session.exec(statement).all()
        patients_public = [_patient_to_public(p) for p in patients]

    return PatientsPublic(data=patients_public, count=count)


@router.get("/{id}", response_model=PatientPublic)
def read_patient(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get patient by ID.
    """
    patient = session.get(Patient, id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not current_user.is_superuser and (patient.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return _patient_to_public(patient, include_owner=True)


@router.post("/", response_model=PatientPublic)
def create_patient(
    *, session: SessionDep, current_user: CurrentUser, patient_in: PatientCreate
) -> Any:
    """
    Create new patient. Superusers only.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    patient = Patient.model_validate(patient_in, update={"owner_id": current_user.id})
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@router.put("/{id}", response_model=PatientPublic)
def update_patient(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    patient_in: PatientUpdate,
) -> Any:
    """
    Update a patient.
    """
    patient = session.get(Patient, id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not current_user.is_superuser and (patient.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    update_dict = patient_in.model_dump(exclude_unset=True)
    patient.sqlmodel_update(update_dict)

    if "description" in update_dict:
        patient.summary_status = "processing"

    session.add(patient)
    session.commit()
    session.refresh(patient)

    if "description" in update_dict:
        try:
            generate_summary_task.delay(str(id), description_changed=True)
        except Exception:
            logger.exception("Failed to enqueue summary task for patient %s", id)

    return _patient_to_public(patient, include_owner=True)


@router.delete("/{id}")
def delete_patient(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a patient.
    """
    patient = session.get(Patient, id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not current_user.is_superuser and (patient.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    session.delete(patient)
    session.commit()
    return Message(message="Patient deleted successfully")


@router.patch("/{id}/owner", response_model=PatientPublic)
def assign_patient_owner(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    body: PatientAssignOwner,
) -> Any:
    """
    Reassign the managing user of a patient. Superusers only.
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    patient = session.get(Patient, id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    new_owner = session.get(User, body.owner_id)
    if not new_owner:
        raise HTTPException(status_code=404, detail="User not found")
    patient.owner_id = body.owner_id
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return _patient_to_public(patient, include_owner=True)
