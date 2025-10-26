if __name__ == "__main__":
    import asyncio
    from app import start_fastapi

    # import argparse

    # args = argparse.ArgumentParser()
    # parsed_args = args.parse_args()
    asyncio.run(start_fastapi())  # parsed_args))
# chart-backend/main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import secrets, time, json

app = FastAPI()
SESSIONS = {}  # session_id -> { user_id, name, created_ms }

# Called from your web after the Sonolus POST succeeds (or directly by sonoserver).
# Goal: mint a website session cookie/token for charts.kizuruki.com.
@app.post("/api/accounts/session/external/complete")
async def external_complete(request: Request):
    body = await request.json()
    # Trust boundary: in production, require an internal secret or
    # have sonoserver call this over localhost-only.
    user = body.get("userProfile") or {}
    user_id = user.get("id") or f"anon-{secrets.token_hex(6)}"
    name = user.get("name") or "Sonolus User"

    sid = secrets.token_urlsafe(24)
    SESSIONS[sid] = {"user_id": user_id, "name": name, "created_ms": int(time.time() * 1000)}
    return JSONResponse({"session": sid, "user": {"id": user_id, "name": name}})

@app.get("/api/accounts/session/me")
async def session_me(request: Request):
    # Expect session token in Authorization: Bearer <sid> or cookie (your choice)
    auth = request.headers.get("authorization") or ""
    sid = auth.replace("Bearer ", "").strip()
    data = SESSIONS.get(sid)
    if not data:
        raise HTTPException(401, "No session")
    return JSONResponse({"user": {"id": data["user_id"], "name": data["name"]}})
