"""HTTP timing log line with caller principal (human vs service identity).

Set by the auth dependencies on ``request.state.principal``
(``user:<id>`` / ``svc:<client_id>``); routes without authentication log ``-``.
"""

from __future__ import annotations

import logging
import time

from starlette.requests import Request

timing_logger = logging.getLogger("api.timing")


async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    principal = getattr(request.state, "principal", "-")
    timing_logger.info(
        "%s %s → %s | %.1fms | principal=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        principal,
    )
    return response
