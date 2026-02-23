from fastapi import HTTPException, Request, status


def get_external_idp_id(request: Request) -> str:
    external_idp_id = request.headers.get("X-User-Id", "").strip()
    if not external_idp_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or empty X-User-Id header",
        )
    return external_idp_id
