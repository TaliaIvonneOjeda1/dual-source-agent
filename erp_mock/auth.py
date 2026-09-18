from fastapi import Header, HTTPException

EXPECTED = "Bearer demo-token"


def require_token(authorization: str | None = Header(default=None)) -> None:
    if authorization != EXPECTED:
        raise HTTPException(
            status_code=401,
            detail="token inválido o ausente; usá Authorization: Bearer demo-token",
        )
