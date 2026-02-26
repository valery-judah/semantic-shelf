import json
import logging
from datetime import UTC, datetime

from books_rec_api.context import eval_request_id_var, eval_run_id_var


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": self.service_name,
            "message": record.getMessage(),
        }

        eval_run_id = eval_run_id_var.get()
        if eval_run_id:
            payload["run_id"] = eval_run_id

        eval_request_id = eval_request_id_var.get()
        if eval_request_id:
            payload["request_id"] = eval_request_id

        default_keys = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
        }
        for key, value in record.__dict__.items():
            if key not in default_keys and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload)


def configure_logging(level: str, output_format: str, service_name: str) -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level.upper())

    handler = logging.StreamHandler()

    if output_format.lower() == "json":
        handler.setFormatter(JsonFormatter(service_name=service_name))
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%SZ",
            )
        )

    root_logger.addHandler(handler)
