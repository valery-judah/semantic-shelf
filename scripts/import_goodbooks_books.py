from __future__ import annotations

import argparse
from pathlib import Path

from scripts.goodbooks_books_importer import import_books


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Goodbooks books into the books table.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Path to goodbooks-10k-extended repository.",
    )
    parser.add_argument(
        "--use-samples",
        action="store_true",
        help="Use samples/books.csv instead of books_enriched.csv.",
    )
    parser.add_argument(
        "--truncate-books",
        action="store_true",
        help="Truncate books table before import.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of rows per upsert batch.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats = import_books(
        data_dir=args.data_dir,
        use_samples=args.use_samples,
        truncate_books=args.truncate_books,
        batch_size=args.batch_size,
    )
    print(
        "Import finished. "
        f"total={stats.total_rows} processed={stats.processed_rows} "
        f"inserted={stats.inserted_rows} updated={stats.updated_rows} "
        f"skipped={stats.skipped_rows} errors={stats.error_rows}"
    )


if __name__ == "__main__":
    main()
