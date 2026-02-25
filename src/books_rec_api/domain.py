import typing
from typing import Annotated, Literal

from pydantic import Field

if typing.TYPE_CHECKING:
    BookId = typing.NewType("BookId", str)
    InternalUserId = typing.NewType("InternalUserId", str)
    ExternalIdpId = typing.NewType("ExternalIdpId", str)
    DatasetUserId = typing.NewType("DatasetUserId", int)
    Score = typing.NewType("Score", float)
    AlgoId = typing.NewType("AlgoId", str)
    RecsVersion = typing.NewType("RecsVersion", str)
else:
    _BookIdStr = Annotated[str, Field(min_length=1, max_length=36)]
    BookId = typing.NewType("BookId", _BookIdStr)

    _InternalUserIdStr = Annotated[str, Field(pattern=r"^usr_[a-f0-9\-]+$")]
    InternalUserId = typing.NewType("InternalUserId", _InternalUserIdStr)

    _ExternalIdpIdStr = Annotated[str, Field(min_length=1)]
    ExternalIdpId = typing.NewType("ExternalIdpId", _ExternalIdpIdStr)

    DatasetUserId = typing.NewType("DatasetUserId", int)

    _ScoreFloat = Annotated[float, Field(ge=0.0, le=1.0)]
    Score = typing.NewType("Score", _ScoreFloat)

    _AlgoIdStr = Annotated[str, Field(min_length=1)]
    AlgoId = typing.NewType("AlgoId", _AlgoIdStr)

    _RecsVersionStr = Annotated[str, Field(min_length=1)]
    RecsVersion = typing.NewType("RecsVersion", _RecsVersionStr)

PopularityScope = Literal["global"]
