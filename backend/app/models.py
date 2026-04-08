import uuid
from datetime import date, datetime, timezone

from pydantic import EmailStr
from sqlalchemy import Date, DateTime, Text
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore[assignment]
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore[assignment]
    description: str | None = Field(default=None, max_length=10000)  # type: ignore[assignment]


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    # Override to use TEXT column type (no length cap at DB level)
    description: str | None = Field(default=None, sa_type=Text())  # type: ignore[assignment]
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    summary: str | None = Field(default=None, sa_type=Text())
    summary_updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner: User | None = Relationship(back_populates="items")
    transcripts: list["EncounterTranscript"] = Relationship(
        back_populates="item", cascade_delete=True
    )


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None
    owner: UserPublic | None = None
    summary: str | None = None
    summary_updated_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Used by superusers to reassign a patient's managing user
class ItemAssignOwner(SQLModel):
    owner_id: uuid.UUID


# Shared properties
class EncounterTranscriptBase(SQLModel):
    text: str = Field(min_length=1, max_length=4000)
    encounter_date: date


class EncounterTranscriptCreate(EncounterTranscriptBase):
    pass


class EncounterTranscriptUpdate(SQLModel):
    text: str | None = Field(default=None, min_length=1, max_length=4000)
    encounter_date: date | None = None


class EncounterTranscript(EncounterTranscriptBase, table=True):
    __tablename__ = "encounter_transcript"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    text: str = Field(sa_type=Text())  # type: ignore[assignment]
    encounter_date: date = Field(sa_type=Date())  # type: ignore[assignment]
    item_id: uuid.UUID = Field(
        foreign_key="item.id", nullable=False, ondelete="CASCADE"
    )
    created_by_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    item: Item | None = Relationship(back_populates="transcripts")
    created_by: User | None = Relationship()


class EncounterTranscriptPublic(EncounterTranscriptBase):
    id: uuid.UUID
    item_id: uuid.UUID
    created_by_id: uuid.UUID
    created_at: datetime | None = None
    created_by: UserPublic | None = None
    is_editable: bool = False


class EncounterTranscriptsPublic(SQLModel):
    data: list[EncounterTranscriptPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
