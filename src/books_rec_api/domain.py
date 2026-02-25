from typing import Annotated, Literal, NewType

from pydantic import Field

_BookIdStr = Annotated[str, Field(min_length=1, max_length=36)]
BookId = NewType("BookId", _BookIdStr)

_InternalUserIdStr = Annotated[str, Field(pattern=r"^usr_[a-f0-9\-]+$")]
InternalUserId = NewType("InternalUserId", _InternalUserIdStr)

_ExternalIdpIdStr = Annotated[str, Field(min_length=1)]
ExternalIdpId = NewType("ExternalIdpId", _ExternalIdpIdStr)

DatasetUserId = NewType("DatasetUserId", int)

_ScoreFloat = Annotated[float, Field(ge=0.0, le=1.0)]
Score = NewType("Score", _ScoreFloat)

_AlgoIdStr = Annotated[str, Field(min_length=1)]
AlgoId = NewType("AlgoId", _AlgoIdStr)

_RecsVersionStr = Annotated[str, Field(min_length=1)]
RecsVersion = NewType("RecsVersion", _RecsVersionStr)

PopularityScope = Literal["global"]
