import pytest

from scripts.goodbooks_interactions_importer import (
    map_book_tag_row,
    map_dataset_user_row,
    map_rating_row,
    map_tag_row,
    map_to_read_row,
)


def test_map_rating_row() -> None:
    mapped = map_rating_row({"user_id": "12", "book_id": "345", "rating": "4"})
    assert mapped == {"user_id": 12, "book_id": "345", "rating": 4}


def test_map_rating_row_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid integer for rating"):
        map_rating_row({"user_id": "12", "book_id": "345", "rating": "x"})


def test_map_tag_row() -> None:
    assert map_tag_row({"tag_id": "7", "tag_name": "favorites"}) == {
        "tag_id": 7,
        "tag_name": "favorites",
    }


def test_map_tag_row_requires_name() -> None:
    with pytest.raises(ValueError, match="tag_name is required"):
        map_tag_row({"tag_id": "7", "tag_name": ""})


def test_map_book_tag_row() -> None:
    assert map_book_tag_row({"goodreads_book_id": "1", "tag_id": "2", "count": "99"}) == {
        "goodreads_book_id": 1,
        "tag_id": 2,
        "count": 99,
    }


def test_map_to_read_row() -> None:
    assert map_to_read_row({"user_id": "9", "book_id": "8"}) == {"user_id": 9, "book_id": "8"}


def test_map_dataset_user_row() -> None:
    assert map_dataset_user_row({"user_id": "42"}) == {"user_id": 42}
