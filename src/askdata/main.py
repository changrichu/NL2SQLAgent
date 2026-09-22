"""AskData FastAPI entry point."""
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import __version__
from .agent.nl2sql_agent import NL2SQLAgent
from .llm_client import LLMClient
from .memory.query_history import QueryHistory


app = FastAPI(
    title="AskData API",
    version=__version__,
    description="Natural-language data analysis over enterprise data sources.",
)

# Per-datasource agent cache (single-process demo; use a pool in production).
_agents: dict[str, NL2SQLAgent] = {}
_history = QueryHistory()


def _get_agent(datasource: str) -> NL2SQLAgent:
    if datasource not in _agents:
        llm = LLMClient()
        _agents[datasource] = NL2SQLAgent(llm=llm, datasource=datasource)
    return _agents[datasource]


class QueryRequest(BaseModel):
    query: str
    datasource: str = "postgres"
    user_id: str = "default"


class QueryResponse(BaseModel):
    sql: str
    results: list
    row_count: int
    explanation: str


class ErrorResponse(BaseModel):
    error: str
    sql: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}


@app.post("/query", response_model=QueryResponse, responses={400: {"model": ErrorResponse}})
async def query(req: QueryRequest):
    try:
        agent = _get_agent(req.datasource)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result = agent.run(query=req.query, user_id=req.user_id)
    _history.add(req.query, result, user_id=req.user_id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return QueryResponse(**result)


@app.get("/history")
def history(limit: int = 10) -> List[dict]:
    return _history.recent(limit)
