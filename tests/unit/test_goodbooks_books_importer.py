from decimal import Decimal

import pytest

from scripts.goodbooks_books_importer import (
    map_book_row,
    parse_listish,
    parse_optional_decimal,
    parse_optional_int,
)


def test_parse_listish_literal_list() -> None:
    assert parse_listish("['a', 'b']") == ["a", "b"]


def test_parse_listish_comma_text() -> None:
    assert parse_listish("J.K. Rowling, Mary GrandPré") == ["J.K. Rowling", "Mary GrandPré"]


def test_parse_listish_empty() -> None:
    assert parse_listish("") == []


def test_parse_optional_int_float_like() -> None:
    assert parse_optional_int("2008.0") == 2008


def test_parse_optional_int_none() -> None:
    assert parse_optional_int(None) is None


def test_parse_optional_int_invalid() -> None:
    with pytest.raises(ValueError, match="Invalid integer value"):
        parse_optional_int("abc")


def test_parse_optional_decimal_value() -> None:
    assert parse_optional_decimal("4.34") == Decimal("4.34")


def test_map_book_row_enriched_shape() -> None:
    row = {
        "book_id": "1",
        "title": "The Hunger Games (The Hunger Games, #1)",
        "authors": "['Suzanne Collins']",
        "genres": "['young-adult', 'fiction']",
        "original_publication_year": "2008.0",
        "goodreads_book_id": "2767052",
        "average_rating": "4.34",
        "pages": "374.0",
        "publishDate": "09/14/08",
    }

    mapped = map_book_row(row)

    assert mapped["id"] == "1"
    assert mapped["title"] == "The Hunger Games (The Hunger Games, #1)"
    assert mapped["authors"] == ["Suzanne Collins"]
    assert mapped["genres"] == ["young-adult", "fiction"]
    assert mapped["publication_year"] == 2008
    assert mapped["goodreads_book_id"] == 2767052
    assert mapped["average_rating"] == Decimal("4.34")
    assert mapped["pages"] == 374
    assert mapped["publish_date_raw"] == "09/14/08"
    assert mapped["source"] == "goodbooks"


def test_map_book_row_requires_title() -> None:
    with pytest.raises(ValueError, match="title is required"):
        map_book_row({"book_id": "10", "title": ""})
