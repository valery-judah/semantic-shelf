from typing import Literal, NewType

BookId = NewType("BookId", str)
InternalUserId = NewType("InternalUserId", str)
ExternalIdpId = NewType("ExternalIdpId", str)
DatasetUserId = NewType("DatasetUserId", int)
Score = NewType("Score", float)
AlgoId = NewType("AlgoId", str)
RecsVersion = NewType("RecsVersion", str)
PopularityScope = Literal["global"]
