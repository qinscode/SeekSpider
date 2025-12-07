"""
API endpoints for managing API authentication tokens
"""
import secrets
from typing import List
from fastapi import APIRouter, HTTPException

from plombery.api.authentication import NeedsAuth
from plombery.database.schemas import ApiToken, ApiTokenCreate, ApiTokenWithSecret
from plombery.database.repository import (
    create_api_token,
    list_api_tokens,
    delete_api_token
)


router = APIRouter(prefix="/api-tokens", tags=["API Tokens"], dependencies=[NeedsAuth])


def generate_secure_token() -> str:
    """Generate a secure random API token."""
    return f"plb_{secrets.token_urlsafe(32)}"


@router.post("/", response_model=ApiTokenWithSecret)
def create_token(data: ApiTokenCreate) -> ApiTokenWithSecret:
    """
    Create a new API token for external API access.

    The token will be returned only once. Make sure to save it securely.
    """
    token = generate_secure_token()

    try:
        api_token = create_api_token(data, token)

        # Return the token with the secret (only this one time)
        return ApiTokenWithSecret(
            id=api_token.id,
            name=api_token.name,
            token=token,
            created_at=api_token.created_at,
            last_used_at=api_token.last_used_at,
            is_active=api_token.is_active
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create API token: {str(e)}")


@router.get("/", response_model=List[ApiToken])
def list_tokens() -> List[ApiToken]:
    """
    List all active API tokens.

    Note: The actual token values are not returned for security reasons.
    """
    try:
        return list_api_tokens()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list API tokens: {str(e)}")


@router.delete("/{token_id}")
def delete_token(token_id: int) -> dict:
    """
    Delete (deactivate) an API token.

    The token will be marked as inactive and can no longer be used for authentication.
    """
    try:
        success = delete_api_token(token_id)

        if not success:
            raise HTTPException(status_code=404, detail="API token not found")

        return {
            "success": True,
            "message": f"API token {token_id} has been deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete API token: {str(e)}")
