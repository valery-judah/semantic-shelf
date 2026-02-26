import json
import logging

from books_rec_api.context import eval_request_id_var, eval_run_id_var
from books_rec_api.logging_config import JsonFormatter, configure_logging


def test_json_formatter_emits_expected_fields() -> None:
    formatter = JsonFormatter(service_name="books-rec-api")
    record = logging.LogRecord(
        name="books_rec_api.main",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello",
        args=(),
        exc_info=None,
    )

    payload = json.loads(formatter.format(record))

    assert payload["service"] == "books-rec-api"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "books_rec_api.main"
    assert payload["message"] == "hello"
    assert "timestamp" in payload


def test_json_formatter_emits_context_vars() -> None:
    formatter = JsonFormatter(service_name="books-rec-api")
    record = logging.LogRecord(
        name="books_rec_api.main",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello",
        args=(),
        exc_info=None,
    )

    t1 = eval_run_id_var.set("run-123")
    t2 = eval_request_id_var.set("req-456")

    try:
        payload = json.loads(formatter.format(record))
        assert payload["eval_run_id"] == "run-123"
        assert payload["request_id"] == "req-456"
    finally:
        eval_run_id_var.reset(t1)
        eval_request_id_var.reset(t2)


def test_configure_logging_plain_text_format() -> None:
    configure_logging(level="DEBUG", output_format="plain", service_name="books-rec-api")

    root_logger = logging.getLogger()

    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0].formatter, logging.Formatter)
