import os
import time
import random
import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

MODE = os.environ.get("MODE", "stable")
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
APP_PORT = int(os.environ.get("APP_PORT", 3000))
START_TIME = time.time()

# Chaos state
chaos_state = {"mode": None, "duration": None, "rate": None}


def add_mode_header(response: JSONResponse) -> JSONResponse:
    if MODE == "canary":
        response.headers["X-Mode"] = "canary"
    return response


@app.middleware("http")
async def chaos_middleware(request: Request, call_next):
    if MODE == "canary" and chaos_state["mode"] == "slow":
        duration = chaos_state.get("duration", 0)
        await asyncio.sleep(duration)

    if MODE == "canary" and chaos_state["mode"] == "error":
        rate = chaos_state.get("rate", 0)
        if random.random() < rate:
            resp = JSONResponse(
                status_code=500,
                content={"error": "Chaos error injection", "mode": MODE},
            )
            if MODE == "canary":
                resp.headers["X-Mode"] = "canary"
            return resp

    response = await call_next(request)
    if MODE == "canary":
        response.headers["X-Mode"] = "canary"
    return response


@app.get("/")
async def root():
    now = datetime.now(timezone.utc).isoformat()
    return add_mode_header(JSONResponse(content={
        "message": f"Welcome to SwiftDeploy API — running in {MODE} mode",
        "mode": MODE,
        "version": APP_VERSION,
        "timestamp": now,
    }))


@app.get("/healthz")
async def healthz():
    uptime = round(time.time() - START_TIME, 2)
    return add_mode_header(JSONResponse(content={
        "status": "ok",
        "uptime_seconds": uptime,
        "mode": MODE,
        "version": APP_VERSION,
    }))


@app.post("/chaos")
async def chaos(request: Request):
    if MODE != "canary":
        return JSONResponse(
            status_code=403,
            content={"error": "Chaos endpoint only available in canary mode"},
        )

    body = await request.json()
    mode = body.get("mode")

    if mode == "slow":
        chaos_state["mode"] = "slow"
        chaos_state["duration"] = body.get("duration", 1)
        chaos_state["rate"] = None
        msg = f"Chaos mode set to slow with duration {chaos_state['duration']}s"

    elif mode == "error":
        chaos_state["mode"] = "error"
        chaos_state["rate"] = body.get("rate", 0.5)
        chaos_state["duration"] = None
        msg = f"Chaos mode set to error with rate {chaos_state['rate']}"

    elif mode == "recover":
        chaos_state["mode"] = None
        chaos_state["duration"] = None
        chaos_state["rate"] = None
        msg = "Chaos mode cleared — service recovering"

    else:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown chaos mode: {mode}"},
        )

    resp = JSONResponse(content={"message": msg, "chaos": chaos_state})
    resp.headers["X-Mode"] = "canary"
    return resp


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=APP_PORT, reload=False)
