import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.app.routers.incidents import router as incidents_router
from services.app.routers.suppliers import router as suppliers_router
from services.app.routers.users import router as users_router
from services.app.routers.auth import router as auth_router
from services.app.routers.profiles import router as profiles_router


logger = logging.getLogger(__name__)

app = FastAPI(title="HealthCore API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    _request: Request, exc: RequestValidationError
):
    """Return 400 with clear field messages instead of raw 422 traces."""
    errors: list[dict[str, str]] = []
    for item in exc.errors():
        loc = item.get("loc") or ()
        field = str(loc[-1]) if loc else "body"
        if field in {"body", "query", "path"} and len(loc) > 1:
            field = str(loc[-1])
        msg = str(item.get("msg") or "Invalid value")
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, ") :]
        errors.append({"field": field, "message": msg})
    return JSONResponse(status_code=400, content={"detail": errors})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Never expose stack traces to API clients."""
    if isinstance(exc, (HTTPException, StarletteHTTPException, RequestValidationError)):
        # Let FastAPI/Starlette dedicated handlers run
        raise exc
    logger.exception(
        "Unhandled error on %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please try again later.",
        },
    )


app.include_router(incidents_router)
app.include_router(suppliers_router)
app.include_router(users_router)
app.include_router(auth_router)
app.include_router(profiles_router)
