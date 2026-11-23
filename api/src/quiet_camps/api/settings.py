from typing import Literal

from pydantic_settings import BaseSettings

from quiet_camps.db.config import LOCAL_URL


class Settings(BaseSettings):
    database_url: str = LOCAL_URL
    debug: bool = False
    experiments: bool = False
    # POST /ask reads plain words with Claude on Amazon Bedrock (ADR 0005). Off unless switched
    # on: it costs money and needs AWS credentials. AWS_PROFILE and AWS_REGION are the standard
    # AWS variables; with no profile, the usual AWS credential chain applies.
    ask_enabled: bool = False
    # Haiku 4.5 is open to every Bedrock account; Haiku 5.5 needs its terms accepted first,
    # then: ASK_MODEL=anthropic.claude-haiku-5-5 and ASK_EFFORT=low (4.5 rejects effort).
    ask_model: str = "anthropic.claude-haiku-4-5"
    ask_effort: Literal["low", "medium", "high"] | None = None
    aws_region: str = "ap-southeast-2"
    aws_profile: str | None = None
