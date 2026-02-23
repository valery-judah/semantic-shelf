import json
from pathlib import Path

from books_rec_api.main import app


def main() -> None:
    schema = app.openapi()
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)

    output_path = docs_dir / "openapi.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    print(f"OpenAPI spec successfully written to {output_path}")


if __name__ == "__main__":
    main()
