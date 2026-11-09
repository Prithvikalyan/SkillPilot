
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.connection import SessionLocal
from app.db.models import CareerRoadmap
from app.schemas.roadmap import (
    CareerRoadmapResponse,
    CareerRoadmapCreate,
    RoadmapGenerateRequest,
    RoadmapReviseRequest,
    RoadmapRevisionProposal,
    RoadmapProgressUpdate,
)
from app.services.roadmap import generate_roadmap, revise_roadmap


router = APIRouter(prefix="/roadmap", tags=["Roadmap"])

# SkillPilot's fixed student.
FIXED_STUDENT_ID = UUID("a5e78c7a-a214-46a4-9532-d5fbc0cf8a54")


class TaskCheckpointUpdate(BaseModel):
    completed: bool


# Keep the existing single-roadmap endpoint for compatibility.
@router.get("", response_model=CareerRoadmapResponse)
def get_roadmap():
    try:
        with SessionLocal() as db:
            roadmap = db.scalar(
                select(CareerRoadmap)
                .where(CareerRoadmap.user_id == FIXED_STUDENT_ID)
                .order_by(CareerRoadmap.created_at.desc())
            )

            if roadmap is None:
                raise HTTPException(
                    status_code=404,
                    detail="Roadmap not found",
                )

            return roadmap

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve roadmap",
        )


# List all roadmaps belonging to this student.
@router.get("/list", response_model=list[CareerRoadmapResponse])
def list_roadmaps():
    try:
        with SessionLocal() as db:
            return db.scalars(
                select(CareerRoadmap)
                .where(CareerRoadmap.user_id == FIXED_STUDENT_ID)
                .order_by(CareerRoadmap.created_at.desc())
            ).all()

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve roadmaps",
        )


# Fetch one roadmap by its ID.
@router.get("/{roadmap_id}", response_model=CareerRoadmapResponse)
def get_roadmap_by_id(roadmap_id: UUID):
    try:
        with SessionLocal() as db:
            roadmap = db.scalar(
                select(CareerRoadmap).where(
                    CareerRoadmap.id == roadmap_id,
                    CareerRoadmap.user_id == FIXED_STUDENT_ID,
                )
            )

            if roadmap is None:
                raise HTTPException(
                    status_code=404,
                    detail="Roadmap not found",
                )

            return roadmap

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve roadmap",
        )


# Delete one roadmap belonging to this student.
@router.delete("/{roadmap_id}")
def delete_roadmap(roadmap_id: UUID):
    try:
        with SessionLocal() as db:
            roadmap = db.scalar(
                select(CareerRoadmap).where(
                    CareerRoadmap.id == roadmap_id,
                    CareerRoadmap.user_id == FIXED_STUDENT_ID,
                )
            )

            if roadmap is None:
                raise HTTPException(
                    status_code=404,
                    detail="Roadmap not found",
                )

            deleted_id = str(roadmap.id)

            db.delete(roadmap)
            db.commit()

            return {
                "success": True,
                "message": "Roadmap deleted successfully",
                "roadmap_id": deleted_id,
            }

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not delete roadmap",
        )


# Update an individual task's completion checkpoint.
@router.patch(
    "/{roadmap_id}/milestones/{milestone_index}/tasks/{task_index}"
)
def update_task_checkpoint(
    roadmap_id: UUID,
    milestone_index: int,
    task_index: int,
    payload: TaskCheckpointUpdate,
):
    try:
        with SessionLocal() as db:
            roadmap = db.scalar(
                select(CareerRoadmap).where(
                    CareerRoadmap.id == roadmap_id,
                    CareerRoadmap.user_id == FIXED_STUDENT_ID,
                )
            )

            if roadmap is None:
                raise HTTPException(
                    status_code=404,
                    detail="Roadmap not found",
                )

            # Copy JSONB data before modifying it.
            milestones = [
                dict(milestone)
                for milestone in roadmap.milestones
            ]

            if not 0 <= milestone_index < len(milestones):
                raise HTTPException(
                    status_code=404,
                    detail="Milestone not found",
                )

            milestone = milestones[milestone_index]
            tasks = milestone.get("tasks", [])

            if not 0 <= task_index < len(tasks):
                raise HTTPException(
                    status_code=404,
                    detail="Task not found",
                )

            completed_tasks = milestone.get("completed_tasks", [])

            # Initialize missing or outdated progress data.
            if len(completed_tasks) != len(tasks):
                completed_tasks = [False] * len(tasks)
            else:
                completed_tasks = list(completed_tasks)

            completed_tasks[task_index] = payload.completed
            milestone["completed_tasks"] = completed_tasks

            # Assign a new list so SQLAlchemy detects the JSONB change.
            roadmap.milestones = milestones

            db.commit()
            db.refresh(roadmap)

            return {
                "success": True,
                "roadmap_id": str(roadmap.id),
                "milestone_index": milestone_index,
                "task_index": task_index,
                "completed": payload.completed,
                "milestones": roadmap.milestones,
            }

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not update task checkpoint",
        )


# Create an additional roadmap manually.
@router.post(
    "",
    response_model=CareerRoadmapResponse,
    status_code=201,
)
def create_roadmap(payload: CareerRoadmapCreate):
    new_roadmap = CareerRoadmap(
        id=uuid4(),
        user_id=FIXED_STUDENT_ID,
        title=payload.title,
        target_role=payload.target_role,
        milestones=[
            milestone.model_dump()
            for milestone in payload.milestones
        ],
    )

    try:
        with SessionLocal() as db:
            db.add(new_roadmap)
            db.commit()
            db.refresh(new_roadmap)
            return new_roadmap

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Could not create roadmap due to a database constraint",
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not create roadmap",
        )


# Generate and save an additional roadmap.
@router.post(
    "/generate",
    response_model=CareerRoadmapResponse,
    status_code=201,
)
def generate_student_roadmap(payload: RoadmapGenerateRequest):
    try:
        generated = generate_roadmap(payload)

    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not generate roadmap using Ollama",
        )

    new_roadmap = CareerRoadmap(
        id=uuid4(),
        user_id=FIXED_STUDENT_ID,
        title=generated["title"],
        target_role=generated["target_role"],
        milestones=generated["milestones"],
    )

    try:
        with SessionLocal() as db:
            db.add(new_roadmap)
            db.commit()
            db.refresh(new_roadmap)
            return new_roadmap

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Could not save generated roadmap due to a database constraint",
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not save generated roadmap",
        )


# Return a revision proposal for the specified roadmap; do not save it yet.
@router.post("/revise", response_model=RoadmapRevisionProposal)
def propose_roadmap_revision(payload: RoadmapReviseRequest):
    try:
        with SessionLocal() as db:
            roadmap = db.scalar(
                select(CareerRoadmap).where(
                    CareerRoadmap.id == payload.roadmap_id,
                    CareerRoadmap.user_id == FIXED_STUDENT_ID,
                )
            )

            if roadmap is None:
                raise HTTPException(
                    status_code=404,
                    detail="Roadmap not found",
                )

            current_roadmap = {
                "title": roadmap.title,
                "target_role": roadmap.target_role,
                "milestones": roadmap.milestones,
            }

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve roadmap for revision",
        )

    try:
        return revise_roadmap(
            current_roadmap=current_roadmap,
            instructions=payload.instructions,
        )

    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not generate roadmap revision using Ollama",
        )


# Accept and save a proposed roadmap revision.
@router.post(
    "/{roadmap_id}/accept-revision",
    response_model=CareerRoadmapResponse,
)
def accept_roadmap_revision(
    roadmap_id: UUID,
    proposal: RoadmapRevisionProposal,
):
    try:
        with SessionLocal() as db:
            roadmap = db.scalar(
                select(CareerRoadmap).where(
                    CareerRoadmap.id == roadmap_id,
                    CareerRoadmap.user_id == FIXED_STUDENT_ID,
                )
            )

            if roadmap is None:
                raise HTTPException(
                    status_code=404,
                    detail="Roadmap not found",
                )

            revised_milestones = [
                milestone.model_dump()
                for milestone in proposal.milestones
            ]

            roadmap.title = proposal.title
            roadmap.target_role = proposal.target_role
            roadmap.milestones = revised_milestones

            db.commit()
            db.refresh(roadmap)

            return roadmap

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not save accepted roadmap revision",
        )


# Update completion status for all tasks in one milestone.
@router.patch(
    "/{roadmap_id}/milestones/{milestone_index}/progress"
)
def update_milestone_progress(
    roadmap_id: UUID,
    milestone_index: int,
    payload: RoadmapProgressUpdate,
):
    try:
        with SessionLocal() as db:
            roadmap = db.scalar(
                select(CareerRoadmap).where(
                    CareerRoadmap.id == roadmap_id,
                    CareerRoadmap.user_id == FIXED_STUDENT_ID,
                )
            )

            if roadmap is None:
                raise HTTPException(
                    status_code=404,
                    detail="Roadmap not found",
                )

            milestones = [
                dict(milestone)
                for milestone in roadmap.milestones
            ]

            if not 0 <= milestone_index < len(milestones):
                raise HTTPException(
                    status_code=404,
                    detail="Milestone not found",
                )

            milestone = milestones[milestone_index]
            tasks = milestone.get("tasks", [])

            if len(payload.completed_tasks) != len(tasks):
                raise HTTPException(
                    status_code=422,
                    detail="Completion status count must match task count",
                )

            milestone["completed_tasks"] = payload.completed_tasks

            roadmap.milestones = milestones
            roadmap.updated_at = datetime.now().astimezone()

            db.commit()
            db.refresh(roadmap)

            return {
                "roadmap_id": str(roadmap.id),
                "milestone_index": milestone_index,
                "completed_tasks": milestone["completed_tasks"],
                "success": True,
            }

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Could not update milestone progress",
        )
