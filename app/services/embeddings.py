from langchain_ollama import OllamaEmbeddings

import re

from sqlalchemy import BigInteger, case, func, null, select, true, and_
from sqlalchemy.dialects.postgresql import insert
from app.core.config import settings
from app.db.connection import SessionLocal
from app.db.models import TutorMessage, TutorMessageEmbedding

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



def hybrid_search(
    query: str,
    conversation_id: str = "default",
    limit: int = 20,
) -> list[dict]:
    """Combine semantic and PostgreSQL full-text search using RRF."""

    if not query or not query.strip():
        raise ValueError("Query must not be empty.")

    if not 1 <= limit <= 50:
        raise ValueError("Limit must be between 1 and 50.")

    # Step 1: Convert the question into an embedding vector.
    query_vector = embed_query(query)

    # Step 2: Prepare keyword-search terms.
    # This creates an OR-separated query, similar to the previous SQL.
    cleaned_query = re.sub(r"[^\w ]+", " ", query.lower())
    query_terms = cleaned_query.split()
    or_query = " OR ".join(query_terms)

    # Step 3: Build a small CTE containing the full-text query
    # and a normalized form of the user's question.
    search_term = (
        select(
            func.websearch_to_tsquery(
                "english",
                or_query,
            ).label("tsq"),
            func.regexp_replace(
                func.lower(query),
                r"[^[:alnum:]_]+",
                "",
                "g",
            ).label("normalized_query"),
        )
        .cte("search_term")
    )

    # Step 4: Semantic search.
    # pgvector's cosine_distance() generates the <=> operator.
    semantic_distance = (
        TutorMessageEmbedding.embedding.cosine_distance(query_vector)
    )

    semantic_results = (
        select(
            TutorMessageEmbedding.message_id,
            func.row_number()
            .over(order_by=semantic_distance)
            .label("semantic_rank"),
        )
        .select_from(TutorMessageEmbedding)
        .join(
            TutorMessage,
            TutorMessage.id == TutorMessageEmbedding.message_id,
        )
        .join(search_term, true())
        .where(
            TutorMessageEmbedding.conversation_id == conversation_id,
            func.regexp_replace(
                func.lower(TutorMessage.content),
                r"[^[:alnum:]_]+",
                "",
                "g",
            )
            != search_term.c.normalized_query,
        )
        .order_by(semantic_distance.asc())
        .limit(limit)
        .cte("semantic_results")
    )

    # Step 5: PostgreSQL full-text keyword search.
    message_tsvector = func.to_tsvector(
        "english",
        TutorMessage.content,
    )

    keyword_rank_score = func.ts_rank_cd(
        message_tsvector,
        search_term.c.tsq,
    )

    keyword_results = (
        select(
            TutorMessage.id.label("message_id"),
            func.row_number()
            .over(order_by=keyword_rank_score.desc())
            .label("keyword_rank"),
        )
        .select_from(TutorMessage)
        .join(search_term, true())
        .where(
            TutorMessage.conversation_id == conversation_id,
            message_tsvector.op("@@")(search_term.c.tsq),
            ~and_(
                TutorMessage.role == "human",
                func.regexp_replace(
                    func.lower(TutorMessage.content),
                    r"[^[:alnum:]_]+",
                    "",
                    "g",
                )
                == search_term.c.normalized_query,
            ),
        )
        .order_by(keyword_rank_score.desc())
        .limit(limit)
        .cte("keyword_results")
    )

    # Step 6: Combine the semantic and keyword rankings.
    # A message can appear in both result lists.
    ranked_results = (
        select(
            semantic_results.c.message_id,
            semantic_results.c.semantic_rank,
            null().cast(BigInteger).label("keyword_rank"),
        )
        .union_all(
            select(
                keyword_results.c.message_id,
                null().cast(BigInteger).label("semantic_rank"),
                keyword_results.c.keyword_rank,
            )
        )
        .cte("ranked_results")
    )

    # Step 7: Calculate Reciprocal Rank Fusion (RRF) scores.
    # The constant 60 preserves the original RRF formula.
    semantic_score = case(
        (
            ranked_results.c.semantic_rank.is_not(None),
            1.0 / (60 + ranked_results.c.semantic_rank),
        ),
        else_=0.0,
    )

    keyword_score = case(
        (
            ranked_results.c.keyword_rank.is_not(None),
            1.0 / (60 + ranked_results.c.keyword_rank),
        ),
        else_=0.0,
    )

    rrf_scores = (
        select(
            ranked_results.c.message_id,
            func.sum(
                semantic_score + keyword_score
            ).label("rrf_score"),
            func.min(
                ranked_results.c.semantic_rank
            ).label("semantic_rank"),
            func.min(
                ranked_results.c.keyword_rank
            ).label("keyword_rank"),
        )
        .group_by(ranked_results.c.message_id)
        .cte("rrf_scores")
    )

    # Step 8: Fetch message details, ordered by the combined RRF score.
    final_statement = (
        select(
            TutorMessage.id.label("message_id"),
            TutorMessage.role,
            TutorMessage.content,
            TutorMessage.created_at,
            rrf_scores.c.rrf_score,
            rrf_scores.c.semantic_rank,
            rrf_scores.c.keyword_rank,
        )
        .join(
            rrf_scores,
            TutorMessage.id == rrf_scores.c.message_id,
        )
        .where(TutorMessage.conversation_id == conversation_id)
        .order_by(rrf_scores.c.rrf_score.desc())
        .limit(limit)
    )

    # Step 9: Execute the SQLAlchemy-built statement.
    with SessionLocal() as db:
        rows = db.execute(final_statement).mappings().all()

    # Step 10: Return ordinary Python dictionaries to the tutor service.
    return [
        {
            "message_id": row["message_id"],
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"],
            "rrf_score": float(row["rrf_score"]),
            "semantic_rank": row["semantic_rank"],
            "keyword_rank": row["keyword_rank"],
        }
        for row in rows
    ]



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