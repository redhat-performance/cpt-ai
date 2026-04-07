"""
CPT AI Regression Analyzer - REST API

FastAPI wrapper around cpt_core for programmatic access.

Usage:
    uvicorn api:app --host 0.0.0.0 --port 8000
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

# Add project root to path for cpt_core imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from cpt_core import CPTConfig, RegressionAnalyzer, ComparisonResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared analyzer instance (connected once at startup)
# ---------------------------------------------------------------------------
analyzer: Optional[RegressionAnalyzer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global analyzer
    config = CPTConfig.from_env()
    analyzer = RegressionAnalyzer(config)
    await analyzer.connect()
    logger.info("RegressionAnalyzer connected")
    yield
    await analyzer.disconnect()
    logger.info("RegressionAnalyzer disconnected")


app = FastAPI(
    title="CPT AI Regression Analyzer API",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RunParams(BaseModel):
    cloud: str = Field(..., examples=["aws"])
    os_vendor: str = Field("rhel", examples=["rhel"])
    os_version: str = Field(..., examples=["9.6"])
    instance: str = Field(..., examples=["m7i.4xlarge"])
    benchmark: str = Field(..., examples=["passmark"])


class CompareRequest(BaseModel):
    run1: RunParams
    run2: RunParams
    detail_level: str = Field("medium", pattern="^(basic|medium|expert)$")


class CompareResponse(BaseModel):
    geomean_delta_pct: float
    geomean_value: float = 1.0
    status: str
    severity: str = "NONE"
    threshold: float = 5.0
    matched_metrics: int
    regressions_count: int = 0
    improvements_count: int = 0
    analysis: str
    run1_id: str
    run2_id: str
    detail_level: str


class AskRequest(BaseModel):
    run1: RunParams
    run2: RunParams
    detail_level: str = Field("medium", pattern="^(basic|medium|expert)$")
    question: str
    chat_history: list[dict] = Field(default_factory=list)


class AskResponse(BaseModel):
    answer: str


class FilterRequest(BaseModel):
    field: str = Field(..., examples=["cloud"])
    filters: Optional[dict] = None


class FilterResponse(BaseModel):
    values: list[dict]


# ---------------------------------------------------------------------------
# Field name mapping (short API names -> OpenSearch field paths)
# ---------------------------------------------------------------------------
FIELD_MAP = {
    "cloud": "metadata.cloud_provider",
    "os_vendor": "metadata.os_vendor",
    "os_version": "system_under_test.operating_system.version",
    "instance": "metadata.instance_type",
    "benchmark": "test.name",
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/compare", response_model=CompareResponse)
async def compare(req: CompareRequest):
    """Compare two benchmark runs and get AI regression analysis."""
    try:
        result = await analyzer.compare(
            run1_params=req.run1.model_dump(),
            run2_params=req.run2.model_dump(),
            detail_level=req.detail_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return CompareResponse(
        geomean_delta_pct=round(result.geomean['delta_pct'], 2),
        geomean_value=round(result.geomean.get('geomean_value', 1.0), 6),
        status=result.geomean['status'],
        severity=result.geomean.get('severity', 'NONE'),
        threshold=result.geomean.get('threshold', 5.0),
        matched_metrics=result.geomean['matched'],
        regressions_count=result.geomean.get('regressions_count', 0),
        improvements_count=result.geomean.get('improvements_count', 0),
        analysis=result.analysis,
        run1_id=result.run1['id'],
        run2_id=result.run2['id'],
        detail_level=result.detail_level,
    )


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    """Ask a follow-up question about a comparison.

    Re-runs the comparison first so the AI has full context.
    """
    try:
        result = await analyzer.compare(
            run1_params=req.run1.model_dump(),
            run2_params=req.run2.model_dump(),
            detail_level=req.detail_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    answer = await analyzer.ask(req.question, result, req.chat_history)
    return AskResponse(answer=answer)


@app.post("/filters", response_model=FilterResponse)
async def filters(req: FilterRequest):
    """Get available dropdown values for a filter field (cloud, os_vendor, etc.)."""
    os_field = FIELD_MAP.get(req.field)
    if not os_field:
        raise HTTPException(status_code=400, detail=f"Unknown field: {req.field}. Valid fields: {list(FIELD_MAP.keys())}")

    # Translate filter keys from short names to OpenSearch field paths
    os_filters = None
    if req.filters:
        os_filters = {}
        for k, v in req.filters.items():
            mapped = FIELD_MAP.get(k)
            if not mapped:
                raise HTTPException(status_code=400, detail=f"Unknown filter field: {k}. Valid fields: {list(FIELD_MAP.keys())}")
            os_filters[mapped] = v

    options = await analyzer.get_filter_options(os_field, os_filters)
    return FilterResponse(
        values=[{"value": v, "count": c} for v, c in options]
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
