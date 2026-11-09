from uuid import UUID

from pydantic import BaseModel, EmailStr


class StudentCreate(BaseModel):
    display_name: str
    email: EmailStr


class StudentResponse(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str


class StudentRegistrationResponse(StudentResponse):
    message: str
