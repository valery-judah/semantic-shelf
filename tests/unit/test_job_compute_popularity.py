import contextlib
from collections.abc import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from books_rec_api.models import Book, BookPopularity
from scripts.job_compute_popularity import compute_popularity


def test_compute_popularity(db_session: Session) -> None:
    b1 = Book(id="b1", title="B1", source="s", ratings_count=100)
    b2 = Book(id="b2", title="B2", source="s", ratings_count=200)
    b3 = Book(id="b3", title="B3", source="s", ratings_count=None)
    b4 = Book(id="b4", title="B4", source="s", ratings_count=50)

    db_session.add_all([b1, b2, b3, b4])
    db_session.commit()

    @contextlib.contextmanager
    def test_session_factory() -> Iterator[Session]:
        yield db_session

    compute_popularity(session_factory=test_session_factory)

    stmt = select(BookPopularity).where(BookPopularity.scope == "global")
    pops = db_session.scalars(stmt).all()

    assert len(pops) == 1
    pop = pops[0]

    assert pop.book_ids == ["b2", "b1", "b4"]

    b5 = Book(id="b5", title="B5", source="s", ratings_count=300)
    db_session.add(b5)
    db_session.commit()

    compute_popularity(session_factory=test_session_factory)

    pops = db_session.scalars(stmt).all()
    assert len(pops) == 1
    assert pops[0].book_ids == ["b5", "b2", "b1", "b4"]
