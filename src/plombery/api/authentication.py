from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Header
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from httpx import HTTPStatusError
from pydantic import BaseModel, HttpUrl
from starlette.middleware.sessions import SessionMiddleware
from typing import Optional

from plombery.auth.providers import get_provider_config
from plombery.auth.supabase_auth import get_supabase_auth
from plombery.config import settings


class LoginRequest(BaseModel):
    email: str
    password: str


def build_auth_router(app: FastAPI) -> APIRouter:
    router = APIRouter(
        prefix="/auth",
        tags=["Authentication"],
    )

    if not settings.auth:
        # If authentication is not enabled, register a
        # dummy endpoint to return an empty user

        @router.get("/whoami")
        async def get_current_user_no_auth(request: Request):
            return {
                "user": None,
                "is_authentication_enabled": False,
            }

        @router.get("/providers")
        async def get_providers_no_auth():
            return []

        @router.post("/login")
        async def login_no_auth():
            raise HTTPException(401, "Authentication is not enabled")

        return router

    app.add_middleware(
        SessionMiddleware, secret_key=settings.auth.secret_key.get_secret_value()
    )

    # Check if Supabase auth is configured
    supabase_auth = get_supabase_auth()

    if supabase_auth:
        # Supabase email/password authentication
        @router.post("/login")
        async def login_with_supabase(request: Request, login_data: LoginRequest):
            """Login with email and password using Supabase Auth"""
            user_data = await supabase_auth.sign_in(login_data.email, login_data.password)

            if not user_data:
                raise HTTPException(401, "Invalid email or password")

            # Store user in session
            request.session["user"] = {
                "email": user_data["email"],
                "name": user_data["name"],
            }

            # Store access token if needed for future requests
            if user_data.get("access_token"):
                request.session["access_token"] = user_data["access_token"]

            return {
                "user": request.session["user"],
                "message": "Login successful"
            }

        @router.get("/whoami")
        async def get_current_user_supabase(request: Request):
            user = request.session.get("user")

            return {
                "user": user,
                "is_authentication_enabled": True,
            }

        @router.post("/logout")
        async def logout_supabase(request: Request):
            access_token = request.session.get("access_token")
            if access_token:
                await supabase_auth.sign_out(access_token)

            request.session.pop("user", None)
            request.session.pop("access_token", None)

            return {"message": "Logout successful"}

        @router.get("/providers")
        async def get_providers_supabase():
            return [
                {
                    "id": "supabase",
                    "name": "Email/Password",
                    "type": "credentials"
                }
            ]

        return router

    if settings.auth.provider:
        provider_config = get_provider_config(settings.auth.provider)

        if not provider_config:
            raise ValueError(
                f"Unsupported authentication provider: {settings.auth.provider}"
            )

        settings.auth.server_metadata_url = HttpUrl(provider_config.get("metadata_url"))
        settings.auth.client_kwargs = provider_config.get("client_kwargs")

    # Explicitly convert the URL objects to str as from Pydantic v2 they're not converted automatically
    # and Authlib complains
    server_metadata_url = (
        str(settings.auth.server_metadata_url)
        if settings.auth.server_metadata_url
        else None
    )
    access_token_url = (
        str(settings.auth.access_token_url) if settings.auth.access_token_url else None
    )
    authorize_url = (
        str(settings.auth.authorize_url) if settings.auth.authorize_url else None
    )
    jwks_uri = str(settings.auth.jwks_uri) if settings.auth.jwks_uri else None

    oauth = OAuth()
    oauth.register(
        name="default",
        client_id=settings.auth.client_id.get_secret_value(),
        client_secret=settings.auth.client_secret.get_secret_value(),
        server_metadata_url=server_metadata_url,
        access_token_url=access_token_url,
        authorize_url=authorize_url,
        jwks_uri=jwks_uri,
        client_kwargs=settings.auth.client_kwargs,
    )

    if not oauth.default:
        raise ValueError("Error registering OAuth client")

    oauth_client: StarletteOAuth2App = oauth.default

    @router.get("/login")
    async def login(request: Request):
        redirect_uri = request.url_for("auth_redirect")

        try:
            return await oauth_client.authorize_redirect(request, redirect_uri)
        except HTTPStatusError as e:
            print(f"Unable to authenticate. Error: {e}")
            raise HTTPException(401, "Unable to authenticate") from e

    @router.post("/logout")
    async def logout(request: Request):
        request.session.pop("user", None)

    @router.get("/whoami")
    async def get_current_user(request: Request):
        user = request.session.get("user")

        return {
            "user": user,
            "is_authentication_enabled": True,
        }

    @router.get("/providers")
    async def get_providers():
        if not settings.auth:
            return []

        return [
            {
                "id": settings.auth.provider,
                "name": provider_config.get("name"),
                "redirect_url": "/api/auth/redirect",
            }
        ]

    @router.get("/redirect")
    async def auth_redirect(request: Request):
        try:
            token: dict = await oauth_client.authorize_access_token(request)
        except Exception as e:
            print(f"Unable to authenticate. Error: {e}")
            raise HTTPException(401, "Unable to authenticate") from e

        user = token.get("userinfo")

        if not user:
            raise HTTPException(401, "Unable to authenticate. Error: No user info")

        request.session["user"] = dict(user)

        return RedirectResponse(url=str(settings.frontend_url))

    return router


async def _needs_auth(request: Request):
    if not settings.auth:
        return None

    user = request.session.get("user")

    if not user:
        raise HTTPException(401, "You must be authenticated to access this API route")

    return user


NeedsAuth = Depends(_needs_auth)


# API Token Authentication
security = HTTPBearer(auto_error=False)


async def _api_token_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    authorization: Optional[str] = Header(None)
) -> dict:
    """
    Authentication dependency for external API access.
    Supports Supabase Bearer token authentication.

    For API access, use: Authorization: Bearer <your-supabase-access-token>
    """
    # Extract token from Authorization header
    token = None

    if credentials:
        token = credentials.credentials
    elif authorization and authorization.startswith("Bearer "):
        token = authorization[7:]  # Remove "Bearer " prefix

    if token:
        # Validate Supabase token
        supabase_auth = get_supabase_auth()
        if supabase_auth:
            user_data = await supabase_auth.get_user(token)
            if user_data:
                return {
                    "type": "supabase_token",
                    "user": user_data
                }

        raise HTTPException(401, "Invalid authentication token")

    # No token provided
    raise HTTPException(401, "Authentication required. Provide a Bearer token in the Authorization header.")


NeedsApiTokenAuth = Depends(_api_token_auth)
