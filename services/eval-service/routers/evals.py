"""Eval execution endpoint — called by the API Gateway, not by end users directly."""

from fastapi import APIRouter
from runner import run_test_case
from schemas import ExecuteSuiteRequest, ExecuteSuiteResponse

router = APIRouter(prefix="/api/v1", tags=["eval"])


@router.post("/execute-suite", response_model=ExecuteSuiteResponse)
async def execute_suite(req: ExecuteSuiteRequest) -> ExecuteSuiteResponse:
    """Run every test case in the suite against the agent, sequentially, and score each."""
    results = [await run_test_case(req.agent, tc) for tc in req.test_cases]
    return ExecuteSuiteResponse(results=results)
