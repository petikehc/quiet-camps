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
    # runtime: Converse on bedrock-runtime, which every Bedrock account has; the au. profile
    # keeps the words in Australia. mantle: the Messages API, which AWS opens per account and
    # region; there ASK_MODEL=anthropic.claude-haiku-4-5 (ASK_EFFORT=low for Haiku 5.5).
    ask_endpoint: Literal["runtime", "mantle"] = "runtime"
    ask_model: str = "au.anthropic.claude-haiku-4-5-20251001-v1:0"
    ask_effort: Literal["low", "medium", "high"] | None = None  # mantle only
    aws_region: str = "ap-southeast-2"
    aws_profile: str | None = None
    # Behind CloudFront (ADR 0006): turn away requests without CloudFront's secret header, and
    # count /ask per viewer by the address in this header, not the connection's.
    origin_secret: str | None = None
    client_ip_header: str | None = None
