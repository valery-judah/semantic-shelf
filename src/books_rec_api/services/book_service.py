import json
import logging
import time
from datetime import datetime

from books_rec_api.domain import AlgoId, BookId, RecsVersion
from books_rec_api.repositories.books_repository import BooksRepository
from books_rec_api.schemas.book import BookRead, PaginatedBooks
from books_rec_api.schemas.recommendation import SimilarBooksResponse

logger = logging.getLogger(__name__)


class BookService:
    def __init__(self, repo: BooksRepository) -> None:
        self.repo = repo

    def get_book(self, book_id: str) -> BookRead | None:
        book = self.repo.get_by_id(book_id)
        if not book:
            return None
        return BookRead.model_validate(book)

    def get_books(self, page: int = 1, size: int = 20, genre: str | None = None) -> PaginatedBooks:

        offset = (page - 1) * size
        items, total = self.repo.list_books(limit=size, offset=offset, genre=genre)

        return PaginatedBooks(
            items=[BookRead.model_validate(item) for item in items],
            total=total,
            page=page,
            size=size,
        )

    def get_similar_books(
        self, book_id: str, limit: int, trace_id: str
    ) -> SimilarBooksResponse | None:
        start_time = time.perf_counter()

        # 1. Validate book exists
        book = self.repo.get_by_id(book_id)
        if not book:
            return None

        # 2. Fetch similarities
        similarities = self.repo.get_similarities(book_id)
        neighbor_ids: list[str] = similarities.neighbor_ids if similarities else []
        algo_id = similarities.algo_id if similarities else None
        recs_version = similarities.recs_version if similarities else None

        # Filter out anchor book and duplicates
        seen = {book_id}
        filtered_neighbors = []
        if limit > 0:
            for nid in neighbor_ids:
                if nid not in seen:
                    seen.add(nid)
                    filtered_neighbors.append(nid)
                    if len(filtered_neighbors) >= limit:
                        break

        neighbors_count = len(filtered_neighbors)
        result_ids = filtered_neighbors.copy()

        # 3. Fallback to popularity if needed
        fallback_count = 0
        if len(result_ids) < limit:
            popularity = self.repo.get_popularity(scope="global")
            if popularity and popularity.book_ids:
                if not recs_version:
                    recs_version = popularity.recs_version
                for pid in popularity.book_ids:
                    if pid not in seen:
                        seen.add(pid)
                        result_ids.append(pid)
                        fallback_count += 1
                        if len(result_ids) >= limit:
                            break

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 4. Telemetry logging
        log_event = {
            "event_name": "similar_request",
            "ts": datetime.utcnow().isoformat() + "Z",
            "request_id": trace_id,
            "anchor_book_id": book_id,
            "limit": limit,
            "returned_count": len(result_ids),
            "neighbors_count": neighbors_count,
            "fallback_count": fallback_count,
            "latency_ms": latency_ms,
            "status_code": 200,
        }
        if algo_id:
            log_event["algo_id"] = algo_id
        if recs_version:
            log_event["recs_version"] = recs_version

        # Output telemetry event as JSON
        logger.info("TELEMETRY: %s", json.dumps(log_event))

        return SimilarBooksResponse(
            book_id=BookId(book_id),
            similar_book_ids=[BookId(nid) for nid in result_ids],
            trace_id=trace_id,
            algo_id=AlgoId(algo_id) if algo_id else None,
            recs_version=RecsVersion(recs_version) if recs_version else None,
        )
