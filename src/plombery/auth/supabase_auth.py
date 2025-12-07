from typing import Optional
from supabase import create_client, Client
from plombery.config import settings


class SupabaseAuth:
    """Supabase authentication handler"""

    def __init__(self):
        if not settings.auth or not settings.auth.supabase_url or not settings.auth.supabase_key:
            raise ValueError("Supabase URL and Key must be configured in settings")

        self.client: Client = create_client(
            settings.auth.supabase_url,
            settings.auth.supabase_key.get_secret_value()
        )

    async def sign_in(self, email: str, password: str) -> Optional[dict]:
        """
        Sign in a user with email and password

        Args:
            email: User's email
            password: User's password

        Returns:
            User session data if successful, None otherwise
        """
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "name": response.user.user_metadata.get("name", response.user.email),
                    "access_token": response.session.access_token if response.session else None,
                }

            return None
        except Exception as e:
            print(f"Supabase sign in error: {e}")
            return None

    async def sign_out(self, access_token: str) -> bool:
        """
        Sign out a user

        Args:
            access_token: User's access token

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.auth.sign_out()
            return True
        except Exception as e:
            print(f"Supabase sign out error: {e}")
            return False

    async def get_user(self, access_token: str) -> Optional[dict]:
        """
        Get user information from access token

        Args:
            access_token: User's access token

        Returns:
            User data if token is valid, None otherwise
        """
        try:
            response = self.client.auth.get_user(access_token)

            if response.user:
                return {
                    "id": response.user.id,
                    "email": response.user.email,
                    "name": response.user.user_metadata.get("name", response.user.email),
                }

            return None
        except Exception as e:
            print(f"Supabase get user error: {e}")
            return None


def get_supabase_auth() -> Optional[SupabaseAuth]:
    """Get SupabaseAuth instance if configured"""
    if (settings.auth and
        settings.auth.supabase_url and
        settings.auth.supabase_key):
        return SupabaseAuth()
    return None
