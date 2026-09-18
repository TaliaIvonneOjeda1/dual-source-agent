from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)
EXPECTED = "demo-token"


def require_token(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> None:
    token = creds.credentials if creds is not None else None
    if token != EXPECTED:
        raise HTTPException(
            status_code=401,
            detail="token inválido o ausente; usá Authorization: Bearer demo-token",
        )
