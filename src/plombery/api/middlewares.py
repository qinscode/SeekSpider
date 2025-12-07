from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from plombery.config import settings


_FRONTEND_FOLDER = Path(__file__).parent.parent / "static"


class SPAStaticFiles(StaticFiles):
    def __init__(self, api_prefix: str) -> None:
        super().__init__(directory=_FRONTEND_FOLDER, html=True)
        self.api_prefix = api_prefix.lstrip("/")

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as ex:
            if not path.startswith(self.api_prefix) and ex.status_code == 404:
                return await super().get_response("index.html", scope)
            else:
                raise ex


def setup_cors(app: FastAPI):
    import logging
    logger = logging.getLogger(__name__)

    origins: List[str] = []
    allow_credentials = True

    if settings.allowed_origins == "*":
        # When allowed_origins is *, allow common development origins
        # because credentials cannot be used with wildcard origins
        # Allow both the configured frontend_url and common dev server ports
        origins = [
            "http://localhost:5173",  # Vite dev server default
            "http://localhost:3000",  # React/Next.js dev server default
            "http://localhost:8000",  # Backend/production default
        ]
        logger.info(f"CORS: Using development origins (wildcard detected): {origins}")
    else:
        origins = [
            # Origins must not contain any path, not even a trailing /
            f"{origin.scheme}://{origin.host}{(':' + str(origin.port)) if origin.port else ''}"
            for origin in settings.allowed_origins
        ]
        logger.info(f"CORS: Using configured origins: {origins}")

    # Don't use * in any header when Allow-Credentials is True
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["HEAD", "GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
    )

    logger.info(f"CORS middleware configured with allow_credentials={allow_credentials}")
