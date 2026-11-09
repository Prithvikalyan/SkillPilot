from fastapi.testclient import TestClient

from app.main import app
from uuid import UUID, uuid4
from unittest.mock import MagicMock
from app.db.models import CareerRoadmap,User

from datetime import datetime, timezone

client = TestClient(app)


def test_home_returns_welcome_message():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to SkillPilot!"}


def test_health_returns_running():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "running"}


def test_tutor_ask_returns_mocked_answer(monkeypatch):
    def fake_generate_answer(question, conversation_id):
        return "Mock tutor answer"

    monkeypatch.setattr(
        "app.api.routes.tutor.generate_tutor_answer",
        fake_generate_answer,
    )

    response = client.post(
        "/tutor/ask",
        json={
            "question": "What is Python?",
            "conversation_id": "test-conversation",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "test-conversation",
        "question": "What is Python?",
        "answer": "Mock tutor answer",
    }


def test_tutor_ask_rejects_empty_question():
    response = client.post(
        "/tutor/ask",
        json={
            "question": "",
            "conversation_id": "test-conversation",
        },
    )

    assert response.status_code == 422


def test_tutor_ask_rejects_question_over_2000_characters():
    response = client.post(
        "/tutor/ask",
        json={
            "question": "x" * 2001,
            "conversation_id": "test-conversation",
        },
    )

    assert response.status_code == 422


def test_tutor_history_rejects_limit_over_100():
    response = client.get(
        "/tutor/history",
        params={
            "conversation_id": "test-conversation",
            "limit": 101,
        },
    )

    assert response.status_code == 422


def test_register_student_returns_created_student(monkeypatch):
    fake_db = MagicMock()

    # The route uses: with SessionLocal() as db
    session_context = MagicMock()
    session_context.__enter__.return_value = fake_db

    monkeypatch.setattr(
        "app.api.routes.students.SessionLocal",
        lambda: session_context,
    )

    response = client.post(
        "/students",
        json={
            "display_name": "Test Student",
            "email": "student@example.com",
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["display_name"] == "Test Student"
    assert body["email"] == "student@example.com"
    assert body["message"] == "Student registered successfully"

    # Verify the endpoint tried to persist the User.
    fake_db.add.assert_called_once()
    added_user = fake_db.add.call_args.args[0]

    assert isinstance(added_user, User)
    assert added_user.display_name == "Test Student"
    assert added_user.email == "student@example.com"

    fake_db.commit.assert_called_once()
    fake_db.refresh.assert_called_once_with(added_user)


def test_get_student_returns_student_from_mock_session(monkeypatch):
    student_id = uuid4()

    fake_student = User(
        id=student_id,
        email="student@example.com",
        display_name="Test Student",
    )

    fake_db = MagicMock()
    fake_db.get.return_value = fake_student

    session_context = MagicMock()
    session_context.__enter__.return_value = fake_db

    monkeypatch.setattr(
        "app.api.routes.students.SessionLocal",
        lambda: session_context,
    )

    response = client.get(f"/students/{student_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": str(student_id),
        "email": "student@example.com",
        "display_name": "Test Student",
    }

    fake_db.get.assert_called_once_with(User, student_id)


def test_get_student_returns_404_when_missing(monkeypatch):
    student_id = uuid4()

    fake_db = MagicMock()
    fake_db.get.return_value = None

    session_context = MagicMock()
    session_context.__enter__.return_value = fake_db

    monkeypatch.setattr(
        "app.api.routes.students.SessionLocal",
        lambda: session_context,
    )

    response = client.get(f"/students/{student_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Student not found"

    fake_db.get.assert_called_once_with(User, student_id)

def test_get_students_returns_list(monkeypatch):
    student_one = User(
        id=uuid4(),
        email="alice@example.com",
        display_name="Alice",
    )
    student_two = User(
        id=uuid4(),
        email="bob@example.com",
        display_name="Bob",
    )

    fake_db = MagicMock()
    fake_db.scalars.return_value.all.return_value = [
        student_one,
        student_two,
    ]

    session_context = MagicMock()
    session_context.__enter__.return_value = fake_db

    monkeypatch.setattr(
        "app.api.routes.students.SessionLocal",
        lambda: session_context,
    )

    response = client.get("/students")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(student_one.id),
            "email": "alice@example.com",
            "display_name": "Alice",
        },
        {
            "id": str(student_two.id),
            "email": "bob@example.com",
            "display_name": "Bob",
        },
    ]

    fake_db.scalars.assert_called_once()

from sqlalchemy.exc import IntegrityError


def test_register_student_duplicate_email_returns_409(monkeypatch):
    fake_db = MagicMock()

    # Simulate PostgreSQL identifying the users_email_key constraint.
    duplicate_error = Exception("duplicate email")
    duplicate_error.diag = MagicMock()
    duplicate_error.diag.constraint_name = "users_email_key"

    fake_db.commit.side_effect = IntegrityError(
        statement="INSERT INTO users",
        params={},
        orig=duplicate_error,
    )

    session_context = MagicMock()
    session_context.__enter__.return_value = fake_db

    monkeypatch.setattr(
        "app.api.routes.students.SessionLocal",
        lambda: session_context,
    )

    response = client.post(
        "/students",
        json={
            "display_name": "Duplicate Student",
            "email": "already-used@example.com",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "This email is already registered"

{
    "title": "Learn Python basics",
    "description": "Learn Python syntax and core concepts.",
    "topics_to_learn": [],
    "tasks": [],
    "project": None,
    "completion_criteria": [],
    "prerequisites": [],
}

def test_get_student_roadmap_returns_404_when_missing(monkeypatch):
    student_id = uuid4()

    fake_db = MagicMock()
    fake_db.scalar.return_value = None

    session_context = MagicMock()
    session_context.__enter__.return_value = fake_db

    monkeypatch.setattr(
        "app.api.routes.students.SessionLocal",
        lambda: session_context,
    )

    response = client.get(f"/students/{student_id}/roadmap")

    assert response.status_code == 404
    assert response.json()["detail"] == "Roadmap not found"

    
def test_list_roadmaps_returns_multiple_roadmaps(monkeypatch):
    student_id = UUID("a5e78c7a-a214-46a4-9532-d5fbc0cf8a54")

    roadmap_one = CareerRoadmap(
        id=uuid4(),
        user_id=student_id,
        title="Python Developer Roadmap",
        target_role="Python Developer",
        milestones=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    roadmap_two = CareerRoadmap(
        id=uuid4(),
        user_id=student_id,
        title="Data Analyst Roadmap",
        target_role="Data Analyst",
        milestones=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    fake_db = MagicMock()
    fake_db.scalars.return_value.all.return_value = [roadmap_one, roadmap_two]

    session_context = MagicMock()
    session_context.__enter__.return_value = fake_db

    monkeypatch.setattr(
        "app.api.routes.roadmap.SessionLocal",
        lambda: session_context,
    )

    response = client.get("/roadmap/list")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert {item["title"] for item in response.json()} == {
        "Python Developer Roadmap",
        "Data Analyst Roadmap",
    }


def test_get_roadmap_by_id_returns_requested_roadmap(monkeypatch):
    student_id = UUID("a5e78c7a-a214-46a4-9532-d5fbc0cf8a54")
    roadmap_id = uuid4()

    fake_roadmap = CareerRoadmap(
        id=roadmap_id,
        user_id=student_id,
        title="Python Developer Roadmap",
        target_role="Python Developer",
        milestones=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    fake_db = MagicMock()
    fake_db.scalar.return_value = fake_roadmap

    session_context = MagicMock()
    session_context.__enter__.return_value = fake_db

    monkeypatch.setattr(
        "app.api.routes.roadmap.SessionLocal",
        lambda: session_context,
    )

    response = client.get(f"/roadmap/{roadmap_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(roadmap_id)
    assert response.json()["title"] == "Python Developer Roadmap"


def test_get_roadmap_by_id_returns_404_when_not_found(monkeypatch):
    fake_db = MagicMock()
    fake_db.scalar.return_value = None

    session_context = MagicMock()
    session_context.__enter__.return_value = fake_db

    monkeypatch.setattr(
        "app.api.routes.roadmap.SessionLocal",
        lambda: session_context,
    )

    response = client.get(f"/roadmap/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Roadmap not found"


def test_create_second_roadmap_succeeds(monkeypatch):
    student_id = UUID("a5e78c7a-a214-46a4-9532-d5fbc0cf8a54")

    fake_db = MagicMock()

    def fake_refresh(roadmap):
        roadmap.created_at = datetime.now(timezone.utc)
        roadmap.updated_at = datetime.now(timezone.utc)

    fake_db.refresh.side_effect = fake_refresh

    session_context = MagicMock()
    session_context.__enter__.return_value = fake_db

    monkeypatch.setattr(
        "app.api.routes.roadmap.SessionLocal",
        lambda: session_context,
    )

    response = client.post(
        "/roadmap",
        json={
            "title": "Data Analyst Roadmap",
            "target_role": "Data Analyst",
            "milestones": [],
        },
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == str(student_id)
    assert response.json()["title"] == "Data Analyst Roadmap"
    fake_db.add.assert_called_once()
    fake_db.commit.assert_called_once()


def test_accept_roadmap_revision_saves_milestones_without_status(
    monkeypatch,
):
    student_id = UUID("a5e78c7a-a214-46a4-9532-d5fbc0cf8a54")
    roadmap_id = uuid4()

    fake_roadmap = CareerRoadmap(
        id=roadmap_id,
        user_id=student_id,
        title="Original Roadmap",
        target_role="Data Analyst",
        milestones=[
            {
    "title": "Learn SQL",
    "description": "Study SQL for analysis.",
    "topics_to_learn": [],
    "tasks": ["Practice joins"],
    "project": None,
    "completion_criteria": [],
    "prerequisites": [],
    },
        ],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    fake_db = MagicMock()
    fake_db.scalar.return_value = fake_roadmap

    session_context = MagicMock()
    session_context.__enter__.return_value = fake_db

    monkeypatch.setattr(
        "app.api.routes.roadmap.SessionLocal",
        lambda: session_context,
    )

    response = client.post(
        f"/roadmap/{roadmap_id}/accept-revision",
        json={
            "title": "Revised Data Analyst Roadmap",
            "target_role": "Data Analyst",
            "milestones": [
                {
    "title": "Learn SQL",
    "description": "Study SQL for analysis.",
    "topics_to_learn": [],
    "tasks": ["Practice joins"],
    "project": None,
    "completion_criteria": [],
    "prerequisites": [],
    },
                {
    "title": "Learn Excel",
    "description": "Learn spreadsheet basics.",
    "topics_to_learn": [],
    "tasks": ["Practice formulas"],
    "project": None,
    "completion_criteria": [],
    "prerequisites": [],
    },
            ],
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["title"] == "Revised Data Analyst Roadmap"
    assert len(body["milestones"]) == 2

    assert body["milestones"][0] == {
    "title": "Learn SQL",
    "description": "Study SQL for analysis.",
    "topics_to_learn": [],
    "tasks": ["Practice joins"],
    "project": None,
    "completion_criteria": [],
    "prerequisites": [],
    }

    assert body["milestones"][1] == {
    "title": "Learn Excel",
    "description": "Learn spreadsheet basics.",
    "topics_to_learn": [],
    "tasks": ["Practice formulas"],
    "project": None,
    "completion_criteria": [],
    "prerequisites": [],
    }

    # The previously stored milestone is omitted from the revised roadmap.
    assert "Old milestone" not in [
        milestone["title"] for milestone in body["milestones"]
    ]

    fake_db.commit.assert_called_once()
    fake_db.refresh.assert_called_once_with(fake_roadmap)



def test_accept_roadmap_revision_returns_404_when_roadmap_missing(
    monkeypatch,
):
    fake_db = MagicMock()
    fake_db.scalar.return_value = None

    session_context = MagicMock()
    session_context.__enter__.return_value = fake_db

    monkeypatch.setattr(
        "app.api.routes.roadmap.SessionLocal",
        lambda: session_context,
    )

    response = client.post(
        f"/roadmap/{uuid4()}/accept-revision",
        json={
            "title": "Revised Roadmap",
            "target_role": "Data Analyst",
            "milestones": [],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Roadmap not found"

    # Missing roadmap should not be committed.
    fake_db.commit.assert_not_called()