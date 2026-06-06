from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    sec_api_key: str
    mongodb_uri: str
    tls_allow_invalid_certs: bool
    openai_api_key: str  # Required only for the research agent; pipeline scripts work without it

    @classmethod
    def from_env(cls) -> "Settings":
        sec_key = os.environ.get("SEC_API_KEY")
        uri = os.environ.get("MONGODB_URI")
        if not sec_key or not uri:
            raise EnvironmentError(
                "Required environment variables SEC_API_KEY and MONGODB_URI must be set. "
                "See .env.example for configuration."
            )
        return cls(
            sec_api_key=sec_key,
            mongodb_uri=uri,
            tls_allow_invalid_certs=(
                os.environ.get("MONGODB_TLS_ALLOW_INVALID_CERTS", "false").lower() == "true"
            ),
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        )


settings = Settings.from_env()
