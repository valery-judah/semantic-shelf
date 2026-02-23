from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from books_rec_api.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    external_idp_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    domain_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
