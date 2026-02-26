from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from books_rec_api.context import eval_request_id_var, eval_run_id_var


class EvalContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        eval_run_id = request.headers.get("X-Eval-Run-Id")
        eval_request_id = request.headers.get("X-Request-Id")

        run_token = eval_run_id_var.set(eval_run_id)
        req_token = eval_request_id_var.set(eval_request_id)

        try:
            return await call_next(request)
        finally:
            eval_run_id_var.reset(run_token)
            eval_request_id_var.reset(req_token)
