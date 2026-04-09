from sqlmodel import Session

from app import crud
from app.models import Patient, PatientCreate
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


def create_random_patient(db: Session) -> Patient:
    user = create_random_user(db)
    owner_id = user.id
    assert owner_id is not None
    title = random_lower_string()
    description = random_lower_string()
    patient_in = PatientCreate(title=title, description=description)
    return crud.create_patient(session=db, patient_in=patient_in, owner_id=owner_id)
