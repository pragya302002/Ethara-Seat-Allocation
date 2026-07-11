from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_employee
from app.database.session import get_db
from app.models.employee import Employee as EmployeeModel
from app.schemas.assistant import (
    AIQueryRequest,
    AIQueryResponse,
    AssistantQueryRequest,
    AssistantQueryResponse,
)
from app.services.ai_assistant_service import AIAssistantService

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])
ai_router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.post("/query", response_model=AssistantQueryResponse)
async def ask_assistant(
    payload: AssistantQueryRequest,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    """Natural language query interface. Read-only — see
    ai_assistant_service.py docstring for the scope reasoning."""
    answer, understood = await AIAssistantService(db).ask(payload.question)
    return AssistantQueryResponse(answer=answer, query_understood=understood)


@ai_router.post("/query", response_model=AIQueryResponse)
async def ai_query(
    payload: AIQueryRequest,
    db: AsyncSession = Depends(get_db),
    _: EmployeeModel = Depends(get_current_employee),
):
    """Matches the spec's exact POST /ai/query contract
    ({"query": "..."} -> {"answer": "..."}). Thin wrapper around the same
    AIAssistantService as /assistant/query — kept as a separate route
    rather than renaming the original, since the frontend is already
    built against /assistant/query and duplicating the route is a lot
    lower-risk than renaming it under time pressure."""
    answer, _understood = await AIAssistantService(db).ask(payload.query)
    return AIQueryResponse(answer=answer)
