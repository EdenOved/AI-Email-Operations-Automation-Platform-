from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ENV = _ROOT / "backend" / ".env"
_ROOT_ENV = _ROOT / ".env"
_ENV_FILE = _BACKEND_ENV if _BACKEND_ENV.exists() else _ROOT_ENV if _ROOT_ENV.exists() else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE) if _ENV_FILE else None, extra="ignore")

    environment: str = Field(default="local", validation_alias="ENVIRONMENT")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/email_ops_clean",
        validation_alias="DATABASE_URL",
    )

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    routing_hitl_confidence_threshold: float = Field(
        default=0.48, ge=0.0, le=1.0, validation_alias="ROUTING_HITL_CONFIDENCE_THRESHOLD"
    )
    roi_assumed_minutes_per_auto_case: float = Field(
        default=5.0, ge=0.5, le=120.0, validation_alias="ROI_ASSUMED_MINUTES_PER_AUTO_CASE"
    )

    gmail_client_id: str | None = Field(default=None, validation_alias="GMAIL_CLIENT_ID")
    gmail_client_secret: str | None = Field(default=None, validation_alias="GMAIL_CLIENT_SECRET")
    gmail_refresh_token: str | None = Field(default=None, validation_alias="GMAIL_REFRESH_TOKEN")
    gmail_user_id: str = Field(default="me", validation_alias="GMAIL_USER_ID")
    gmail_poll_query: str = Field(default="in:inbox is:unread -category:promotions", validation_alias="GMAIL_POLL_QUERY")
    gmail_poll_interval_seconds: int = Field(default=20, validation_alias="GMAIL_POLL_INTERVAL_SECONDS")
    gmail_max_messages_per_poll: int = Field(default=5, validation_alias="GMAIL_MAX_MESSAGES_PER_POLL")
    gmail_mark_as_read_after_ingest: bool = Field(default=True, validation_alias="GMAIL_MARK_AS_READ_AFTER_INGEST")
    gmail_ingest_watermark_enabled: bool = Field(default=True, validation_alias="GMAIL_INGEST_WATERMARK_ENABLED")
    gmail_reset_ingest_watermark: bool = Field(default=False, validation_alias="GMAIL_RESET_INGEST_WATERMARK")
    gmail_ingest_max_internal_age_seconds: int = Field(default=0, validation_alias="GMAIL_INGEST_MAX_INTERNAL_AGE_SECONDS")
    email_ingest_enabled: bool = Field(default=True, validation_alias="EMAIL_INGEST_ENABLED")

    hubspot_access_token: str | None = Field(default=None, validation_alias="HUBSPOT_ACCESS_TOKEN")
    hubspot_portal_id: str | None = Field(default=None, validation_alias="HUBSPOT_PORTAL_ID")
    hubspot_pipeline: str | None = Field(default=None, validation_alias="HUBSPOT_PIPELINE")
    hubspot_pipeline_stage: str | None = Field(default=None, validation_alias="HUBSPOT_PIPELINE_STAGE")

    jira_base_url: str | None = Field(default=None, validation_alias="JIRA_BASE_URL")
    jira_email: str | None = Field(default=None, validation_alias="JIRA_EMAIL")
    jira_api_token: str | None = Field(default=None, validation_alias="JIRA_API_TOKEN")
    jira_project_key: str = Field(default="DEMO", validation_alias="JIRA_PROJECT_KEY")
    jira_issue_type: str = Field(default="Task", validation_alias="JIRA_ISSUE_TYPE")

    internal_api_key: str | None = Field(default="dev-internal", validation_alias="INTERNAL_API_KEY")
    admin_api_key: str | None = Field(default="dev-admin", validation_alias="ADMIN_API_KEY")


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings()
    return _SETTINGS
