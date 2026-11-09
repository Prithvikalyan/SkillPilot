CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS tutor_messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('human', 'ai')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tutor_messages_conversation
    ON tutor_messages (conversation_id, id);

CREATE TABLE IF NOT EXISTS tutor_message_embeddings (
    message_id BIGINT PRIMARY KEY
        REFERENCES tutor_messages(id) ON DELETE CASCADE,
    conversation_id TEXT NOT NULL,
    embedding VECTOR(768) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tutor_message_embeddings_conversation
    ON tutor_message_embeddings (conversation_id);