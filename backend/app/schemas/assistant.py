from pydantic import BaseModel


class AssistantQueryRequest(BaseModel):
    question: str


class AssistantQueryResponse(BaseModel):
    answer: str
    query_understood: bool


class AIQueryRequest(BaseModel):
    """Matches the spec's exact POST /ai/query contract: {"query": "..."}"""
    query: str


class AIQueryResponse(BaseModel):
    """Matches the spec's exact POST /ai/query contract: {"answer": "..."}"""
    answer: str
