import pytest
from types import SimpleNamespace

from app.services import embeddings

from sqlalchemy.dialects import postgresql

from datetime import datetime


def test_embed_text_returns_768_dimensions(monkeypatch):
    fake_vector = [0.1] * 768

    fake_model = SimpleNamespace(
        embed_documents=lambda texts: [fake_vector]
    )

    monkeypatch.setattr(embeddings, "embedding_model", fake_model)

    result = embeddings.embed_text("A sample document")

    assert result == fake_vector
    assert len(result) == 768


def test_embed_query_returns_768_dimensions(monkeypatch):
    fake_vector = [0.2] * 768

    fake_model = SimpleNamespace(
        embed_query=lambda text: fake_vector
    )

    monkeypatch.setattr(embeddings, "embedding_model", fake_model)

    result = embeddings.embed_query("A sample question")

    assert result == fake_vector
    assert len(result) == 768


def test_embed_text_rejects_wrong_dimensions(monkeypatch):
    fake_vector = [0.1] * 10

    fake_model = SimpleNamespace(
        embed_documents=lambda texts: [fake_vector]
    )

    monkeypatch.setattr(embeddings, "embedding_model", fake_model)

    with pytest.raises(ValueError, match="Expected 768 dimensions"):
        embeddings.embed_text("A sample document")


def test_embed_query_rejects_wrong_dimensions(monkeypatch):
    fake_vector = [0.2] * 10

    fake_model = SimpleNamespace(
        embed_query=lambda text: fake_vector
    )

    monkeypatch.setattr(embeddings, "embedding_model", fake_model)

    with pytest.raises(ValueError, match="Expected 768 dimensions"):
        embeddings.embed_query("A sample question")


class FakeReadSession:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def get(self, model_class, message_id):
        return self.message


class FakeWriteSession:
    def __init__(self):
        self.executed_statement = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement):
        self.executed_statement = statement


class FakeSessionFactory:
    def __init__(self, message):
        self.read_session = FakeReadSession(message)
        self.write_session = FakeWriteSession()

    def __call__(self):
        return self.read_session

    def begin(self):
        return self.write_session


def test_index_message_raises_when_message_is_missing(monkeypatch):
    fake_sessions = FakeSessionFactory(message=None)

    monkeypatch.setattr(embeddings, "SessionLocal", fake_sessions)

    def unexpected_embed_text(text):
        pytest.fail("embed_text should not run when the message is missing")

    monkeypatch.setattr(embeddings, "embed_text", unexpected_embed_text)

    with pytest.raises(ValueError, match="Message 42 was not found"):
        embeddings.index_message(42)


def test_index_message_builds_embedding_upsert(monkeypatch):
    message = SimpleNamespace(
        id=42,
        conversation_id="conversation-abc",
        content="Explain Python lists",
    )
    fake_sessions = FakeSessionFactory(message)

    monkeypatch.setattr(embeddings, "SessionLocal", fake_sessions)

    fake_vector = [0.25] * 768
    monkeypatch.setattr(
        embeddings,
        "embed_text",
        lambda content: fake_vector,
    )

    embeddings.index_message(42)

    statement = fake_sessions.write_session.executed_statement
    assert statement is not None

    # Compile as PostgreSQL SQL and check that it uses an upsert.
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled).upper()

    assert "INSERT INTO" in sql
    assert "ON CONFLICT" in sql
    assert compiled.params["message_id"] == 42
    assert compiled.params["conversation_id"] == "conversation-abc"
    assert compiled.params["embedding"] == fake_vector



class FakeSearchResult:
    def all(self):
        message = SimpleNamespace(
            id=7,
            role="human",
            content="Explain Python lists",
            created_at=datetime(2026, 1, 1, 12, 0, 0),
        )

        # Simulate SQLAlchemy returning (message, cosine_distance).
        return [(message, 0.125)]


class FakeSearchSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement):
        return FakeSearchResult()


def test_search_messages_rejects_empty_query():
    with pytest.raises(ValueError, match="Search query cannot be empty"):
        embeddings.search_messages("   ")


@pytest.mark.parametrize("limit", [0, 21])
def test_search_messages_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="Limit must be between 1 and 20"):
        embeddings.search_messages("python lists", limit=limit)


def test_search_messages_formats_results(monkeypatch):
    fake_vector = [0.1] * 768

    monkeypatch.setattr(
        embeddings,
        "embed_query",
        lambda query: fake_vector,
    )
    monkeypatch.setattr(
        embeddings,
        "SessionLocal",
        lambda: FakeSearchSession(),
    )

    results = embeddings.search_messages(
        query="python lists",
        conversation_id="conversation-abc",
        limit=5,
    )

    assert results == [
        {
            "message_id": 7,
            "role": "human",
            "content": "Explain Python lists",
            "created_at": datetime(2026, 1, 1, 12, 0, 0),
            "distance": 0.125,
        }
    ]