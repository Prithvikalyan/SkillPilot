from types import SimpleNamespace

from app.services.tutor import load_recent_history


class FakeResult:
    def __init__(self, messages):
        self.messages = messages

    def all(self):
        return self.messages


class FakeDB:
    def __init__(self, messages):
        self.messages = messages
        self.statement = None

    def scalars(self, statement):
        self.statement = statement
        return FakeResult(self.messages)


def test_load_recent_history_returns_messages_chronologically():
    # Simulate the database returning newest messages first.
    newest_first = [
        SimpleNamespace(id=3, content="Third"),
        SimpleNamespace(id=2, content="Second"),
        SimpleNamespace(id=1, content="First"),
    ]
    db = FakeDB(newest_first)

    result = load_recent_history(db, conversation_id="test-conversation")

    # The helper should reverse them into chronological order.
    assert [message.id for message in result] == [1, 2, 3]

    # It should request the default maximum of 10 messages.
    assert db.statement._limit_clause.value == 10

def test_ask_tutor_returns_answer_when_indexing_fails(monkeypatch):
    from contextlib import contextmanager

    from app.services import tutor

    class FakeDB:
        def __init__(self):
            self.added_messages = []
            self.committed = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def add_all(self, messages):
            self.added_messages.extend(messages)

        def flush(self):
            # Simulate PostgreSQL assigning message IDs.
            self.added_messages[0].id = 101
            self.added_messages[1].id = 102

        def commit(self):
            self.committed = True

    fake_db = FakeDB()

    @contextmanager
    def fake_session_local():
        yield fake_db

    monkeypatch.setattr(tutor, "SessionLocal", fake_session_local)
    monkeypatch.setattr(tutor, "load_recent_history", lambda db, conversation_id: [])
    monkeypatch.setattr(tutor, "hybrid_search", lambda **kwargs: [])
    fake_model = SimpleNamespace(
    invoke=lambda messages: SimpleNamespace(
        content="Here is the answer."
    )
)

    monkeypatch.setattr(tutor, "model", fake_model)

    def failing_index(message_id):
        raise RuntimeError("Embedding service unavailable")

    monkeypatch.setattr(tutor, "index_message", failing_index)

    result = tutor.ask_tutor(
        question="What is Python?",
        conversation_id="test-conversation",
    )

    assert fake_db.committed is True
    assert len(fake_db.added_messages) == 2
    assert result == "Here is the answer."