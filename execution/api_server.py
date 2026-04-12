from __future__ import annotations

from datetime import date
from typing import Callable

from fastapi import Body, FastAPI, HTTPException, Query
from pydantic import BaseModel


class HistoricalRequest(BaseModel):
    from_date: date
    to_date: date


def create_app(
    *,
    run_historical: Callable[[date, date], dict],
    get_status: Callable[[], dict],
) -> FastAPI:
    web_app = FastAPI(title="AI Email Bot Phase 2")

    @web_app.get("/")
    def health() -> dict:
        payload = get_status()
        payload["endpoints"] = ["POST /classify-historical", "GET /classify-historical"]
        return payload

    def _run(from_date: date, to_date: date) -> dict:
        if from_date > to_date:
            raise HTTPException(status_code=400, detail="from_date must be <= to_date")
        try:
            return run_historical(from_date, to_date)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @web_app.post("/classify-historical")
    def classify_historical_post(payload: HistoricalRequest = Body(...)) -> dict:
        return _run(payload.from_date, payload.to_date)

    @web_app.get("/classify-historical")
    def classify_historical_get(
        from_date: date = Query(...),
        to_date: date = Query(...),
    ) -> dict:
        return _run(from_date, to_date)

    return web_app
