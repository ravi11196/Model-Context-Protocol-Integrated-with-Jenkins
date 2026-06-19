import hashlib
import hmac
import logging
import os
import time
import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from fastmcp import FastMCP
from functions import register_tools
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from git_tools import register_git_tools
from autofix import register_autofix


# ============================================================
# LOAD ENV
# ============================================================

load_dotenv()

JENKINS_URL = os.getenv("JENKINS_URL", "").strip()
USERNAME = os.getenv("USERNAME", "").strip()
API_TOKEN = os.getenv("API_TOKEN", "").strip()
API_KEY_HASH = os.getenv("API_KEY_HASH", "").strip()

RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_MAX_HITS = int(os.getenv("RATE_LIMIT_MAX_HITS", "10"))

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

logger.info(f" Jenkins URL: [{JENKINS_URL}]")

# ============================================================
# AUTH HELPERS
# ============================================================

def hash_key(plain_key: str) -> str:
    return hashlib.sha256(plain_key.encode()).hexdigest()


def is_valid_api_key(incoming_key: str) -> bool:
    incoming_hash = hash_key(incoming_key)
    return hmac.compare_digest(incoming_hash, API_KEY_HASH)

# ============================================================
# RATE LIMITER
# ============================================================

_attempts: dict = {}

def is_brute_force(ip: str) -> bool:
    now = time.monotonic()
    bucket = _attempts.get(ip, {"count": 0, "start": now})

    if now - bucket["start"] > RATE_LIMIT_WINDOW:
        bucket = {"count": 0, "start": now}

    bucket["count"] += 1
    _attempts[ip] = bucket

    return bucket["count"] > RATE_LIMIT_MAX_HITS

# ============================================================
# AUTH MIDDLEWARE
# ============================================================

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # Allow health endpoint without API key
        if request.url.path == "/health":
            return await call_next(request)

        raw_key = (
            request.headers.get("x-api-key")
            or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        )

        if not raw_key:
            return JSONResponse({"error": "Missing API key."}, status_code=401)

        if not is_valid_api_key(raw_key):
            ip = request.client.host if request.client else "unknown"

            if is_brute_force(ip):
                logger.warning(f"Brute force detected | ip={ip}")
                return JSONResponse({"error": "Too many attempts."}, status_code=429)

            logger.warning(f"Invalid API key | ip={ip}")
            return JSONResponse({"error": "Invalid API key."}, status_code=401)

        logger.info(f"Authorized request | ip={request.client.host}")
        return await call_next(request)

# ============================================================
# MCP SERVER
# ============================================================

mcp = FastMCP("jenkins-tools")

def auth():
    return (USERNAME, API_TOKEN)

def get_crumb():
    url = f"{JENKINS_URL}/crumbIssuer/api/json"

    r = requests.get(url, auth=auth(), timeout=10)
    r.raise_for_status()   # better error handling

    data = r.json()
    return {
        data["crumbRequestField"]: data["crumb"]
    }

# ============================================================
# REGISTER TOOLS
# ============================================================

register_tools(
    mcp,
    JENKINS_URL,
    auth,
    get_crumb

)

register_git_tools(
    mcp,
    os.getenv("GIT_API_URL"),
    os.getenv("GIT_TOKEN")
)

register_autofix(mcp)
# ============================================================
# FASTAPI APP
# ============================================================

#mcp_app = mcp.http_app()
mcp_app = mcp.http_app(transport="http")
#mcp_app = mcp.http_app(streamable=False)

app = FastAPI(
    lifespan=mcp_app.lifespan
)

@app.get("/health")
async def health():
    return {"status": "ok"}

# Add auth middleware
app.add_middleware(APIKeyMiddleware)

# Clean mount (NO prefix hacking needed)
app.mount("/mcp-server", mcp_app)

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn

    print("==== MAIN APP ROUTES ====")
    for route in app.routes:
        try:
            print(route.path)
        except Exception:
            print(route)

    print("==== MCP APP ROUTES ====")
    for route in mcp_app.routes:
        try:
            print(route.path)
        except Exception:
            print(route)

    uvicorn.run(app, host="0.0.0.0", port=8000)
