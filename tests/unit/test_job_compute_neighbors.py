import contextlib
from collections.abc import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from books_rec_api.models import Book, BookSimilarity
from scripts.job_compute_neighbors import (
    compute_jaccard,
    compute_neighbors,
    normalize_metadata,
)


def test_normalize_metadata_empty() -> None:
    assert normalize_metadata(None) == frozenset()
    assert normalize_metadata([]) == frozenset()
    assert normalize_metadata(["", "   "]) == frozenset()


def test_normalize_metadata_values() -> None:
    assert normalize_metadata([" Author 1 ", "Author 2"]) == frozenset(["Author 1", "Author 2"])


def test_compute_jaccard() -> None:
    assert compute_jaccard(frozenset(["a", "b"]), frozenset(["b", "c"])) == 0.3333333333333333
    assert compute_jaccard(frozenset(), frozenset()) == 0.0


def test_compute_neighbors(db_session: Session) -> None:
    b1 = Book(
        id="b1",
        title="Book 1",
        authors=["A1", "A2"],
        genres=["G1"],
        source="goodbooks",
    )
    b2 = Book(
        id="b2",
        title="Book 2",
        authors=["A2"],
        genres=["G1", "G2"],
        source="goodbooks",
    )
    b3 = Book(
        id="b3",
        title="Book 3",
        authors=["A3"],
        genres=["G3"],
        source="goodbooks",
    )
    b4 = Book(
        id="b4",
        title="Book 4",
        authors=["A2"],
        genres=["G1", "G2"],
        source="goodbooks",
    )
    db_session.add_all([b1, b2, b3, b4])
    db_session.commit()

    @contextlib.contextmanager
    def test_session_factory() -> Iterator[Session]:
        yield db_session

    compute_neighbors(k=2, session_factory=test_session_factory)

    stmt = select(BookSimilarity).order_by(BookSimilarity.book_id)
    sims = db_session.scalars(stmt).all()

    assert len(sims) == 4

    sim_map = {s.book_id: s for s in sims}
    s1 = sim_map["b1"]

    assert s1.neighbor_ids == ["b2", "b4"]
    assert "b1" not in s1.neighbor_ids

    assert len(s1.neighbor_ids) <= 2
