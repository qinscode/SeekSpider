"""
API endpoints for managing SingleSource API tokens (database-only storage)
"""
import os
import json
import subprocess
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from plombery.api.authentication import NeedsAuth
from plombery.database.base import SessionLocal

router = APIRouter(prefix="/tokens", tags=["Tokens"], dependencies=[NeedsAuth])

# Path to the token generation script
# __file__ is /path/to/plombery/src/plombery/api/routers/tokens.py
# We need to go up 5 levels to get to project root
SCRIPT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
    "scraper",
    "flow_meter_scraper"
)
TOKEN_SCRIPT = os.path.join(SCRIPT_DIR, "generate_client_tokens.py")


class BaseTokenRequest(BaseModel):
    base_token: str


class TokenResponse(BaseModel):
    success: bool
    message: str
    tokens_generated: Optional[int] = None


@router.get("/base")
def get_base_token() -> dict:
    """Get the current base token from database only."""
    try:
        # Get from database only (no file fallback)
        with SessionLocal() as db:
            result = db.execute(
                text("SELECT value FROM api_tokens WHERE key = 'base_token' LIMIT 1")
            ).fetchone()

            if result:
                return {"base_token": result[0]}
            else:
                return {"base_token": ""}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read base token: {str(e)}")


@router.post("/base")
def update_base_token(request: BaseTokenRequest) -> dict:
    """Update the base token in database only."""
    try:
        # Save to database only (no script file update)
        with SessionLocal() as db:
            # Use upsert (INSERT ... ON CONFLICT DO UPDATE)
            db.execute(
                text("""
                    INSERT INTO api_tokens (key, value, updated_at)
                    VALUES ('base_token', :value, NOW())
                    ON CONFLICT (key)
                    DO UPDATE SET value = :value, updated_at = NOW()
                """),
                {"value": request.base_token}
            )
            db.commit()

        return {
            "success": True,
            "message": "Base token updated successfully in database"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update base token: {str(e)}")


@router.post("/generate")
def generate_client_tokens(request: Optional[BaseTokenRequest] = None) -> TokenResponse:
    """
    Generate client tokens using the base token.
    The script will automatically save tokens to database.
    If base_token is provided, it will be used; otherwise, use from database/env.
    """
    try:
        # Build the command
        cmd = ["python3", TOKEN_SCRIPT]

        if request and request.base_token:
            cmd.append(request.base_token)

        # Run the script (it will save to database automatically)
        result = subprocess.run(
            cmd,
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Check if successful
        if result.returncode != 0:
            return TokenResponse(
                success=False,
                message=f"Failed to generate tokens: {result.stderr}",
                tokens_generated=0
            )

        # Parse the output to count successful tokens
        import re
        success_match = re.search(r'Successfully generated (\d+)/(\d+)', result.stderr)
        tokens_generated = int(success_match.group(1)) if success_match else 0

        # The script already saved tokens to database, so we don't need to do it again

        return TokenResponse(
            success=True,
            message=f"Successfully generated {tokens_generated} client tokens",
            tokens_generated=tokens_generated
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Token generation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate tokens: {str(e)}")


@router.get("/client")
def get_client_tokens() -> dict:
    """Get the client tokens from database only."""
    try:
        # Get from database only (no file fallback)
        with SessionLocal() as db:
            result = db.execute(
                text("SELECT key, value, updated_at FROM api_tokens WHERE key LIKE 'client_token_%'")
            ).fetchall()

            if not result:
                # No tokens in database - return empty
                return {"tokens": {}, "timestamp": None}

            tokens = {}
            latest_timestamp = None

            for row in result:
                key = row[0]
                value = row[1]
                updated_at = row[2]

                # Extract site name from key (client_token_SiteName -> SiteName)
                site_name = key.replace("client_token_", "")

                # Parse the stored value
                try:
                    token_data = json.loads(value)
                    tokens[site_name] = token_data
                except json.JSONDecodeError:
                    # If it's a plain string (just the token), wrap it
                    tokens[site_name] = {"token": value}

                # Track latest timestamp
                if latest_timestamp is None or updated_at > latest_timestamp:
                    latest_timestamp = updated_at

            timestamp_str = latest_timestamp.strftime("%Y-%m-%d %H:%M:%S") if latest_timestamp else None

            return {
                "tokens": tokens,
                "timestamp": timestamp_str
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read client tokens: {str(e)}")
