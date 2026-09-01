from __future__ import annotations

from fastapi import FastAPI, Request, Response

from packages.core.correlation import new_correlation_id, set_correlation_id

app = FastAPI(title="FitnessOS Athlete API", version="0.1.0")


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    correlation_id = request.headers.get("x-correlation-id") or new_correlation_id()
    set_correlation_id(correlation_id)
    response: Response = await call_next(request)
    response.headers["x-correlation-id"] = correlation_id
    return response


@app.get("/health/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    # Dependency-aware checks are added as platform dependencies are introduced.
    return {"status": "ready"}
