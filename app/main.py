from fastapi import FastAPI

from app.api.routes.system import router as system_router
from app.api.routes.students import router as students_router
from app.api.routes.tutor import router as tutor_router
from app.api.routes.roadmap import router as roadmap_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SkillPilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(students_router)
app.include_router(tutor_router)
app.include_router(roadmap_router)
