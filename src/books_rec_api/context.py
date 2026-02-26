import contextvars

eval_run_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "eval_run_id", default=None
)
eval_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "eval_request_id", default=None
)
