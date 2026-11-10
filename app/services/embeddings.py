from langchain_ollama import OllamaEmbeddings

import re

from sqlalchemy import BigInteger, case, func, null, select, true, and_
from sqlalchemy.dialects.postgresql import insert
from app.core.config import settings
from app.db.connection import SessionLocal
from app.db.models import TutorMessage, TutorMessageEmbedding
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder


EMBEDDING_MODEL = "nomic-embed-text"
EXPECTED_DIMENSIONS = 768

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

reranker = CrossEncoder(RERANKER_MODEL)

embedding_model = OllamaEmbeddings(
    model=EMBEDDING_MODEL,
    base_url=settings.ollama_base_url,
)


def embed_text(text_to_embed: str) -> list[float]:
    """Embed a message that will be stored and searched later."""
    vector = embedding_model.embed_documents(
        [f"search_document: {text_to_embed}"]
    )[0]

    if len(vector) != EXPECTED_DIMENSIONS:
        raise ValueError(
            f"Expected {EXPECTED_DIMENSIONS} dimensions, "
            f"but received {len(vector)}."
        )

    return vector


def embed_query(query: str) -> list[float]:
    """Embed a user's search question."""
    vector = embedding_model.embed_query(f"search_query: {query}")

    if len(vector) != EXPECTED_DIMENSIONS:
        raise ValueError(
            f"Expected {EXPECTED_DIMENSIONS} dimensions, "
            f"but received {len(vector)}."
        )

    return vector


def index_message(message_id: int) -> None:
    """Generate and save the embedding for an existing chat message."""

    # Load the message through the ORM. Close this session before calling Ollama.
    with SessionLocal() as db:
        message = db.get(TutorMessage, message_id)

        if message is None:
            raise ValueError(f"Message {message_id} was not found.")

        conversation_id = message.conversation_id
        content = message.content

    embedding = embed_text(content)

    # PostgreSQL UPSERT: insert a new embedding, or update the existing one.
    # SQLAlchemy builds this statement using the ORM model's table.
    insert_statement = insert(TutorMessageEmbedding).values(
        message_id=message_id,
        conversation_id=conversation_id,
        embedding=embedding,
    )

    upsert_statement = insert_statement.on_conflict_do_update(
        index_elements=[TutorMessageEmbedding.message_id],
        set_={
            "conversation_id": insert_statement.excluded.conversation_id,
            "embedding": insert_statement.excluded.embedding,
            "created_at": func.now(),
        },
    )

    with SessionLocal.begin() as db:
        db.execute(upsert_statement)


def search_messages(
    query: str,
    conversation_id: str = "default",
    limit: int = 5,
) -> list[dict]:
    """Find historical messages relevant to a user's question."""

    if not query.strip():
        raise ValueError("Search query cannot be empty.")

    if not 1 <= limit <= 20:
        raise ValueError("Limit must be between 1 and 20.")

    query_vector = embed_query(query)

    # pgvector's cosine_distance() creates the PostgreSQL <=> operation.
    distance = TutorMessageEmbedding.embedding.cosine_distance(query_vector)

    statement = (
        select(TutorMessage, distance.label("distance"))
        .join(
            TutorMessage,
            TutorMessage.id == TutorMessageEmbedding.message_id,
        )
        .where(
            TutorMessageEmbedding.conversation_id == conversation_id
        )
        .order_by(distance.asc())
        .limit(limit)
    )

    with SessionLocal() as db:
        rows = db.execute(statement).all()

    return [
        {
            "message_id": message.id,
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at,
            "distance": float(distance_value),
        }
        for message, distance_value in rows
    ]


def index_unindexed_messages() -> int:
    """Index existing messages that do not yet have embeddings."""

    statement = (
        select(TutorMessage.id)
        .outerjoin(
            TutorMessageEmbedding,
            TutorMessage.id == TutorMessageEmbedding.message_id,
        )
        .where(TutorMessageEmbedding.message_id.is_(None))
        .order_by(TutorMessage.id.asc())
    )

    with SessionLocal() as db:
        message_ids = db.execute(statement).scalars().all()

    indexed_count = 0

    for message_id in message_ids:
        index_message(message_id)
        indexed_count += 1

    return indexed_count




def hybrid_search(query: str, conversation_id: str = "default", limit: int = 20):
    """
    Combine BM25 keyword search and pgvector semantic search
    using Reciprocal Rank Fusion (RRF).
    """

    if not query or not query.strip():
        return []

    if limit < 1:
        raise ValueError("limit must be greater than 0")

    # Tokenize the search query
    query_tokens = re.findall(r"\b\w+\b", query.lower())

    if not query_tokens:
        return []

    # Generate query embedding for semantic search
    query_vector = embed_query(query)

    # Retrieve extra candidates before RRF
    candidate_limit = max(limit * 4, 20)

    session = SessionLocal()

    try:
        # --------------------------------------------------
        # 1. Load messages for BM25 keyword search
        # --------------------------------------------------

        messages = session.execute(
            select(TutorMessage).where(
                TutorMessage.conversation_id == conversation_id
            )
        ).scalars().all()

        # Tokenize each message
        bm25_messages = []
        tokenized_corpus = []

        for message in messages:
            tokens = re.findall(
                r"\b\w+\b",
                message.content.lower()
            )

            if tokens:
                bm25_messages.append(message)
                tokenized_corpus.append(tokens)

        # --------------------------------------------------
        # 2. BM25 keyword retrieval
        # --------------------------------------------------

        bm25_results = []

        if tokenized_corpus:
            bm25 = BM25Okapi(
                tokenized_corpus,
                k1=1.5,
                b=0.75
            )

            scores = bm25.get_scores(query_tokens)

            # Sort documents by BM25 score
            ranked_indices = sorted(
                range(len(scores)),
                key=lambda index: scores[index],
                reverse=True
            )

            bm25_rank = 0

            for index in ranked_indices:

                # Ignore documents that do not match the query
                if scores[index] <= 0:
                    continue

                message = bm25_messages[index]

                bm25_rank += 1

                bm25_results.append({
                    "message": message,
                    "rank": bm25_rank,
                    "score": float(scores[index])
                })

                if bm25_rank >= candidate_limit:
                    break

        # --------------------------------------------------
        # 3. Vector semantic retrieval using pgvector
        # --------------------------------------------------

        semantic_query = (
            select(
                TutorMessage,
                TutorMessageEmbedding.embedding.cosine_distance(
                    query_vector
                ).label("distance")
            )
            .join(
                TutorMessageEmbedding,
                TutorMessageEmbedding.message_id == TutorMessage.id
            )
            .where(
                TutorMessage.conversation_id == conversation_id
            )
            .order_by("distance")
            .limit(candidate_limit)
        )

        semantic_rows = session.execute(
            semantic_query
        ).all()

        # --------------------------------------------------
        # 4. Reciprocal Rank Fusion (RRF)
        # --------------------------------------------------

        rrf_constant = 60

        combined_results = {}

        # Add BM25 rankings
        for result in bm25_results:

            message = result["message"]
            message_id = message.id
            rank = result["rank"]

            if message_id not in combined_results:
                combined_results[message_id] = {
                    "message_id": message_id,
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at,
                    "rrf_score": 0.0,
                    "semantic_rank": None,
                    "bm25_rank": None
                }

            combined_results[message_id]["rrf_score"] += (
                1.0 / (rrf_constant + rank)
            )

            combined_results[message_id]["bm25_rank"] = rank

        # Add semantic rankings
        for rank, row in enumerate(semantic_rows, start=1):

            message = row[0]
            message_id = message.id

            if message_id not in combined_results:
                combined_results[message_id] = {
                    "message_id": message_id,
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at,
                    "rrf_score": 0.0,
                    "semantic_rank": None,
                    "bm25_rank": None
                }

            combined_results[message_id]["rrf_score"] += (
                1.0 / (rrf_constant + rank)
            )

            combined_results[message_id]["semantic_rank"] = rank

        # --------------------------------------------------
        # 5. Sort using the combined RRF score
        # --------------------------------------------------

        final_results = sorted(
            combined_results.values(),
            key=lambda result: result["rrf_score"],
            reverse=True
        )

        return final_results[:limit]

    finally:
        session.close()




def rerank_messages(
    query: str,
    candidates: list[dict],
    limit: int = 5,
) -> list[dict]:
    """Rerank retrieved messages by relevance to the user's question."""

    if not query.strip():
        raise ValueError("Reranking query cannot be empty.")

    if limit < 1:
        raise ValueError("Reranking limit must be at least 1.")

    if not candidates:
        return []

    pairs = [
        (query, candidate["content"])
        for candidate in candidates
    ]

    scores = reranker.predict(pairs)

    ranked_candidates = []

    for candidate, score in zip(candidates, scores):
        result = candidate.copy()
        result["rerank_score"] = float(score)
        ranked_candidates.append(result)

    ranked_candidates.sort(
        key=lambda item: item["rerank_score"],
        reverse=True,
    )

    return ranked_candidates[:limit]