from fastapi import FastAPI
from fastapi.testclient import TestClient

from books_rec_api.context import eval_request_id_var, eval_run_id_var
from books_rec_api.middleware import EvalContextMiddleware


def test_eval_context_middleware() -> None:
    app = FastAPI()
    app.add_middleware(EvalContextMiddleware)

    @app.get("/")
    def read_root() -> dict:
        return {
            "eval_run_id": eval_run_id_var.get(),
            "eval_request_id": eval_request_id_var.get(),
        }

    client = TestClient(app)

    # Without headers
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"eval_run_id": None, "eval_request_id": None}

    # With headers
    response = client.get("/", headers={"X-Eval-Run-Id": "run-123", "X-Request-Id": "req-456"})
    assert response.status_code == 200
    assert response.json() == {
        "eval_run_id": "run-123",
        "eval_request_id": "req-456",
    }
