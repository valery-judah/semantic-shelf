from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class TelemetryEventBase(BaseModel):
    ts: datetime = Field(description="Timestamp of the event in UTC")
    request_id: str = Field(description="Join key, matching the trace_id from the API")
    anchor_book_id: str = Field(description="The ID of the anchor book")
    algo_id: str = Field(description="The algorithm identifier used")
    recs_version: str = Field(description="The recommendation artifacts version")
    experiment_id: str | None = Field(default=None, description="The experiment identifier")
    variant_id: str | None = Field(default=None, description="The assigned variant identifier")
    bucket_key_hash: str | None = Field(
        default=None, description="Pseudonymous hash of the assignment key"
    )


class SimilarImpressionEvent(TelemetryEventBase):
    event_name: Literal["similar_impression"]
    surface: str = Field(description="The UI surface where recommendations were shown")
    shown_book_ids: list[str] = Field(description="List of book IDs shown to the user")
    positions: list[int] = Field(description="Positions of the shown books (0-indexed)")
    client_platform: str | None = Field(default=None, description="e.g., ios, android, web")
    app_version: str | None = Field(default=None, description="e.g., 1.12.0")

    @model_validator(mode="after")
    def validate_positions(self) -> "SimilarImpressionEvent":
        if len(self.shown_book_ids) != len(self.positions):
            raise ValueError("Length of shown_book_ids must match length of positions")
        if any(p < 0 for p in self.positions):
            raise ValueError("Positions must be non-negative integers")
        return self


class SimilarClickEvent(TelemetryEventBase):
    event_name: Literal["similar_click"]
    clicked_book_id: str = Field(description="The ID of the book that was clicked")
    position: int = Field(description="Position of the clicked book (0-indexed)", ge=0)


class SimilarShelfAddEvent(TelemetryEventBase):
    event_name: Literal["similar_shelf_add"]
    book_id: str = Field(description="The ID of the book added to shelf")


class SimilarReadingStartEvent(TelemetryEventBase):
    event_name: Literal["similar_reading_start"]
    book_id: str = Field(description="The ID of the book started")


class SimilarReadingFinishEvent(TelemetryEventBase):
    event_name: Literal["similar_reading_finish"]
    book_id: str = Field(description="The ID of the book finished")


class SimilarRatingEvent(TelemetryEventBase):
    event_name: Literal["similar_rating"]
    book_id: str = Field(description="The ID of the book rated")
    rating_value: int = Field(description="The rating given (1-5)", ge=1, le=5)


TelemetryEvent = Annotated[
    SimilarImpressionEvent
    | SimilarClickEvent
    | SimilarShelfAddEvent
    | SimilarReadingStartEvent
    | SimilarReadingFinishEvent
    | SimilarRatingEvent,
    Field(discriminator="event_name"),
]


class EventBatchRequest(BaseModel):
    events: list[TelemetryEvent] = Field(description="A batch of telemetry events to ingest")
