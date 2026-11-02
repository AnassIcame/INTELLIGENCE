"""Authentification par clé API, transmise dans l'en-tête X-API-Key."""
import secrets

from fastapi import Header, HTTPException, status

from maintai.config import get_settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Refuse la requête si la clé est absente ou fausse."""
    configured_key = get_settings().api_key
    if configured_key is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured on server",
        )
    if x_api_key is None or not secrets.compare_digest(x_api_key, configured_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
