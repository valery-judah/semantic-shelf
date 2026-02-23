from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-User-Id", auto_error=False)


def get_external_idp_id(
    api_key: Annotated[str | None, Depends(api_key_header)] = None,
) -> str:
    if not api_key or not api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-Id header",
        )
    return api_key.strip()
