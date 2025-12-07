from pathlib import Path
from typing import Any, List, Literal, Optional, Tuple, Type, Union

from pydantic import AnyHttpUrl, BaseModel, Field, HttpUrl, SecretStr
from pydantic_core import Url
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource

from plombery.config.parser import SettingsFileSource
from plombery.schemas import NotificationRule

BASE_SETTINGS_FOLDER = Path()


class AuthSettings(BaseModel):
    client_id: Optional[SecretStr] = None
    client_secret: Optional[SecretStr] = None
    provider: Optional[str] = None
    server_metadata_url: Optional[HttpUrl] = None
    access_token_url: Optional[HttpUrl] = None
    authorize_url: Optional[HttpUrl] = None
    jwks_uri: Optional[HttpUrl] = None
    client_kwargs: Optional[Any] = None
    secret_key: SecretStr = SecretStr("not-very-secret-string")
    microsoft_tenant_id: Optional[str] = None
    # Supabase Auth settings
    supabase_url: Optional[str] = None
    supabase_key: Optional[SecretStr] = None


class Settings(BaseSettings):
    auth: Optional[AuthSettings] = None
    allowed_origins: Union[List[AnyHttpUrl], Literal["*"]] = "*"
    data_path: Path = Field(default_factory=Path.cwd)
    database_url: str = "sqlite:///./plombery.db"
    database_auth_token: Optional[str] = None
    frontend_url: AnyHttpUrl = Url("http://localhost:8000")
    notifications: Optional[List[NotificationRule]] = None

    model_config = SettingsConfigDict(
        env_file=BASE_SETTINGS_FOLDER / ".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            file_secret_settings,
            SettingsFileSource(settings_cls),
        )
