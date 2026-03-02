"""Centralized application settings using pydantic-settings."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings managed via environment variables."""

    # Analysis Policy
    ANALYSIS_MODE: Literal["deterministic", "hybrid", "llm_only"] = "deterministic"
    ANALYSIS_TIMEOUT_MS: int = 0
    ANALYSIS_USE_CIRCUIT_BREAKER: bool = True
    ANALYSIS_ARTIFACTS_ENABLE: bool = False

    # LLM Settings
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = ""
    LLM_DISABLE: bool = False
    LLM_PIPELINE_MODE: str = "single"
    LLM_MAX_OUTPUT_TOKENS: int = 4096
    LLM_MAX_RETRIES: int = 2
    LLM_BASE_DELAY_SEC: int = 5
    LLM_HTTP_TIMEOUT_SEC: int = 45

    # Gemini Settings
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # GLM Settings
    GLM_API_KEY: str = ""
    GLM_MODEL: str = "glm-5"
    GLM_API_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"

    # Circuit Breaker Defaults
    LLM_CB_FAILURE_THRESHOLD: int = 3
    LLM_CB_OPEN_SEC: int = 120
    RAG_CB_FAILURE_THRESHOLD: int = 3
    RAG_CB_OPEN_SEC: int = 120

    # LLM Cost Simulation
    LLM_PRICE_INPUT_PER_1M: float = 0.075
    LLM_PRICE_OUTPUT_PER_1M: float = 0.30
    LLM_MONTHLY_REQUESTS: float = 1000.0
    LLM_TOKEN_ESTIMATE_CHAR_DIVISOR: float = 4.0

    # RAG Settings
    RAG_ENABLE: bool = True
    RAG_OFFLINE_ALLOW: bool = True
    RAG_WARMUP_ON_START: bool = False
    RAG_MAX_CONTEXT_CHARS: int = 6000

    # Ruleset / Calibration
    RULESET_DIR: str = "config/rulesets"
    RULESET_GENERATED_DIR: str | None = None
    RULESET_ALLOW_GENERATED: bool = False
    CALIBRATION_MIN_SAMPLES: int = 20
    CALIBRATION_WEIGHT_TCO: float = 0.7
    CALIBRATION_WEIGHT_RISK: float = 0.3

    # Sources
    SOURCE_VERIFY_MAX_AGE_DAYS: int = 90

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Global settings instance
settings = Settings()
