from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field




class RoadmapMilestone(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str

    # What the learner should study in this milestone
    topics_to_learn: list[str] = Field(default_factory=list)

    # Practical actions the learner should complete
    tasks: list[str] = Field(default_factory=list)

    # Completion status for each task, in the same order as tasks.
    completed_tasks: list[bool] = Field(default_factory=list)
    # A hands-on project is useful, but not mandatory for every milestone
    project: str | None = None

    # Observable outcomes that show the milestone is complete
    completion_criteria: list[str] = Field(default_factory=list)

    # Earlier milestones or knowledge needed first
    prerequisites: list[str] = Field(default_factory=list)


class CareerRoadmapResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    target_role: str | None
    milestones: list[RoadmapMilestone]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CareerRoadmapCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    target_role: str | None = None
    milestones: list[RoadmapMilestone] = Field(default_factory=list)


class RoadmapGenerateRequest(BaseModel):
    target_role: str = Field(min_length=1, max_length=200)
    current_skills: list[str] = Field(default_factory=list)
    background: str | None = None

class RoadmapReviseRequest(BaseModel):
    roadmap_id: UUID
    instructions: str = Field(min_length=1, max_length=2000)


class RoadmapRevisionProposal(BaseModel):
    title: str
    target_role: str | None = None
    milestones: list[RoadmapMilestone]

class RoadmapProgressUpdate(BaseModel):
    completed_tasks: list[bool]