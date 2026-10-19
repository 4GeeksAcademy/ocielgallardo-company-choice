"""Agent endpoint (compiled LangGraph over the clinic knowledge base)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from data.pipelines.agent_graph import run_agent
from services.app.core.deps import get_current_user
from services.app.models.user import UserPublic
from services.app.schemas import AgentQueryRequest, RagQueryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=RagQueryResponse)
def query_agent(
    body: AgentQueryRequest,
    current_user: UserPublic = Depends(get_current_user),
) -> RagQueryResponse:
    """Answer a coordinator question through the compiled agent graph.

    Thin wrapper over ``run_agent()`` — no retrieval/generation logic here.
    The memory session is the caller-provided ``session_id`` when present,
    otherwise the authenticated user (one pending memory proposal per
    session; see ``docs/rag/agent-graph.md`` §10).
    Returns only the model-generated string (never raw chunks or scores).
    Returns 503 when the knowledge backend is unavailable; never a raw
    traceback.
    """
    session_id = (body.session_id or "").strip() or f"user:{current_user.id}"
    try:
        answer = run_agent(body.question, session_id=session_id)["answer"]
    except RuntimeError as exc:
        logger.warning("Agent unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge assistant is temporarily unavailable.",
        ) from exc
    except Exception as exc:  # Qdrant connectivity, LLM transport, ...
        logger.exception("Agent query failed for question %.60r", body.question)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge assistant is temporarily unavailable.",
        ) from exc
    return RagQueryResponse(question=body.question, answer=answer)
