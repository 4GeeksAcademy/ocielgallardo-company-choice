"""Knowledge-assistant endpoint (RAG over clinic policies/procedures)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from data.pipelines.rag import query as answer_question
from services.app.core.deps import get_current_user
from services.app.models.user import UserPublic
from services.app.schemas import RagQueryRequest, RagQueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/query", response_model=RagQueryResponse)
def query_knowledge_base(
    body: RagQueryRequest,
    _current_user: UserPublic = Depends(get_current_user),
) -> RagQueryResponse:
    """Answer a coordinator question from the Qdrant knowledge base.

    Thin wrapper over ``query()`` from ``data/pipelines/rag`` — no
    retrieval/generation logic here. Returns only the model-generated
    string (never raw Qdrant chunks or similarity scores). Returns 503
    when RAG is not configured or Qdrant is unreachable.
    """
    try:
        answer = answer_question(body.question)
    except RuntimeError as exc:
        logger.warning("RAG unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # Qdrant connectivity, LLM transport, ...
        logger.exception("RAG query failed for question %.60r", body.question)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge assistant is temporarily unavailable.",
        ) from exc
    return RagQueryResponse(question=body.question, answer=answer)
