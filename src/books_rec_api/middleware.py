import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from books_rec_api.context import eval_request_id_var, eval_run_id_var

logger = logging.getLogger("books_rec_api.request")


class EvalContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        eval_run_id = request.headers.get("X-Eval-Run-Id") or "none"
        eval_request_id = request.headers.get("X-Request-Id") or f"req-{uuid.uuid4().hex[:12]}"

        run_token = eval_run_id_var.set(eval_run_id)
        req_token = eval_request_id_var.set(eval_request_id)
        start = time.perf_counter()

        try:
            response = await call_next(request)
            latency_ms = max((time.perf_counter() - start) * 1000, 0.0)
            logger.info(
                "http_request_complete",
                extra={
                    "run_id": eval_run_id,
                    "request_id": eval_request_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "status_code": response.status_code,
                    "latency_ms": round(latency_ms, 3),
                },
            )
            return response
        finally:
            eval_run_id_var.reset(run_token)
            eval_request_id_var.reset(req_token)
