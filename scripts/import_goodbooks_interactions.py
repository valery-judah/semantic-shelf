from __future__ import annotations

import argparse
from pathlib import Path

from scripts.goodbooks_interactions_importer import import_interactions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Goodbooks ratings/tags/book_tags/to_read tables."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Path to goodbooks-10k-extended repository.",
    )
    parser.add_argument(
        "--use-samples",
        action="store_true",
        help="Read CSV files from samples/ subdirectory.",
    )
    parser.add_argument(
        "--truncate-tables",
        action="store_true",
        help="Truncate ratings, tags, book_tags and to_read before import.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Number of rows per bulk upsert batch.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stats = import_interactions(
        data_dir=args.data_dir,
        use_samples=args.use_samples,
        truncate_tables=args.truncate_tables,
        batch_size=args.batch_size,
    )

    print(
        "dataset_users: "
        f"total={stats.dataset_users.total_rows} inserted={stats.dataset_users.inserted_rows} "
        f"updated={stats.dataset_users.updated_rows} errors={stats.dataset_users.error_rows}"
    )
    print(
        "ratings: "
        f"total={stats.ratings.total_rows} inserted={stats.ratings.inserted_rows} "
        f"updated={stats.ratings.updated_rows} errors={stats.ratings.error_rows}"
    )
    print(
        "tags: "
        f"total={stats.tags.total_rows} inserted={stats.tags.inserted_rows} "
        f"updated={stats.tags.updated_rows} errors={stats.tags.error_rows}"
    )
    print(
        "book_tags: "
        f"total={stats.book_tags.total_rows} inserted={stats.book_tags.inserted_rows} "
        f"updated={stats.book_tags.updated_rows} errors={stats.book_tags.error_rows}"
    )
    print(
        "to_read: "
        f"total={stats.to_read.total_rows} inserted={stats.to_read.inserted_rows} "
        f"updated={stats.to_read.updated_rows} errors={stats.to_read.error_rows}"
    )


if __name__ == "__main__":
    main()
