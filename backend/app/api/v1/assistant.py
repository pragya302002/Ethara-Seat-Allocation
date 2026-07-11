from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_employee
from app.database.session import get_db
from app.models.employee import Employee as EmployeeModel
from app.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse
from app.services.ai_assistant_service import AIAssistantService

router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


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
