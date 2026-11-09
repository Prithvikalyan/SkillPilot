from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.connection import SessionLocal

from app.db.models import CareerRoadmap, User
from app.schemas.roadmap import CareerRoadmapResponse

from app.schemas.student import (
    StudentCreate,
    StudentResponse,
    StudentRegistrationResponse,
)

router = APIRouter(prefix="/students", tags=["Students"])

@router.post("", response_model=StudentRegistrationResponse)
def register_student(student: StudentCreate):
    new_student = User(
        id=uuid4(),
        email=str(student.email),
        display_name=student.display_name,
    )

    try:
        with SessionLocal() as db:
            db.add(new_student)
            db.commit()
            db.refresh(new_student)

            response = {
                "id": str(new_student.id),
                "email": new_student.email,
                "display_name": new_student.display_name,
                "message": "Student registered successfully",
            }

        return response

    except IntegrityError as exc:
        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name == "users_email_key":
            raise HTTPException(
                status_code=409,
                detail="This email is already registered",
            )

        raise HTTPException(
            status_code=500,
            detail="Could not register student",
        )


@router.get("", response_model=list[StudentResponse])
def get_students():
    try:
        with SessionLocal() as db:
            students = db.scalars(
                select(User).order_by(User.display_name)
            ).all()

            return [
                {
                    "id": str(student.id),
                    "email": student.email,
                    "display_name": student.display_name,
                }
                for student in students
            ]

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve students",
        )


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: UUID):
    try:
        with SessionLocal() as db:
            student = db.get(User, student_id)

            if student is None:
                raise HTTPException(
                    status_code=404,
                    detail="Student not found",
                )

            return {
                "id": str(student.id),
                "email": student.email,
                "display_name": student.display_name,
            }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve student",
        )
    
    
@router.get("/{student_id}/roadmap", response_model=CareerRoadmapResponse)
def get_student_roadmap(student_id: UUID):
    try:
        with SessionLocal() as db:
            roadmap = db.scalar(
                select(CareerRoadmap).where(
                    CareerRoadmap.user_id == student_id
                )
            )

            if roadmap is None:
                raise HTTPException(
                    status_code=404,
                    detail="Roadmap not found",
                )

            return roadmap

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve roadmap",
        )